"""Download actual EKVG METAR observations; retain native report times and raw provenance."""
import io,json,hashlib
from pathlib import Path
import pandas as pd
import requests
OUT=Path("outputs/station-audit")
URL="https://mesonet.agron.iastate.edu/cgi-bin/request/asos.py"
def main():
    OUT.mkdir(parents=True,exist_ok=True)
    status={"station":"EKVG","status":"failed","source":URL}
    try:
        params={"station":"EKVG","data":["tmpf","sknt","drct","metar"],"year1":2026,"month1":4,"day1":1,"year2":2026,"month2":11,"day2":20,"tz":"Etc/UTC","format":"onlycomma","latlon":"yes","elev":"yes","missing":"M","trace":"T","report_type":[3,4]}
        r=requests.get(URL,params=params,timeout=180);r.raise_for_status()
        (OUT/"EKVG_raw.csv").write_bytes(r.content)
        status.update(url=r.url,sha256=hashlib.sha256(r.content).hexdigest())
        d=pd.read_csv(io.BytesIO(r.content),comment="#",na_values=["M","T"],dtype={"station":str})
        required={"station","valid","tmpf","sknt","drct","metar"}
        if not required.issubset(d.columns) or d.empty:raise ValueError("Missing METAR columns or no reports")
        if set(d.station)!={"EKVG"}:raise ValueError("Unexpected station identity")
        d["valid_time"]=pd.to_datetime(d.valid,utc=True,errors="raise")
        if not d.valid_time.between(pd.Timestamp("2026-04-01",tz="UTC"),pd.Timestamp("2026-11-20",tz="UTC"),inclusive="left").all():raise ValueError("Unexpected dates")
        d["temperature_C"]=(pd.to_numeric(d.tmpf,errors="coerce")-32)*5/9
        d["wind_ms"]=pd.to_numeric(d.sknt,errors="coerce")*0.5144444444444445
        d["direction_deg"]=pd.to_numeric(d.drct,errors="coerce")
        d["quality_ok"]=d.temperature_C.between(-40,40)&d.wind_ms.between(0,65)
        d["offset_min"]=d.valid_time.dt.minute
        d.to_csv(OUT/"EKVG_normalized.csv",index=False)
        clean=d[d.quality_ok].copy()
        status.update(status="downloaded",reports=len(d),paired_valid_reports=len(clean),duplicate_timestamps=int(d.valid_time.duplicated(keep=False).sum()),days=int(clean.valid_time.dt.date.nunique()),minute_distribution={str(k):int(v) for k,v in clean.offset_min.value_counts().items()},metadata={c:d[c].dropna().unique().tolist() for c in ["lat","lon","elevation"] if c in d},warning="Native report times preserved. No assumption of exact-hour matching or validated sensor height; no training eligibility until metadata and timing reviewed.")
    except Exception as e:status["error"]=str(e);raise
    finally:(OUT/"vagar_status.json").write_text(json.dumps(status,indent=2,default=str))
if __name__=="__main__":main()
