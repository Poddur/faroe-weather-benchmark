"""Auditable predeclared-issue WeatherNext historical scorecard.

One block per independent forecast issue (date), not station/lead independence.
No significance claims from a small retrospective sample.
"""
import argparse,json,hashlib
from pathlib import Path
import numpy as np
import pandas as pd
def prepare(root):
    root=Path(root)
    m=json.loads((root/"manifest.json").read_text())
    for filename,key in [("forecasts.csv","forecast_csv_sha256"),("observations.csv","observation_csv_sha256"),("dmi_original_features.json","dmi_original_features_sha256")]:
        actual=hashlib.sha256((root/filename).read_bytes()).hexdigest()
        if actual!=m.get(key):raise ValueError("SHA256 mismatch: "+filename)
    if m.get("status")!="exploratory_success":raise ValueError("Source collection must have succeeded")
    f=pd.read_csv(root/"forecasts.csv",dtype={"station_id":str})
    o=pd.read_csv(root/"observations.csv",dtype={"station_id":str})
    for c in ["init_time","valid_time"]:f[c]=pd.to_datetime(f[c],utc=True)
    o["valid_time"]=pd.to_datetime(o.valid_time,utc=True)
    if f.duplicated(["station_id","variable","init_time","valid_time","model"]).any():raise ValueError("Duplicate forecast keys")
    if o.duplicated(["station_id","variable","valid_time"]).any():raise ValueError("Duplicate observation keys")
    if not ((f.valid_time-f.init_time)==pd.to_timedelta(f.lead_hours,unit="h")).all():raise ValueError("Model lead/valid mismatch")
    if (f.model!="WeatherNext3").any():raise ValueError("Non-WeatherNext model in archive")
    join=f.merge(o,on=["station_id","variable","valid_time"],how="left",
        suffixes=("","_observed"),validate="many_to_one",indicator=True)
    if ((join._merge=="both")&(join.unit!=join.unit_observed)).any():raise ValueError("Units mismatched")
    paired=join[join._merge=="both"].copy()
    paired["error"]=paired.value-paired.observed
    paired["absolute_error"]=paired.error.abs()
    paired["squared_error"]=paired.error**2
    paired["month"]=paired.init_time.dt.strftime("%Y-%m")
    return m,join,paired

def group_scores(paired,by):
    fields=by if isinstance(by,list) else [by]
    if paired.empty:
        return pd.DataFrame(columns=fields+["n","independent_issues","mae","rmse","bias"])
    g=paired.groupby(fields,dropna=False)
    result=g.agg(n=("error","size"),independent_issues=("init_time","nunique"),
        mae=("absolute_error","mean"),squared=("squared_error","mean"),bias=("error","mean")).reset_index()
    result["rmse"]=np.sqrt(result.pop("squared"))
    return result

def bootstrap_mae_issues(paired,group_fields,seed=20261115,n_bootstrap=1000):
    rng=np.random.default_rng(seed);results=[]
    for names,group in paired.groupby(group_fields,dropna=False):
        if not isinstance(names,tuple):names=(names,)
        unique=group.init_time.unique()
        if len(unique)<10:continue
        per_issue=[group[group.init_time==x].absolute_error.to_numpy(dtype=float) for x in unique]
        draws=[]
        for _ in range(n_bootstrap):
            idx=rng.integers(0,len(per_issue),size=len(per_issue))
            draws.append(np.concatenate([per_issue[i] for i in idx]).mean())
        row=dict(zip(group_fields,names))
        row.update(independent_issues=len(unique),mae_ci95_low=float(np.percentile(draws,2.5)),
                   mae_ci95_high=float(np.percentile(draws,97.5)))
        results.append(row)
    return pd.DataFrame(results,columns=list(group_fields)+["independent_issues","mae_ci95_low","mae_ci95_high"])

def build(root):
    root=Path(root);m,all_rows,paired=prepare(root)
    bylead=group_scores(paired,["variable","lead_hours"])
    bystation=group_scores(paired,["station_id","variable","lead_hours"])
    bymonth=group_scores(paired,["month","variable","lead_hours"])
    ci=bootstrap_mae_issues(paired,["variable","lead_hours"])
    for name,frame in [("scorecard_by_lead",bylead),("scorecard_by_station",bystation),
                       ("scorecard_by_month",bymonth),("confidence_intervals",ci)]:
        frame.to_csv(root/(name+".csv"),index=False)
    n_dates=int(paired.init_time.nunique())
    total=len(all_rows);matched=len(paired)
    lines=[
        "# WeatherNext 3: historical Faroe Islands verification",
        "",
        "**Research status:** Retrospective WeatherNext 3 archive sample against DMI metObs. "
        "Historical availability does not prove prospective publication at original issue time.",
        "",
        f"- Requested initialization dates: **{len(m.get('issue_times_utc',[]))}**.",
        f"- Retrieved forecast values: **{total}**, paired with actual DMI station observations: **{matched}** "
        f"({100*matched/total:.1f}% coverage)." if total else "- No forecasts.",
        f"- Independent issue timestamps with paired observations: **{n_dates}**.",
        "- Stations: Suður 06009, Tórshavn 06011, Eiði 06014.",
        "- 2m temperature: °C; 10m scalar wind: m/s; errors = forecast − observed.",
        "",
        "## By-lead metrics (pooled station locations and issue dates)",
        "",
        "| Variable | Lead | N | Issue dates | MAE | RMSE | Bias |",
        "|---|---:|---:|---:|---:|---:|---:|",
    ]
    for row in bylead.itertuples():
        lines.append(f"| {row.variable} | +{row.lead_hours}h | {row.n} | {row.independent_issues} | {row.mae:.3f} | {row.rmse:.3f} | {row.bias:+.3f} |")
    lines += ["","## Statistical and observational limitations","",
      "- Bootstrap uncertainty resamples **entire independent issue dates**, not individual station records. "
      "Intervals only reported for groups with at least ten independent initializations.",
      "- The 20 predeclared dates are spaced two per month across January–October 2026; "
      "this is **not** a complete daily 2026 retrospective test.",
      "- Three stations share regional weather; do not interpret their observations as three independent storms.",
      "- DMI sensor height, wind averaging period, topography and potential historical data revisions remain unverified.",
      "- The WeatherNext historical archive may be reconstructed or backfilled; model publication provenance is not verified.",
      "- This is WeatherNext vs DMI **only**. No equivalent ECMWF/HARMONIE historical archived issues "
      "exist in this project for these same dates, so no three-model ranking can be inferred.",
      "",
      "## Machine-readable datasets","",
      "See scorecard_by_lead.csv, scorecard_by_station.csv, scorecard_by_month.csv, "
      "confidence_intervals.csv and the original forecast/observation/raw feature files, with SHA-256 in manifest.json.",""]
    (root/"RESEARCH_REPORT.md").write_text("\n".join(lines))
    return {"paired":matched,"forecast":total,"unique_issue_times":n_dates,"groups":len(bylead)}

def main():
    p=argparse.ArgumentParser();p.add_argument("--root",required=True);a=p.parse_args()
    print(json.dumps(build(a.root),indent=2))
if __name__=="__main__":main()
