import sys,json,hashlib
from pathlib import Path
import pandas as pd
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/"src"))
from verify_operational import verify

def test_operational_verification(tmp_path):
    root=tmp_path
    src=root/"forecast"/"raw"/"harmonie";src.mkdir(parents=True)
    obs=root/"observations";obs.mkdir()
    sample=src/"source.json";sample.write_text('{"ok":true}')
    data={
      "status":"success","issue_time_utc":"2026-11-14T00:00:00Z",
      "files":[{"path":"raw/harmonie/source.json",
                "sha256":hashlib.sha256(sample.read_bytes()).hexdigest(),
                "bytes":sample.stat().st_size}]
    }
    (root/"forecast"/"manifest.json").write_text(json.dumps(data))
    rows=[]
    for model in ("ECMWF_IFS","HARMONIE_DINI"):
        rows.append(dict(station_id="06011",model=model,variable="temperature_2m",unit="C",
                         init_time="2026-11-14T00:00:00Z",valid_time="2026-11-14T06:00:00Z",
                         lead_hours=6,value=5))
    pd.DataFrame(rows).to_csv(root/"forecast"/"matched_forecasts.csv",index=False)
    pd.DataFrame([dict(station_id="06011",variable="temperature_2m",valid_time="2026-11-14T06:00:00Z",value=5,unit="C")]).to_csv(obs/"observations.csv",index=False)
    result=verify(root)
    assert result["status"]=="pass"
    sample.write_text('{"modified":true}')
    assert verify(root)["status"]=="failed"
