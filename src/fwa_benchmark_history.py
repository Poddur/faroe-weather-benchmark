"""Accumulate immutable prospective paired evidence, no model tuning or peeking.
The GitHub workflow handles publishing this small aggregated JSON receipt.
"""
import argparse, json, math
from pathlib import Path
from collections import defaultdict
import numpy as np
VERSION="fixed_native_boundary_v1"
def update(existing,new):
    evidence=list(existing.get("evidence",[]))
    keys={(x["run"],x["valid"],x["station"],x["parameter"]) for x in evidence}
    for r in new:
        if r["algorithm"]!=VERSION:raise ValueError("algorithm version changed; start a distinct series")
        key=tuple(r[k] for k in ("run","valid","station","parameter"))
        if key in keys:
            other=next(x for x in evidence if tuple(x[k] for k in ("run","valid","station","parameter"))==key)
            if other!=r:raise ValueError("conflicting observation revision; manual review")
            continue
        keys.add(key);evidence.append(r)
    evidence.sort(key=lambda x:(x["valid"],x["station"],x["parameter"]))
    summary=[]
    for var in ("temp_dry","wind_speed"):
        a=[x for x in evidence if x["parameter"]==var and x["physics_prediction"] is not None]
        all_= [x for x in evidence if x["parameter"]==var]
        days=sorted({x["valid"][:10] for x in a})
        stations=sorted({x["station"] for x in a})
        raw=float(np.mean([x["raw_abs_error"] for x in a])) if a else None
        corrected=float(np.mean([x["physics_abs_error"] for x in a])) if a else None
        improvement=100*(1-corrected/raw) if raw else None
        # Bootstrap date-clusters only after the minimum evidence threshold; deterministic.
        ci=None
        if len(days)>=30 and len(stations)>=3:
            daily=defaultdict(list)
            for x in a:daily[x["valid"][:10]].append((x["raw_abs_error"],x["physics_abs_error"]))
            clusters=list(daily.values())
            rng=np.random.default_rng(20261121)
            deltas=[]
            for _ in range(2000):
                picks=rng.integers(0,len(clusters),size=len(clusters))
                pairs=[p for ix in picks for p in clusters[ix]]
                d=np.asarray(pairs)
                deltas.append(float(np.mean(d[:,1]-d[:,0])))
            ci=[float(np.quantile(deltas,.025)),float(np.quantile(deltas,.975))]
        summary.append(dict(parameter=var,all_observations=len(all_),paired=len(a),unique_dates=len(days),stations=stations,raw_MAE=raw,physics_MAE=corrected,improvement_pct=improvement,paired_MAE_delta_ci95=ci,conclusion="evaluation_eligible" if ci is not None else "insufficient_prospective_evidence"))
    return dict(schema=1,algorithm=VERSION,evidence=evidence,summary=summary,validation_policy={"minimum_distinct_dates":30,"minimum_stations":3,"uncertainty":"date cluster bootstrap 2000, deterministic seed","no_parameter_refitting":True,"comparison":"identical valid-time and station pairs"},provenance="DMI native HARMONIE past-valid forecasts and DMI metObs")
def main():
    p=argparse.ArgumentParser();p.add_argument("--prior");p.add_argument("--new",required=True);p.add_argument("--output",required=True);a=p.parse_args()
    prior=json.loads(Path(a.prior).read_text()) if a.prior and Path(a.prior).exists() else {}
    records=json.loads(Path(a.new).read_text())
    out=update(prior,records)
    Path(a.output).write_text(json.dumps(out,indent=2,allow_nan=False))
    print(json.dumps(out["summary"],indent=2))
if __name__=="__main__":main()
