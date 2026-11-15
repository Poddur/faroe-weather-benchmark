"""Fixtures test selection correctness independent of remote Icechunk access."""
import sys
from pathlib import Path
import numpy as np
import pandas as pd
import pytest
import xarray as xr
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/"src"))
from probe_weathernext_dynamical import forecast_rows
def test_three_station_historical_point_selection():
    lat=np.array([61.4,62.0,62.3])
    lon=np.array([352.9,353.2,353.3])  # nearest longitude must be selected in 0..360 convention
    coords={"init_time":[np.datetime64("2026-11-14T00:00:00")],"statistic":["mean"],"lead_time":[np.timedelta64(6,"h")],"y":lat,"x":lon}
    vals=np.ones((1,1,1,3,3))*5.5
    temp=xr.DataArray(vals,dims=tuple(coords),coords=coords)
    wind=xr.DataArray(vals+3,dims=tuple(coords),coords=coords)
    ds=xr.Dataset({"temperature_2m":temp,"wind_speed_10m":wind})
    data=forecast_rows(ds,"2026-11-14T00:00:00Z",6)
    assert len(data)==6
    assert set(r["unit"] for r in data)=={"C","m/s"}
    assert set(r["station_id"] for r in data)=={"06009","06011","06014"}
    assert set(r["valid_time"] for r in data)=={"2026-11-14T06:00:00Z"}

def test_unavailable_future_lead_is_not_silently_filled():
    coords={"init_time":[np.datetime64("2026-11-14T00:00:00")],"statistic":["mean"],"lead_time":[np.timedelta64(6,"h")],"y":[62.0],"x":[353.2]}
    arr=xr.DataArray(np.ones((1,1,1,1,1)),coords=coords,dims=tuple(coords))
    ds=xr.Dataset({"temperature_2m":arr,"wind_speed_10m":arr})
    with pytest.raises((KeyError,ValueError)):
        forecast_rows(ds,"2026-11-14T00:00:00Z",12,station_ids=("06011",))
