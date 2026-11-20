"""Bounded exact-run physics input probe; never fit or modify frozen models."""
import json,math,time
from pathlib import Path
import requests
import pandas as pd
from probe_weathernext_dynamical import PRODUCT,STATIONS
from fwa_historical_pilot import URL
OUT=Path("outputs/physics2")
DATES=["2026-08-22","2026-10-03","2026-11-12"]
MODELS=["ecmwf_ifs","dmi_harmonie_arome_europe"]
LEVELS=[1000,925,850]
def main():
    OUT.mkdir(parents=True,exist_ok=True)
    status={"status":"started","probes":[],"bigquery_queries":0}
    try:
        for sid,st in STATIONS.items():
            for day in DATES:
                for model in MODELS:
                    for kind,variables in [("surface",["temperature_2m","wind_speed_10m","wind_direction_10m","surface_pressure"]),("vertical",[f"{v}_{p}hPa" for p in LEVELS for v in ["temperature","geopotential_height","wind_speed","wind_direction"]])]:
                        rec=dict(station=sid,issue=day,model=model,kind=kind)
                        try:
                            params=dict(latitude=st["lat"],longitude=st["lon"],run=day+"T00:00",models=model,hourly=",".join(variables),wind_speed_unit="ms",timezone="GMT",forecast_days=2,cell_selection="nearest",elevation="nan")
                            resp=requests.get(URL,params=params,timeout=90)
                            rec["http"]=resp.status_code
                            rec["url"]=resp.url
                            path=OUT/f"{sid}_{day}_{model}_{kind}.json"
                            path.write_bytes(resp.content)
                            resp.raise_for_status()
                            j=resp.json()
                            h=j["hourly"];u=j["hourly_units"]
                            rec.update(elevation=j.get("elevation"),latitude=j.get("latitude"),longitude=j.get("longitude"),units=u,coverage={})
                            for v in variables:
                                vals=[]
                                for lead in [6,12,24]:
                                    t=(pd.Timestamp(day)+pd.Timedelta(hours=lead)).strftime("%Y-%m-%dT%H:%M")
                                    a=h.get(v,[None]*len(h["time"]))[h["time"].index(t)]
                                    vals.append(a if isinstance(a,(int,float)) and math.isfinite(a) else None)
                                rec["coverage"][v]=vals
                            rec["status"]="response_received"
                        except Exception as e:rec.update(status="error",error=str(e)[:500])
                        status["probes"].append(rec)
                        (OUT/"status.json").write_text(json.dumps(status,indent=2,allow_nan=False))
                        time.sleep(2)
        try:
            import dynamical_catalog
            ds=dynamical_catalog.open(PRODUCT,chunks=None)
            try:status["weathernext_surface"]={k:{"dims":list(v.dims),"units":v.attrs.get("units")} for k,v in ds.data_vars.items()}
            finally:ds.close()
            try:
                ds=dynamical_catalog.open(PRODUCT,group="pressure_level",chunks=None)
                try:status["weathernext_pressure"]={k:{"dims":list(v.dims),"units":v.attrs.get("units")} for k,v in ds.data_vars.items()}
                finally:ds.close()
            except Exception as e:status["weathernext_pressure_error"]=str(e)[:500]
        except Exception as e:status["weathernext_error"]=str(e)[:500]
        status["status"]="probe_complete"
    finally:(OUT/"status.json").write_text(json.dumps(status,indent=2,default=str))
if __name__=="__main__":main()
