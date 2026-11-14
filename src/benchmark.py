"""Paired, deterministic station forecast verification; UTC and canonical units."""
import argparse,hashlib,json
from pathlib import Path
import numpy as np
import pandas as pd
KEY=["station_id","variable","init_time","lead_hours","valid_time"]
UNITS={"temperature_2m":"C","wind_speed_10m":"m/s","msl_pressure":"hPa","precipitation_1h":"mm"}
def read_forecasts(path):
    df=pd.read_csv(path,dtype={"station_id":str,"model":str,"variable":str,"unit":str})
    need=set(KEY+["model","value","unit"])
    if need-set(df):raise ValueError(f"Missing forecast columns: {sorted(need-set(df))}")
    for c in ["init_time","valid_time"]:df[c]=pd.to_datetime(df[c],utc=True,errors="raise")
    df["lead_hours"]=pd.to_numeric(df.lead_hours,errors="raise").astype(int)
    df["value"]=pd.to_numeric(df.value,errors="raise")
    if df.value.isna().any() or not np.isfinite(df.value).all():raise ValueError("Nonfinite forecast")
    if (df.lead_hours<=0).any() or not ((df.valid_time-df.init_time)==pd.to_timedelta(df.lead_hours,unit="h")).all():raise ValueError("Inconsistent time/lead")
    if df.duplicated(KEY+["model"]).any():raise ValueError("Duplicate forecast keys")
    for v,u in UNITS.items():
        if ((df.variable==v)&(df.unit!=u)).any():raise ValueError("Incorrect unit: "+v)
    if (~df.variable.isin(UNITS)).any():raise ValueError("Unknown variable")
    return df
def read_observations(path):
    df=pd.read_csv(path,dtype={"station_id":str,"variable":str,"unit":str})
    need={"station_id","variable","valid_time","value","unit"}
    if need-set(df):raise ValueError(f"Missing observation columns: {sorted(need-set(df))}")
    df["valid_time"]=pd.to_datetime(df.valid_time,utc=True,errors="raise")
    df["value"]=pd.to_numeric(df.value,errors="raise")
    if df.value.isna().any() or not np.isfinite(df.value).all():raise ValueError("Invalid observations")
    if df.duplicated(["station_id","variable","valid_time"]).any():raise ValueError("Duplicate observations")
    for v,u in UNITS.items():
        if ((df.variable==v)&(df.unit!=u)).any():raise ValueError("Incorrect observation unit: "+v)
    if (~df.variable.isin(UNITS)).any():raise ValueError("Unknown observation variable")
    return df
def metrics(error):
    a=np.asarray(error,float)
    return {"n":int(a.size),"mae":float(np.abs(a).mean()),"rmse":float(np.sqrt(np.square(a).mean())),"bias":float(a.mean())}
def analysis(forecasts,observations,models,bootstrap=1000,seed=20261114):
    if len(models)<2 or len(set(models))!=len(models):raise ValueError("Specify >=2 distinct models")
    f=forecasts[forecasts.model.isin(models)].copy()
    if set(models)-set(f.model):raise ValueError("Missing model data")
    obs=observations[["station_id","variable","valid_time","value","unit"]].rename(columns={"value":"observed","unit":"obs_unit"})
    merged=f.merge(obs,on=["station_id","variable","valid_time"],how="inner",validate="many_to_one")
    if (merged.unit!=merged.obs_unit).any():raise ValueError("Unit mismatch")
    common=merged.groupby(KEY,dropna=False).model.nunique().reset_index(name="present")
    merged=merged.merge(common[common.present==len(models)][KEY],on=KEY,validate="many_to_one")
    if merged.empty:raise ValueError("No paired records")
    merged["error"]=merged.value-merged.observed
    merged["abs_error"]=merged.error.abs()
    rows=[]
    for key,g in merged.groupby(["variable","lead_hours","model"],sort=True):
        rows.append(dict(zip(["variable","lead_hours","model"],key),**metrics(g.error)))
    scores=pd.DataFrame(rows).sort_values(["variable","lead_hours","model"]).reset_index(drop=True)
    base=models[0];rng=np.random.default_rng(seed);comparisons=[]
    for (variable,lead),g in merged.groupby(["variable","lead_hours"],sort=True):
        wide=g.pivot(index=KEY,columns="model",values="abs_error").reset_index()
        wide["init_day"]=wide.init_time.dt.strftime("%Y-%m-%d")
        for model in models[1:]:
            wide["delta"]=wide[model]-wide[base]
            daily=[p.delta.to_numpy() for _,p in wide.groupby("init_day",sort=True)]
            ci=(float("nan"),float("nan"))
            if len(daily)>=2 and bootstrap:
                samples=[]
                for _ in range(bootstrap):
                    sample=rng.integers(0,len(daily),len(daily))
                    samples.append(float(np.concatenate([daily[i] for i in sample]).mean()))
                ci=tuple(float(x) for x in np.percentile(samples,[2.5,97.5]))
            comparisons.append({"variable":variable,"lead_hours":int(lead),"baseline":base,"challenger":model,"paired_n":len(wide),"independent_init_days":len(daily),"delta_mae_challenger_minus_baseline":float(wide.delta.mean()),"ci95_low":ci[0],"ci95_high":ci[1]})
    return merged,scores,pd.DataFrame(comparisons)
def main():
    p=argparse.ArgumentParser()
    p.add_argument("--forecasts",required=True);p.add_argument("--observations",required=True)
    p.add_argument("--models",nargs="+",default=["WeatherNext3","ECMWF_IFS","HARMONIE"])
    p.add_argument("--output",default="outputs");p.add_argument("--bootstrap",type=int,default=1000)
    a=p.parse_args();out=Path(a.output);out.mkdir(parents=True,exist_ok=True)
    f=read_forecasts(a.forecasts);o=read_observations(a.observations)
    paired,scores,comp=analysis(f,o,a.models,a.bootstrap)
    for name,df in [("paired_records",paired),("scores",scores),("paired_comparisons",comp)]:
        df.to_csv(out/f"{name}.csv",index=False,float_format="%.8f")
    manifest={"models":a.models,"forecast_rows":len(f),"observation_rows":len(o),"common_keys":len(paired)//len(a.models),"bootstrap_reps":a.bootstrap,"bootstrap_seed":20261114,"input_sha256":{p:hashlib.sha256(Path(p).read_bytes()).hexdigest() for p in [a.forecasts,a.observations]}}
    (out/"manifest.json").write_text(json.dumps(manifest,indent=2)+"\n")
    print(scores.to_string(index=False));print(comp.to_string(index=False))
if __name__=="__main__":main()
