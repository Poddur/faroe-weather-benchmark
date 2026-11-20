"""Probe actual near-surface WeatherNext profiles and native DMI forecast inventory."""
import json,math
from pathlib import Path
import pandas as pd
import requests
from probe_weathernext_dynamical import PRODUCT,STATIONS
OUT=Path("outputs/physics2-native")
def main():
    OUT.mkdir(parents=True,exist_ok=True)
    receipt={"status":"started","bigquery_queries":0,"profiles":[]}
    try:
        import dynamical_catalog
        ds=dynamical_catalog.open(PRODUCT,chunks=None)
        try:
            fields=["wind_speed_10m","wind_speed_100m","wind_u_10m","wind_v_10m","wind_u_100m","wind_v_100m","temperature_2m","dew_point_temperature_2m","sea_surface_temperature","pressure_reduced_to_mean_sea_level","cloud_cover_low","downward_short_wave_radiation_flux_surface"]
            receipt["units"]={v:ds[v].attrs.get("units") for v in fields}
            for sid,st in STATIONS.items():
                for day in ["2026-08-22","2026-10-03","2026-11-12"]:
                    for lead in [6,12,24]:
                        rec=dict(station=sid,issue=day,lead=lead)
                        try:
                            point=ds[fields].sel(init_time=pd.Timestamp(day).to_datetime64(),lead_time=pd.Timedelta(hours=lead),statistic="mean").sel(y=st["lat"],x=st["lon"]%360,method="nearest")
                            rec.update(grid_lat=float(point.y.item()),grid_lon=float(point.x.item()))
                            if abs(rec["grid_lat"]-st["lat"])>.11 or abs(rec["grid_lon"]-st["lon"]%360)>.11:raise ValueError("grid mismatch")
                            for v in fields:
                                a=float(point[v].values.item())
                                rec[v]=a if math.isfinite(a) else None
                            rec["status"]="ok" if all(rec[v] is not None for v in fields[:8]) else "incomplete"
                        except Exception as e:rec.update(status="error",error=str(e)[:400])
                        receipt["profiles"].append(rec)
                        (OUT/"status.json").write_text(json.dumps(receipt,indent=2))
        finally:ds.close()
    except Exception as e:receipt["weathernext_error"]=str(e)[:500]
    receipt["dmi_inventory"]=[]
    for collection in ["harmonie_dini","harmonie_dini_sf","harmonie_dini_pl"]:
        rec={"collection":collection}
        try:
            url=f"https://opendataapi.dmi.dk/v1/forecastdata/collections/{collection}/items"
            resp=requests.get(url,params={"limit":3},timeout=60)
            rec.update(http=resp.status_code,url=resp.url)
            (OUT/f"{collection}.json").write_bytes(resp.content)
            resp.raise_for_status()
            rec["features"]=resp.json().get("features",[])
        except Exception as e:rec["error"]=str(e)[:500]
        receipt["dmi_inventory"].append(rec)
    receipt["status"]="probe_complete"
    (OUT/"status.json").write_text(json.dumps(receipt,indent=2,default=str))
if __name__=="__main__":main()
