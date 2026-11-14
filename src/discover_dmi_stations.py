"""Download official DMI station candidates; all are unverified until manually inspected."""
import argparse,csv,json
from pathlib import Path
import requests
URL="https://opendataapi.dmi.dk/v2/metObs/collections/station/items"
def parse(features):
    result=[]
    for f in features:
        p=f.get("properties",{});coords=f.get("geometry",{}).get("coordinates",[])
        if len(coords)<2 or not p.get("stationId"):continue
        result.append(dict(station_id=str(p["stationId"]),lon=coords[0],lat=coords[1],name=p.get("name",""),network=p.get("type",""),sensor_height_m="",notes="CANDIDATE: verify instrument height and period"))
    return result
def main():
    ap=argparse.ArgumentParser();ap.add_argument("--output",default="data/stations_candidates.csv");a=ap.parse_args()
    out=Path(a.output);out.parent.mkdir(parents=True,exist_ok=True);all_=[];offset=0
    while True:
        r=requests.get(URL,params={"bbox":"-8,61,-6,63","limit":1000,"offset":offset},timeout=60);r.raise_for_status()
        features=r.json().get("features",[]);all_+=features
        if len(features)<1000:break
        offset+=1000
        if offset>500000:raise RuntimeError("Pagination guard")
    out.with_suffix(".raw.json").write_text(json.dumps(all_,indent=2,ensure_ascii=False),encoding="utf8")
    rows={row["station_id"]:row for row in parse(all_)}
    with out.open("w",newline="",encoding="utf8") as f:
        w=csv.DictWriter(f,fieldnames=["station_id","lat","lon","name","network","sensor_height_m","notes"]);w.writeheader();w.writerows(rows.values())
    print("Candidates:",len(rows),"(not yet verified)",out)
if __name__=="__main__":main()
