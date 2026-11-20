"""Frozen FWA2 validation; separate directional wind experiment."""
import json,hashlib
from pathlib import Path
import pandas as pd
import numpy as np
from fwa_historical_pilot import MODELS,ISSUES,LEADS,om_rows,URL
from historical_weathernext_benchmark import collect_observations
from probe_weathernext_dynamical import PRODUCT,STATIONS,forecast_rows
import requests
from sklearn.linear_model import Ridge
from sklearn.pipeline import make_pipeline
from sklearn.preprocessing import StandardScaler

NEW=sorted(list(pd.date_range("2026-08-22","2026-11-17",freq="W-SAT",tz="UTC"))+list(pd.date_range("2026-08-25","2026-11-17",freq="W-TUE",tz="UTC")))
KEY=["station_id","variable","init_time","valid_time","lead_hours"]
def wide(f,o):
    for c in ("init_time","valid_time"):f[c]=pd.to_datetime(f[c],utc=True,format="ISO8601")
    o["valid_time"]=pd.to_datetime(o.valid_time,utc=True,format="ISO8601")
    if f.duplicated(KEY+["model"]).any():raise ValueError("duplicate forecasts")
    if not ((f.valid_time-f.init_time)==pd.to_timedelta(f.lead_hours,unit="h")).all():raise ValueError("lead mismatch")
    return f.pivot(index=KEY,columns="model",values="value").reset_index().merge(o[["station_id","variable","valid_time","observed"]],on=["station_id","variable","valid_time"],validate="many_to_one").dropna(subset=MODELS+["observed"])
def frozen(w,weights):
    b=pd.DataFrame([{"station_id":x["station_id"],"variable":x["variable"],"lead_hours":x["lead_hours"],**{"bias_"+m:x["bias"][m] for m in MODELS}} for x in weights])
    w=w.merge(b,on=["station_id","variable","lead_hours"],validate="many_to_one",how="left")
    if w[["bias_"+m for m in MODELS]].isna().any().any():raise ValueError("missing frozen coefficients")
    w["FWA2"]=sum(w[m]-w["bias_"+m] for m in MODELS)/3
    return w
def scores(w,methods):
    out=[]
    for (v,l),g in w.assign(group=0).groupby(["variable","group"]):
        for m in methods:
            e=g[m]-g.observed
            out.append(dict(variable=v,model=m,n=len(e),mae=float(e.abs().mean()),rmse=float(np.sqrt((e**2).mean())),bias=float(e.mean())))
    return out
def intervals(w,candidate,base):
    d=w.assign(delta=(w[candidate]-w.observed).abs()-(w[base]-w.observed).abs())
    blocks=[g.delta.to_numpy() for _,g in d.groupby(d.init_time.dt.strftime("%G-%V"))]
    if len(blocks)<8:return None
    rng=np.random.default_rng(20261119)
    draws=[np.concatenate([blocks[i] for i in rng.integers(len(blocks),size=len(blocks))]).mean() for _ in range(2000)]
    return dict(candidate=candidate,baseline=base,delta=float(d.delta.mean()),weeks=len(blocks),ci95=list(map(float,np.percentile(draws,[2.5,97.5]))))
