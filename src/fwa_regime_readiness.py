"""Prospective REGIME EVALUATION ONLY of frozen FWA geographic v2 dense cases.
Never train, refit, tune thresholds or choose days based on held-out outcomes.
"""
import json,argparse
from pathlib import Path
from collections import defaultdict
import numpy as np
MIN_DAYS=30;MIN_STATIONS=3
def read(history_path,geo_path):
    history=json.loads(Path(history_path).read_text());geo=json.loads(Path(geo_path).read_text())
    if history.get("algorithm")!="fixed_native_boundary_v2_new_sites":raise ValueError("Unexpected frozen physics candidate")
    sites=geo["stations"]
    out=[]
    for x in history.get("evidence",[]):
        if x.get("physics_prediction") is None:continue
        if x["station"] not in sites:raise ValueError("Unclassified station")
        v=dict(x)
        v["site_class"]=sites[x["station"]]["topographic_position"]
        v["coastal"]=bool(sites[x["station"]]["coastal"])
        v["date"]=x["valid"][:10]
        v["paired_delta_MAE"]=float(x["physics_abs_error"])-float(x["raw_abs_error"])
        if not np.isfinite(v["paired_delta_MAE"]):raise ValueError("Nonfinite forecast error")
        out.append(v)
    return out
def build(rows):
    groups=[]
    dimensions=["overall","station","site_class","coastal","wind_sector","forecast_strong_wind","observed_strong_wind","forecast_inversion","observation_source","lead_hours"]
    for variable in ("temp_dry","wind_speed"):
        subset=[x for x in rows if x["parameter"]==variable]
        for dim in dimensions:
            values=[None] if dim=="overall" else sorted(set(x.get(dim) for x in subset),key=str)
            for val in values:
                group=[x for x in subset if dim=="overall" or x.get(dim)==val]
                if not group:continue
                days=sorted(set(x["date"] for x in group));sites=set(x["station"] for x in group)
                eligible=len(days)>=MIN_DAYS and len(sites)>=MIN_STATIONS
                mean=float(np.mean([x["paired_delta_MAE"] for x in group]))
                ci=None
                if eligible:
                    clusters=defaultdict(list)
                    for x in group:clusters[x["date"]].append(x["paired_delta_MAE"])
                    c=list(clusters.values());rng=np.random.default_rng(20261121);bs=[]
                    for _ in range(2000):
                        ix=rng.integers(0,len(c),size=len(c));v=[e for i in ix for e in c[i]]
                        bs.append(np.mean(v))
                    ci=[float(np.quantile(bs,.025)),float(np.quantile(bs,.975))]
                groups.append(dict(variable=variable,dimension=dim,value=str(val),n=len(group),distinct_dates=len(days),distinct_stations=len(sites),stations=sorted(sites),raw_MAE=float(np.mean([x["raw_abs_error"] for x in group])),physics_MAE=float(np.mean([x["physics_abs_error"] for x in group])),paired_delta_MAE=mean,CI95_date_bootstrap=ci,eligible_for_descriptive_inference=eligible))
    strong=[r for r in rows if r["parameter"]=="wind_speed" and r.get("observed_strong_wind")]
    inversions=[r for r in rows if r.get("forecast_inversion")]
    # One modeled atmospheric profile per station/issue/validity: do not count
    # temperature and wind verification of the SAME atmosphere twice.
    unique_inversions={(r["run"],r["valid"],r["station"]) for r in inversions}
    conditions={"strong_observed":{"n":len(strong),"days":len(set(x["date"] for x in strong)),"stations":len(set(x["station"] for x in strong))},"forecast_inversions":{"n":len(unique_inversions),"days":len(set(x["date"] for x in inversions)),"stations":len(set(x["station"] for x in inversions))}}
    return dict(status="evaluation_only",distinct_dates=len(set(x["date"] for x in rows)),paired_cases=len(rows),groups=groups,conditions=conditions,readiness={"overall":any(x["eligible_for_descriptive_inference"] and x["dimension"]=="overall" for x in groups),"strong_wind":conditions["strong_observed"]["n"]>=30 and conditions["strong_observed"]["days"]>=10 and conditions["strong_observed"]["stations"]>=3,"inversion":conditions["forecast_inversions"]["n"]>=30 and conditions["forecast_inversions"]["days"]>=10 and conditions["forecast_inversions"]["stations"]>=3,"terrain_effect":False},limitations=["No evidence may be used for tuning this frozen candidate","With only 5 stations, geographical subgroup differences confounded with site identities; a future independent site replication is required before causal claims","Forecast-defined inversion is not directly observed inversion","METAR temperature/wind and DMI observed variables differ in sampling, time and sensor conditions","High-wind observed threshold is an EX POST regime, not permissible inference input","Dataset cannot establish best-model status without external baselines and seasonal skill evidence"])
def main():
    p=argparse.ArgumentParser();p.add_argument("--history",required=True);p.add_argument("--geography",required=True);p.add_argument("--output",required=True);a=p.parse_args()
    d=build(read(a.history,a.geography))
    Path(a.output).parent.mkdir(parents=True,exist_ok=True);Path(a.output).write_text(json.dumps(d,indent=2,allow_nan=False))
    print(json.dumps({k:v for k,v in d.items() if k!="groups"},indent=2))
if __name__=="__main__":main()
