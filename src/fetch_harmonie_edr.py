"""HARMONIE EDR point collector with explicit issue IDs and raw archives."""
import argparse,hashlib,json,math,re
from pathlib import Path
import requests,pandas as pd
BASE="https://opendataapi.dmi.dk/v1/forecastedr/collections"
FIELDS={"temperature-2m":("temperature_2m","C",lambda x:x-273.15),"wind-speed-10m":("wind_speed_10m","m/s",float)}
COLLECTIONS=["harmonie_dini_sf","harmonie_ig_sf"]
def get(url,params=None):
    r=requests.get(url,params=params,timeout=75);r.raise_for_status();return r.json()
def instances(d):return [r["id"] for r in d.get("instances",[]) if isinstance(r,dict) and "id" in r]
def runtime(inst):
    m=re.search(r"\d{4}-\d{2}-\d{2}T\d{6}Z",inst)
    if not m:raise ValueError("Unrecognized instance ID: "+inst)
    return pd.to_datetime(m.group(),format="%Y-%m-%dT%H%M%SZ",utc=True)
def parse(payload,station,init,leads,max_km=15):
    if payload.get("type")!="FeatureCollection" or not isinstance(payload.get("features"),list):
        raise ValueError("Unexpected GeoJSON")
    rows=[]
    for feat in payload["features"]:
        props=feat.get("properties",{});coords=feat.get("geometry",{}).get("coordinates",[])
        if len(coords)<2:raise ValueError("No returned grid point")
        lon,lat=map(float,coords[:2]);p1,p2=map(math.radians,[float(station.lat),lat]);dl=math.radians(lon-float(station.lon))
        a=math.sin((p2-p1)/2)**2+math.cos(p1)*math.cos(p2)*math.sin(dl/2)**2
        distance=12742*math.asin(min(1,math.sqrt(a)))
        if distance>max_km:raise ValueError("Out-of-domain/distant grid point: %.1f km"%distance)
        if "step" not in props:raise ValueError("Missing forecast valid time")
        valid=pd.to_datetime(props["step"],utc=True);lead=(valid-init).total_seconds()/3600
        if lead not in leads or lead<=0:continue
        for source,(var,unit,conv) in FIELDS.items():
            if source not in props or props[source] is None:continue
            value=conv(float(props[source]))
            if not math.isfinite(value):raise ValueError("Nonfinite forecast")
            rows.append(dict(station_id=str(station.station_id),variable=var,init_time=init.isoformat(),valid_time=valid.isoformat(),lead_hours=int(lead),model="HARMONIE",value=value,unit=unit,source_grid_lat=lat,source_grid_lon=lon,source_grid_distance_km=distance))
    return rows
def main():
    ap=argparse.ArgumentParser()
    ap.add_argument("--station-csv",required=True)
    ap.add_argument("--collection",choices=COLLECTIONS,default="harmonie_dini_sf")
    ap.add_argument("--output",required=True)
    ap.add_argument("--archive",default="raw/harmonie")
    ap.add_argument("--leads",type=int,nargs="+",default=[6,12,24,48])
    a=ap.parse_args();stations=pd.read_csv(a.station_csv,dtype={"station_id":str})
    archive=Path(a.archive);archive.mkdir(parents=True,exist_ok=True)
    out=Path(a.output);out.parent.mkdir(parents=True,exist_ok=True)
    data=get(f"{BASE}/{a.collection}/instances")
    (archive/f"{a.collection}_instances.json").write_text(json.dumps(data,indent=2),encoding="utf8")
    ids=sorted(instances(data))
    if not ids:raise RuntimeError("No published model run instances")
    rows=[];status=[]
    for inst in ids[-2:]:
        init=runtime(inst)
        for st in stations.itertuples(index=False):
            url=f"{BASE}/{a.collection}/instances/{inst}/position"
            params={"coords":f"POINT({st.lon} {st.lat})","crs":"crs84","f":"GeoJSON","parameter-name":",".join(FIELDS)}
            try:
                payload=get(url,params);path=archive/f"{a.collection}_{inst}_{st.station_id}.json"
                path.write_text(json.dumps(payload),encoding="utf8")
                parsed=parse(payload,st,init,set(a.leads))
                if not parsed:raise ValueError("No matching forecast steps or parameters")
                for row in parsed:row.update(source_collection=a.collection,source_instance=inst,raw_sha256=hashlib.sha256(path.read_bytes()).hexdigest())
                rows+=parsed;status.append((str(st.station_id),inst,"ok",len(parsed)))
            except (requests.RequestException,ValueError) as e:status.append((str(st.station_id),inst,str(e),0))
    pd.DataFrame(status,columns=["station_id","instance","status","rows"]).to_csv(out.with_suffix(".status.csv"),index=False)
    if not rows:raise RuntimeError("No HARMONIE data; check coverage/status")
    df=pd.DataFrame(rows)
    if df.duplicated(["station_id","variable","init_time","valid_time","model"]).any():raise ValueError("Duplicate forecast keys")
    df.to_csv(out,index=False)
if __name__=="__main__":main()