def directions(w,cache):
    rows=[]
    for issue in sorted(w.init_time.unique()):
        for sid,st in STATIONS.items():
            p=cache/(pd.Timestamp(issue).strftime("%Y%m%d")+"_"+sid+".json")
            try:
                if p.exists():j=json.loads(p.read_text())
                else:
                    resp=requests.get(URL,params=dict(latitude=st["lat"],longitude=st["lon"],run=pd.Timestamp(issue).strftime("%Y-%m-%dT%H:%M"),models="dmi_harmonie_arome_europe",hourly="wind_direction_10m",timezone="GMT",forecast_days=2,cell_selection="nearest",elevation="nan"),timeout=(15,90))
                    resp.raise_for_status();j=resp.json()
                h=j["hourly"]
                if j["hourly_units"]["wind_direction_10m"]!="°":raise ValueError("direction unit")
                segment=[]
                for lead in LEADS:
                    v=pd.Timestamp(issue)+pd.Timedelta(hours=lead)
                    a=float(h["wind_direction_10m"][h["time"].index(v.strftime("%Y-%m-%dT%H:%M"))])
                    if not 0<=a<=360:raise ValueError("invalid bearing")
                    segment.append(dict(station_id=sid,init_time=issue,lead_hours=lead,sin=np.sin(np.radians(a)),cos=np.cos(np.radians(a))))
                rows.extend(segment);p.write_text(json.dumps(j))
            except (requests.RequestException,ValueError,KeyError,TypeError) as e:print("Direction unavailable",issue,sid,str(e)[:180],flush=True)
    return pd.DataFrame(rows,columns=["station_id","init_time","lead_hours","sin","cos"])
