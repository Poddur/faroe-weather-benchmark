from datetime import datetime,timezone
import sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/"src"))
from collect_matched_forecasts import pick_common_instance,haversine,harmonie_rows
import pytest

def test_same_issue_selection():
    now=datetime(2026,11,14,17,0,tzinfo=timezone.utc)
    dt,run=pick_common_instance(["2026-11-14T120000Z","2026-11-14T000000Z","2026-11-13T120000Z"],now)
    assert run=="2026-11-14T000000Z"
    assert dt.hour==0

def test_reject_nonmatching_issue():
    with pytest.raises(ValueError,match="No available"):
        pick_common_instance(["2026-11-14T120000Z"],datetime(2026,11,14,17,tzinfo=timezone.utc))

def test_distant_point_rejected():
    init=datetime(2026,11,14,0,tzinfo=timezone.utc)
    payload={"type":"FeatureCollection","features":[{"geometry":{"coordinates":[0,60]},"properties":{"step":"2026-11-14T06:00:00Z","temperature-2m":275,"wind-speed-10m":8}}]}
    with pytest.raises(ValueError,match="too far"):
        harmonie_rows(payload,{"id":"06011","lat":62.0231,"lon":-6.7647},init,"2026-11-14T000000Z",expected_leads=(6,))

def test_harmonie_conversion_and_lead():
    init=datetime(2026,11,14,0,tzinfo=timezone.utc)
    payload={"type":"FeatureCollection","features":[{"geometry":{"coordinates":[-6.7647,62.0231]},"properties":{"step":"2026-11-14T06:00:00.000Z","temperature-2m":275.15,"wind-speed-10m":8}}]}
    result=harmonie_rows(payload,{"id":"06011","lat":62.0231,"lon":-6.7647},init,"2026-11-14T000000Z",expected_leads=(6,))
    assert len(result)==2
    assert next(r for r in result if r["variable"]=="temperature_2m")["value"]==pytest.approx(2)
    assert result[0]["lead_hours"]==6
