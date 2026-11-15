import hashlib,json,sys
from pathlib import Path
import pandas as pd
import pytest
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/"src"))
from report_historical_weathernext import build

def test_research_report_integrity_and_bounded_uncertainty(tmp_path):
    root=tmp_path
    forecast=pd.DataFrame([dict(model="WeatherNext3",station_id="06011",variable="temperature_2m",
        init_time="2026-10-01T00:00:00Z",valid_time="2026-10-01T06:00:00Z",
        lead_hours=6,value=5.5,unit="C")])
    obs=pd.DataFrame([dict(station_id="06011",variable="temperature_2m",
        valid_time="2026-10-01T06:00:00Z",value=5.0,unit="C")])
    forecast.to_csv(root/"forecasts.csv",index=False)
    obs.to_csv(root/"observations.csv",index=False)
    (root/"dmi_original_features.json").write_text("[]")
    hashes={}
    for n,k in [("forecasts.csv","forecast_csv_sha256"),
                ("observations.csv","observation_csv_sha256"),
                ("dmi_original_features.json","dmi_original_features_sha256")]:
        hashes[k]=hashlib.sha256((root/n).read_bytes()).hexdigest()
    (root/"manifest.json").write_text(json.dumps({"status":"exploratory_success",
        "issue_times_utc":["2026-10-01T00:00:00Z"],**hashes}))
    out=build(root)
    assert out["paired"]==1
    assert out["unique_issue_times"]==1
    summary=pd.read_csv(root/"scorecard_by_lead.csv")
    assert summary.mae.iloc[0]==pytest.approx(0.5)
    assert (root/"RESEARCH_REPORT.md").exists()
    assert "not" in (root/"RESEARCH_REPORT.md").read_text().lower()
    obs.loc[0,"value"]=999
    obs.to_csv(root/"observations.csv",index=False)
    with pytest.raises(ValueError,match="SHA256 mismatch"):
        build(root)
