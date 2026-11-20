"""Validate national Faroese DTM before exposing terrain covariates.
Source: Data from the Faroese Environment Agency, Umhvørvisstovan:
FO_DTM_2009_10m.tif. Terms: https://www.foroyakort.fo/um-foeroyakort/terms-and-conditions-in-english
"""
import json,hashlib,datetime
from pathlib import Path
import numpy as np
import rasterio
from rasterio.warp import transform_bounds
from pyproj import Transformer,Geod
from probe_weathernext_dynamical import STATIONS
URL="https://cdn.foroyakort.fo/geodata/raster/DTM/FO_DTM_2009_10m.tif"
# Independent geographic landmarks; broad tolerances account for raster sampling.
LANDMARKS=[("Slættaratindur",62.296,-7.012,700,900),("Torshavn vicinity",62.0231,-6.7647,-10,250),("Suduroy vicinity",61.3957,-6.6818,-10,350)]
def validate(path):
    geod=Geod(ellps="WGS84")
    with rasterio.open(path) as ds:
        if ds.crs is None or not ds.crs.is_projected or ds.count!=1:raise ValueError("Expected one projected terrain band")
        if ds.crs.linear_units.lower() not in ("metre","meter","metres","meters","m"):raise ValueError("Expected metric CRS")
        if not np.allclose(ds.res,(10,10),atol=.05):raise ValueError("Expected 10m resolution")
        west,south,east,north=transform_bounds(ds.crs,"EPSG:4326",*ds.bounds,densify_pts=41)
        if not (-9<west<-7.5 and -6.5<east<-5 and 60.5<south<61.5 and 62.35<north<63.5):raise ValueError(f"Not Faroese extent: {west,south,east,north}")
        tr=Transformer.from_crs("EPSG:4326",ds.crs,always_xy=True)
        def sample(lon,lat):
            xy=list(zip(*tr.transform(np.asarray(lon),np.asarray(lat))))
            arr=np.array([float(a[0]) if not np.ma.getmaskarray(a)[0] else np.nan for a in ds.sample(xy,masked=True)])
            arr[(arr< -20)|(arr>1000)]=np.nan
            return arr
        landmarks=[]
        for name,lat,lon,lo,hi in LANDMARKS:
            z=sample([lon],[lat])[0]
            if not np.isfinite(z) or not lo<=z<=hi:raise ValueError(f"Landmark elevation mismatch {name}: {z}")
            landmarks.append(dict(name=name,latitude=lat,longitude=lon,elevation_m=float(z)))
        profiles={}
        for sid,st in STATIONS.items():
            lat,lon=st["lat"],st["lon"]
            z=sample([lon],[lat])[0]
            if not np.isfinite(z):raise ValueError("Station lacks valid terrain: "+sid)
            angles=np.arange(0,360,5)
            distances=np.arange(100,2001,50)
            aa,dd=np.meshgrid(angles,distances,indexing="ij")
            xx,yy,_=geod.fwd(np.full(aa.size,lon),np.full(aa.size,lat),aa.ravel(),dd.ravel())
            terrain=sample(xx,yy).reshape(aa.shape)
            # Never silently replace missing land/sea cells with zero.
            slopes=np.degrees(np.arctan2(terrain-z,dd))
            sectors=[]
            for a in angles:
                mask=np.abs((angles-a+180)%360-180)<=15
                sub=slopes[mask]
                coverage=float(np.isfinite(sub).mean())
                sectors.append(dict(direction_deg=int(a),coverage=coverage,
                    shelter_deg=float(np.nanmax(sub)) if coverage>=.8 else None,
                    exposure_deg=float(-np.nanmean(sub)) if coverage>=.8 else None))
            profiles[sid]=dict(lat=lat,lon=lon,station_elevation_m=float(z),sectors=sectors)
        return dict(status="geography_verified",source=URL,attribution="Data from the Faroese Environment Agency, Umhvørvisstovan: FO_DTM_2009_10m.tif",retrieved_utc=datetime.datetime.now(datetime.timezone.utc).isoformat(),sha256=hashlib.sha256(Path(path).read_bytes()).hexdigest(),crs=ds.crs.to_string(),bounds_wgs84=[west,south,east,north],resolution_m=list(ds.res),landmarks=landmarks,stations=profiles)
def attach(frame,receipt):
    if receipt["status"]!="geography_verified":raise ValueError("unverified terrain")
    frame=frame.copy()
    vals=[]
    for row in frame.itertuples():
        deg=np.degrees(np.arctan2(row.sin,row.cos))%360
        sector=receipt["stations"][row.station_id]["sectors"][int(np.floor(deg/5+.5))%72]
        vals.append([sector["shelter_deg"],sector["exposure_deg"]])
    frame[["shelter","exposure"]]=np.asarray(vals,dtype=float)
    return frame.dropna(subset=["shelter","exposure"])
if __name__=="__main__":
    import sys
    p=Path(sys.argv[2]);p.parent.mkdir(parents=True,exist_ok=True)
    try:r=validate(sys.argv[1])
    except Exception as e:
        p.write_text(json.dumps({"status":"failed","source":URL,"error":str(e)},indent=2));raise
    p.write_text(json.dumps(r,indent=2))
