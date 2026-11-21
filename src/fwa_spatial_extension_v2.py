"""Prospective FWA geographic extension v2; original HARMONIE is immutable control.
Observations are used ONLY for scoring, never for forecast corrections. Separate series from v1.
"""
import argparse,datetime as dt,hashlib,io,json,math
from pathlib import Path
import numpy as np,pandas as pd,requests
from scipy.spatial import cKDTree
from fwa_prospective_benchmark import correct,sphere,distance_km
VERSION="fixed_native_boundary_v2_new_sites"
NEW={"06012":{"lat":62.3195,"lon":-6.3205},"EKVG":{"lat":62.0664,"lon":-7.2847}}
def vagar_observations(valid):
    # IEM archive reports frequently at :20 and :50; only the last past report within 15 minutes is eligible.
    start=valid-dt.timedelta(days=1);end=valid+dt.timedelta(days=1)
    params=dict(station="EKVG",data=["tmpf","sknt","drct","metar"],year1=start.year,month1=start.month,day1=start.day,year2=end.year,month2=end.month,day2=end.day,tz="Etc/UTC",format="onlycomma",latlon="yes",elev="yes",missing="M",trace="T",report_type=[3,4])
    res=requests.get("https://mesonet.agron.iastate.edu/cgi-bin/request/asos.py",params=params,timeout=120);res.raise_for_status()
    df=pd.read_csv(io.BytesIO(res.content),comment="#",na_values=["M","T"])
    if not {"station","valid","tmpf","sknt","lat","lon","elevation"}.issubset(df.columns):raise ValueError("METAR archive schema changed")
    if df.empty: return [],{"status":"empty"}
    times=pd.to_datetime(df.valid,utc=True,errors="raise")
    prior=df.loc[(times<=pd.Timestamp(valid))&(times>=pd.Timestamp(valid-dt.timedelta(minutes=15)))].copy()
    if prior.empty:return [],{"status":"no_past_report_within_15min","reports":len(df)}
    prior["utc"]=pd.to_datetime(prior.valid,utc=True)
    mx=prior.utc.max();prior=prior[prior.utc==mx]
    if len(prior)!=1:raise ValueError("duplicate METAR time")
    p=prior.iloc[0]
    if p.station!="EKVG" or abs(float(p.lat)-NEW["EKVG"]["lat"])>.005 or abs(float(p.lon)-NEW["EKVG"]["lon"])>.005 or abs(float(p.elevation)-85)>5:raise ValueError("EKVG metadata mismatch")
    timestamp=mx.isoformat().replace("+00:00","Z")
    out=[]
    for parameter,raw,conv in [("temp_dry",p.tmpf,lambda x:(float(x)-32)*5/9),("wind_speed",p.sknt,lambda x:float(x)*0.5144444444444445)]:
        try:
            val=conv(raw)
            ok=math.isfinite(val) and ((-40<=val<=40) if parameter=="temp_dry" else (0<=val<=65))
            if ok:out.append(dict(station="EKVG",parameter=parameter,value=val,lat=float(p.lat),lon=float(p.lon),observed=timestamp,source="IEM METAR",time_offset_min=int((valid-mx.to_pydatetime()).total_seconds()/60)))
        except (TypeError,ValueError):pass
    return out,{"status":"past_only","selected_time":timestamp,"offset_minutes":int((valid-mx.to_pydatetime()).total_seconds()/60),"archive_reports":len(df)}
def dmi_observations(path,valid):
    out=[]
    for o in json.loads(Path(path).read_text()):
        if "feature" not in o:continue
        p=o["feature"]["properties"];sid=o["station"]
        if o["valid"]!=valid or p["stationId"]!=sid or p["parameterId"]!=o["parameter"] or p["observed"]!=valid:raise ValueError("DMI observation identity/timing")
        lat=o["feature"]["geometry"]["coordinates"][1];lon=o["feature"]["geometry"]["coordinates"][0]
        value=float(p["value"])
        if not math.isfinite(value):continue
        if (o["parameter"]=="temp_dry" and not -40<=value<=40) or (o["parameter"]=="wind_speed" and not 0<=value<=65):continue
        out.append(dict(station=sid,parameter=o["parameter"],value=value,lat=float(lat),lon=float(lon),observed=valid,source="DMI metObs",time_offset_min=0))
    return out
