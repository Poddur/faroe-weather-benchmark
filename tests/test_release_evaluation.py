import json,hashlib,sys,zipfile
from pathlib import Path
import pandas as pd
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/"src"))
from evaluate_releases import report,normalize

def test_weekly_report_from_raw_archive(tmp_path):
    root=tmp_path/"payload";root.mkdir()
    (root/"forecast"/"raw").mkdir(parents=True)
    (root/"observations").mkdir()
    raw=root/"forecast"/"raw"/"source.json";raw.write_text('{"value":1}')
    manifest={"status":"success","files":[{"path":"raw/source.json","sha256":hashlib.sha256(raw.read_bytes()).hexdigest(),"bytes":raw.stat().st_size}]}
    (root/"forecast"/"manifest.json").write_text(json.dumps(manifest))
    (root/"verification.json").write_text(json.dumps({"status":"pass"}))
    forecasts=[]
    for model,val in (("ECMWF_IFS",5.5),("HARMONIE_DINI",5.0)):
        forecasts.append({"station_id":"06011","model":model,"variable":"temperature_2m","value":val,"unit":"C","init_time":"2026-11-14T00:00:00Z","valid_time":"2026-11-14T06:00:00Z","lead_hours":6})
    pd.DataFrame(forecasts).to_csv(root/"forecast"/"matched_forecasts.csv",index=False)
    pd.DataFrame([{"station_id":"06011","variable":"temperature_2m","valid_time":"2026-11-14T06:00:00Z","value":5.0,"unit":"C"}]).to_csv(root/"observations"/"observations.csv",index=False)
    zipname=tmp_path/"issue_example.zip"
    with zipfile.ZipFile(zipname,"w") as z:
        for f in root.rglob("*"):
            if f.is_file():z.write(f,f.relative_to(root).as_posix())
    res=report([zipname],tmp_path/"report",bootstrap=0)
    assert res["status"]=="exploratory"
    assert res["paired_model_rows"]==2
    scores=pd.read_csv(tmp_path/"report"/"scores.csv").set_index("model")
    assert scores.loc["HARMONIE_DINI","mae"]==0

def test_conflicting_overlapping_observations_rejected():
    forecasts=pd.DataFrame([{"model":"ECMWF_IFS","station_id":"06011","variable":"temperature_2m","init_time":"2026-11-14T00:00:00Z","valid_time":"2026-11-14T06:00:00Z","lead_hours":6,"value":5,"unit":"C"}])
    obs=pd.DataFrame([{"station_id":"06011","variable":"temperature_2m","valid_time":"2026-11-14T06:00:00Z","value":v,"unit":"C"} for v in (5.0,7.0)])
    import pytest
    with pytest.raises(ValueError,match="Conflicting observation"):
        normalize(forecasts,obs)
