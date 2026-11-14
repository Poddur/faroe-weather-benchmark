"""Read-only live availability/format probe for DMI HARMONIE EDR.

Never relabel a model run; never treat a latest-run response as evidence of an
issue time. Probe tries documented singular '/instance' first and records status.
"""
import argparse, json, hashlib, re, sys
from pathlib import Path
from datetime import datetime, timezone
from urllib.parse import quote
import requests

ROOT="https://opendataapi.dmi.dk/v1/forecastedr/collections"
COLLECTIONS=("harmonie_nea_sf","harmonie_dini_sf","harmonie_ig_sf")
STATIONS={"06009":(-6.6818,61.3957),"06011":(-6.7647,62.0231),"06014":(-7.074,62.2995)}
PARAMS=("temperature-2m","wind-speed-10m","pressure-sealevel")
def request(url,params=None):
    try:
        r=requests.get(url,params=params,timeout=75,headers={"Accept":"application/json"})
        try: body=r.json()
        except ValueError: body={"non_json_body_preview":r.text[:1000]}
        return {"status":r.status_code,"url":r.url,"body":body}
    except requests.RequestException as e:
        return {"status":None,"url":url,"transport_error":str(e),"body":{}}
def summarize(reply):
    data=reply.get("body",{})
    if not isinstance(data,dict):return {"schema_type":type(data).__name__}
    features=data.get("features",[])
    summary={"schema_type":data.get("type"),"error_title":data.get("title"),"features":len(features) if isinstance(features,list) else None}
    if isinstance(features,list) and features:
        first=features[0]
        props=first.get("properties",{})
        summary.update(properties=list(props),sample_step=props.get("step"),sample_grid=first.get("geometry",{}).get("coordinates"))
    return summary
def main():
    p=argparse.ArgumentParser();p.add_argument("--output",default="outputs/harmonie-probe");args=p.parse_args()
    out=Path(args.output);out.mkdir(parents=True,exist_ok=True)
    catalog=request(ROOT);(out/"catalog.json").write_text(json.dumps(catalog,indent=2,ensure_ascii=False))
    records=[]
    catalog_list=[]
    if isinstance(catalog.get("body"),dict):
        catalog_list=[c.get("id") for c in catalog["body"].get("collections",[]) if isinstance(c,dict)]
    for collection in COLLECTIONS:
        meta=request(f"{ROOT}/{collection}")
        (out/f"{collection}_metadata.json").write_text(json.dumps(meta,indent=2,ensure_ascii=False))
        if meta["status"]!=200:
            records.append({"model":collection,"endpoint":"metadata","status":meta["status"],"details":summarize(meta)})
            continue
        for station,(lon,lat) in STATIONS.items():
            params={"coords":f"POINT({lon} {lat})","crs":"crs84","parameter-name":",".join(PARAMS[:2]),"f":"GeoJSON"}
            response=request(f"{ROOT}/{collection}/position",params)
            (out/f"{collection}_{station}_latest.json").write_text(json.dumps(response,indent=2,ensure_ascii=False))
            records.append({"model":collection,"station_id":station,"endpoint":"latest_position","status":response["status"],"details":summarize(response)})
        # These are exploratory and must not be promoted to proven issue times.
        for path in ("instances","instance"):
            response=request(f"{ROOT}/{collection}/{path}")
            (out/f"{collection}_{path}_listing.json").write_text(json.dumps(response,indent=2,ensure_ascii=False))
            records.append({"model":collection,"endpoint":path,"status":response["status"],"details":{"keys":list(response["body"]) if isinstance(response["body"],dict) else []}})
    (out/"summary.json").write_text(json.dumps({"run_utc":datetime.now(timezone.utc).isoformat(),"catalog_http":catalog["status"],"listed_collections":catalog_list,"results":records},indent=2,ensure_ascii=False))
    found=[r for r in records if r["endpoint"]=="latest_position" and r["status"]==200 and r["details"].get("features",0)>0]
    print("HARMONIE successful point responses:",len(found))
    for rec in records:print(rec["model"],rec.get("station_id",""),rec["endpoint"],rec["status"],rec["details"].get("features",""))
    if not found:sys.exit("No valid HARMONIE point forecasts; inspect uploaded diagnostics.")
if __name__=="__main__":main()
