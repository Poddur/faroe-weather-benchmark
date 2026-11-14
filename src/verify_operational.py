"""Inspect an operational collection and make machine-readable integrity evidence.

This checks only collection integrity and unit/time matching, NOT forecast skill.
"""
import argparse,hashlib,json
from pathlib import Path
import pandas as pd
def verify(path):
    root=Path(path);mf=root/"forecast"/"manifest.json"; report={"status":"failed","errors":[]}
    if not mf.exists():
        report["errors"].append("forecast manifest missing");return report
    data=json.loads(mf.read_text());report["issue_time_utc"]=data.get("issue_time_utc")
    for f in data.get("files",[]):
        filename=root/"forecast"/f["path"]
        if not filename.is_file(): report["errors"].append("missing "+str(filename));continue
        hash_=hashlib.sha256(filename.read_bytes()).hexdigest()
        if hash_!=f["sha256"] or filename.stat().st_size!=f["bytes"]:report["errors"].append("checksum/size mismatch "+str(filename))
    if data.get("status")!="success":report["errors"].append("collector manifest reports failure")
    csv=root/"forecast"/"matched_forecasts.csv"
    if csv.exists():
        forecast=pd.read_csv(csv,dtype={"station_id":str})
        expect={"ECMWF_IFS","HARMONIE_DINI"}
        if set(forecast.model)!=expect:report["errors"].append("forecast model set mismatch")
        keys=["station_id","variable","init_time","valid_time","lead_hours"]
        pairs=forecast.groupby(keys,dropna=False).model.nunique()
        if (pairs!=2).any():report["errors"].append("missing counterpart at same issue/lead/valid time")
        if forecast.duplicated(keys+["model"]).any():report["errors"].append("duplicate forecast key")
        report["forecast_rows"]=len(forecast)
        report["paired_forecast_cases"]=len(pairs)
    else: report["errors"].append("matched_forecasts.csv missing")
    o=root/"observations"/"observations.csv"
    if o.exists():
        obs=pd.read_csv(o,dtype={"station_id":str})
        if obs.duplicated(["station_id","variable","valid_time"]).any():report["errors"].append("duplicate observations")
        report["observation_rows"]=len(obs)
    else: report["errors"].append("observations.csv missing")
    report["raw_file_count"]=len(data.get("files",[]))
    report["status"]="pass" if not report["errors"] else "failed"
    return report
def main():
    p=argparse.ArgumentParser();p.add_argument("--root",default="outputs/operational");a=p.parse_args()
    root=Path(a.root);root.mkdir(parents=True,exist_ok=True)
    output=verify(root)
    (root/"verification.json").write_text(json.dumps(output,indent=2)+"\n")
    print(json.dumps(output,indent=2))
    if output["status"]!="pass":raise SystemExit(1)
if __name__=="__main__":main()
