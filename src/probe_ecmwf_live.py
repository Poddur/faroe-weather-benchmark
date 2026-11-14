"""Fetch exactly one recent ECMWF IFS surface GRIB and sample 3 Faroe points.

Probe is deliberately not a production archive or quality-controlled comparison.
Retrieval may be unavailable until a complete model issue is published.
"""
import argparse, hashlib, json, math, sys
from pathlib import Path
from datetime import datetime, timedelta, timezone
import numpy as np
STATIONS={"06009":(61.3957,-6.6818),"06011":(62.0231,-6.7647),"06014":(62.2995,-7.074)}
def choose_init(now):
    # Avoid partially published newest cycle: choose most recent 00/12 at least 14h old.
    dt=now-timedelta(hours=14)
    return dt.replace(hour=12 if dt.hour>=12 else 0,minute=0,second=0,microsecond=0)
def closest_grib(path):
    import xarray as xr
    ds=xr.open_dataset(str(path),engine="cfgrib",backend_kwargs={"indexpath":""})
    try:
        key="t2m"
        if key not in ds:raise ValueError("GRIB missing t2m; variables="+str(list(ds.data_vars)))
        points=[]
        for sid,(lat,lon) in STATIONS.items():
            coord=lon%360 if float(ds.longitude.max())>180 else lon
            p=ds.sel(latitude=lat,longitude=coord,method="nearest")
            value=float(p[key].values.item())-273.15
            plat=float(p.latitude.values.item());plon=float(p.longitude.values.item())
            if not math.isfinite(value):raise ValueError("Non-finite model temperature")
            points.append({"station_id":sid,"model_temperature_2m_C":value,"grid_lat":plat,"grid_lon":plon})
        return points
    finally:ds.close()
def main():
    p=argparse.ArgumentParser();p.add_argument("--output",default="outputs/ecmwf-probe");p.add_argument("--resolution",choices=["0p25","0p1"],default="0p25");p.add_argument("--step",type=int,default=6)
    a=p.parse_args();out=Path(a.output);out.mkdir(parents=True,exist_ok=True)
    now=datetime.now(timezone.utc);init=choose_init(now)
    manifest={"model":"ECMWF_IFS","source":"ecmwf-opendata","resolution":a.resolution,"init_time_utc":init.isoformat(),"step_hours":a.step,"station_coordinates_source":"DMI station metadata discovery, provisional geographic sampling","status":"starting"}
    path=out/"ecmwf_2t.grib2"
    try:
        from ecmwf.opendata import Client
        client=Client(source="ecmwf",model="ifs",resol=a.resolution)
        client.retrieve(date=init.strftime("%Y-%m-%d"),time=init.hour,stream="oper",type="fc",step=a.step,param="2t",levtype="sfc",target=str(path))
        if not path.exists() or not path.stat().st_size:raise RuntimeError("No GRIB downloaded")
        manifest.update(status="downloaded",bytes=path.stat().st_size,sha256=hashlib.sha256(path.read_bytes()).hexdigest())
        manifest["samples"]=closest_grib(path)
        manifest["status"]="parsed"
        print("ECMWF issue",init.isoformat(),"bytes",path.stat().st_size,"samples",len(manifest["samples"]))
    except Exception as e:
        manifest.update(status="failed",error=f"{type(e).__name__}: {e}")
        print("ECMWF probe failed:",str(e),file=sys.stderr)
    finally:
        (out/"manifest.json").write_text(json.dumps(manifest,indent=2),encoding="utf8")
    if manifest["status"]!="parsed":sys.exit(1)
if __name__=="__main__":main()
