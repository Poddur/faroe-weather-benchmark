"""Research pilot: exact-run historical forecasts and chronological out-of-sample MOS.
No BigQuery, no live service, no claim of operational publication timing.
"""
import json,time,hashlib
from pathlib import Path
import numpy as np
import pandas as pd
import requests
from historical_weathernext_benchmark import collect_observations
from probe_weathernext_dynamical import PRODUCT,STATIONS,forecast_rows

MODELS=["ECMWF_9km","HARMONIE_DINI_OM","WeatherNext3"]
IDS=["ecmwf_ifs","dmi_harmonie_arome_europe"]
LEADS=[6,12,24]
# Fixed weekly sample, no selection by forecast performance.
ISSUES=pd.date_range("2026-04-02","2026-11-12",freq="7D",tz="UTC")
URL="https://single-runs-api.open-meteo.com/v1/forecast"

def om_rows(issue,raw,cache):
    rows=[]
    for sid,s in STATIONS.items():
        params=dict(latitude=s["lat"],longitude=s["lon"],run=issue.strftime("%Y-%m-%dT%H:%M"),
                    models=",".join(IDS),hourly="temperature_2m,wind_speed_10m",
                    wind_speed_unit="ms",timezone="GMT",forecast_days=2,cell_selection="nearest",elevation="nan")
        path=cache/(issue.strftime("%Y%m%d")+"_"+sid+".json")
        if path.exists():
            item=json.loads(path.read_text())
            j=item["response"]
        else:
            for attempt in range(3):
                try:
                    response=requests.get(URL,params=params,timeout=(15,120))
                    response.raise_for_status()
                    j=response.json()
                    item={"url":response.url,"response":j}
                    break
                except (requests.Timeout,requests.ConnectionError):
                    if attempt==2:raise
                    time.sleep(5*(attempt+1))
        raw.append(item)
        h=j["hourly"];units=j["hourly_units"]
        for model,mid in zip(MODELS,IDS):
            for lead in LEADS:
                valid=issue+pd.Timedelta(hours=lead)
                idx=h["time"].index(valid.strftime("%Y-%m-%dT%H:%M"))
                for var,unit in [("temperature_2m","C"),("wind_speed_10m","m/s")]:
                    key=var+"_"+mid
                    if units[key] not in (("°C","C") if unit=="C" else ("m/s","ms")):raise ValueError("Unexpected units "+key)
                    value=h[key][idx]
                    if value is None or not np.isfinite(value):raise ValueError("No model coverage: "+key+" "+sid)
                    rows.append(dict(model=model,station_id=sid,variable=var,unit=unit,init_time=issue,valid_time=valid,lead_hours=lead,value=value))
        path.write_text(json.dumps(item))
        time.sleep(2)
    return rows

def backtest(f,o):
    keys=["station_id","variable","init_time","valid_time","lead_hours"]
    f=f.copy();o=o.copy()
    for c in ["init_time","valid_time"]:f[c]=pd.to_datetime(f[c],utc=True)
    o["valid_time"]=pd.to_datetime(o.valid_time,utc=True)
    if f.duplicated(keys+["model"]).any():raise ValueError("Duplicate forecasts")
    if not ((f.valid_time-f.init_time)==pd.to_timedelta(f.lead_hours,unit="h")).all():raise ValueError("Invalid forecast lead")
    w=f.pivot(index=keys,columns="model",values="value").reset_index()
    w=w.merge(o[["station_id","variable","valid_time","observed"]],on=["station_id","variable","valid_time"],validate="many_to_one")
    w=w.dropna(subset=MODELS+["observed"])
    dates=sorted(w.init_time.unique())
    if len(dates)<20:raise ValueError("Fewer than 20 complete issue dates")
    # First 60% training; remaining 40% held out. No tuning on holdout.
    split=dates[int(len(dates)*0.6)]
    train=w[(w.init_time<split)&(w.valid_time<split-pd.Timedelta(hours=6))]
    test=w[w.init_time>=split].copy()
    if train.empty or test.empty:raise ValueError("Invalid time split")
    test["FWA1"]=test[MODELS].mean(axis=1)
    test["FWA2"]=np.nan;test["FWA3"]=np.nan
    weights=[]
    # Conservative inverse-MAE model weights, learned on training only.
    for group,g in train.groupby(["station_id","variable","lead_hours"]):
        if len(g)<8:continue
        error=g[MODELS].subtract(g.observed,axis=0)
        bias=error.mean()
        corrected=error-bias
        mae=corrected.abs().mean()
        inv=1/np.maximum(mae,0.1);weight=inv/inv.sum()
        mask=(test.station_id==group[0])&(test.variable==group[1])&(test.lead_hours==group[2])
        x=test.loc[mask,MODELS]-bias
        test.loc[mask,"FWA2"]=x.mean(axis=1)
        test.loc[mask,"FWA3"]=x.mul(weight).sum(axis=1)
        weights.append(dict(station_id=group[0],variable=group[1],lead_hours=int(group[2]),training_n=len(g),bias=bias.to_dict(),weights=weight.to_dict()))
    methods=MODELS+["FWA1","FWA2","FWA3"]
    test=test.dropna(subset=methods)
    if test.empty:raise ValueError("No eligible held-out groups")
    scores=[]
    for (var,lead),g in test.groupby(["variable","lead_hours"]):
        for m in methods:
            e=g[m]-g.observed
            scores.append(dict(variable=var,lead_hours=int(lead),model=m,n=len(e),mae=float(e.abs().mean()),rmse=float(np.sqrt((e**2).mean())),bias=float(e.mean())))
    return test,scores,weights,{"split_utc":str(split),"train_dates":int(train.init_time.nunique()),"test_dates":int(test.init_time.nunique()),"test_cases":len(test)}

