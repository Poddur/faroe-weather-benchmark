"""WeatherNext 3 BigQuery adapter; not activated without access + GCP IAM.

Requires the Analytics Hub listing to be linked into user's own project.
Uses exact initialization hour and bound station/lead query parameters.
There is an explicit bytes-billed cap and a dry-run before execution.
"""
import argparse,json,math,re,os
from datetime import datetime,timezone,timedelta
from pathlib import Path
import pandas as pd
from collect_matched_forecasts import SITES,haversine,iso

TABLE_RE=re.compile(r"^[A-Za-z0-9_-]+\.[A-Za-z0-9_]+\.weathernext_3_0_0_0p1deg$")
SQL="""
SELECT
  f.time AS valid_time,
  f.hours AS lead_hours,
  f.temperature_2m_mean - 273.15 AS temperature_c,
  f.wind_speed_10m_mean AS wind_speed_mps,
  ST_Y(t.geography) AS grid_lat,
  ST_X(t.geography) AS grid_lon,
  ST_DISTANCE(t.geography,ST_GEOGPOINT(@longitude,@latitude)) AS distance_m
FROM `{table}` AS t, UNNEST(t.forecast) AS f
WHERE
  t.init_time = @issue
  AND ST_DWITHIN(t.geography, ST_GEOGPOINT(@longitude,@latitude), 15000)
  AND f.hours IN UNNEST(@leads)
QUALIFY ROW_NUMBER() OVER (PARTITION BY f.hours ORDER BY distance_m) = 1
"""
def query_sql(table):
    if not TABLE_RE.fullmatch(table):raise ValueError("Specify an Analytics Hub-linked 0.1-degree WeatherNext 3 table in full project.dataset.table form")
    return SQL.format(table=table)
def convert(records,sid,issue,leads):
    output=[];seen=set()
    for record in records:
        d=dict(record);lead=int(d["lead_hours"])
        if lead not in leads or lead in seen:raise ValueError("Duplicate/unexpected WeatherNext forecast step")
        seen.add(lead)
        valid=pd.Timestamp(d["valid_time"])
        if valid.tzinfo is None:raise ValueError("Unzoned WeatherNext timestamp")
        valid=valid.tz_convert("UTC")
        if valid != pd.Timestamp(issue)+pd.Timedelta(hours=lead):raise ValueError("Mismatched WeatherNext lead/valid time")
        if float(d["distance_m"])>15000:raise ValueError("WeatherNext nearest cell too distant")
        for var,value,unit in (("temperature_2m",d["temperature_c"],"C"),("wind_speed_10m",d["wind_speed_mps"],"m/s")):
            val=float(value)
            if not math.isfinite(val):raise ValueError("Missing/nonfinite WeatherNext value")
            output.append(dict(station_id=sid,model="WeatherNext3",variable=var,unit=unit,
                               init_time=iso(issue),valid_time=iso(valid.to_pydatetime()),lead_hours=lead,
                               value=val,grid_lat=float(d["grid_lat"]),grid_lon=float(d["grid_lon"]),
                               grid_distance_km=float(d["distance_m"])/1000))
    if seen!=set(leads):raise ValueError("WeatherNext incomplete lead times")
    return output
def collect(table,issue,out,max_bytes=1000000000,leads=(6,12,24)):
    from google.cloud import bigquery
    client=bigquery.Client()
    sql=query_sql(table)
    rows=[];raw={};estimated=0
    for sid,site in SITES.items():
        params=[
          bigquery.ScalarQueryParameter("issue","TIMESTAMP",issue),
          bigquery.ScalarQueryParameter("longitude","FLOAT64",site["lon"]),
          bigquery.ScalarQueryParameter("latitude","FLOAT64",site["lat"]),
          bigquery.ArrayQueryParameter("leads","INT64",list(leads))]
        cfg=bigquery.QueryJobConfig(query_parameters=params,maximum_bytes_billed=max_bytes,use_query_cache=True)
        dry_cfg=bigquery.QueryJobConfig(query_parameters=params,dry_run=True,use_query_cache=False)
        dry_job=client.query(sql,job_config=dry_cfg)
        estimated+=int(dry_job.total_bytes_processed or 0)
        if int(dry_job.total_bytes_processed or 0)>max_bytes:
            raise RuntimeError(f"WeatherNext query for {sid} would scan more than {max_bytes} bytes. Refusing execution.")
        result=[dict(row) for row in client.query(sql,job_config=cfg).result()]
        raw[sid]=result
        rows+=convert(result,sid,issue,set(leads))
    dest=Path(out);dest.mkdir(parents=True,exist_ok=True)
    df=pd.DataFrame(rows);df.to_csv(dest/"weathernext_forecasts.csv",index=False)
    (dest/"bigquery_response.json").write_text(json.dumps(raw,default=str,indent=2))
    (dest/"manifest.json").write_text(json.dumps({"issue_time_utc":iso(issue),"table":table,"max_bytes_billed_per_station":max_bytes,"estimated_total_bytes_scanned":estimated,"station_ids":list(SITES),"rows":len(df),"note":"Must verify Google real-time/historical redistribution terms prior to publication"},indent=2))
    return df
def main():
    p=argparse.ArgumentParser();p.add_argument("--table",default=os.getenv("WEATHERNEXT_BQ_TABLE"))
    p.add_argument("--issue",required=True);p.add_argument("--output",default="outputs/weathernext")
    p.add_argument("--maximum-bytes-billed",type=int,default=1000000000)
    args=p.parse_args()
    if not args.table:raise SystemExit("WEATHERNEXT_BQ_TABLE required after access approval")
    issue=pd.Timestamp(args.issue)
    if issue.tzinfo is None:raise SystemExit("Timezone required")
    collect(args.table,issue.to_pydatetime(),args.output,args.maximum_bytes_billed)
if __name__=="__main__":main()
