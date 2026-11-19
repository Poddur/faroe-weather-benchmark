"""Bounded retrospective three-model evaluation of archived original forecasts.
No BigQuery usage. No WeatherNext rows with valid time less than one hour old.
Missing archive issues are recorded, never substituted with another issue.
"""
import argparse,json,hashlib
from pathlib import Path
import pandas as pd
from evaluate_releases import read_archives,normalize
from probe_weathernext_dynamical import PRODUCT,forecast_rows,VARIABLES
from compare_three_models import compare

def run(archives,out,now=None,open_fn=None):
    now=pd.Timestamp.now(tz="UTC") if now is None else pd.Timestamp(now)
    if now.tzinfo is None:raise ValueError("Timezone required")
    out=Path(out);out.mkdir(parents=True,exist_ok=True)
    manifest={"status":"failed","source":PRODUCT,"license":"CC BY 4.0; Google WeatherNext 3 via dynamical.org",
              "mode":"retrospective","bigquery_queries":0,"missing_issues":[]}
    try:
        f,o,nb,problems=read_archives(archives)
        f,o=normalize(f,o)
        manifest.update(valid_source_bundles=nb,excluded_bundles=problems)
        if problems:raise ValueError("Source archive integrity failure")
        f["init_time"]=pd.to_datetime(f.init_time,utc=True)
        f["valid_time"]=pd.to_datetime(f.valid_time,utc=True)
        eligible=sorted(f.loc[f.init_time+pd.Timedelta(hours=25)<=now,"init_time"].unique())[-24:]
        manifest["eligible_issues"]=[str(i) for i in eligible]
        if not eligible:raise ValueError("No mature archived issue")
        if open_fn is None:
            import dynamical_catalog
            open_fn=dynamical_catalog.open
        ds=open_fn(PRODUCT,chunks=None)
        rows=[];matched=[]
        try:
            if "degree_Celsius" not in ds["temperature_2m"].attrs.get("units",""):raise ValueError("Unexpected temperature units")
            if ds["wind_speed_10m"].attrs.get("units") not in ("m s-1","m/s"):raise ValueError("Unexpected wind units")
            for issue in eligible:
                try:
                    segment=[]
                    for lead in (6,12,24):segment.extend(forecast_rows(ds,issue,lead))
                    if len(segment)!=18:raise ValueError("Incomplete issue")
                    rows.extend(segment);matched.append(issue)
                except (KeyError,ValueError,RuntimeError) as exc:
                    manifest["missing_issues"].append({"issue":str(issue),"reason":str(exc)[:300]})
        finally:
            ds.close()
        if not rows:raise ValueError("No complete WeatherNext issues available")
        base=f[f.init_time.isin(matched)].copy()
        paths=[out/"base_forecasts.csv",out/"weathernext_forecasts.csv",out/"observations.csv"]
        for frame,path in zip([base,pd.DataFrame(rows),o],paths):frame.to_csv(path,index=False)
        result=compare(*paths,out/"scores",now=now)
        manifest.update(result,complete_weathernext_issues=len(matched),
                        status="partial" if manifest["missing_issues"] else "exploratory",
                        source_hashes={p.name:hashlib.sha256(p.read_bytes()).hexdigest() for p in paths},
                        newest_archived_issue=str(f.init_time.max()),
                        retrieved_utc=now.isoformat())
    finally:
        (out/"status.json").write_text(json.dumps(manifest,indent=2)+"\n")
    return manifest

def main():
    p=argparse.ArgumentParser();p.add_argument("--archive-dir",required=True);p.add_argument("--output",required=True)
    a=p.parse_args()
    print(json.dumps(run(list(Path(a.archive_dir).rglob("issue_*.zip")),a.output),indent=2))
if __name__=="__main__":main()
