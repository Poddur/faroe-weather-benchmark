"""Descriptive historic observations by wind regime, NOT prospective forecast skill or inversions."""
import json,io,hashlib,math,argparse
from pathlib import Path
import numpy as np,pandas as pd,requests
from fetch_dmi_observations import polite_get
DMI_BASE="https://opendataapi.dmi.dk/v2/metObs/collections/observation/items"
def fetch_batched(sid,param,start,end):
    # DMI officially allows up to 300000 items per response; bounded to 20000
    # to avoid 1000-item pagination latency. Reject incomplete pages.
    limit=20000;offset=0
    for page in range(15):
        request=dict(stationId=sid,parameterId=param,datetime=f"{start}/{end}",limit=limit,offset=offset)
        response=polite_get(request)
        data=response.json()
        records=data.get("features",[])
        if len(records)>limit:raise ValueError("Unexpected API page size")
        yield from records
        if len(records)<limit:return
        offset+=limit
    raise RuntimeError("DMI oversized pagination exceeded 15 pages")
START="2026-04-01T00:00:00Z";END="2026-11-21T00:00:00Z"
IDS=["06009","06011","06012","06014"];PARAMS=["temp_dry","wind_speed","wind_dir"]
NAMES={"06009":"Akraberg","06011":"Torshavn","06012":"Fugloy","06014":"Eidi","EKVG":"Vagar Airport"}
def collect_dmi():
    rows=[];counts=[]
    for sid in IDS:
        for param in PARAMS:
            features=list(fetch_batched(sid,param,START,END))
            counts.append({"station":sid,"parameter":param,"features":len(features)})
            for x in features:
                p=x["properties"];v=p.get("value")
                if str(p.get("stationId"))!=sid or p.get("parameterId")!=param:raise ValueError("identity mismatch")
                if v is None:continue
                t=pd.Timestamp(p["observed"])
                if t.tzinfo is None:raise ValueError("missing UTC timezone")
                t=t.tz_convert("UTC")
                if not pd.Timestamp(START)<=t<pd.Timestamp(END) or t!=t.floor("h"):continue
                v=float(v)
                if not math.isfinite(v):continue
                lo,hi={"temp_dry":(-40,40),"wind_speed":(0,65),"wind_dir":(0,360)}[param]
                if not lo<=v<=hi:continue
                rows.append({"station":sid,"time":t,"parameter":param,"value":v})
            print(sid,param,len(features),flush=True)
    d=pd.DataFrame(rows)
    if d.empty or d.duplicated(["station","time","parameter"]).any():raise ValueError("no observations or duplicate values")
    d=d.pivot(index=["station","time"],columns="parameter",values="value").reset_index()
    d.columns.name=None;d["source"]="DMI metObs"
    return d,counts
def collect_metar():
    url="https://mesonet.agron.iastate.edu/cgi-bin/request/asos.py"
    args=dict(station="EKVG",data=["tmpf","sknt","drct","metar"],year1=2026,month1=4,day1=1,year2=2026,month2=11,day2=21,tz="Etc/UTC",format="onlycomma",latlon="yes",elev="yes",missing="M",trace="T",report_type=[3,4])
    r=requests.get(url,params=args,timeout=180);r.raise_for_status()
    d=pd.read_csv(io.BytesIO(r.content),comment="#",na_values=["M","T"])
    if not {"station","valid","tmpf","sknt","drct","lat","lon","elevation"}.issubset(d.columns):raise ValueError("METAR schema changed")
    if not d.station.eq("EKVG").all():raise ValueError("wrong METAR station")
    d["time"]=pd.to_datetime(d.valid,utc=True,errors="raise")
    d=d[(d.time>=pd.Timestamp(START))&(d.time<pd.Timestamp(END))]
    if not d.lat.between(62.06,62.08).all() or not d.lon.between(-7.30,-7.27).all() or not d.elevation.between(80,90).all():raise ValueError("METAR location changed")
    if d.time.duplicated().any():raise ValueError("METAR duplicate timestamps")
    d["temp_dry"]=(pd.to_numeric(d.tmpf,errors="coerce")-32)*5/9
    d["wind_speed"]=pd.to_numeric(d.sknt,errors="coerce")*.5144444444444445
    d["wind_dir"]=pd.to_numeric(d.drct,errors="coerce")
    for k,lo,hi in [("temp_dry",-40,40),("wind_speed",0,65),("wind_dir",0,360)]:
        d.loc[~d[k].between(lo,hi),k]=np.nan
    d=d[["time","temp_dry","wind_speed","wind_dir"]].copy()
    d.insert(0,"station","EKVG");d["source"]="IEM METAR"
    return d,{"url":r.url,"raw_sha256":hashlib.sha256(r.content).hexdigest(),"reports":len(d)}
def report(d):
    groups=[];order=["N","NE","E","SE","S","SW","W","NW"]
    d=d.copy();d["date"]=d.time.dt.strftime("%Y-%m-%d")
    d["sector"]=d.wind_dir.map(lambda v:order[int(((v+22.5)%360)//45)] if pd.notna(v) else None)
    for sid,g in d.groupby("station"):
        strong=g[g.wind_speed>=10];paired=g.dropna(subset=["wind_speed","wind_dir"])
        groups.append({"station":sid,"name":NAMES[sid],"source":g.source.iloc[0],"reports":len(g),"days":int(g.date.nunique()),"temperature":int(g.temp_dry.notna().sum()),"wind_speed":int(g.wind_speed.notna().sum()),"wind_direction":int(g.wind_dir.notna().sum()),"paired_wind_direction":len(paired),"strong_10ms_reports":len(strong),"strong_10ms_days":int(strong.date.nunique()),"max_wind_ms":float(g.wind_speed.max()) if g.wind_speed.notna().any() else None,"direction_counts":{v:int((paired.sector==v).sum()) for v in order},"inversion":"not observable from surface-only records"})
    return groups
def main():
    p=argparse.ArgumentParser();p.add_argument("--output",required=True);a=p.parse_args();out=Path(a.output);out.mkdir(parents=True,exist_ok=True)
    receipt={"status":"started","start":START,"end_exclusive":END,"strong_wind_threshold_ms":10}
    try:
        dmi,counts=collect_dmi();iem,meta=collect_metar()
        rows=pd.concat([dmi,iem],ignore_index=True)
        if rows.duplicated(["station","time"]).any():raise ValueError("duplicate station timestamps")
        rows.sort_values(["station","time"]).to_csv(out/"observations.csv.gz",index=False,compression="gzip")
        receipt.update(status="complete",stations=report(rows),rows=len(rows),days=int(rows.time.dt.date.nunique()),dmi_request_counts=counts,metar=meta,training_prohibition="Descriptive weather regimes only. No fitting to prospective benchmark dates.",inversion="Native vertical model profiles needed; no observed inversion evidence in this table.")
    except Exception as e:receipt.update(status="failed",error=str(e));raise
    finally:(out/"status.json").write_text(json.dumps(receipt,indent=2))
if __name__=="__main__":main()