def evaluate(grid_file,meta_file,dmi_file,original_profile_file,new_profile_file,metar=True):
    meta=json.loads(Path(meta_file).read_text())
    if hashlib.sha256(Path(grid_file).read_bytes()).hexdigest()!=meta["sha256"] or meta["wind_components"]!="earth_relative":raise ValueError("invalid model archive")
    if meta["units"]!={"orog_m":"m","t2_K":"K","t100_K":"K","u10":"m/s","v10":"m/s","u100":"m/s","v100":"m/s"}:raise ValueError("invalid units")
    valid=dt.datetime.fromisoformat(meta["valid"].replace("Z","+00:00"))
    issue=dt.datetime.fromisoformat(meta["run"].replace("Z","+00:00"))
    if valid<=issue:raise ValueError("nonforecast")
    original=json.loads(Path(original_profile_file).read_text())["stations"]
    new=json.loads(Path(new_profile_file).read_text())["stations"]
    if set(new)!={"06012","EKVG"}:raise ValueError("unexpected new site profiles")
    profiles={**original,**new}
    obs=dmi_observations(dmi_file,meta["valid"])
    metar_a,metar_receipt=vagar_observations(valid) if metar else ([],{"status":"disabled"})
    obs+=metar_a
    seen=set();rows=[]
    with np.load(grid_file) as a:
        tree=cKDTree(sphere(a["lat"],a["lon"]))
        for o in obs:
            key=(o["station"],o["parameter"],meta["valid"])
            if key in seen:raise ValueError("duplicate station, variable, valid")
            seen.add(key);sid=o["station"]
            chord,i=tree.query(sphere([o["lat"]],[o["lon"]])[0]);grid_km=float(distance_km(chord))
            if grid_km>5:raise ValueError("too far from native model")
            raw={k:float(a[k][i]) for k in ["orog_m","t2_K","t100_K","u10","v10","u100","v100"]}
            baseline=raw["t2_K"]-273.15 if o["parameter"]=="temp_dry" else float(math.hypot(raw["u10"],raw["v10"]))
            terrain=profiles.get(sid)
            reason="no_verified_terrain";correction=None;direction=float(math.degrees(math.atan2(-raw["u100"],-raw["v100"]))%360)
            inversion=bool(raw["t100_K"]>raw["t2_K"])
            if terrain:
                km=float(distance_km(np.linalg.norm(sphere([o["lat"]],[o["lon"]])[0]-sphere([terrain["lat"]],[terrain["lon"]])[0])))
                if km<=.25:
                    c=correct(raw,terrain)
                    correction=c["temperature_C" if o["parameter"]=="temp_dry" else "wind_ms"]
                    reason="matched_terrain" if correction is not None else "insufficient_terrain_coverage"
                else:reason="station_coordinate_mismatch"
            speed=float(math.hypot(raw["u10"],raw["v10"]))
            heading=int(((direction+22.5)%360)//45)
            regimes=["N","NE","E","SE","S","SW","W","NW"]
            rows.append(dict(station=sid,parameter=o["parameter"],run=meta["run"],valid=meta["valid"],observation=o["value"],observation_time=o["observed"],observation_offset_minutes=o["time_offset_min"],observation_source=o["source"],raw_prediction=baseline,physics_prediction=correction,raw_abs_error=abs(baseline-o["value"]),physics_abs_error=abs(correction-o["value"]) if correction is not None else None,terrain_match=reason,model_grid_distance_km=grid_km,wind_from_deg=direction,wind_sector=regimes[heading],forecast_wind_ms=speed,observed_strong_wind=bool(o["parameter"]=="wind_speed" and o["value"]>=10),forecast_strong_wind=bool(speed>=10),forecast_inversion=inversion,vertical_temperature_difference_K=raw["t100_K"]-raw["t2_K"],algorithm=VERSION))
    return rows,metar_receipt
def summarize(rows):
    result=[]
    for variable in ["temp_dry","wind_speed"]:
        for group in ["overall","station","wind_sector","forecast_strong_wind","forecast_inversion"]:
            values=sorted(set([None if group=="overall" else x[group] for x in rows if x["parameter"]==variable]),key=str)
            for v in values:
                subset=[x for x in rows if x["parameter"]==variable and (group=="overall" or x[group]==v)]
                paired=[x for x in subset if x["physics_prediction"] is not None]
                n_days=len({x["valid"][:10] for x in paired})
                baseline=float(np.mean([x["raw_abs_error"] for x in paired])) if paired else None
                physics=float(np.mean([x["physics_abs_error"] for x in paired])) if paired else None
                result.append(dict(variable=variable,group=group,label=str(v),n=len(paired),all_observed=len(subset),days=n_days,raw_MAE=baseline,physics_MAE=physics,delta_MAE=physics-baseline if paired else None,eligible=n_days>=30 and len({x["station"] for x in paired})>=3))
    return result
def main():
    p=argparse.ArgumentParser()
    for name in ["input","meta","dmi","profiles","new-profiles","output"]:p.add_argument("--"+name,required=True)
    a=p.parse_args();out=Path(a.output);out.mkdir(parents=True,exist_ok=True)
    rows,metar=evaluate(a.input,a.meta,a.dmi,a.profiles,a.new_profiles)
    (out/"paired.json").write_text(json.dumps(rows,indent=2,allow_nan=False))
    d=dict(status="scored",algorithm=VERSION,observations=len(rows),paired=sum(x["physics_prediction"] is not None for x in rows),metar=metar,scores=summarize(rows),limitation="Exploratory new-site geographic proxies; forecast-defined inversion and wind regimes; METAR temperature integer precision and preceding-report timing differ from hourly DMI observations.")
    (out/"status.json").write_text(json.dumps(d,indent=2,allow_nan=False))
    print(json.dumps({k:v for k,v in d.items() if k!="scores"},indent=2))
if __name__=="__main__":main()