def main():
    out=Path("outputs/fwa-pilot");out.mkdir(parents=True,exist_ok=True)
    status={"status":"failed","requested_issues":len(ISSUES),"missing":[],"bigquery_queries":0}
    cache=Path("fwa-cache");cache.mkdir(exist_ok=True)
    raw=[];rows=[];issues=[]
    try:
        import dynamical_catalog
        ds=dynamical_catalog.open(PRODUCT,chunks=None)
        try:
            if "degree_Celsius" not in ds.temperature_2m.attrs.get("units","") or ds.wind_speed_10m.attrs.get("units") not in ("m s-1","m/s"):raise ValueError("WeatherNext unit mismatch")
            for issue in ISSUES:
                try:
                    segment=om_rows(issue,raw,cache)
                    for lead in LEADS:segment.extend(forecast_rows(ds,issue,lead))
                    if len(segment)!=54:raise ValueError("Incomplete dataset")
                    rows.extend(segment);issues.append(issue)
                    print("Complete issue",issue,flush=True)
                except (requests.RequestException,KeyError,ValueError,RuntimeError) as e:
                    status["missing"].append({"issue":str(issue),"reason":str(e)[:400]})
                    print("Missing issue",issue,str(e)[:400],flush=True)
                    if not issues and len(status["missing"])>=3:raise RuntimeError("Initial access probe failed; no further calls")
        finally:ds.close()
        status["complete_issues"]=len(issues)
        pd.DataFrame(rows).to_csv(out/"forecasts.csv",index=False)
        if len(issues)<20:raise ValueError("Insufficient common issues")
        # Existing helper expects at most a few weeks per batch; each date is exact.
        obs=[];features=[];requests_info=[]
        for i in range(0,len(issues),8):
            o,r,q=collect_observations(issues[i:i+8],LEADS)
            obs.append(o);features.extend(r);requests_info.extend(q)
        f=pd.DataFrame(rows);o=pd.concat(obs,ignore_index=True)
        f.to_csv(out/"forecasts.csv",index=False);o.to_csv(out/"observations.csv",index=False)
        (out/"dmi_raw.json").write_text(json.dumps(features,default=str))
        test,scores,weights,split=backtest(f,o)
        test.to_csv(out/"heldout.csv",index=False)
        pd.DataFrame(scores).to_csv(out/"scores.csv",index=False)
        (out/"weights.json").write_text(json.dumps(weights,indent=2))
        status.update(status="exploratory_success",**split,scores=scores,forecast_rows=len(f),observation_rows=len(o))
    except Exception as e:
        status["error"]=str(e);raise
    finally:
        (out/"open_meteo_raw.json").write_text(json.dumps(raw,default=str))
        (out/"status.json").write_text(json.dumps(status,indent=2,default=str))
if __name__=="__main__":main()
