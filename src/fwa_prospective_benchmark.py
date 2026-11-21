"""Pre-registered prospective benchmark of original native HARMONIE vs fixed terrain corrections.
Inputs must represent completed forecasts, not future-valid outputs. No learning or observations in inference.
"""
import argparse, json, hashlib, datetime as dt
from pathlib import Path
import numpy as np
from scipy.spatial import cKDTree
from probe_weathernext_dynamical import STATIONS

G=9.80665
PROFILE_PATH=Path("config/faroe_terrain_profiles.json")
PHYSICS_VERSION="fixed_native_boundary_v1"
# Research parameters frozen before prospective evaluation; not optimized on daily scores.
WIND_SHELTER_STRENGTH=0.15
WIND_LIMIT=(0.75,1.25)
TEMP_LIMIT_C=2.
def sphere(lat,lon):
    x=np.radians(np.asarray(lat,dtype=float));y=np.radians(np.asarray(lon,dtype=float))
    return np.column_stack((np.cos(x)*np.cos(y),np.cos(x)*np.sin(y),np.sin(x)))
def distance_km(chord):return 6371*2*np.arcsin(np.minimum(chord/2,1))
def correct(raw,terrain):
    """Point correction using native (model) orography and measured station terrain; no observed weather."""
    t2,t100,orog=[float(raw[k]) for k in ("t2_K","t100_K","orog_m")]
    if not (180<t2<330 and 180<t100<330 and -100<orog<1000):raise ValueError("unphysical native fields")
    lapse=np.clip((t2-t100)/98,-.01,.012)
    local_z=float(terrain["station_elevation_m"])
    if not -20<local_z<1000:raise ValueError("bad local elevation")
    corrected_temp=float(t2-273.15+np.clip(-lapse*(local_z-orog),-TEMP_LIMIT_C,TEMP_LIMIT_C))
    u10,v10,u100,v100=[float(raw[k]) for k in ("u10","v10","u100","v100")]
    raw_wind=float(np.hypot(u10,v10))
    dfrom=float(np.degrees(np.arctan2(-u100,-v100))%360)
    sector=terrain["sectors"][int(np.floor(dfrom/5+.5))%72]
    angle=sector.get("shelter_deg")
    wind=None
    if sector.get("coverage",0)>=.8 and angle is not None:
        factor=float(np.clip(1-WIND_SHELTER_STRENGTH*np.tanh(max(0,float(angle))/15),*WIND_LIMIT))
        wind=raw_wind*factor
    return dict(temperature_C=corrected_temp,wind_ms=wind,raw_temperature_C=t2-273.15,raw_wind_ms=raw_wind,wind_from_deg=dfrom,lapse_K_per_km=float(lapse*1000),source_model_orography_m=orog,station_terrain_m=local_z)