def main():
    out=Path("outputs/confirmatory");out.mkdir(parents=True,exist_ok=True)
    orig=Path("original");cache=Path("confirm-cache");cache.mkdir(exist_ok=True)
    direction_cache=Path("direction-cache");direction_cache.mkdir(exist_ok=True)
    status={"status":"failed","planned_dates":len(NEW),"missing":[],"bigquery_queries":0}
    raw=[];rows=[];obs=[];features=[]
    try:
        weight_path=orig/"weights.json";weights=json.loads(weight_path.read_text())
        status["frozen_weights_sha256"]=hashlib.sha256(weight_path.read_bytes()).hexdigest()
        assert not set(NEW)&set(ISSUES)
        import dynamical_catalog
        ds=dynamical_catalog.open(PRODUCT,chunks=None)
        try:
            if "degree_Celsius" not in ds.temperature_2m.attrs.get("units","") or ds.wind_speed_10m.attrs.get("units") not in ("m s-1","m/s"):raise ValueError("WeatherNext units")
            for issue in NEW:
                checkpoint=cache/(issue.strftime("%Y%m%d")+"_all.csv")
                try:
                    if checkpoint.exists(): segment=pd.read_csv(checkpoint,dtype={"station_id":str}).to_dict("records")
                    else:
                        segment=om_rows(issue,raw,cache)
                        for lead in LEADS:segment.extend(forecast_rows(ds,issue,lead))
                        if len(segment)!=54:raise ValueError("incomplete issue")
                        pd.DataFrame(segment).to_csv(checkpoint,index=False)
                    if len(segment)!=54:raise ValueError("invalid checkpoint")
                    rows.extend(segment)
                    print("Complete",issue,flush=True)
                except (requests.RequestException,ValueError,KeyError,RuntimeError) as e:status["missing"].append({"issue":str(issue),"error":str(e)[:300]})
        finally:ds.close()
        f=pd.DataFrame(rows);f.to_csv(out/"forecasts.csv",index=False)
        dates=sorted(pd.to_datetime(f.init_time,utc=True,format="ISO8601").unique())
        for issue in dates:
            p=cache/(pd.Timestamp(issue).strftime("%Y%m%d")+"_obs.json")
            if p.exists():
                saved=json.loads(p.read_text());o=pd.DataFrame(saved["rows"]);r=saved["raw"]
            else:
                o,r,_=collect_observations([issue],LEADS)
                p.write_text(json.dumps({"rows":o.to_dict("records"),"raw":r},default=str))
            obs.append(o);features.extend(r)
        o=pd.concat(obs,ignore_index=True);o.to_csv(out/"observations.csv",index=False)
        (out/"DMI_raw.json").write_text(json.dumps(features,default=str))
        w=frozen(wide(f,o),weights)
        w.to_csv(out/"frozen_predictions.csv",index=False)
        status.update(complete_forecast_dates=len(dates),paired_dates=int(w.init_time.nunique()),paired_cases=len(w),frozen_scores=scores(w,MODELS+["FWA2"]))
        status["temperature_intervals"]=[intervals(w[w.variable=="temperature_2m"],"FWA2",m) for m in MODELS]
        status["temperature_validation"]="adequate_pilot" if w.init_time.nunique()>=20 and w.groupby(["station_id","variable","lead_hours"]).ngroups==18 else "insufficient"
        (out/"status.json").write_text(json.dumps(status,indent=2))
        # Wind development uses original training data only, never original or new test targets.
        train=wide(pd.read_csv(orig/"forecasts.csv",dtype={"station_id":str}),pd.read_csv(orig/"observations.csv",dtype={"station_id":str}))
        train=train[(train.variable=="wind_speed_10m")&(train.init_time<pd.Timestamp("2026-08-20",tz="UTC"))&(train.valid_time<pd.Timestamp("2026-08-19T18:00Z"))]
        test=w[w.variable=="wind_speed_10m"].copy()
        d=directions(pd.concat([train,test]),direction_cache)
        for frame in (train,test):frame["init_time"]=pd.to_datetime(frame.init_time,utc=True)
        d["init_time"]=pd.to_datetime(d.init_time,utc=True)
        keys=["station_id","init_time","lead_hours"]
        train=train.merge(d,on=keys,validate="one_to_one");test=test.merge(d,on=keys,validate="one_to_one")
        receipt=json.loads(Path("config/faroe_terrain_profiles.json").read_text())
        if receipt["sha256"]!="c30eac4363b97ad7745ea2f2ab04d3f0263ff3984c39fe68abd6fa84a6bd9fb2" or receipt["crs"]!="EPSG:5316":raise ValueError("Terrain provenance mismatch")
        for sid,st in STATIONS.items():
            site=receipt["stations"][sid]
            if abs(site["lat"]-st["lat"])>1e-8 or abs(site["lon"]-st["lon"])>1e-8:raise ValueError("Terrain station mismatch")
            if [x["direction_deg"] for x in site["sectors"]]!=list(range(0,360,5)):raise ValueError("Terrain sector mismatch")
        from faroe_terrain import attach
        train=attach(train,receipt);test=attach(test,receipt)
        status["terrain_status"]="verified_profiles_attached"
        status["terrain_sha256"]=receipt["sha256"]
        status["directional_train_dates"]=int(train.init_time.nunique())
        status["directional_test_dates"]=int(test.init_time.nunique())
        if train.init_time.nunique()<10 or test.init_time.nunique()<20:raise ValueError("insufficient directional dates")
        def design(x,cols):
            return pd.concat([x[cols],pd.get_dummies(x.station_id,prefix="site",dtype=float).reindex(columns=["site_"+s for s in STATIONS],fill_value=0),pd.get_dummies(x.lead_hours,prefix="lead",dtype=float).reindex(columns=["lead_"+str(l) for l in LEADS],fill_value=0)],axis=1)
        for m,cols in [("FWA4A",MODELS),("FWA4B",MODELS+["sin","cos"]),("FWA4C",MODELS+["sin","cos","shelter","exposure"])]:
            model=make_pipeline(StandardScaler(),Ridge(alpha=10))
            model.fit(design(train,cols),train.observed-train["HARMONIE_DINI_OM"])
            test[m]=np.maximum(0,test["HARMONIE_DINI_OM"]+model.predict(design(test,cols)))
        test.to_csv(out/"wind_predictions.csv",index=False)
        status.update(wind_scores=scores(test,MODELS+["FWA2","FWA4A","FWA4B","FWA4C"]),wind_train_dates=int(train.init_time.nunique()),wind_test_dates=int(test.init_time.nunique()),wind_intervals=[intervals(test,m,"HARMONIE_DINI_OM") for m in ["FWA4A","FWA4B","FWA4C"]]+[intervals(test,"FWA4B","FWA4A"),intervals(test,"FWA4C","FWA4B")],terrain_status="evaluated",status="exploratory_success")
    except Exception as e:status["error"]=str(e);raise
    finally:
        (out/"status.json").write_text(json.dumps(status,indent=2,default=str))
if __name__=="__main__":main()
