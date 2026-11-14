"""Probe availability of DMI observations without claiming verification."""
import csv,json,argparse,requests
from collections import Counter
from datetime import datetime,timedelta,timezone
from pathlib import Path

BASE="https://opendataapi.dmi.dk/v2/metObs/collections/observation/items"
STATIONS=["06007","06008","06009","06011","06012","06013","06014"]
PARAMETERS=["temp_dry","wind_speed","pressure_at_sea","precip_past1h"]
def probe(station,param,start,end):
    params={"stationId":station,"parameterId":param,"datetime":f"{start}/{end}","limit":1000}
    response=requests.get(BASE,params=params,timeout=60)
    response.raise_for_status()
    payload=response.json()
    features=payload.get("features",[])
    if not isinstance(features,list):raise ValueError("Unexpected DMI features")
    times=[f.get("properties",{}).get("observed") for f in features]
    nonempty=[t for t in times if t]
    flags=Counter(str(f.get("properties",{}).get("quality", "unspecified")) for f in features)
    return {"station_id":station,"parameter":param,"returned_first_page":len(features),"page_limit":1000,
            "potentially_more_pages":len(features)==1000,
            "earliest_on_page":min(nonempty) if nonempty else "",
            "latest_on_page":max(nonempty) if nonempty else "",
            "quality_values":json.dumps(dict(flags),sort_keys=True),
            "http_status":response.status_code}
def main():
    p=argparse.ArgumentParser();p.add_argument("--hours",type=int,default=24)
    p.add_argument("--out",default="data/observation_probe.csv");a=p.parse_args()
    if not 1<=a.hours<=168:raise ValueError("Hours must be 1..168")
    end=datetime.now(timezone.utc);start=end-timedelta(hours=a.hours)
    start_iso=start.strftime("%Y-%m-%dT%H:%M:%SZ");end_iso=end.strftime("%Y-%m-%dT%H:%M:%SZ")
    rows=[];errors=[]
    for station in STATIONS:
        for param in PARAMETERS:
            try: rows.append(probe(station,param,start_iso,end_iso))
            except Exception as exc:errors.append({"station_id":station,"parameter":param,"error":str(exc)})
    out=Path(a.out);out.parent.mkdir(parents=True,exist_ok=True)
    columns=["station_id","parameter","returned_first_page","page_limit","potentially_more_pages","earliest_on_page","latest_on_page","quality_values","http_status"]
    with out.open("w",newline="",encoding="utf8") as f:
        w=csv.DictWriter(f,fieldnames=columns);w.writeheader();w.writerows(rows)
    out.with_suffix(".metadata.json").write_text(json.dumps({"start_utc":start_iso,"end_utc":end_iso,"errors":errors,"successful_queries":len(rows)},indent=2),encoding="utf8")
    print(f"Probe: {len(rows)} successful queries, {len(errors)} errors, {sum(r['returned_first_page'] for r in rows)} observations on first pages")
    if errors:print(json.dumps(errors,ensure_ascii=False))
    if errors or not any(r["returned_first_page"] for r in rows):raise SystemExit(1)
if __name__=="__main__":main()
