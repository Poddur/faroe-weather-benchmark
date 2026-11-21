"""Read-only independent scorecard of frozen FWA2/FWA4A vs exact-run models.

Use only immutable FWA winter checkpoint rows; never refit any model.
"""
import argparse
import hashlib
import json
from pathlib import Path
import numpy as np
import pandas as pd

LOCK_SHA="374bf294dd33741ba0dd635ad68308439108c93b903fbe4e8179533417c44085"
SITES=("06009","06011","06014")
LEADS=(6,12,24)
MODELS=("ECMWF_9km","HARMONIE_DINI_OM","WeatherNext3")
VARIABLES=(("temperature_2m","FWA2"),("wind_speed_10m","FWA4A"))
KEY=("station_id","variable","init_time","valid_time","lead_hours")

def sha(p):
    return hashlib.sha256(Path(p).read_bytes()).hexdigest()

def weekly_cluster_interval(frame,candidate,baseline,draws,seed):
    """Paired issue-week bootstrap; never treat station/leads as independent."""
    e=(frame[candidate]-frame.observed).abs()-(frame[baseline]-frame.observed).abs()
    week=frame.init_time.dt.strftime("%G-%V")
    blocks=[e.loc[group.index].to_numpy(dtype=float) for _,group in frame.groupby(week)]
    if len(blocks)<8:return None
    totals=np.array([x.sum() for x in blocks])
    counts=np.array([len(x) for x in blocks])
    rng=np.random.default_rng(seed)
    selected=rng.integers(len(blocks),size=(draws,len(blocks)))
    values=totals[selected].sum(axis=1)/counts[selected].sum(axis=1)
    # Nine prespecified comparisons: six overall + three strong-wind.
    # Bonferroni adjustment protects the simultaneous 95% decision.
    alpha=.05/9
    return [float(x) for x in np.quantile(values,[alpha/2,1-alpha/2])]

def judge(data,out,protocol):
    """Pre-winter, fixed evidence gate; no coefficients or forecasts are changed."""
    min_dates=protocol["minimum_dates"]
    min_weeks=protocol.get("minimum_weeks",10)
    min_group=protocol.get("minimum_cases_per_station_lead",63)
    weeks=int(data.init_time.dt.strftime("%G-%V").nunique())
    counts=data.groupby(["variable","station_id","lead_hours"]).size()
    expected=pd.MultiIndex.from_product([[v for v,_ in VARIABLES],SITES,LEADS])
    minimum_cases=int(counts.reindex(expected,fill_value=0).min())
    coverage=out["complete_dates"]>=min_dates and weeks>=min_weeks and minimum_cases>=min_group
    result={"status":"insufficient_data","minimum_dates":min_dates,
            "independent_issue_days":out["complete_dates"],
            "independent_issue_weeks":weeks,"multiplicity_control":"Bonferroni 9 predeclared paired comparisons, familywise 95% confidence","minimum_station_lead_cases":minimum_cases,
            "coverage_eligible":bool(coverage),
            "temperature_vs_three":"insufficient_data",
            "wind_average_vs_three":"insufficient_data",
            "strong_wind_safety":"insufficient_data",
            "overall":"insufficient_data"}
    if not coverage:return result
    draws=protocol.get("bootstrap_draws",10000)
    seed=protocol.get("seed",20261120)
    for item in out["comparisons"]:
        part=data[data.variable==item["variable"]]
        item["paired_week_bootstrap_familywise_ci"]=weekly_cluster_interval(part,item["candidate"],item["baseline"],draws,seed)
        item["week_clusters"]=weeks
        item["superiority_demonstrated"]=item["paired_week_bootstrap_familywise_ci"][1]<0
        item["inferiority_demonstrated"]=item["paired_week_bootstrap_familywise_ci"][0]>0
        item["insufficient_for_final_inference"]=False
    temperature=[x for x in out["comparisons"] if x["variable"]=="temperature_2m"]
    wind=[x for x in out["comparisons"] if x["variable"]=="wind_speed_10m"]
    result["temperature_vs_three"]="superior_to_all_three" if all(x["superiority_demonstrated"] for x in temperature) else "not_demonstrated"
    result["wind_average_vs_three"]="superior_to_all_three" if all(x["superiority_demonstrated"] for x in wind) else "not_demonstrated"
    storm=data[(data.variable=="wind_speed_10m")&(data.observed>=protocol.get("strong_threshold",15))]
    storm_dates=int(storm.init_time.nunique())
    storm_weeks=int(storm.init_time.dt.strftime("%G-%V").nunique()) if not storm.empty else 0
    result["observed_strong_ge15_cases"]=int(len(storm))
    result["observed_strong_ge15_dates"]=storm_dates
    result["observed_strong_ge15_weeks"]=storm_weeks
    storms_eligible=(len(storm)>=protocol.get("minimum_strong_cases",30) and
        storm_dates>=protocol.get("minimum_strong_dates",12) and
        storm_weeks>=protocol.get("minimum_strong_weeks",8))
    if storms_eligible:
        safety=[]
        for model in MODELS:
            ci=weekly_cluster_interval(storm,"FWA4A",model,draws,seed)
            missing_fwa=int(((storm.FWA4A<protocol.get("strong_threshold",15))).sum())
            missing_base=int(((storm[model]<protocol.get("strong_threshold",15))).sum())
            safety.append({"baseline":model,"strong_cases":int(len(storm)),
                "fwa_mae":float((storm.FWA4A-storm.observed).abs().mean()),
                "baseline_mae":float((storm[model]-storm.observed).abs().mean()),
                "delta_mae_familywise_ci":ci,
                "fwa_misses":missing_fwa,"baseline_misses":missing_base,
                "safety_pass":bool(ci is not None and ci[1]<=0 and missing_fwa<=missing_base)})
        result["storm_comparisons"]=safety
        result["strong_wind_safety"]="pass" if all(x["safety_pass"] for x in safety) else "not_demonstrated"
    result["status"]="evaluated"
    result["overall"]="superior_to_all_three_with_storm_safety" if (
        result["temperature_vs_three"]=="superior_to_all_three" and
        result["wind_average_vs_three"]=="superior_to_all_three" and
        result["strong_wind_safety"]=="pass") else "not_demonstrated"
    return result

