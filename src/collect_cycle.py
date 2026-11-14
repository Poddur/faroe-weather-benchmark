"""Run one auditable collection cycle, never a background worker."""
import argparse,json,subprocess,sys
from datetime import datetime,timezone,timedelta
from pathlib import Path
import pandas as pd
def main():
    p=argparse.ArgumentParser()
    p.add_argument("--stations",default="data/stations_verified.csv")
    p.add_argument("--archive-root",default="archive")
    p.add_argument("--harmonie-collection",default="harmonie_dini_sf")
    p.add_argument("--include-ecmwf",action="store_true")
    p.add_argument("--include-harmonie",action="store_true")
    p.add_argument("--include-observations",action="store_true")
    a=p.parse_args()
    if not Path(a.stations).exists():raise SystemExit("Verified stations file missing: "+a.stations)
    stations=pd.read_csv(a.stations,dtype={"station_id":str})
    now=datetime.now(timezone.utc)
    root=Path(a.archive_root)/now.strftime("%Y-%m-%d")/now.strftime("%H%M%SZ")
    root.mkdir(parents=True,exist_ok=True)
    cmds=[];py=sys.executable
    if a.include_harmonie:
        cmds.append(("harmonie",[py,"src/fetch_harmonie_edr.py","--station-csv",a.stations,"--collection",a.harmonie_collection,"--archive",str(root/"raw_harmonie"),"--output",str(root/"harmonie.csv")]))
    if a.include_ecmwf:
        candidate=now-timedelta(hours=10);hour=12 if candidate.hour>=12 else 0
        cmds.append(("ecmwf",[py,"src/fetch_ecmwf_ifs.py","--station-csv",a.stations,"--init-date",candidate.strftime("%Y-%m-%d"),"--init-hour",str(hour),"--cache",str(root/"raw_ecmwf"),"--output",str(root/"ecmwf.csv")]))
    if a.include_observations:
        end=now.replace(minute=0,second=0,microsecond=0);start=end-timedelta(hours=36)
        cmds.append(("observations",[py,"src/fetch_dmi_observations.py","--station-ids",*stations.station_id.astype(str).tolist(),"--start",start.strftime("%Y-%m-%dT%H:%M:%SZ"),"--end",end.strftime("%Y-%m-%dT%H:%M:%SZ"),"--output",str(root/"observations.csv")]))
    if not cmds:raise SystemExit("Select at least one --include-* source")
    statuses=[]
    for name,cmd in cmds:
        result=subprocess.run(cmd,capture_output=True,text=True)
        (root/f"{name}.log").write_text(result.stdout+"\nSTDERR:\n"+result.stderr,encoding="utf8")
        statuses.append({"source":name,"returncode":result.returncode,"argv":cmd})
    (root/"cycle_manifest.json").write_text(json.dumps({"started_utc":now.isoformat(),"results":statuses},indent=2),encoding="utf8")
    print("Cycle:",root,"results:",[(x["source"],x["returncode"]) for x in statuses])
    sys.exit(1 if any(x["returncode"] for x in statuses) else 0)
if __name__=="__main__":main()
