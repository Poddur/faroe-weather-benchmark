"""Strict common-case SQLite warehouse for Faroese weather model verification.

Never silently equate FWA-2/FWA-4A with similarly named implementations.
No pooled scores unless all five verified models share the same case key.
"""
import argparse,csv,json,sqlite3,math
from pathlib import Path

KEY=("init_time","valid_time","lead_hours","station_id","variable")
MODELS=("HARMONIE_DINI","ECMWF_IFS","WeatherNext3","FWA-2","FWA-4A")
DDL="""
CREATE TABLE IF NOT EXISTS models (
 model_id TEXT PRIMARY KEY, implementation_path TEXT, implementation_version TEXT,
 code_sha TEXT, identity_verified INTEGER NOT NULL DEFAULT 0
);
CREATE TABLE IF NOT EXISTS forecasts (
 init_time TEXT NOT NULL, valid_time TEXT NOT NULL, lead_hours INTEGER NOT NULL,
 station_id TEXT NOT NULL, variable TEXT NOT NULL, model_id TEXT NOT NULL,
 prediction REAL NOT NULL, unit TEXT NOT NULL, provenance TEXT NOT NULL,
 PRIMARY KEY(init_time,valid_time,lead_hours,station_id,variable,model_id),
 FOREIGN KEY(model_id) REFERENCES models(model_id)
);
CREATE TABLE IF NOT EXISTS observations (
 station_id TEXT NOT NULL, valid_time TEXT NOT NULL, variable TEXT NOT NULL,
 observed REAL NOT NULL, unit TEXT NOT NULL, source TEXT NOT NULL,
 PRIMARY KEY(station_id,valid_time,variable)
);
CREATE VIEW IF NOT EXISTS common_cases AS
 SELECT f.init_time,f.valid_time,f.lead_hours,f.station_id,f.variable,
 COUNT(DISTINCT f.model_id) AS models_present,
 COUNT(DISTINCT CASE WHEN m.identity_verified=1 THEN f.model_id END) AS verified_models,
 COUNT(DISTINCT f.model_id) FILTER(WHERE m.model_id IN
 ('HARMONIE_DINI','ECMWF_IFS','WeatherNext3','FWA-2','FWA-4A')) AS required_models
 FROM forecasts f JOIN models m ON f.model_id=m.model_id
 JOIN observations o ON o.station_id=f.station_id AND o.valid_time=f.valid_time
 AND o.variable=f.variable AND o.unit=f.unit
 GROUP BY f.init_time,f.valid_time,f.lead_hours,f.station_id,f.variable;
"""
def finite(x):
 x=float(x)
 if not math.isfinite(x):raise ValueError("nonfinite value")
 return x
