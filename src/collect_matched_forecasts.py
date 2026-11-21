"""Collect a *matched issue time* from ECMWF IFS and HARMONIE DINI.

This is a manual, scientific pilot. 0.25 degree IFS temperature/wind, single
HARMONIE issue; raw model files plus provenance remain in output artifact.
The system deliberately fails if both models cannot provide the same issue.
"""
import argparse, hashlib, json, math, re, sys, time
from datetime import datetime, timedelta, timezone
from pathlib import Path
import requests
import numpy as np
import pandas as pd

DMI="https://opendataapi.dmi.dk/v1/forecastedr/collections/harmonie_dini_sf"
SITES={"06009":{"lat":61.3957,"lon":-6.6818},"06011":{"lat":62.0231,"lon":-6.7647},"06014":{"lat":62.2995,"lon":-7.074}}
LEADS=(6,12,24)
def dmi_request(url,params=None):
    """DMI API calls are rate-limited. One request at a time, honor HTTP 429."""
    for attempt in range(5):
        time.sleep(2.5)
        response=requests.get(url,params=params,timeout=75)
        if response.status_code!=429:
            response.raise_for_status()
            return response
        header=response.headers.get("Retry-After","").strip()
        try:
            wait=max(5,min(120,float(header)))
        except ValueError:
            wait=min(120,15*(2**attempt))
        print(f"DMI HTTP 429 on attempt {attempt+1}/5; retry in {wait:.0f}s",file=sys.stderr,flush=True)
        if attempt<4:time.sleep(wait)
    raise RuntimeError("DMI API rate limit persisted through five polite retries")
