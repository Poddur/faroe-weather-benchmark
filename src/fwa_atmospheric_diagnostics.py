"""Physical diagnostics from native GRIB point profiles, with explicit missing-data gates."""
import math,json
from pathlib import Path
G=9.80665
CP=1004.0
def diagnostics(z0,z1,t0,t1,u0,v0,u1,v1,barrier_m=None):
    dz=z1-z0
    if not 0<dz<=2000 or min(t0,t1)<180 or max(t0,t1)>330:raise ValueError("invalid profile")
    lapse=(t0-t1)/dz
    # Dry Brunt-Vaisala frequency approximation; not moist stability.
    n2=G/((t0+t1)/2)*(G/CP-lapse)
    shear=math.hypot(u1-u0,v1-v0)/dz
    speed=math.hypot(u1,v1)
    fr=speed/(math.sqrt(n2)*barrier_m) if n2>0 and barrier_m is not None and barrier_m>0 else None
    return dict(lapse_K_per_km=lapse*1000,vector_shear_per_s=shear,N2_dry_per_s2=n2,bulk_Ri=n2/shear**2 if shear>1e-6 else None,Froude_dry_proxy=fr)
def temp_correct(t,local_z,model_z,lapse_K_per_km):
    if not all(math.isfinite(x) for x in [t,local_z,model_z,lapse_K_per_km]):raise ValueError("nonfinite input")
    # Conservative research bounds; not calibrated physical laws.
    lapse=max(-10,min(12,lapse_K_per_km))
    return t+max(-2,min(2,-lapse*(local_z-model_z)/1000))
def analyze(rows,terrain):
    out=[]
    for sid,st in terrain["stations"].items():
        rr=[r for r in rows if r["station"]==sid and r["collection"]=="harmonie_dini_sf" and r.get("stepType")=="instant"]
        def pick(names,level,types,units):
            a=[r for r in rr if r["shortName"] in names and r["level"]==level and r["typeOfLevel"] in types and r["units"] in units]
            if len(a)!=1:raise ValueError(f"missing/ambiguous {names}/{level}: {len(a)}")
            return a[0]
        rec={"station":sid,"status":"missing"}
        try:
            z=pick(["z","orog","gh"],0,["surface","heightAboveGround"],["m","m**2 s**-2","m2 s-2","gpm"])
            model_z=z["value"]/G if z["units"] in ("m**2 s**-2","m2 s-2") else z["value"]
            def at(names,h,units):return pick(names,h,["heightAboveGround"],units)
            t0=at(["2t","t"],2,["K"]);t1=at(["t"],100,["K"])
            u0=at(["10u","u"],10,["m s**-1","m s-1"]);v0=at(["10v","v"],10,["m s**-1","m s-1"])
            u1=at(["u"],100,["m s**-1","m s-1"]);v1=at(["v"],100,["m s**-1","m s-1"])
            pts=[z,t0,t1,u0,v0,u1,v1]
            if len({(r["grid_lat"],r["grid_lon"],r["run"],r["valid"]) for r in pts})!=1:raise ValueError("different grid or forecast times")
            # Temperature and wind use different lower heights: compute separately.
            lapse=(t0["value"]-t1["value"])/98
            n2=G/((t0["value"]+t1["value"])/2)*(G/CP-lapse)
            shear=math.hypot(u1["value"]-u0["value"],v1["value"]-v0["value"])/90
            direction=math.degrees(math.atan2(-u1["value"],-v1["value"]))%360
            sector=st["sectors"][int(math.floor(direction/5+.5))%72]
            # Sector angle alone cannot identify the actual barrier height.
            rec.update(status="diagnostic",run=z["run"],valid=z["valid"],model_height_m=model_z,local_height_m=st["station_elevation_m"],lapse_K_per_km=lapse*1000,N2_dry_per_s2=n2,vector_shear_per_s=shear,bulk_Ri_proxy=n2/shear**2 if shear>1e-6 else None,wind_from_deg=direction,shelter_angle_deg=sector["shelter_deg"],Froude_dry_proxy=None,Froude_blocker="actual directional barrier height required",raw_temperature_C=t0["value"]-273.15,corrected_temperature_C=temp_correct(t0["value"]-273.15,st["station_elevation_m"],model_z,lapse*1000))
        except Exception as e:rec["error"]=str(e)
        out.append(rec)
    return out
if __name__=="__main__":
    import sys
    rows=json.loads(Path(sys.argv[1]).read_text());terrain=json.loads(Path(sys.argv[2]).read_text())
    Path(sys.argv[3]).write_text(json.dumps(analyze(rows,terrain),indent=2,allow_nan=False))
