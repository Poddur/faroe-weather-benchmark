import sys
from pathlib import Path
import pandas as pd
import pytest
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/"src"))
from historical_weathernext_benchmark import score, DEFAULT_ISSUES, DEFAULT_LEADS
def test_historical_scoring_strict_time_match():
    f=pd.DataFrame([
      {"station_id":"06011","variable":"temperature_2m","valid_time":"2026-10-01T06:00:00Z",
       "init_time":"2026-10-01T00:00:00Z","lead_hours":6,"model":"WeatherNext3","value":6,"unit":"C"},
      {"station_id":"06011","variable":"temperature_2m","valid_time":"2026-10-01T12:00:00Z",
       "init_time":"2026-10-01T00:00:00Z","lead_hours":12,"model":"WeatherNext3","value":7,"unit":"C"}])
    o=pd.DataFrame([{"station_id":"06011","variable":"temperature_2m","valid_time":"2026-10-01T06:00:00Z",
                    "observed":5.0,"unit":"C"}])
    paired,all_records,summary=score(f,o)
    assert len(paired)==1 and len(all_records)==2
    assert summary.iloc[0].mae==1.0
    assert int((~all_records.has_observation).sum())==1
def test_bad_observation_units_rejected():
    f=pd.DataFrame([{"station_id":"06011","variable":"wind_speed_10m","valid_time":"2026-10-01T06:00:00Z",
       "init_time":"2026-10-01T00:00:00Z","lead_hours":6,"model":"WeatherNext3","value":9,"unit":"m/s"}])
    o=pd.DataFrame([{"station_id":"06011","variable":"wind_speed_10m","valid_time":"2026-10-01T06:00:00Z",
       "observed":9,"unit":"km/h"}])
    with pytest.raises(ValueError,match="units mismatch"):score(f,o)
def test_default_historical_cases():
    assert len(DEFAULT_ISSUES)==2
    assert DEFAULT_LEADS==[6,12,24]
