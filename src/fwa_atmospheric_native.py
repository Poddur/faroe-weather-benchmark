"""Native HARMONIE GRIB evidence extraction; bounded downloads, explicit units."""
import json, math, hashlib
from pathlib import Path
import requests
import numpy as np
from eccodes import codes_grib_new_from_file,codes_get,codes_grib_find_nearest,codes_release
from probe_weathernext_dynamical import STATIONS
OUT=Path("outputs/atmospheric")
BASE="https://opendataapi.dmi.dk/v1/forecastdata/collections"
MAX_BYTES=800*1024**2
def get(g,k):
    try:return codes_get(g,k)
    except Exception:return None
def download(url,path):
    if not url.startswith("https://dmi-opendata.s3.eu-north-1.amazonaws.com/forecastdata/"):raise ValueError("unexpected host")
    h=hashlib.sha256();n=0
    with requests.get(url,stream=True,timeout=(20,120)) as r:
        r.raise_for_status()
        with path.open("wb") as f:
            for b in r.iter_content(1024**2):
                n+=len(b)
                if n>MAX_BYTES:raise ValueError("download cap exceeded")
                h.update(b);f.write(b)
    return {"bytes":n,"sha256":h.hexdigest()}
def decode(path):
    rows=[];inventory=[]
    with path.open("rb") as f:
        while True:
            g=codes_grib_new_from_file(f)
            if g is None:break
            try:
                m={k:get(g,k) for k in ["shortName","name","units","typeOfLevel","level","dataDate","dataTime","validityDate","validityTime","stepType","stepRange","gridType","paramId"]}
                inventory.append(m)
                if m["shortName"] not in ("z","gh","orog","lsm","t","2t","u","v","10u","10v","r","2r","sp","pres","p","q","d","2d"):continue
                for sid,st in STATIONS.items():
                    p=codes_grib_find_nearest(g,st["lat"],st["lon"])[0]
                    value=float(p["value"])
                    if not math.isfinite(value) or abs(value)>1e19 or value==get(g,"missingValue"):continue
                    if float(p["distance"])>5:raise ValueError("nearest grid point exceeds 5 km")
                    rows.append(dict(m,station=sid,grid_lat=float(p["lat"]),grid_lon=float(p["lon"]),distance_km=float(p["distance"]),value=value))
            finally:codes_release(g)
    if not inventory:raise ValueError("empty GRIB")
    return inventory,rows
def main():
    OUT.mkdir(parents=True,exist_ok=True)
    receipt={"status":"started","files":[],"bigquery_queries":0}
    rows=[]
    try:
        # Match exactly the same run and valid time between SF and PL.
        inventories={}
        for collection in ["harmonie_dini_sf","harmonie_dini_pl"]:
            r=requests.get(f"{BASE}/{collection}/items",params={"limit":50},timeout=60);r.raise_for_status()
            inventories[collection]={(x["properties"]["modelRun"],x["properties"]["datetime"]):x for x in r.json()["features"]}
        common=sorted(set(inventories["harmonie_dini_sf"])&set(inventories["harmonie_dini_pl"]))
        if not common:raise ValueError("No common model run and validity in inventories")
        run,valid=common[-1]
        receipt.update(run=run,valid=valid)
        for collection,inv in inventories.items():
            x=inv[(run,valid)];url=x["asset"]["data"]["href"];path=OUT/(collection+".grib")
            rec={"collection":collection,"url":url}
            receipt["files"].append(rec)
            try:
                rec.update(download(url,path))
                fields,data=decode(path)
                rec.update(fields=fields,extracted_rows=len(data),status="decoded")
                rows.extend(dict(r,collection=collection,run=run,valid=valid) for r in data)
            finally:
                path.unlink(missing_ok=True)
                (OUT/"extracted.json").write_text(json.dumps(rows,indent=2))
                (OUT/"status.json").write_text(json.dumps(receipt,indent=2))
        receipt["status"]="decoded" if rows else "no_fields"
    except Exception as e:receipt.update(status="failed",error=str(e));raise
    finally:(OUT/"status.json").write_text(json.dumps(receipt,indent=2))
if __name__=="__main__":main()
