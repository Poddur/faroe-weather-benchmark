import sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/"src"))
from discover_dmi_stations import parse

def test_station_candidate_parsing():
    data=[{"properties":{"stationId":"00001","name":"Test"},"geometry":{"coordinates":[-6.8,62.0]}},
          {"properties":{"name":"Missing identifier"},"geometry":{"coordinates":[-6.7,62.1]}}]
    result=parse(data)
    assert len(result)==1
    assert result[0]["station_id"]=="00001"
    assert result[0]["sensor_height_m"]==""
