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
    assert all(q["insufficient_for_final_inference"] for q in result["comparisons"])\n    assert result["decision"]["overall"]=="insufficient_data"
    paired.write_text(paired.read_text().replace("5.0","9.0",1))
    with pytest.raises(ValueError,match="tampered"):
        scorecard.score(cache,lock)

def test_incomplete_excluded_without_scoring(tmp_path,monkeypatch):
    cache,lock,_=fixture(tmp_path,monkeypatch,complete=False)
    result=scorecard.score(cache,lock)
    assert result["complete_dates"]==0
    assert len(result["incomplete_dates"])==1
    assert result["comparisons"]==[]


def test_statistical_gate_rejects_insufficient_week_coverage():
    dates=pd.date_range("2026-11-21",periods=7,freq="D",tz="UTC")
    z=pd.DataFrame({"init_time":dates})
    out={"complete_dates":len(dates),"comparisons":[]}
    decision=scorecard.judge(z,out,{"minimum_dates":60,"minimum_weeks":10,"minimum_cases_per_station_lead":63})
    assert decision["overall"]=="insufficient_data"


def test_statistical_decision_on_full_synthetic_winter():
    # Synthetic controls test only the evidence gate, never model skill.
    dates=pd.date_range("2026-11-21",periods=70,freq="D",tz="UTC")
    rows=[]
    for date in dates:
        for site in scorecard.SITES:
            for lead in scorecard.LEADS:
                for variable,candidate in scorecard.VARIABLES:
                    wind=variable=="wind_speed_10m"
                    observed=20.0 if wind else 4.0
                    rows.append({"station_id":site,"variable":variable,
                        "init_time":date,"valid_time":date+pd.Timedelta(hours=lead),
                        "lead_hours":lead,"observed":observed,
                        "ECMWF_9km":5.0,"HARMONIE_DINI_OM":6.0,"WeatherNext3":7.0,
                        "FWA2":4.5,"FWA4A":18.0})
    data=pd.DataFrame(rows)
    out={"complete_dates":len(dates),"comparisons":[
        {"variable":var,"candidate":candidate,"baseline":m,
         "insufficient_for_final_inference":True}
        for var,candidate in scorecard.VARIABLES for m in scorecard.MODELS]}
    proto={"minimum_dates":60,"minimum_weeks":10,"minimum_cases_per_station_lead":63,
        "minimum_strong_cases":30,"minimum_strong_dates":12,"minimum_strong_weeks":8,
        "strong_threshold":15,"bootstrap_draws":1000,"seed":20261120}
    decision=scorecard.judge(data,out,proto)
    assert decision["coverage_eligible"] is True
    assert decision["temperature_vs_three"]=="superior_to_all_three"
    assert decision["wind_average_vs_three"]=="superior_to_all_three"
    assert decision["strong_wind_safety"]=="pass"
    assert decision["overall"]=="superior_to_all_three_with_storm_safety"
    assert all(x["superiority_demonstrated"] for x in out["comparisons"])


def test_statistical_gate_rejects_no_storm_coverage():
    dates=pd.date_range("2026-11-21",periods=70,freq="D",tz="UTC")
    rows=[]
    for date in dates:
        for site in scorecard.SITES:
            for lead in scorecard.LEADS:
                for variable,_ in scorecard.VARIABLES:
                    rows.append({"station_id":site,"variable":variable,"lead_hours":lead,
                        "init_time":date,"observed":4.0,
                        "ECMWF_9km":5.0,"HARMONIE_DINI_OM":6.0,
                        "WeatherNext3":7.0,"FWA2":4.5,"FWA4A":4.5})
    data=pd.DataFrame(rows)
    out={"complete_dates":70,"comparisons":[
        {"variable":var,"candidate":candidate,"baseline":m}
        for var,candidate in scorecard.VARIABLES for m in scorecard.MODELS]}
    proto={"minimum_dates":60,"minimum_weeks":10,"minimum_cases_per_station_lead":63,
        "minimum_strong_cases":30,"minimum_strong_dates":12,"minimum_strong_weeks":8,
        "strong_threshold":15,"bootstrap_draws":1000,"seed":20261120}
    decision=scorecard.judge(data,out,proto)
    assert decision["coverage_eligible"] is True
    assert decision["strong_wind_safety"]=="insufficient_data"
    assert decision["overall"]=="not_demonstrated"
