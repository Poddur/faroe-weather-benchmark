"""Historical WeatherNext 3 versus original DMI station observations.

Explicit retrospective archive experiment. Fixed, bounded 2026 dates; strict
exact-hour matching; raw observation features and forecast source provenance.
Never imply ECMWF/HARMONIE forecasts for these dates exist in our local archive.
"""
import argparse,hashlib,json,math,time,traceback
from collections import defaultdict
from datetime import datetime,timezone,timedelta
from pathlib import Path
import pandas as pd
from probe_weathernext_dynamical import PRODUCT,STATIONS,VARIABLES,forecast_rows,utc
from fetch_dmi_observations import fetch

PARAM_TO_VAR={"temp_dry":"temperature_2m","wind_speed":"wind_speed_10m"}
UNITS={"temperature_2m":"C","wind_speed_10m":"m/s"}
DEFAULT_ISSUES=["2026-10-01T00:00:00Z","2026-10-08T00:00:00Z"]
DEFAULT_LEADS=[6,12,24]
def collect_observations(issues,leads):
    # Exactly once per station/variable per selected date (not once per lead).
    raw=[];found=[];requests_info=[]
    for issue in issues:
        start=pd.Timestamp(issue)
        end=start+pd.Timedelta(hours=max(leads))
        for sid in STATIONS:
            for parameter,variable in PARAM_TO_VAR.items():
                n=0
                for feature in fetch(sid,utc(start),utc(end),parameter):
                    raw.append(feature)
                    props=feature["properties"]
                    if props.get("value") is None:continue
                    ts=pd.Timestamp(props["observed"])
                    if ts.tzinfo is None:raise ValueError("Unzoned DMI observation")
                    ts=ts.tz_convert("UTC")
                    if ts not in {start+pd.Timedelta(hours=h) for h in leads}:continue
                    value=float(props["value"])
                    if not math.isfinite(value):raise ValueError("Nonfinite DMI observation")
                    found.append({"station_id":sid,"variable":variable,"valid_time":utc(ts),
                                  "observed":value,"unit":UNITS[variable],"dmi_parameter":parameter,
                                  "observation_id":feature.get("id")})
                    n+=1
                requests_info.append({"init_time":utc(start),"station_id":sid,"parameter":parameter,"matched_records":n})
    o=pd.DataFrame(found)
    if not o.empty and o.duplicated(["station_id","variable","valid_time"]).any():
        raise ValueError("Conflicting or duplicated DMI records; do not silently select")
    return o,raw,requests_info

def score(forecasts,obs):
    if obs.empty:raise ValueError("DMI observations missing for all requested dates")
    combined=forecasts.merge(obs,on=["station_id","variable","valid_time"],how="left",
                             suffixes=("","_observed"),validate="many_to_one",indicator=True)
    if ((combined._merge=="both")&(combined.unit!=combined.unit_observed)).any():
        raise ValueError("Forecast/observation units mismatch")
    combined["has_observation"]=combined._merge.eq("both")
    paired=combined[combined.has_observation].copy()
    paired["error"]=paired.value-paired.observed
    paired["absolute_error"]=paired.error.abs()
    if paired.empty:raise ValueError("No matched WeatherNext/DMI pairs")
    summary=(paired.groupby(["variable","lead_hours"],dropna=False).agg(
        n=("error","size"),mae=("absolute_error","mean"),
        bias=("error","mean"),rmse=("error",lambda x:float((x**2).mean()**0.5)),
        independent_issues=("init_time","nunique")).reset_index())
    return paired,combined,summary