def make_records(source_npz,sidecar,obs_json,profiles_json):
    meta=json.loads(Path(sidecar).read_text())
    checksum=hashlib.sha256(Path(source_npz).read_bytes()).hexdigest()
    if checksum!=meta["sha256"] or meta["wind_components"]!="earth_relative":raise ValueError("source provenance or vector orientation invalid")
    if meta["units"]!={"orog_m":"m","t2_K":"K","t100_K":"K","u10":"m/s","v10":"m/s","u100":"m/s","v100":"m/s"}:raise ValueError("native units mismatch")
    issue=dt.datetime.fromisoformat(meta["run"].replace("Z","+00:00"))
    valid=dt.datetime.fromisoformat(meta["valid"].replace("Z","+00:00"))
    if valid<=issue:raise ValueError("nonforecast interval")
    profiles=json.loads(Path(profiles_json).read_text())["stations"]
    records=[]
    with np.load(source_npz) as a:
        keys=("orog_m","t2_K","t100_K","u10","v10","u100","v100")
        n=len(a["lat"])
        if any(a[k].shape!=(n,) or not np.isfinite(a[k]).all() for k in keys):raise ValueError("missing native grid fields")
        tree=cKDTree(sphere(a["lat"],a["lon"]))
        seen=set()
        for o in json.loads(Path(obs_json).read_text()):
            if "feature" not in o:continue
            sid=o["station"];parameter=o["parameter"]
            f=o["feature"];p=f["properties"]
            if p["stationId"]!=sid or p["parameterId"]!=parameter or p["observed"]!=meta["valid"] or o["valid"]!=meta["valid"]:raise ValueError("observation identity/time mismatch")
            unique=(sid,parameter,meta["valid"])
            if unique in seen:raise ValueError("duplicate observation")
            seen.add(unique)
            lon,lat=map(float,f["geometry"]["coordinates"])
            chord,i=tree.query(sphere([lat],[lon])[0])
            dist=float(distance_km(chord))
            if dist>5:raise ValueError("native grid too distant")
            raw={k:a[k][i].item() for k in keys}
            raw_temp=raw["t2_K"]-273.15;raw_wind=float(np.hypot(raw["u10"],raw["v10"]))
            value=float(p["value"])
            if not np.isfinite(value):raise ValueError("nonfinite observation")
            if parameter=="wind_speed" and not 0<=value<=65:continue
            if parameter=="temp_dry" and not -40<=value<=40:continue
            pred={"temperature_C":None,"wind_ms":None}
            terrain_distance_m=None;reason="no_terrain_profile"
            if sid in profiles:
                st=STATIONS[sid]
                km=float(distance_km(np.linalg.norm(sphere([lat],[lon])[0]-sphere([st["lat"]],[st["lon"]])[0])))
                terrain_distance_m=km*1000
                if km<=.25:
                    pred=correct(raw,profiles[sid]);reason="matched_terrain"
                else:reason="station_terrain_coordinate_mismatch"
            target="temperature_C" if parameter=="temp_dry" else "wind_ms"
            baseline=raw_temp if parameter=="temp_dry" else raw_wind
            revised=pred[target]
            if revised is not None and not np.isfinite(revised):raise ValueError("nonfinite corrected prediction")
            records.append(dict(station=sid,parameter=parameter,run=meta["run"],valid=meta["valid"],lead_hours=(valid-issue).total_seconds()/3600,observation=value,raw_prediction=float(baseline),physics_prediction=revised,raw_abs_error=abs(baseline-value),physics_abs_error=None if revised is None else abs(revised-value),terrain_match=reason,terrain_distance_m=terrain_distance_m,native_distance_km=dist,algorithm=PHYSICS_VERSION))
    return records
def aggregate(rows):
    output=[]
    for var in ("temp_dry","wind_speed"):
        a=[r for r in rows if r["parameter"]==var and r["physics_prediction"] is not None]
        b=[r for r in rows if r["parameter"]==var]
        if a:
            raw=float(np.mean([r["raw_abs_error"] for r in a]));new=float(np.mean([r["physics_abs_error"] for r in a]))
            improvement=100*(1-new/raw) if raw else None
        else:raw=new=improvement=None
        output.append(dict(parameter=var,matched=len(a),all_observed=len(b),raw_MAE=raw,physics_MAE=new,improvement_pct=improvement))
    return output
def main():
    p=argparse.ArgumentParser()
    p.add_argument("--input",required=True);p.add_argument("--meta",required=True);p.add_argument("--obs",required=True)
    p.add_argument("--profiles",default=str(PROFILE_PATH));p.add_argument("--output",required=True)
    a=p.parse_args();out=Path(a.output);out.mkdir(parents=True,exist_ok=True)
    rows=make_records(a.input,a.meta,a.obs,a.profiles)
    (out/"paired.json").write_text(json.dumps(rows,indent=2))
    scores=aggregate(rows)
    doc={"status":"scored","method":PHYSICS_VERSION,"records":len(rows),"scores":scores,"forecast_run":json.loads(Path(a.meta).read_text())["run"],"forecast_valid":json.loads(Path(a.meta).read_text())["valid"],"restrictions":"One forecast snapshot. Pre-registered fixed algorithm, no fit. Only same-station paired observations; do not infer scientific gain from a single day."}
    (out/"status.json").write_text(json.dumps(doc,indent=2))
    print(json.dumps(doc,indent=2))
if __name__=="__main__":main()
