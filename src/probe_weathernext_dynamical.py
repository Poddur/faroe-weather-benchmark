"""One bounded, credential-free WeatherNext 3 direct Icechunk historical probe.

Do not use dynamical.org's /v1/forecasts API for WN3: that API does
not support this product. The catalog's Zarr/Icechunk access is supported.
No background ingestion or read-all operations.
"""
import argparse, json, math, hashlib, sys, traceback
from datetime import datetime, timezone, timedelta
from pathlib import Path
import numpy as np
import pandas as pd

PRODUCT="google-weathernext3-forecast-15-day-0-1-degree-virtual"
CATALOG_URL="https://stac.dynamical.org/catalog.json"
STATIONS={
    "06009":{"name":"Sudur","lat":61.3957,"lon":-6.6818},
    "06011":{"name":"Torshavn","lat":62.0231,"lon":-6.7647},
    "06014":{"name":"Eidi","lat":62.2995,"lon":-7.0740},
}
VARIABLES={"temperature_2m":("temperature_2m","C"),
           "wind_speed_10m":("wind_speed_10m","m/s")}
def utc(t):return pd.Timestamp(t).tz_convert("UTC").strftime("%Y-%m-%dT%H:%M:%SZ")
def forecast_rows(ds,issue,lead_hours,station_ids=tuple(STATIONS)):
    """Fetch exactly six scalar values; protect from accidental whole-grid reads."""
    assert len(station_ids)<=3 and 1<=lead_hours<=48
    rows=[]
    init=pd.Timestamp(issue)
    if init.tzinfo is None:raise ValueError("issue must be UTC aware")
    issue64=init.tz_convert("UTC").tz_localize(None).to_datetime64()
    # x coordinates are 0...360 degrees, not negative longitudes.
    for station_id in station_ids:
        st=STATIONS[station_id]
        selectors={"init_time":issue64,"lead_time":pd.Timedelta(hours=lead_hours),
                   "statistic":"mean","y":st["lat"],"x":st["lon"]%360}
        for src,(variable,unit) in VARIABLES.items():
            scalar=ds[src].sel(
                init_time=selectors["init_time"],lead_time=selectors["lead_time"],
                statistic="mean").sel(y=st["lat"],x=st["lon"]%360,method="nearest")
            # Trigger a read only after we have selected all five axes.
            if scalar.ndim!=0:raise ValueError("Non-scalar slice; refusing broad remote read")
            value=float(scalar.values.item())
            if not math.isfinite(value):raise ValueError("Missing WeatherNext 3 value")
            latitude=float(scalar.y.values.item());longitude=float(scalar.x.values.item())
            longitude=longitude-360 if longitude>180 else longitude
            if abs(latitude-st["lat"])>0.11 or abs(longitude-st["lon"])>0.11:
                raise ValueError("Unreasonably distant selected grid cell")
            rows.append({"station_id":station_id,"model":"WeatherNext3","variable":variable,
                "value":value,"unit":unit,"init_time":utc(init),"valid_time":utc(init+pd.Timedelta(hours=lead_hours)),
                "lead_hours":lead_hours,"source_product":PRODUCT,"statistic":"mean",
                "grid_lat":latitude,"grid_lon":longitude,
                "notes":"historical archive retrieval; not independently confirmed original real-time publication"})
    if len(rows)!=len(station_ids)*len(VARIABLES):raise RuntimeError("Incomplete output")
    return rows
def main():
    p=argparse.ArgumentParser()
    p.add_argument("--issue",default="2026-11-14T00:00:00Z")
    p.add_argument("--lead",type=int,default=6)
    p.add_argument("--output",default="outputs/weathernext-direct-test")
    a=p.parse_args()
    out=Path(a.output);out.mkdir(parents=True,exist_ok=True)
    manifest={"source":"dynamical.org Icechunk / Google WeatherNext 3","catalog_url":CATALOG_URL,
      "product":PRODUCT,"requested_issue_utc":a.issue,"lead_hours":a.lead,
      "data_license_reference":"https://dynamical.org/catalog/"+PRODUCT+"/",
      "state":"started","expected_values":6,"dataset_product_type":"historical archive"}
    try:
        import dynamical_catalog
        ds=dynamical_catalog.open(PRODUCT,chunks=None)
        manifest["dimensions"]={k:int(v) for k,v in ds.sizes.items()}
        manifest["variables_available"]=sorted(list(ds.data_vars))
        manifest["variable_units"]={v:ds[v].attrs.get("units","not specified") for v in VARIABLES}
        for v in VARIABLES:
            if v not in ds.data_vars:raise ValueError("Catalog variable missing: "+v)
        records=forecast_rows(ds,a.issue,a.lead)
        frame=pd.DataFrame(records)
        path=out/"forecasts.csv";frame.to_csv(path,index=False)
        manifest.update(state="success",rows=len(frame),csv_sha256=hashlib.sha256(path.read_bytes()).hexdigest(),
                        retrieved_utc=datetime.now(timezone.utc).isoformat())
        print(frame[["station_id","variable","value","unit","init_time","valid_time"]].to_string(index=False),flush=True)
    except Exception as exc:
        manifest.update(state="failed",error=f"{type(exc).__name__}: {exc}",traceback=traceback.format_exc()[-6000:])
        raise
    finally:
        (out/"manifest.json").write_text(json.dumps(manifest,indent=2,default=str),encoding="utf8")
if __name__=="__main__":main()