def iso(x):
 from datetime import datetime,timezone
 t=datetime.fromisoformat(str(x).replace("Z","+00:00"))
 if t.utcoffset() is None:raise ValueError("timestamp lacks timezone")
 return t.astimezone(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
def add_forecast(db, row):
 vals=[row[k] for k in KEY]
 vals[0]=iso(vals[0]);vals[1]=iso(vals[1]);vals[2]=int(vals[2])
 from datetime import datetime
 a=datetime.fromisoformat(vals[0].replace("Z","+00:00"));b=datetime.fromisoformat(vals[1].replace("Z","+00:00"))
 if (b-a).total_seconds()!=vals[2]*3600:raise ValueError("lead mismatch")
 vals+= [row["model_id"],finite(row["prediction"]),row["unit"],row["provenance"]]
 existing=db.execute("SELECT prediction,unit FROM forecasts WHERE "+ " AND ".join(k+"=?" for k in KEY)+" AND model_id=?",vals[:6]).fetchone()
 if existing and existing!=(vals[6],vals[7]):raise ValueError("conflicting immutable forecast")
 db.execute("INSERT OR IGNORE INTO forecasts VALUES (?,?,?,?,?,?,?,?,?)",vals)
def add_obs(db,r):
 vals=(r["station_id"],iso(r["valid_time"]),r["variable"],finite(r["observed"]),r["unit"],r["source"])
 old=db.execute("SELECT observed,unit FROM observations WHERE station_id=? AND valid_time=? AND variable=?",vals[:3]).fetchone()
 if old and old!=(vals[3],vals[4]):raise ValueError("conflicting observation")
 db.execute("INSERT OR IGNORE INTO observations VALUES (?,?,?,?,?,?)",vals)
def import_geo(db,path):
 for r in json.loads(Path(path).read_text())["evidence"]:
  variable="temperature_2m" if r["parameter"]=="temp_dry" else "wind_speed_10m"
  unit="C" if r["parameter"]=="temp_dry" else "m/s"
  lead=int(r.get("lead_hours",round((__import__("datetime").datetime.fromisoformat(r["valid"].replace("Z","+00:00"))-__import__("datetime").datetime.fromisoformat(r["run"].replace("Z","+00:00"))).total_seconds()/3600)))
  base=dict(init_time=r["run"],valid_time=r["valid"],lead_hours=lead,station_id=r["station"],variable=variable,unit=unit,provenance=str(path))
  add_obs(db,dict(station_id=r["station"],valid_time=r["valid"],variable=variable,observed=r["observation"],unit=unit,source=r.get("observation_source","unknown")))
  add_forecast(db,dict(base,model_id="HARMONIE_DINI",prediction=r["raw_prediction"]))
  # Preserve the original implementation name, NOT an unverified FWA-2 or FWA-4A alias.
  if r.get("physics_prediction") is not None:
   add_forecast(db,dict(base,model_id="fixed_native_boundary_v2_new_sites",prediction=r["physics_prediction"]))
def import_operational(db,forecast,observations):
 with open(observations,newline="") as f:
  for r in csv.DictReader(f):
   variable={"temp_dry":"temperature_2m","wind_speed":"wind_speed_10m"}.get(r["variable"],r["variable"])
   add_obs(db,dict(station_id=r["station_id"],valid_time=r["valid_time"],variable=variable,observed=r.get("value",r.get("observed")),unit=r["unit"],source=str(observations)))
 with open(forecast,newline="") as f:
  for r in csv.DictReader(f):
   add_forecast(db,dict(init_time=r["init_time"],valid_time=r["valid_time"],lead_hours=r["lead_hours"],station_id=r["station_id"],variable=r["variable"],model_id=r["model"],prediction=r["value"],unit=r["unit"],provenance=str(forecast)))
def main():
 p=argparse.ArgumentParser()
 p.add_argument("--db",default="outputs/common-model-test.sqlite")
 p.add_argument("--geo",action="append",default=[])
 p.add_argument("--operational-forecasts")
 p.add_argument("--operational-observations")
 p.add_argument("--report",default="outputs/common-model-test-report.json")
 a=p.parse_args()
 Path(a.db).parent.mkdir(parents=True,exist_ok=True)
 db=sqlite3.connect(a.db);db.execute("PRAGMA foreign_keys=ON");db.executescript(DDL)
 for model in MODELS+("fixed_native_boundary_v2_new_sites",):
  db.execute("INSERT OR IGNORE INTO models(model_id,identity_verified) VALUES (?,?)",(model,int(model in ("HARMONIE_DINI","ECMWF_IFS","WeatherNext3"))))
 for file in a.geo:import_geo(db,file)
 if bool(a.operational_forecasts)!=bool(a.operational_observations):raise ValueError("operational forecast and observation files must be supplied together")
 if a.operational_forecasts:import_operational(db,a.operational_forecasts,a.operational_observations)
 db.commit()
 allcases=db.execute("SELECT COUNT(*) FROM common_cases").fetchone()[0]
 complete=db.execute("SELECT COUNT(*) FROM common_cases WHERE required_models=5 AND verified_models=5").fetchone()[0]
 counts=dict(db.execute("SELECT model_id,COUNT(*) FROM forecasts GROUP BY model_id").fetchall())
 report=dict(schema=1,model_registry={r[0]:dict(path=r[1],version=r[2],code_sha=r[3],identity_verified=bool(r[4])) for r in db.execute("SELECT * FROM models")},forecast_rows=counts,observed_case_keys=allcases,verified_five_model_cases=complete,score_status="eligible" if complete else "BLOCKED_NO_FIVE_MODEL_COMMON_CASES",note="FWA-2 and FWA-4A identity must be independently pinned to immutable code SHA before scoring.")
 Path(a.report).parent.mkdir(parents=True,exist_ok=True);Path(a.report).write_text(json.dumps(report,indent=2)+"\\n")
 print(json.dumps(report,indent=2))
if __name__=="__main__":main()
