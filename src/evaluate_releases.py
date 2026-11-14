"""Read archived GitHub Release ZIPs and evaluate only common real observations.

This module NEVER downloads reforecasts, substitutes missing values, or assigns
success to an insufficient sample. Inputs are the immutable original cycle ZIPs.
"""
import argparse,io,json,zipfile,hashlib
from pathlib import Path
import numpy as np
import pandas as pd
from benchmark import read_forecasts,read_observations,analysis

FK=["model","station_id","variable","init_time","lead_hours","valid_time"]
OK=["station_id","variable","valid_time"]
MODELS=["ECMWF_IFS","HARMONIE_DINI"]
def read_archives(files):
    fcs=[];obs=[];valid_bundles=0;problems=[]
    for archive in sorted(map(Path,files)):
        try:
            with zipfile.ZipFile(archive) as z:
                listed=set(z.namelist())
                need={"forecast/matched_forecasts.csv","observations/observations.csv","forecast/manifest.json","verification.json"}
                if not need.issubset(listed):raise ValueError("Missing expected ZIP files")
                source_manifest=json.loads(z.read("forecast/manifest.json"))
                verification=json.loads(z.read("verification.json"))
                if source_manifest["status"]!="success" or verification["status"]!="pass":raise ValueError("Not verified successful collection")
                for item in source_manifest.get("files",[]):
                    p="forecast/"+item["path"]
                    data=z.read(p)
                    if hashlib.sha256(data).hexdigest()!=item["sha256"] or len(data)!=item["bytes"]:raise ValueError("Source hash mismatch "+p)
                f=pd.read_csv(io.BytesIO(z.read("forecast/matched_forecasts.csv")),dtype={"station_id":str})
                o=pd.read_csv(io.BytesIO(z.read("observations/observations.csv")),dtype={"station_id":str})
                fcs.append(f);obs.append(o);valid_bundles+=1
        except Exception as exc:
            problems.append({"archive":archive.name,"error":str(exc)})
    if not fcs:raise ValueError("No valid archive ZIPs")
    return pd.concat(fcs,ignore_index=True),pd.concat(obs,ignore_index=True),valid_bundles,problems

def normalize(forecasts,observations):
    f=forecasts.copy();o=observations.copy()
    for name,frame,keys in (("forecast",f,FK),("observation",o,OK)):
        frame["value"]=pd.to_numeric(frame.value,errors="raise")
        if not np.isfinite(frame.value).all():raise ValueError("Nonfinite "+name)
        for c in ("valid_time",):frame[c]=pd.to_datetime(frame[c],utc=True).dt.strftime("%Y-%m-%dT%H:%M:%SZ")
        if name=="forecast":
            frame["init_time"]=pd.to_datetime(frame.init_time,utc=True).dt.strftime("%Y-%m-%dT%H:%M:%SZ")
        # Duplicate equal source rows may occur in re-runs or overlapping observation pulls.
        conflicts=frame.groupby(keys,dropna=False).agg(distinct_values=("value","nunique"),distinct_units=("unit","nunique"))
        bad=conflicts[(conflicts.distinct_values>1)|(conflicts.distinct_units>1)]
        if len(bad):
            raise ValueError(f"Conflicting {name} source revisions for {len(bad)} unique keys; human data audit required")
    return f.drop_duplicates(FK),o.drop_duplicates(OK)

def report(files,out,bootstrap=500):
    out=Path(out);out.mkdir(parents=True,exist_ok=True)
    f,o,nb,problems=read_archives(files)
    f,o=normalize(f,o)
    f=read_forecasts(_temp_csv(out/"_forecast_input.csv",f))
    o=read_observations(_temp_csv(out/"_observation_input.csv",o))
    manifest={"valid_source_bundles":nb,"excluded_bundles":problems,"forecast_rows":len(f),"observation_rows":len(o),"models":MODELS,"status":"insufficient","warnings":["This is exploratory verification, not proof of model superiority."]}
    try:
        paired,scores,delta=analysis(f,o,MODELS,bootstrap=bootstrap)
        paired.to_csv(out/"paired_records.csv",index=False);scores.to_csv(out/"scores.csv",index=False);delta.to_csv(out/"model_differences.csv",index=False)
        independent_days=paired.init_time.dt.strftime("%Y-%m-%d").nunique()
        manifest.update(status="exploratory" if independent_days<10 else "analysis_ready_for_review",paired_model_rows=len(paired),independent_init_days=int(independent_days))
        if independent_days<10:manifest["warnings"].append("Fewer than 10 model issue dates: insufficient independent cases for claims.")
    except ValueError as e:
        manifest["warnings"].append(str(e))
    finally:
        for n in ("_forecast_input.csv","_observation_input.csv"):
            (out/n).unlink(missing_ok=True)
    (out/"report.json").write_text(json.dumps(manifest,indent=2)+"\n")
    print(json.dumps(manifest,indent=2))
    return manifest

def _temp_csv(path,df):
    df.to_csv(path,index=False);return path

def main():
    p=argparse.ArgumentParser()
    p.add_argument("--archive-dir",default="release-bundles")
    p.add_argument("--output",default="outputs/report")
    args=p.parse_args()
    files=list(Path(args.archive_dir).rglob("issue_*.zip"))
    if not files:raise SystemExit("No issue archives downloaded")
    report(files,args.output)
if __name__=="__main__":main()
