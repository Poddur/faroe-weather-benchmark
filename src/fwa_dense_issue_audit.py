"""Recompute dense benchmark aggregate statistics with model-run dependence.
Never changes immutable observations, forecasts, station identifiers or predictions.
"""
import argparse,json
from pathlib import Path
from collections import defaultdict
import numpy as np
VERSION="fixed_native_boundary_v2_new_sites"
def correct_history(d):
    if d.get("algorithm")!=VERSION:raise ValueError("Wrong frozen candidate")
    evidence=d.get("evidence",[])
    for row in evidence:
        if "run" not in row or "valid" not in row:raise ValueError("missing forecast identity")
        if row["algorithm"]!=VERSION:raise ValueError("mixed model versions")
        if row.get("lead_hours") not in [6,12,18,24]:raise ValueError("not predeclared dense lead")
    for stat in d.get("summary",[]):
        variable=stat["variable"];dim=stat["group"];value=stat["label"]
        x=[r for r in evidence if r["parameter"]==variable and r["physics_prediction"] is not None and (dim=="overall" or str(r.get(dim))==value)]
        issue_dates=sorted(set(r["run"][:10] for r in x))
        stations=set(r["station"] for r in x)
        stat["unique_issue_days"]=len(issue_dates)
        stat["distinct_forecast_runs"]=len(set(r["run"] for r in x))
        stat["valid_dates"]=stat.get("days")
        stat["eligible"]=len(issue_dates)>=30 and len(stations)>=3
        ci=None
        if stat["eligible"]:
            clusters=defaultdict(list)
            for r in x:clusters[r["run"][:10]].append(r["physics_abs_error"]-r["raw_abs_error"])
            vals=list(clusters.values());rng=np.random.default_rng(20261121);bs=[]
            for _ in range(2000):
                picks=rng.integers(0,len(vals),size=len(vals))
                bs.append(float(np.mean([e for i in picks for e in vals[i]])))
            ci=[float(np.quantile(bs,.025)),float(np.quantile(bs,.975))]
        stat["paired_MAE_delta_CI95"]=ci
    d["independent_forecast_issue_days"]=len(set(r["run"][:10] for r in evidence))
    d["sampling_unit"]="originating forecast issue UTC date, NOT all valid dates or station-variable records"
    d["uncertainty"]="cluster bootstrap by model issue day, 2000 draws, fixed seed"
    d["readiness_gate"]="at least 30 different forecast issue dates and at least 3 stations within the reported group"
    return d
def main():
    p=argparse.ArgumentParser();p.add_argument("--input",required=True);p.add_argument("--output",required=True);a=p.parse_args()
    d=correct_history(json.loads(Path(a.input).read_text()))
    Path(a.output).write_text(json.dumps(d,indent=2,allow_nan=False))
    print(json.dumps({"forecast_issue_days":d["independent_forecast_issue_days"],"groups":[x for x in d["summary"] if x["group"]=="overall"]},indent=2))
if __name__=="__main__":main()
