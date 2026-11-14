"""Retrieve recent ECMWF IFS 0.1-degree GRIB. NOT historical reforecasts."""
import argparse
from pathlib import Path
import pandas as pd
import numpy as np
def extract(path,param,station_lat,station_lon):
    import xarray as xr
    ds=xr.open_dataset(path,engine="cfgrib")
    try:
        actual={"2t":"t2m","10u":"u10","10v":"v10","msl":"msl"}.get(param,param)
        if actual not in ds:raise ValueError(f"Missing {actual} in GRIB; got {list(ds.data_vars)}")
        lons=ds.longitude.values
        lon=float(station_lon)%360 if float(np.nanmax(lons))>180 else float(station_lon)
        point=ds.sel(latitude=float(station_lat),longitude=lon,method="nearest")
        value=point[actual].values.item()
        if not np.isfinite(value):raise ValueError("Nonfinite GRIB value")
        return float(value),float(point.latitude.values),float(point.longitude.values)
    finally:ds.close()
def main():
    p=argparse.ArgumentParser();p.add_argument("--station-csv",required=True)
    p.add_argument("--init-date",required=True);p.add_argument("--init-hour",type=int,choices=[0,6,12,18],default=0)
    p.add_argument("--leads",type=int,nargs="+",default=[6,12,24,48])
    p.add_argument("--cache",default="raw/ecmwf");p.add_argument("--output",required=True)
    a=p.parse_args()
    from ecmwf.opendata import Client
    client=Client(source="ecmwf",model="ifs",resol="0p1")
    stations=pd.read_csv(a.station_csv,dtype={"station_id":str})
    dt=pd.Timestamp(f"{a.init_date}T{a.init_hour:02d}:00:00Z")
    cache=Path(a.cache);cache.mkdir(parents=True,exist_ok=True)
    fields=[("2t","temperature_2m","C",lambda x:x-273.15),("10u","wind_u_10m","m/s",float),("10v","wind_v_10m","m/s",float),("msl","msl_pressure","hPa",lambda x:x/100)]
    rows=[]
    for lead in a.leads:
        for par,_,_,_ in fields:
            dest=cache/f"ifs_{a.init_date}_{a.init_hour:02d}UTC_{lead:03d}h_{par}.grib2"
            if not dest.exists():
                client.retrieve(date=a.init_date,time=a.init_hour,step=lead,levtype="sfc",stream="oper",type="fc",param=par,resol="0p1",target=str(dest))
        for st in stations.itertuples(index=False):
            values={}
            for par,var,unit,convert in fields:
                path=cache/f"ifs_{a.init_date}_{a.init_hour:02d}UTC_{lead:03d}h_{par}.grib2"
                val,lat,lon=extract(path,par,st.lat,st.lon)
                values[var]=float(convert(val))
            values["wind_speed_10m"]=float(np.hypot(values.pop("wind_u_10m"),values.pop("wind_v_10m")))
            for var,val in values.items():
                rows.append({"station_id":str(st.station_id),"variable":var,"init_time":dt.isoformat(),"lead_hours":lead,"valid_time":(dt+pd.Timedelta(hours=lead)).isoformat(),"model":"ECMWF_IFS","value":val,"unit":{"temperature_2m":"C","wind_speed_10m":"m/s","msl_pressure":"hPa"}[var],"source_grid_lat":lat,"source_grid_lon":lon})
    out=Path(a.output);out.parent.mkdir(exist_ok=True,parents=True)
    pd.DataFrame(rows).to_csv(out,index=False)
if __name__=="__main__":main()
