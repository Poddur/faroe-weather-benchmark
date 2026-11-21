"""One-off out-of-sample score of frozen FWA2/FWA4A on exact-run sources.

New issues 2026-11-19 and 2026-11-20 are after the locked 2026-11-18
training cutoff. This does not alter the registered winter 2026-11-21+
confirmatory protocol. Archive provenance is retrospective, not live issuance.
"""
import json
from pathlib import Path
import numpy as np
import pandas as pd
from fwa5_winter import load_lock,load_terrain,wide_forecasts,predict,MODELS,VARS,KEY,DKEY
from fwa_historical_pilot import om_rows
from probe_weathernext_dynamical import PRODUCT,forecast_rows
from historical_weathernext_benchmark import collect_observations

ISSUES=[pd.Timestamp("2026-11-19T00:00:00Z"),pd.Timestamp("2026-11-20T00:00:00Z")]
MAP={"ECMWF_9km":"ECMWF_9km","HARMONIE_DINI_OM":"HARMONIE_DINI_OM","WeatherNext3":"WeatherNext3"}
NAMES={"temperature_2m":"FWA2","wind_speed_10m":"FWA4A"}

def test(out=Path("outputs/fwa-frozen-holdout")):
    import dynamical_catalog
    out.mkdir(parents=True,exist_ok=True)
    lock=load_lock(); terrain=load_terrain(lock)
    assert pd.Timestamp(lock["training_latest_valid"]) < ISSUES[0]
    source_cache=out/"source-cache"; source_cache.mkdir(exist_ok=True)
    result={"status":"started","model_lock_sha256":"374bf294dd33741ba0dd635ad68308439108c93b903fbe4e8179533417c44085",
      "model_input_source":"Open-Meteo exact-run ECMWF 9km/HARMONIE DINI; Google WeatherNext3 historical dynamical.org",
      "research_design":"Frozen post-training historical pilot; separate from registered winter confirmation",
      "issue_dates_requested":[str(x) for x in ISSUES],"issues":[],"comparisons":[]}
    ds=None
    try:
        ds=dynamical_catalog.open(PRODUCT,chunks=None)
        if "degree_Celsius" not in ds.temperature_2m.attrs.get("units",""):raise ValueError("WeatherNext temperature unit changed")
        if ds.wind_speed_10m.attrs.get("units") not in ("m s-1","m/s"):raise ValueError("WeatherNext wind unit changed")
        all_pairs=[]
        for issue in ISSUES:
            info={"issue":str(issue),"complete":False}
            result["issues"].append(info)
            try:
                raw=[]
                f=pd.DataFrame(om_rows(issue,raw,source_cache))
                for lead in (6,12,24):
                    f=pd.concat([f,pd.DataFrame(forecast_rows(ds,issue,lead))],ignore_index=True)
                w=wide_forecasts(f,issue)
                assert len(w)==18
                # FWA4A does not depend on wind direction; frozen FWA5 predictor
                # uses the original FWA4A coefficients and makes the missing-
                # direction fallback explicit. We score FWA4A only, NOT FWA5W.
                empty_direction=pd.DataFrame(columns=DKEY+["sin","cos"])
                forecast=predict(w,empty_direction,lock,terrain)
                obs,obs_raw,queries=collect_observations([issue],[6,12,24])
                obs=obs.copy()
                obs["valid_time"]=pd.to_datetime(obs.valid_time,utc=True,format="ISO8601")
                if obs.duplicated(["station_id","variable","valid_time"]).any():
                    raise ValueError("Duplicate independent observations")
                pairs=forecast.merge(obs[["station_id","variable","valid_time","observed"]],
                    on=["station_id","variable","valid_time"],how="left",validate="many_to_one")
                matched=pairs.dropna(subset=["observed"]).copy()
                for field in MODELS+["FWA2","FWA4A"]:
                    if field in matched:matched[field]=pd.to_numeric(matched[field],errors="coerce")
                if not np.isfinite(matched[MODELS+["observed"]].to_numpy(dtype=float)).all():
                    raise ValueError("Nonfinite forecast or observation")
                # Missing observations are exclusions, never imputed.
                info.update(complete=True,forecast_cases=len(forecast),matched_cases=len(matched),
                    missing_observations=len(pairs)-len(matched),observation_requests=queries)
                matched.to_csv(out/(issue.strftime("%Y%m%d")+"_paired.csv"),index=False)
                all_pairs.append(matched)
            except Exception as ex:
                info.update(error=f"{type(ex).__name__}: {ex}")
                print("ISSUE FAILED",str(issue),str(ex),flush=True)
        if all_pairs:
            z=pd.concat(all_pairs,ignore_index=True)
            for variable,candidate in NAMES.items():
                part=z[z.variable==variable]
                for model in MODELS:
                    x=part[[candidate,model,"observed","init_time"]].dropna()
                    if x.empty:continue
                    ea=(x[candidate]-x.observed).abs()
                    eb=(x[model]-x.observed).abs()
                    result["comparisons"].append({"variable":variable,"candidate":candidate,"baseline":model,
                        "cases":len(x),"independent_issue_days":int(x.init_time.nunique()),
                        "fwa_mae":float(ea.mean()),"baseline_mae":float(eb.mean()),
                        "delta_mae":float((ea-eb).mean()),
                        "fwa_improvement_pct":float(100*(eb.mean()-ea.mean())/eb.mean()) if eb.mean() else None,
                        "issue_deltas":[{"issue":str(k),"delta_mae":float(((q[candidate]-q.observed).abs()-(q[model]-q.observed).abs()).mean())} for k,q in x.groupby("init_time")]})
            result["matched_dates"]=int(z.init_time.nunique())
            result["status"]="exploratory_completed" if all(t["complete"] for t in result["issues"]) else "partial_exploratory"
        else:result["status"]="failed_no_paired_data"
    finally:
        if ds is not None:ds.close()
        (out/"status.json").write_text(json.dumps(result,indent=2,default=str,allow_nan=False))
    print(json.dumps(result,indent=2,default=str,allow_nan=False),flush=True)
    if result["status"]=="failed_no_paired_data":raise RuntimeError("No valid test comparisons")
    return result

if __name__=="__main__":test()
