"""Read-only FWA winter scorecard regression checks."""
import hashlib
import json
from pathlib import Path
import sys
import pandas as pd
import pytest

sys.path.insert(0,str(Path(__file__).resolve().parents[1]/"src"))
import fwa_locked_reference_scorecard as scorecard

def fixture(tmp_path,monkeypatch,complete=True):
    cache=tmp_path/"cache";cache.mkdir()
    lock=tmp_path/"lock.json"
    lock.write_text(json.dumps({"protocol":{"first_issue":"2026-11-21","last_issue":"2027-02-12","minimum_dates":60}}))
    monkeypatch.setattr(scorecard,"LOCK_SHA",scorecard.sha(lock))
    issue=pd.Timestamp("2026-11-21T00:00:00Z")
    rows=[]
    for site in scorecard.SITES:
        for var,candidate in scorecard.VARIABLES:
            for lead in scorecard.LEADS:
                rows.append({"station_id":site,"variable":var,"init_time":str(issue),
                    "valid_time":str(issue+pd.Timedelta(hours=lead)),"lead_hours":lead,
                    "observed":4.0,"ECMWF_9km":5.0,"HARMONIE_DINI_OM":6.0,
                    "WeatherNext3":7.0,"FWA2":4.5,"FWA4A":4.5})
    paired=cache/"20261121_paired.csv"
    pd.DataFrame(rows).to_csv(paired,index=False)
    manifest={"issue":str(issue),"lock_sha256":scorecard.LOCK_SHA,
              "complete":complete,"paired_cases":18,"paired_sha256":scorecard.sha(paired)}
    (cache/"20261121.json").write_text(json.dumps(manifest))
    return cache,lock,paired

def test_awaiting_without_checkpoints(tmp_path,monkeypatch):
    cache,lock,_=fixture(tmp_path,monkeypatch)
    (cache/"20261121.json").unlink()
    result=scorecard.score(cache,lock)
    assert result["status"]=="awaiting_eligible_archives"
    assert result["comparisons"]==[]

def test_paired_frozen_comparisons(tmp_path,monkeypatch):
    cache,lock,paired=fixture(tmp_path,monkeypatch)
    result=scorecard.score(cache,lock)
    assert result["complete_dates"]==1
    assert len(result["comparisons"])==6
    assert len(result["station_lead_scores"])==18
    assert all(q["cases"]==9 for q in result["comparisons"])
    assert result["comparisons"][0]["delta_mae"]==-0.5
    assert all(q["insufficient_for_final_inference"] for q in result["comparisons"])
    paired.write_text(paired.read_text().replace("5.0","9.0",1))
    with pytest.raises(ValueError,match="tampered"):
        scorecard.score(cache,lock)

def test_incomplete_excluded_without_scoring(tmp_path,monkeypatch):
    cache,lock,_=fixture(tmp_path,monkeypatch,complete=False)
    result=scorecard.score(cache,lock)
    assert result["complete_dates"]==0
    assert len(result["incomplete_dates"])==1
    assert result["comparisons"]==[]
