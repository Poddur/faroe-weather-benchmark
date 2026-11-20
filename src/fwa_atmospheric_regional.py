"""Extract one completed native HARMONIE regional snapshot, with no future-valid output.
DMI Open Data, CC BY 4.0; regional subset, geopotential conversion, optional wind rotation.
"""
import datetime as dt, json, hashlib
from pathlib import Path
import requests,numpy as np
from eccodes import codes_grib_new_from_file,codes_get,codes_get_array,codes_get_values,codes_release
from pyproj import Proj
from fwa_atmospheric_native import download,BASE
from fetch_dmi_observations import fetch
OUT=Path("outputs/atmospheric-regional")
FIELDS={("z",0):("orog_m","m**2 s**-2"),("2t",2):("t2_K","K"),("t",100):("t100_K","K"),("10u",10):("u10","m s**-1"),("10v",10):("v10","m s**-1"),("u",100):("u100","m s**-1"),("v",100):("v100","m s**-1"),("10si",10):("native_speed","m s**-1"),("10wdir",10):("native_direction","Degree true")}
UNITS={"orog_m":"m","t2_K":"K","t100_K":"K","u10":"m/s","v10":"m/s","u100":"m/s","v100":"m/s"}
def iso(t):return t.strftime("%Y-%m-%dT%H:%M:%SZ")
def gribtime(g,date,time):return dt.datetime.strptime(str(codes_get(g,date))+str(codes_get(g,time)).zfill(4),"%Y%m%d%H%M").replace(tzinfo=dt.timezone.utc)
def decode(path,issue,valid):
    a={};flags={};geo=None;mask=None;projection=None
    with path.open("rb") as f:
        while True:
            g=codes_grib_new_from_file(f)
            if g is None:break
            try:
                key=(codes_get(g,"shortName"),codes_get(g,"level"))
                if key not in FIELDS or codes_get(g,"typeOfLevel")!="heightAboveGround":continue
                name,unit=FIELDS[key]
                if codes_get(g,"units")!=unit or codes_get(g,"stepType")!="instant":raise ValueError("wrong field unit or step: "+name)
                if gribtime(g,"dataDate","dataTime")!=issue or gribtime(g,"validityDate","validityTime")!=valid:raise ValueError("GRIB time mismatch")
                if name in a:raise ValueError("duplicate field "+name)
                lat=np.asarray(codes_get_array(g,"latitudes"));lon=(np.asarray(codes_get_array(g,"longitudes"))+180)%360-180
                m=(lat>=60.95)&(lat<=62.75)&(lon>=-8.6)&(lon<=-5.15)
                if geo is None:geo=(lat[m],lon[m]);mask=m
                elif not (np.array_equal(geo[0],lat[m]) and np.array_equal(geo[1],lon[m])):raise ValueError("grid coordinates differ")
                values=np.asarray(codes_get_values(g))[m]
                if not np.isfinite(values).all() or np.any(abs(values)>1e19) or np.any(values==codes_get(g,"missingValue")):raise ValueError("missing values "+name)
                a[name]=values
                if name in ("u10","v10","u100","v100"):
                    flags[name]=int(codes_get(g,"uvRelativeToGrid"))
                    if flags[name]==1:
                        if codes_get(g,"gridType")!="lambert":raise ValueError("unsupported grid-relative wind projection")
                        p={k:float(codes_get(g,k)) for k in ["LoVInDegrees","Latin1InDegrees","Latin2InDegrees","LaDInDegrees"]}
                        if projection is not None and p!=projection:raise ValueError("different wind projections")
                        projection=p
            finally:codes_release(g)
    if set(a)!=set(v[0] for v in FIELDS.values()):raise ValueError("missing fields "+str(set(v[0] for v in FIELDS.values())-set(a)))
    if len(set(flags.values()))!=1 or list(flags.values())[0] not in (0,1):raise ValueError("ambiguous wind component orientation")
    a["lat"],a["lon"]=geo;a["orog_m"]/=9.80665
    mag=np.hypot(a["u10"],a["v10"]); noncalm=(mag>1)&(a["native_speed"]>1)
    if noncalm.sum()<20:raise ValueError("inadequate noncalm wind direction checks")
    def angle_error(u,v):
        d=np.degrees(np.arctan2(-u,-v))%360
        return np.abs((d-a["native_direction"]+180)%360-180)[noncalm]
    rotation="none"
    if list(flags.values())[0]==1:
        p=projection
        proj=Proj(proj="lcc",lon_0=p["LoVInDegrees"],lat_0=p["LaDInDegrees"],lat_1=p["Latin1InDegrees"],lat_2=p["Latin2InDegrees"],R=6371229)
        gamma=np.radians(np.asarray(proj.get_factors(a["lon"],a["lat"]).meridian_convergence))
        options=[]
        for sign in [-1,1]:
            c=np.cos(gamma);s=np.sin(sign*gamma);u=a["u10"]*c-a["v10"]*s;v=a["u10"]*s+a["v10"]*c
            options.append((float(np.percentile(angle_error(u,v),95)),sign,c,s))
        options.sort(key=lambda x:x[0]);_,sign,c,s=options[0]
        for h in ["10","100"]:
            u=a["u"+h].copy();v=a["v"+h].copy()
            a["u"+h]=u*c-v*s;a["v"+h]=u*s+v*c
        rotation=f"lambert convergence sign {sign}; checked against native true direction"
    e=angle_error(a["u10"],a["v10"])
    speed_error=abs(np.hypot(a["u10"],a["v10"])-a["native_speed"])
    if np.percentile(e,95)>2 or np.percentile(speed_error,95)>.3:raise ValueError(f"wind direction/speed validation failed {np.percentile(e,95)} {np.percentile(speed_error,95)}")
    return a,dict(wind_flags=flags,rotation=rotation,direction_error_p95_deg=float(np.percentile(e,95)),speed_error_p95_ms=float(np.percentile(speed_error,95)))