def iso(t): return t.astimezone(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
def sha(path):return hashlib.sha256(Path(path).read_bytes()).hexdigest()
def pick_common_instance(ids,now,min_age_hours=15,max_age_hours=44):
    """Prefer mature issues, but recover from a temporary DMI inventory gap.

    A 12–15h issue is a fallback ONLY when no 15–44h issue is listed.
    Forecast issuance is never inferred: both sources must still provide the
    exact same 00/12 UTC run, and every requested lead is validated downstream.
    """
    mature=[]
    fallback=[]
    for item in ids:
        m=re.fullmatch(r"(\d{4}-\d{2}-\d{2}T\d{6}Z)",str(item))
        if not m:continue
        t=datetime.strptime(m.group(1),"%Y-%m-%dT%H%M%SZ").replace(tzinfo=timezone.utc)
        age=(now-t).total_seconds()/3600
        if t.hour not in (0,12) or t.minute!=0 or age>max_age_hours:
            continue
        if age>=min_age_hours:
            mature.append((t,item))
        elif min_age_hours==15 and age>=12:
            fallback.append((t,item))
    if mature:
        return max(mature)
    if fallback:
        selected=max(fallback)
        print(f"HARMONIE inventory fallback: using already-issued 00/12 UTC run {selected[1]} aged 12–15h; exact ECMWF issue and all leads remain mandatory",file=sys.stderr,flush=True)
        return selected
    raise ValueError("No available HARMONIE 00/12 UTC issue aged 12–44h (preferred 15–44h)")
def haversine(lat1,lon1,lat2,lon2):
    r1,r2=map(math.radians,[lat1,lat2]);dlat=r2-r1;dlon=math.radians(lon2-lon1)
    a=math.sin(dlat/2)**2+math.cos(r1)*math.cos(r2)*math.sin(dlon/2)**2
    return 12742*math.asin(min(1,math.sqrt(a)))
def harmonie_rows(payload,station,issue,source_id,expected_leads=LEADS):
    if payload.get("type")!="FeatureCollection":raise ValueError("Unexpected HARMONIE GeoJSON type")
    rows=[]
    for feat in payload.get("features",[]):
        props=feat.get("properties",{}); coords=feat.get("geometry",{}).get("coordinates",[])
        if len(coords)<2:raise ValueError("Missing forecast grid coordinates")
        d=haversine(station["lat"],station["lon"],float(coords[1]),float(coords[0]))
        if d>5:raise ValueError("HARMONIE grid point too far from station: %.3f km"%d)
        valid=pd.Timestamp(props["step"])
        if valid.tzinfo is None:raise ValueError("Unzoned HARMONIE time")
        valid=valid.tz_convert("UTC")
        lead=(valid-pd.Timestamp(issue)).total_seconds()/3600
        if lead not in expected_leads:continue
        for key,var,unit,convert in (("temperature-2m","temperature_2m","C",lambda x:x-273.15),("wind-speed-10m","wind_speed_10m","m/s",float)):
            if key not in props:raise ValueError("Missing HARMONIE parameter "+key)
            val=float(convert(float(props[key])))
            if not math.isfinite(val):raise ValueError("Non-finite HARMONIE value")
            rows.append({"station_id":station["id"],"model":"HARMONIE_DINI","variable":var,"unit":unit,"init_time":iso(issue),"valid_time":iso(valid.to_pydatetime()),"lead_hours":int(lead),"value":val,"grid_lat":float(coords[1]),"grid_lon":float(coords[0]),"grid_distance_km":d,"source_instance":source_id})
    if len(rows)!=2*len(expected_leads):raise ValueError("HARMONIE lacks requested lead/variable combination")
    return rows
def ecmwf_rows(grib,issue,variable,station):
    import xarray as xr
    ds=xr.open_dataset(str(grib),engine="cfgrib",backend_kwargs={"indexpath":""})
    try:
        names={"2t":"t2m","10u":"u10","10v":"v10"}
        v=names[variable]
        lon=station["lon"]%360 if float(ds.longitude.max())>180 else station["lon"]
        point=ds.sel(latitude=station["lat"],longitude=lon,method="nearest")
        if v not in point:raise ValueError("Missing ECMWF GRIB var "+v)
        val=float(point[v].values.item())
        if not math.isfinite(val):raise ValueError("Nonfinite ECMWF GRIB")
        return val,float(point.latitude.values.item()),float(point.longitude.values.item())
    finally:ds.close()
def collect(out,now,leads=LEADS,resolution="0p25"):
    from ecmwf.opendata import Client
    out=Path(out);(out/"raw"/"harmonie").mkdir(parents=True,exist_ok=True);(out/"raw"/"ecmwf").mkdir(parents=True,exist_ok=True)
    manifest={"fetched_at_utc":iso(now),"resolution":resolution,"requested_leads":list(leads),"status":"starting","files":[]}
    try:
        r=dmi_request(DMI+"/instances")
        path=out/"raw"/"harmonie"/"instances.json";path.write_bytes(r.content)
        manifest["files"].append({"path":str(path.relative_to(out)),"sha256":sha(path),"bytes":path.stat().st_size})
        j=r.json();instances=[x["id"] for x in j["instances"]]
        issue,source_id=pick_common_instance(instances,now)
        manifest.update(issue_time_utc=iso(issue),harmonie_instance=source_id)
        rows=[];client=Client(source="ecmwf",model="ifs",resol=resolution)
        grib={}
        for lead in leads:
            for field in ("2t","10u","10v"):
                dst=out/"raw"/"ecmwf"/f"ifs_{issue:%Y%m%dT%H}Z_{lead:03d}h_{field}.grib2"
                client.retrieve(date=issue.strftime("%Y-%m-%d"),time=issue.hour,stream="oper",type="fc",step=lead,param=field,levtype="sfc",target=str(dst))
                if not dst.exists() or dst.stat().st_size==0:raise ValueError("Empty ECMWF GRIB: "+str(dst))
                manifest["files"].append({"path":str(dst.relative_to(out)),"sha256":sha(dst),"bytes":dst.stat().st_size})
                grib[lead,field]=dst
        for sid,coords in SITES.items():
            station=dict(coords,id=sid)
            endpoint=f"{DMI}/instances/{source_id}/position"
            params={"coords":f"POINT({coords['lon']} {coords['lat']})","crs":"crs84","parameter-name":"temperature-2m,wind-speed-10m","f":"GeoJSON"}
            r=dmi_request(endpoint,params)
            raw=out/"raw"/"harmonie"/f"{source_id}_{sid}.json";raw.write_bytes(r.content)
            manifest["files"].append({"path":str(raw.relative_to(out)),"sha256":sha(raw),"bytes":raw.stat().st_size,"source_url":r.url})
            rows+=harmonie_rows(r.json(),station,issue,source_id,leads)
            for lead in leads:
                values={}
                for field in ("2t","10u","10v"):
                    values[field],lat,lon=ecmwf_rows(grib[lead,field],issue,field,station)
                valid=issue+timedelta(hours=lead)
                for variable,value,unit in (("temperature_2m",values["2t"]-273.15,"C"),("wind_speed_10m",math.hypot(values["10u"],values["10v"]),"m/s")):
                    rows.append({"station_id":sid,"model":"ECMWF_IFS","variable":variable,"unit":unit,"init_time":iso(issue),"valid_time":iso(valid),"lead_hours":lead,"value":value,"grid_lat":lat,"grid_lon":lon,"grid_distance_km":haversine(coords["lat"],coords["lon"],lat,lon),"source_instance":iso(issue)})
        df=pd.DataFrame(rows)
        key=["model","station_id","variable","init_time","valid_time"]
        if df.duplicated(key).any():raise ValueError("Duplicate key")
        count=2*len(SITES)*2*len(leads)
        if len(df)!=count:raise ValueError(f"Incomplete collection: {len(df)} != {count}")
        df.to_csv(out/"matched_forecasts.csv",index=False)
        manifest.update(status="success",forecast_rows=len(df),models=sorted(df.model.unique()),station_ids=sorted(SITES),notes="Actual DMI observations have NOT yet been joined. This is NOT an accuracy test.")
    except Exception as exc:
        manifest.update(status="failed",error=f"{type(exc).__name__}: {exc}")
        raise
    finally:
        (out/"manifest.json").write_text(json.dumps(manifest,indent=2,ensure_ascii=False),encoding="utf8")
def main():
    p=argparse.ArgumentParser();p.add_argument("--output",default="outputs/matched");a=p.parse_args()
    collect(a.output,datetime.now(timezone.utc))
if __name__=="__main__":main()
