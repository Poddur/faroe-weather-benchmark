"""Exploratory terrain-class differences, using ONLY original pilot training dates.
Never fit on, read, or derive thresholds from 2026-11-20+ prospective tests.
"""
import argparse,io,json,hashlib,zipfile
from pathlib import Path
import numpy as np,pandas as pd
CUTOFF=pd.Timestamp("2026-08-20T00:00:00Z")
def compute(path,classes):
    conf=json.loads(Path(classes).read_text());sites=conf["stations"]
    with zipfile.ZipFile(path) as z:
        f=pd.read_csv(io.BytesIO(z.read("forecasts.csv")),dtype={"station_id":str})
        o=pd.read_csv(io.BytesIO(z.read("observations.csv")),dtype={"station_id":str})
    for frame in (f,o):frame["valid_time"]=pd.to_datetime(frame.valid_time,utc=True,format="mixed")
    f["init_time"]=pd.to_datetime(f.init_time,utc=True,format="mixed")
    raw=f[(f.model=="HARMONIE_DINI_OM")&(f.init_time<CUTOFF)]
    merged=raw.merge(o[["station_id","variable","valid_time","observed"]],on=["station_id","variable","valid_time"],how="inner",validate="one_to_one")
    merged=merged[merged.station_id.isin(["06009","06011","06014"])].copy()
    if merged.empty or merged.init_time.ge(CUTOFF).any():raise ValueError("No clean pre-August data")
    merged["error"]=merged.value-merged.observed;merged["abs_error"]=merged.error.abs()
    merged["wind_observed_strong"]=np.where(merged.variable.eq("wind_speed_10m"),merged.observed.ge(10),False)
    merged["terrain_class"]=merged.station_id.map(lambda x:sites[x]["topographic_class"])
    if merged.duplicated(["station_id","variable","init_time","valid_time"]).any():raise ValueError("duplicated forecast identity")
    output=[]
    for var in ["temperature_2m","wind_speed_10m"]:
        sub=merged[merged.variable==var]
        for dim in ["station_id","terrain_class"]:
            for name,g in sub.groupby(dim):
                output.append(dict(variable=var,dimension=dim,group=name,cases=len(g),dates=int(g.init_time.dt.date.nunique()),MAE=float(g.abs_error.mean()),signed_bias=float(g.error.mean()),mean_observation=float(g.observed.mean()),strong_observed_cases=int(g.wind_observed_strong.sum()),lead_hours=sorted(g.lead_hours.unique().tolist())))
        if var=="wind_speed_10m":
            for is_strong,g in sub.groupby("wind_observed_strong"):
                output.append(dict(variable=var,dimension="observed_wind_ge_10ms",group=str(bool(is_strong)),cases=len(g),dates=int(g.init_time.dt.date.nunique()),MAE=float(g.abs_error.mean()),signed_bias=float(g.error.mean()),mean_observation=float(g.observed.mean()),strong_observed_cases=int(g.wind_observed_strong.sum()),lead_hours=sorted(g.lead_hours.unique().tolist())))
    return dict(status="exploratory_only",forecast_source_sha256=hashlib.sha256(Path(path).read_bytes()).hexdigest(),train_issue_cutoff_exclusive=CUTOFF.isoformat(),records=len(merged),training_issue_dates=int(merged.init_time.dt.date.nunique()),results=output,geographic_limit="3 training stations: two elevated-TPI, one neutral-TPI, NO valley proxy station in training. Class effects are not identifiable independently of site and sensor.",inversion_limit="Historical pilot contains no atmospheric 2m-100m temperature difference, so inversion cannot be retrospectively assessed.",prohibition="Never optimize the v2 frozen model or evaluate deployment on prospective v2 evidence.")
def main():
    p=argparse.ArgumentParser();p.add_argument("--archive",required=True);p.add_argument("--classes",required=True);p.add_argument("--output",required=True);a=p.parse_args();out=compute(a.archive,a.classes);Path(a.output).parent.mkdir(parents=True,exist_ok=True);Path(a.output).write_text(json.dumps(out,indent=2));print(json.dumps(out,indent=2))
if __name__=="__main__":main()
