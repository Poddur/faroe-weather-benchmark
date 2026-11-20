"""Bounded station discovery and observation coverage audit; no model changes."""
import json, time
from pathlib import Path
import requests
import pandas as pd
from fetch_dmi_observations import fetch
OUT=Path("outputs/station-audit")
BASE="https://opendataapi.dmi.dk/v2/metObs/collections/station/items"
KNOWN={"06007","06008","06009","06011","06013","06014"}
WINDOWS=[("2026-04-02","2026-04-04"),("2026-08-22","2026-08-24"),("2026-11-12","2026-11-14")]
PARAMS=["temp_dry","wind_speed","wind_dir"]
def main():
    OUT.mkdir(parents=True,exist_ok=True)
    receipt={"status":"started","registry_error":None,"stations":[],"probes":[],"bigquery_queries":0}
    try:
        registry=[]
        try:
            for page in range(20):
                resp=requests.get(BASE,params={"country":"FRO","limit":1000,"offset":page*1000},timeout=60)
                resp.raise_for_status()
                feats=resp.json()["features"]
                registry.extend(feats)
                if len(feats)<1000:break
            else:raise RuntimeError("registry pagination cap")
            registry=[f for f in registry if str(f["properties"].get("stationId","")).startswith("060") or f["properties"].get("country") in ("FRO","FO","Faroe Islands")]
        except Exception as e:receipt["registry_error"]=str(e)
        (OUT/"registry.json").write_text(json.dumps(registry,indent=2))
        ids=sorted(KNOWN|{str(f["properties"]["stationId"]) for f in registry if str(f["properties"].get("stationId","")).startswith("060")})
        receipt["stations"]=ids
        if len(ids)>40:raise ValueError("unexpected station count")
        for sid in ids:
            for start,end in WINDOWS:
                for param in PARAMS:
                    a=pd.Timestamp(start,tz="UTC");b=pd.Timestamp(end,tz="UTC")
                    record={"station_id":sid,"parameter":param,"start":start,"end_exclusive":end,"expected_hours":48}
                    try:
                        feats=list(fetch(sid,a.isoformat().replace("+00:00","Z"),b.isoformat().replace("+00:00","Z"),param))
                        ts=[];vals=[]
                        for f in feats:
                            p=f["properties"];t=pd.Timestamp(p["observed"])
                            if t.tzinfo is None:raise ValueError("missing timezone")
                            t=t.tz_convert("UTC")
                            if a<=t<b and t==t.floor("h") and p.get("value") is not None:
                                if str(p["stationId"])!=sid or p.get("parameterId")!=param:raise ValueError("identity mismatch")
                                v=float(p["value"])
                                if not __import__("math").isfinite(v):raise ValueError("nonfinite")
                                ts.append(t);vals.append(v)
                        record.update(hourly_unique=len(set(ts)),duplicates=len(ts)-len(set(ts)),raw_count=len(feats),min=min(vals) if vals else None,max=max(vals) if vals else None,status="ok")
                    except Exception as e:record.update(status="error",error=str(e)[:400])
                    receipt["probes"].append(record)
                    print(record,flush=True)
                    (OUT/"status.json").write_text(json.dumps(receipt,indent=2))
        receipt["status"]="audit_complete" if not any(p["status"]=="error" for p in receipt["probes"]) and not receipt["registry_error"] else "partial"
    except Exception as e:receipt.update(status="failed",error=str(e));raise
    finally:(OUT/"status.json").write_text(json.dumps(receipt,indent=2))
if __name__=="__main__":main()