def main():
    OUT.mkdir(parents=True,exist_ok=True)
    r={"status":"started","bigquery_queries":0};path=OUT/"source.grib"
    try:
        now=dt.datetime.now(dt.timezone.utc);issue=now.replace(hour=now.hour//3*3,minute=0,second=0,microsecond=0)-dt.timedelta(hours=12);valid=issue+dt.timedelta(hours=6)
        assert valid<now-dt.timedelta(hours=3)
        q=requests.get(BASE+"/harmonie_dini_sf/items",params={"modelRun":iso(issue),"datetime":iso(valid),"limit":5},timeout=60);q.raise_for_status()
        fs=[x for x in q.json()["features"] if x["properties"]["modelRun"]==iso(issue) and x["properties"]["datetime"]==iso(valid)]
        if len(fs)!=1:raise ValueError("exact past forecast unavailable")
        r.update(issue=iso(issue),valid=iso(valid),url=fs[0]["asset"]["data"]["href"])
        r["source"]=download(r["url"],path)
        a,checks=decode(path,issue,valid);r.update(checks=checks,native_cells=len(a["lat"]))
        target=OUT/"native_grid.npz";np.savez_compressed(target,**a)
        meta=dict(run=iso(issue),valid=iso(valid),sha256=hashlib.sha256(target.read_bytes()).hexdigest(),units=UNITS,wind_components="earth_relative",attribution="Danish Meteorological Institute (DMI) Open Data Forecasts, "+iso(now),license="https://creativecommons.org/licenses/by/4.0/",source_url=r["url"],changes="Regional subset; geopotential divided by standard gravity; grid-relative wind rotated when required.",checks=checks)
        (OUT/"native_grid.json").write_text(json.dumps(meta,indent=2))
        r["status"]="regional_decoded"
        obs=[]
        for sid in ["06009","06011","06012","06014"]:
            for param in ["temp_dry","wind_speed"]:
                try:
                    features=list(fetch(sid,iso(valid),iso(valid+dt.timedelta(minutes=1)),param))
                    matches=[x for x in features if x["properties"]["stationId"]==sid and x["properties"]["parameterId"]==param and dt.datetime.fromisoformat(x["properties"]["observed"].replace("Z","+00:00"))==valid]
                    if len(matches)==1:obs.append({"station":sid,"parameter":param,"valid":iso(valid),"feature":matches[0]})
                    else:obs.append({"station":sid,"parameter":param,"status":"missing_or_duplicate","matches":len(matches)})
                except Exception as e:obs.append({"station":sid,"parameter":param,"status":"error","error":str(e)[:300]})
        (OUT/"observations.json").write_text(json.dumps(obs,indent=2))
        r["observation_matches"]=sum("feature" in x for x in obs)
    except Exception as e:r.update(status="failed",error=str(e));raise
    finally:
        path.unlink(missing_ok=True);(OUT/"status.json").write_text(json.dumps(r,indent=2))
if __name__=="__main__":main()