def run(out,issue_times=DEFAULT_ISSUES,leads=DEFAULT_LEADS,open_fn=None,observation_fn=None):
    if len(issue_times)>8 or len(leads)>3:raise ValueError("Bounded pilot max 8 issues and 3 leads")
    issues=[utc(pd.Timestamp(x)) for x in issue_times]
    if len(set(issues))!=len(issues):raise ValueError("Duplicate issue time")
    if sorted(set(leads))!=sorted(leads) or any(l not in (6,12,24) for l in leads):
        raise ValueError("Requested lead times must be distinct subset of +6/+12/+24h")
    out=Path(out);out.mkdir(parents=True,exist_ok=True)
    manifest={"source":PRODUCT,"issue_times_utc":issues,"lead_hours":leads,
              "observations":"DMI metObs v2","status":"started",
              "expected_forecast_rows":len(issues)*len(leads)*len(STATIONS)*len(VARIABLES),
              "interpretation":"Retrospective historical-archive verification; contemporary issuance unverified",
              "started_utc":datetime.now(timezone.utc).isoformat()}
    try:
        if open_fn is None:
            import dynamical_catalog
            open_fn=dynamical_catalog.open
        ds=open_fn(PRODUCT,chunks=None)
        manifest["dimensions"]={k:int(v) for k,v in ds.sizes.items()}
        manifest["units"]={v:ds[v].attrs.get("units","") for v in VARIABLES}
        if "degree_Celsius" not in manifest["units"]["temperature_2m"]:
            raise ValueError("Unverified WeatherNext temperature unit: "+str(manifest["units"]["temperature_2m"]))
        if manifest["units"]["wind_speed_10m"] not in ("m s-1","m/s"):
            raise ValueError("Unverified WeatherNext wind unit")
        rows=[]
        for issue in issues:
            for lead in leads:
                segment=forecast_rows(ds,issue,lead)
                rows.extend(segment)
                print("WeatherNext historical extracted",issue,"lead",lead,"rows",len(segment),flush=True)
        forecasts=pd.DataFrame(rows)
        if len(forecasts)!=manifest["expected_forecast_rows"]:raise ValueError("Incomplete forecast extraction")
        if forecasts.duplicated(["model","station_id","variable","init_time","valid_time"]).any():
            raise ValueError("Duplicate model keys")
        fp=out/"forecasts.csv";forecasts.to_csv(fp,index=False)
        manifest["forecast_csv_sha256"]=hashlib.sha256(fp.read_bytes()).hexdigest()
        if observation_fn is None:observation_fn=collect_observations
        observed,raw,requests_info=observation_fn(issues,leads)
        obs_path=out/"observations.csv";observed.to_csv(obs_path,index=False)
        raw_path=out/"dmi_original_features.json";raw_path.write_text(json.dumps(raw,ensure_ascii=False),encoding="utf8")
        (out/"dmi_query_coverage.json").write_text(json.dumps(requests_info,indent=2))
        manifest["observation_csv_sha256"]=hashlib.sha256(obs_path.read_bytes()).hexdigest()
        manifest["dmi_original_features_sha256"]=hashlib.sha256(raw_path.read_bytes()).hexdigest()
        paired,all_records,summary=score(forecasts,observed)
        paired.to_csv(out/"paired.csv",index=False)
        all_records.to_csv(out/"coverage.csv",index=False)
        summary.to_csv(out/"scores.csv",index=False)
        independent=paired.init_time.nunique()
        manifest.update(status="exploratory_success",forecast_rows=len(forecasts),
                        observation_rows=len(observed),paired_rows=len(paired),
                        independent_init_times=int(independent),
                        missing_forecast_obs=int((~all_records.has_observation).sum()),
                        notice="Historical backfill sample, NOT prospective skill or 3-model ranking")
        print("Historical WeatherNext summary:",summary.to_string(index=False),flush=True)
    except Exception as exc:
        manifest.update(status="failed",error=f"{type(exc).__name__}: {exc}",traceback=traceback.format_exc()[-6000:])
        raise
    finally:
        (out/"manifest.json").write_text(json.dumps(manifest,indent=2,ensure_ascii=False))
    return manifest

def main():
    p=argparse.ArgumentParser()
    p.add_argument("--issue",action="append",dest="issues")
    p.add_argument("--leads",type=int,nargs="+",default=DEFAULT_LEADS)
    p.add_argument("--output",default="outputs/weathernext-historical")
    a=p.parse_args()
    run(a.output,a.issues or DEFAULT_ISSUES,a.leads)
if __name__=="__main__":main()
