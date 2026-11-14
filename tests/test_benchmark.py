import sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/"src"))
import pandas as pd
import pytest
from benchmark import analysis,read_forecasts,read_observations

@pytest.fixture
def example(tmp_path):
    obs=pd.DataFrame([{"station_id":"A","variable":"temperature_2m","valid_time":"2026-01-02T00:00:00Z","value":5,"unit":"C"}])
    fc=pd.DataFrame([{"station_id":"A","variable":"temperature_2m","init_time":"2026-01-01T00:00:00Z","valid_time":"2026-01-02T00:00:00Z","lead_hours":24,"model":m,"value":v,"unit":"C"} for m,v in [("WeatherNext3",6),("ECMWF_IFS",7),("HARMONIE",5)]])
    fc.to_csv(tmp_path/"fc.csv",index=False);obs.to_csv(tmp_path/"obs.csv",index=False)
    return tmp_path/"fc.csv",tmp_path/"obs.csv"
def test_paired_scores(example):
    f,o=example
    paired,scores,delta=analysis(read_forecasts(f),read_observations(o),["WeatherNext3","ECMWF_IFS","HARMONIE"],bootstrap=0)
    assert len(paired)==3
    assert scores.set_index("model").loc["HARMONIE","mae"]==0
    assert delta.set_index("challenger").loc["HARMONIE","delta_mae_challenger_minus_baseline"]==-1
def test_missing_model_rejected(example):
    f,o=example;df=pd.read_csv(f);df[df.model!="HARMONIE"].to_csv(f,index=False)
    with pytest.raises(ValueError,match="Missing model"):
        analysis(read_forecasts(f),read_observations(o),["WeatherNext3","ECMWF_IFS","HARMONIE"])
def test_duplicate_rejected(example):
    f,_=example;df=pd.read_csv(f);pd.concat([df,df.iloc[[0]]]).to_csv(f,index=False)
    with pytest.raises(ValueError,match="Duplicate"):read_forecasts(f)
def test_inconsistent_lead_rejected(example):
    f,_=example;df=pd.read_csv(f);df.loc[0,"lead_hours"]=12;df.to_csv(f,index=False)
    with pytest.raises(ValueError,match="Inconsistent"):read_forecasts(f)
def test_wrong_unit_rejected(example):
    f,_=example;df=pd.read_csv(f);df.loc[0,"unit"]="K";df.to_csv(f,index=False)
    with pytest.raises(ValueError,match="Incorrect unit"):read_forecasts(f)
