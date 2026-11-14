"""Download DMI metObs hourly matching records without silently resolving duplicates."""
import argparse,json
from pathlib import Path
import pandas as pd
import requests
BASE="https://opendataapi.dmi.dk/v2/metObs/collections/observation/items"
PARAMS={"temp_dry":("temperature_2m","C"),"wind_speed":("wind_speed_10m","m/s"),"pressure_at_sea":("msl_pressure","hPa"),"precip_past1h":("precipitation_1h","mm")}
def fetch(station,start,end,parameter):
    page=0;seen=set()
    while True:
        args={"stationId":station,"parameterId":parameter,"datetime":f"{start}/{end}","limit":1000,"offset":page*1000}
        r=requests.get(BASE,params=args,timeout=60);r.raise_for_status()
        features=r.json().get("features",[])
        if not features:break
        for x in features:
            if x.get("id") not in seen:
                seen.add(x.get("id"));yield x
        if len(features)<1000:break
        page+=1
        if page>500:raise RuntimeError("DMI pagination guard")
def main():
    p=argparse.ArgumentParser();p.add_argument("--station-ids",nargs="+",required=True)
    p.add_argument("--start",required=True);p.add_argument("--end",required=True)
    p.add_argument("--variables",nargs="+",choices=list(PARAMS),default=["temp_dry","wind_speed","pressure_at_sea"])
    p.add_argument("--output",required=True);a=p.parse_args();records=[];raw=[]
    for station in a.station_ids:
        for parameter in a.variables:
            for f in fetch(station,a.start,a.end,parameter):
                raw.append(f);prop=f["properties"];val=prop.get("value")
                if val is None:continue
                if parameter=="precip_past1h" and float(val)<0:continue
                ts=pd.Timestamp(prop["observed"])
                if ts.tzinfo is None:raise RuntimeError("DMI timestamp missing timezone")
                ts=ts.tz_convert("UTC")
                if ts.minute!=0 or ts.second!=0:continue
                variable,unit=PARAMS[parameter]
                records.append({"station_id":str(prop["stationId"]),"variable":variable,"valid_time":ts.isoformat(),"value":float(val),"unit":unit})
    out=Path(a.output);out.parent.mkdir(parents=True,exist_ok=True)
    df=pd.DataFrame(records,columns=["station_id","variable","valid_time","value","unit"])
    if df.duplicated(["station_id","variable","valid_time"]).any():raise RuntimeError("Duplicate observations require manual quality review")
    df.to_csv(out,index=False)
    out.with_suffix(".raw.json").write_text(json.dumps(raw,ensure_ascii=False),encoding="utf8")
    print("DMI observations:",len(df),"saved to",out)
if __name__=="__main__":main()
