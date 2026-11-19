"""Prepare a three-model comparison from historical (expired-valid-time) data.

No network access, no billing, and no publication. A caller must separately
establish data licensing and source provenance. This is retrospective only.
"""
import argparse,json
from pathlib import Path
import pandas as pd
from benchmark import read_forecasts, read_observations, analysis, KEY

MODELS=["ECMWF_IFS","HARMONIE_DINI","WeatherNext3"]
def compare(base_path,wn_path,obs_path,out,now=None):
    now=pd.Timestamp.now(tz="UTC") if now is None else pd.Timestamp(now)
    if now.tzinfo is None: raise ValueError("Timezone required")
    base=read_forecasts(base_path)
    wn=read_forecasts(wn_path)
    obs=read_observations(obs_path)
    if set(base.model)!={"ECMWF_IFS","HARMONIE_DINI"} or set(wn.model)!={"WeatherNext3"}:
        raise ValueError("Unexpected model identities")
    if (wn.valid_time>now-pd.Timedelta(hours=1)).any():
        raise ValueError("Refusing nonhistorical WeatherNext data in public archive path")
    f=pd.concat([base,wn],ignore_index=True)
    if f.duplicated(KEY+["model"]).any(): raise ValueError("Duplicate forecast keys")
    paired,scores,delta=analysis(f,obs,MODELS,bootstrap=0)
    days=int(paired.init_time.dt.normalize().nunique())
    if days>=10:
        paired,scores,delta=analysis(f,obs,MODELS,bootstrap=1000)
        mask=delta.independent_init_days<10
        delta.loc[mask,["ci95_low","ci95_high"]]=float("nan")
    out=Path(out);out.mkdir(parents=True,exist_ok=True)
    for name,frame in [("paired_records",paired),("scores",scores),("model_differences",delta)]:
        frame.to_csv(out/(name+".csv"),index=False)
    result={"status":"exploratory","models":MODELS,"common_cases":len(paired)//3,
            "independent_issue_days":days,"forecast_rows_by_model":f.groupby("model").size().to_dict(),
            "interpretation":"Retrospective archive comparison; not evidence of prospective availability or superiority."}
    (out/"manifest.json").write_text(json.dumps(result,indent=2))
    return result
def main():
    p=argparse.ArgumentParser()
    for name in ("base","weathernext","observations","output"):p.add_argument("--"+name,required=True)
    a=p.parse_args();print(json.dumps(compare(a.base,a.weathernext,a.observations,a.output),indent=2))
if __name__=="__main__":main()
