from datetime import datetime,timezone
import sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/"src"))
from probe_ecmwf_live import choose_init
from probe_harmonie_live import summarize

def test_ecmwf_init_is_old_enough():
    now=datetime(2026,11,14,16,0,tzinfo=timezone.utc)
    init=choose_init(now)
    assert init.isoformat()=="2026-11-14T00:00:00+00:00"
    assert (now-init).total_seconds()/3600>=14

def test_harmonie_schema_diagnostic():
    r={"body":{"type":"FeatureCollection","features":[{"type":"Feature","geometry":{"coordinates":[-6.7,62.0]},"properties":{"step":"2026-11-15T00:00:00Z","temperature-2m":280.1}}]}}
    s=summarize(r)
    assert s["features"]==1
    assert s["sample_step"]=="2026-11-15T00:00:00Z"
    assert "temperature-2m" in s["properties"]