def score(cache,lock_file):
    if sha(lock_file)!=LOCK_SHA:raise ValueError("Frozen winter lock SHA mismatch")
    p=json.loads(Path(lock_file).read_text())["protocol"]
    first=pd.Timestamp(p["first_issue"],tz="UTC");last=pd.Timestamp(p["last_issue"],tz="UTC")
    out={"status":"awaiting_eligible_archives","evaluation_type":"descriptive_read_only",
         "lock_sha256":LOCK_SHA,"data_source":"existing FWA winter exact-run retrospective checkpoints",
         "source_limitation":"Historical source retrieval cannot establish real-time publication availability",
         "final_protocol_minimum_dates":p["minimum_dates"],"complete_dates":0,
         "incomplete_dates":[],"comparisons":[],"station_lead_scores":[]}
    frames=[]
    for manifest in sorted(Path(cache).glob("????????.json")):
        m=json.loads(manifest.read_text());issue=pd.Timestamp(m["issue"])
        if issue.tzinfo is None or not first<=issue<=last:raise ValueError("Invalid winter issue")
        if m.get("lock_sha256")!=LOCK_SHA:raise ValueError("Checkpoint model lock mismatch")
        if not m.get("complete",False):
            out["incomplete_dates"].append(str(issue));continue
        paired=Path(cache)/(manifest.stem+"_paired.csv")
        if not paired.exists() or sha(paired)!=m.get("paired_sha256"):
            raise ValueError("Missing or tampered paired checkpoint")
        x=pd.read_csv(paired,dtype={"station_id":str})
        for t in ("init_time","valid_time"):x[t]=pd.to_datetime(x[t],utc=True,format="ISO8601")
        if len(x)!=18 or m.get("paired_cases")!=18 or x[list(KEY)].isna().any().any() or x.duplicated(list(KEY)).any():
            raise ValueError("Unexpected winter case count or duplicate keys")
        if not x.init_time.eq(issue).all() or not ((x.valid_time-x.init_time)==pd.to_timedelta(x.lead_hours,unit="h")).all():
            raise ValueError("Forecast initialization or validity mismatch")
        required={(s,v,l) for s in SITES for v,_ in VARIABLES for l in LEADS}
        if set(zip(x.station_id,x.variable,x.lead_hours))!=required:
            raise ValueError("Incomplete station/lead/variable grid")
        for var,candidate in VARIABLES:
            a=x[x.variable==var]
            if not np.isfinite(a[list(MODELS)+[candidate,"observed"]].to_numpy(dtype=float)).all():
                raise ValueError("Nonfinite input or observation")
        frames.append(x)
    if not frames:return out
    data=pd.concat(frames,ignore_index=True)
    if data.duplicated(list(KEY)).any():raise ValueError("Duplicate issue case")
    out["complete_dates"]=int(data.init_time.nunique())
    out["issue_dates"]=sorted(data.init_time.dt.strftime("%Y-%m-%d").unique().tolist())
    w=data[data.variable=="wind_speed_10m"]
    out["observed_wind_ge_10ms"]=int(w.observed.ge(10).sum())
    for var,candidate in VARIABLES:
        v=data[data.variable==var]
        for model in MODELS:
            fwa=(v[candidate]-v.observed).abs();baseline=(v[model]-v.observed).abs()
            out["comparisons"].append(dict(variable=var,candidate=candidate,baseline=model,
                cases=len(v),independent_issue_days=int(v.init_time.nunique()),
                fwa_mae=float(fwa.mean()),baseline_mae=float(baseline.mean()),
                delta_mae=float((fwa-baseline).mean()),
                per_issue_delta=[dict(issue=str(date),delta=float(((group[candidate]-group.observed).abs()-(group[model]-group.observed).abs()).mean()))
                    for date,group in v.groupby("init_time")],
                insufficient_for_final_inference=out["complete_dates"]<p["minimum_dates"]))
        for (site,lead),group in v.groupby(["station_id","lead_hours"]):
            out["station_lead_scores"].append(dict(variable=var,station=site,lead_hours=int(lead),
                cases=len(group),fwa_mae=float((group[candidate]-group.observed).abs().mean()),
                harmonie_mae=float((group["HARMONIE_DINI_OM"]-group.observed).abs().mean())))
    out["decision"]=judge(data,out,p)
    out["status"]="statistically_evaluated" if out["decision"]["coverage_eligible"] else "descriptive_only"
    return out

def main():
    ap=argparse.ArgumentParser()
    ap.add_argument("--cache",type=Path,default=Path("winter-cache"))
    ap.add_argument("--lock",type=Path,default=Path("config/fwa_winter_lock.json"))
    ap.add_argument("--out",type=Path,default=Path("outputs/fwa-winter/frozen_reference_scorecard.json"))
    args=ap.parse_args()
    result=score(args.cache,args.lock)
    args.out.parent.mkdir(parents=True,exist_ok=True)
    args.out.write_text(json.dumps(result,indent=2,allow_nan=False)+"\n")
    print(json.dumps(dict(status=result["status"],complete_dates=result["complete_dates"],comparisons=result["comparisons"]),indent=2))

if __name__=="__main__":main()
