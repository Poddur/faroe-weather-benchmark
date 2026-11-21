"""Strict immutable separate geographical benchmark v2 and regime scorecards."""
import argparse,json
from collections import defaultdict
from pathlib import Path
import numpy as np
from fwa_spatial_extension_v2 import VERSION,summarize
def update(prior,new):
    if prior and prior.get("algorithm")!=VERSION:raise ValueError("version mismatch: do not overwrite v1")
    evidence={tuple(r[k] for k in ("run","valid","station","parameter")):r for r in prior.get("evidence",[])}
    for row in new:
        if row.get("algorithm")!=VERSION:raise ValueError("unexpected model version")
        key=tuple(row[k] for k in ("run","valid","station","parameter"))
        if key in evidence and evidence[key]!=row:raise ValueError("immutable case changed: "+str(key))
        evidence[key]=row
    records=[evidence[k] for k in sorted(evidence)]
    stats=summarize(records)
    # Show confidence intervals only for pre-registered 30 independent dates + 3 stations.
    for stat in stats:
        stat["paired_MAE_delta_CI95"]=None
        subset=[x for x in records if x["parameter"]==stat["variable"] and x["physics_prediction"] is not None and (stat["group"]=="overall" or str(x[stat["group"]])==stat["label"])]
        days=sorted(set(x["valid"][:10] for x in subset));stations=set(x["station"] for x in subset)
        if len(days)<30 or len(stations)<3:continue
        buckets=defaultdict(list)
        for x in subset:buckets[x["valid"][:10]].append((x["physics_abs_error"]-x["raw_abs_error"],1))
        b=list(buckets.values());rng=np.random.default_rng(20261121);bs=[]
        for _ in range(2000):
            draw=rng.integers(0,len(b),size=len(b))
            vals=[p[0] for i in draw for p in b[i]]
            bs.append(float(np.mean(vals)))
        stat["paired_MAE_delta_CI95"]=[float(np.quantile(bs,.025)),float(np.quantile(bs,.975))]
    return dict(schema=2,algorithm=VERSION,evidence=records,summary=stats,policy=dict(min_dates=30,min_stations=3,hold_original_HARMONIE_unchanged=True,metar_max_lag_minutes=15,metar_future_reports_forbidden=True,source_comparability_warning="METAR and DMI instruments/reporting differ; station and source groups reported separately",status="exploratory_until_eligibility"))
def main():
    a=argparse.ArgumentParser();a.add_argument("--prior");a.add_argument("--new",required=True);a.add_argument("--output",required=True);opts=a.parse_args()
    prior=json.loads(Path(opts.prior).read_text()) if opts.prior and Path(opts.prior).exists() else {}
    new=json.loads(Path(opts.new).read_text())
    out=update(prior,new);Path(opts.output).write_text(json.dumps(out,indent=2,allow_nan=False))
    print(json.dumps({"observations":len(out["evidence"]),"overall":[x for x in out["summary"] if x["group"]=="overall"]},indent=2))
if __name__=="__main__":main()
