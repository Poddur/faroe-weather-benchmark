"""Locked, out-of-time winter validation. Exact-run archives, not live issuance.
No fitting, tuning, BigQuery, or observation-dependent prediction.
"""
import argparse, hashlib, json, math
from pathlib import Path
import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
LOCK_SHA = '374bf294dd33741ba0dd635ad68308439108c93b903fbe4e8179533417c44085'
MODELS = ['ECMWF_9km','HARMONIE_DINI_OM','WeatherNext3']
SITES = ['06009','06011','06014']
LEADS = [6,12,24]
VARS = ['temperature_2m','wind_speed_10m']
KEY = ['station_id','variable','init_time','valid_time','lead_hours']
DKEY = ['station_id','init_time','lead_hours']
UNITS = dict(zip(VARS,['C','m/s']))

def sha(p): return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def load_lock():
    p = ROOT/'config/fwa_winter_lock.json'
    if sha(p) != LOCK_SHA: raise ValueError('Model/protocol lock changed')
    return json.loads(p.read_text())

def git_blob_sha(b): return hashlib.sha1(b'blob '+str(len(b)).encode()+b'\0'+b).hexdigest()
def load_terrain(lock):
    p = ROOT/'config/faroe_terrain_profiles.json'
    b = p.read_bytes()
    if git_blob_sha(b) != lock['terrain_git_blob']: raise ValueError('Terrain lock changed')
    r = json.loads(b)
    if r['sha256'] != lock['terrain_dtm_sha256'] or r['crs'] != 'EPSG:5316' or r['status'] != 'geography_verified': raise ValueError('Terrain provenance')
    for site in SITES:
        sectors = r['stations'][site]['sectors']
        if [x['direction_deg'] for x in sectors] != list(range(0,360,5)): raise ValueError('Terrain sector grid')
        for x in sectors:
            if x['coverage'] < .8 or not np.isfinite([x['shelter_deg'],x['exposure_deg']]).all(): raise ValueError('Terrain coverage')
    return r

def normalize(w):
    w = w[KEY+MODELS].copy()
    for c in ['init_time','valid_time']: w[c] = pd.to_datetime(w[c],utc=True,format='ISO8601')
    if w.empty or w[KEY].isna().any().any() or w.duplicated(KEY).any(): raise ValueError('Invalid forecast keys')
    if not set(w.station_id)<=set(SITES) or not set(w.variable)<=set(VARS) or not set(w.lead_hours)<=set(LEADS): raise ValueError('Unsupported forecast group')
    if not ((w.valid_time-w.init_time)==pd.to_timedelta(w.lead_hours,unit='h')).all(): raise ValueError('Invalid lead')
    if not np.isfinite(w[MODELS].to_numpy(dtype=float)).all(): raise ValueError('Nonfinite forecast')
    if (w.loc[w.variable==VARS[1],MODELS]<0).any().any(): raise ValueError('Negative wind input')
    return w

def wide_forecasts(f,issue):
    f=f.copy()
    f['init_time']=pd.to_datetime(f.init_time,utc=True,format='ISO8601')
    f['valid_time']=pd.to_datetime(f.valid_time,utc=True,format='ISO8601')
    expect={(s,v,l,m) for s in SITES for v in VARS for l in LEADS for m in MODELS}
    actual=set(zip(f.station_id,f.variable,f.lead_hours,f.model))
    if len(f)!=54 or actual!=expect or f.duplicated(KEY+['model']).any() or not f.init_time.eq(issue).all(): raise ValueError('Incomplete or incorrect exact-run forecasts')
    if not f.unit.eq(f.variable.map(UNITS)).all(): raise ValueError('Forecast units')
    return normalize(f.pivot(index=KEY,columns='model',values='value').reset_index())

def features(d):
    x=pd.DataFrame(index=d.index)
    for s in SITES: x['site_'+s]=(d.station_id==s).astype(float)
    for l in LEADS: x['lead_'+str(l)]=(d.lead_hours==l).astype(float)
    speed=d.FWA4A
    x['speed']=speed
    for k in [5,10,15]: x['hinge'+str(k)]=(speed-k).clip(lower=0)
    x['sin']=d.sin; x['cos']=d.cos
    for s in SITES:
        x['sin_'+s]=d.sin*x['site_'+s]; x['cos_'+s]=d.cos*x['site_'+s]
    for c in ['shelter','exposure']:
        x[c]=d[c]; x[c+'_speed']=d[c]*speed
    return x

def predict(w,direction,lock,terrain):
    w=normalize(w)
    key=[f'{s}|{v}|{l}' for s,v,l in zip(w.station_id,w.variable,w.lead_hours)]
    bias=np.array([lock['FWA2_bias'][k] for k in key])
    w['FWA2']=(w[MODELS].to_numpy()-bias).mean(axis=1)
    t=w[w.variable==VARS[0]].copy()
    q=w[w.variable==VARS[1]].copy()
    p=lock['FWA5T']
    tx=np.column_stack([(t.station_id==s).astype(float) for s in SITES])
    t['FWA5T']=t.FWA2+tx@np.asarray(p['coefficients'])+p['intercept']
    if q.empty: return t
    x=np.column_stack([np.ones(len(q)),q[MODELS],q.station_id=='06011',q.station_id=='06014',q.lead_hours==12,q.lead_hours==24])
    q['FWA4A']=np.maximum(0,q.HARMONIE_DINI_OM+x@np.asarray(lock['FWA4A']['coefficients']))
    d=direction[DKEY+['sin','cos']].copy()
    d['init_time']=pd.to_datetime(d.init_time,utc=True,format='ISO8601')
    if d.duplicated(DKEY).any(): raise ValueError('Duplicate direction')
    q=q.merge(d,on=DKEY,how='left',validate='one_to_one')
    ok=np.isfinite(q.sin)&np.isfinite(q.cos)&(np.abs(q.sin*q.sin+q.cos*q.cos-1)<1e-6)
    q['direction_available']=ok
    q['shelter']=np.nan; q['exposure']=np.nan
    for i,row in q.loc[ok].iterrows():
        deg=np.degrees(np.arctan2(row['sin'],row['cos']))%360
        sec=terrain['stations'][row.station_id]['sectors'][int(np.floor(deg/5+.5))%72]
        q.loc[i,['shelter','exposure']]=[sec['shelter_deg'],sec['exposure_deg']]
    q['FWA5W_terrain']=np.nan
    p=lock['specialist']
    if ok.any():
        y=q.loc[ok]; xx=features(y)
        if list(xx)!=p['columns'] or not np.isfinite(xx.to_numpy()).all(): raise ValueError('Invalid specialist features')
        q.loc[ok,'FWA5W_terrain']=np.maximum(0,y.FWA4A+xx.to_numpy()@np.asarray(p['coefficients'])+p['intercept'])
    q['activated']=ok&(q.FWA4A>=lock['protocol']['gate_threshold'])
    q['FWA5W']=np.where(q.activated,q.FWA5W_terrain,q.FWA4A)
    return pd.concat([t,q],ignore_index=True)

def pair(pred,obs):
    if obs.empty: return pred.assign(observed=np.nan).iloc[0:0]
    obs=obs.copy(); obs['valid_time']=pd.to_datetime(obs.valid_time,utc=True,format='ISO8601')
    if not obs.unit.eq(obs.variable.map(UNITS)).all(): raise ValueError('Observation units')
    if not np.isfinite(obs.observed.to_numpy(dtype=float)).all(): raise ValueError('Nonfinite observation')
    if (obs.loc[obs.variable==VARS[1],'observed']<0).any(): raise ValueError('Negative wind observation')
    return pred.merge(obs[['station_id','variable','valid_time','observed']],on=['station_id','variable','valid_time'],validate='many_to_one')

def dates(v): return int(v.init_time.nunique())
def week_id(v): return v.init_time.dt.strftime('%G-%V')
def coverage(v,p):
    groups=v.groupby(['station_id','lead_hours']).size().reindex(pd.MultiIndex.from_product([SITES,LEADS]),fill_value=0)
    result={'cases':len(v),'dates':dates(v),'weeks':int(week_id(v).nunique()),'minimum_group_cases':int(groups.min())}
    result['adequate']=result['dates']>=p['minimum_dates'] and result['weeks']>=p['minimum_weeks'] and result['minimum_group_cases']>=p['minimum_cases_per_station_lead']
    return result

def compare(v,a,b,p,mask=None):
    selected=np.ones(len(v),dtype=bool) if mask is None else np.asarray(mask,dtype=bool)
    ea=(v[a]-v.observed).abs(); eb=(v[b]-v.observed).abs(); delta=ea-eb
    z=pd.DataFrame({'week':week_id(v),'sum':np.where(selected,delta,0),'n':selected.astype(int)})
    z=z.groupby('week')[['sum','n']].sum(); active=z.n.gt(0).sum()
    out={'candidate':a,'reference':b,'n':int(selected.sum()),'dates':dates(v.loc[selected]),'weeks':int(active),'mae':float(ea.loc[selected].mean()) if selected.any() else None,'reference_mae':float(eb.loc[selected].mean()) if selected.any() else None,'delta':float(delta.loc[selected].mean()) if selected.any() else None,'ci95':None}
    if active>=8:
        rng=np.random.default_rng(p['seed']); ix=rng.integers(len(z),size=(p['bootstrap_draws'],len(z)))
        n=z.n.to_numpy()[ix].sum(axis=1); sums=z['sum'].to_numpy()[ix].sum(axis=1)
        out['ci95']=np.percentile(sums[n>0]/n[n>0],[2.5,97.5]).tolist()
    return out

def evaluate(v,lock):
    p=lock['protocol']; t=v[v.variable==VARS[0]].copy(); w=v[v.variable==VARS[1]].copy()
    tc=coverage(t,p); wc=coverage(w,p)
    result={'temperature_coverage':tc,'wind_coverage':wc,'temperature_status':'insufficient','specialist_status':'insufficient'}
    if not t.empty:
        r=compare(t,'FWA5T','FWA2',p); stations={s:compare(t[t.station_id==s],'FWA5T','FWA2',p) for s in SITES}
        result.update(temperature_primary=r,temperature_stations=stations,temperature_vs_raw=[compare(t,'FWA5T',m,p) for m in MODELS])
        if tc['adequate'] and r['ci95'] is not None:
            result['temperature_status']='pass' if r['ci95'][1]<0 and all(s['delta'] is not None and s['delta']<=p['max_station_temperature_mae_increase'] for s in stations.values()) else 'not_demonstrated'
    if not w.empty:
        actual=w.observed>=p['strong_threshold']; base=w.FWA4A>=p['strong_threshold']; specialist=w.FWA5W>=p['strong_threshold']; eligible=w.FWA4A>=p['gate_threshold']; available=w.direction_available.eq(True)
        c=compare(w,'FWA5W','FWA4A',p); strong=compare(w,'FWA5W','FWA4A',p,actual)
        fraction=float(available.mean()); gate_fraction=float(available.loc[eligible].mean()) if eligible.any() else 0.
        alerts={m:{'hits':int((a&actual).sum()),'misses':int((~a&actual).sum()),'false_alarms':int((a&~actual).sum())} for m,a in [('FWA4A',base),('FWA5W',specialist)]}
        result.update(wind_primary=strong,wind_overall=c,wind_reference_vs_raw=[compare(w,'FWA4A',m,p) for m in MODELS],wind_direction_fraction=fraction,wind_gate_direction_fraction=gate_fraction,wind_alerts=alerts)
        ready=wc['adequate'] and strong['n']>=p['minimum_strong_cases'] and strong['dates']>=p['minimum_strong_dates'] and strong['weeks']>=p['minimum_strong_weeks'] and min(fraction,gate_fraction)>=p['min_direction_fraction'] and strong['ci95'] is not None and c['ci95'] is not None
        if ready:
            result['specialist_status']='pass' if strong['ci95'][1]<0 and c['ci95'][1]<=p['max_wind_mae_increase'] and alerts['FWA5W']['misses']<=alerts['FWA4A']['misses'] else 'not_demonstrated'
    return result

def replay(evidence,lock,terrain):
    a=Path(evidence)/'frozen_predictions.csv'; b=Path(evidence)/'wind_predictions.csv'
    if sha(a)!=lock['source_frozen_predictions_sha256'] or sha(b)!=lock['source_wind_predictions_sha256']: raise ValueError('Replay evidence changed')
    f=pd.read_csv(a,dtype={'station_id':str}); w=pd.read_csv(b,dtype={'station_id':str})
    out=predict(f,w[DKEY+['sin','cos']],lock,terrain)
    z=out.merge(f[KEY+['FWA2']].assign(init_time=pd.to_datetime(f.init_time,utc=True,format='ISO8601'),valid_time=pd.to_datetime(f.valid_time,utc=True,format='ISO8601')),on=KEY,suffixes=('','_original'),validate='one_to_one')
    e2=float((z.FWA2-z.FWA2_original).abs().max()); assert len(z)==432 and e2<1e-10
    z=out.merge(w[KEY+['FWA4A','shelter','exposure']].assign(init_time=pd.to_datetime(w.init_time,utc=True,format='ISO8601'),valid_time=pd.to_datetime(w.valid_time,utc=True,format='ISO8601')),on=KEY,suffixes=('','_original'),validate='one_to_one')
    e4=float((z.FWA4A-z.FWA4A_original).abs().max()); assert len(z)==189 and e4<1e-10
    assert np.allclose(z.shelter,z.shelter_original,rtol=0,atol=1e-10) and np.allclose(z.exposure,z.exposure_original,rtol=0,atol=1e-10)
    altered=f.copy(); altered['observed']=999999
    pd.testing.assert_frame_equal(out,predict(altered,w[DKEY+['sin','cos']],lock,terrain))
    missing=predict(f,w[DKEY+['sin','cos']].iloc[0:0],lock,terrain); wind=missing[missing.variable==VARS[1]]
    assert wind.FWA5W.eq(wind.FWA4A).all() and not wind.activated.any()
    return {'status':'replay_pass','fwa2_cases':432,'fwa4a_cases':189,'max_fwa2_error':e2,'max_fwa4a_error':e4,'terrain_cases':189,'observation_invariance':True,'missing_direction_fallback':True}

def atomic_json(path,obj):
    tmp=path.with_suffix(path.suffix+'.tmp'); tmp.write_text(json.dumps(obj,default=str,allow_nan=False,indent=2)); tmp.replace(path)

def run(out,cache,lock,terrain,smoke=False):
    from fwa_historical_pilot import om_rows
    from fwa_confirmatory import directions
    from historical_weathernext_benchmark import collect_observations
    from probe_weathernext_dynamical import PRODUCT, STATIONS, forecast_rows
    import dynamical_catalog
    p=lock['protocol']; now=pd.Timestamp.now(tz='UTC').normalize()
    for s in SITES:
        for axis in ['lat','lon']:
            if abs(terrain['stations'][s][axis]-STATIONS[s][axis])>1e-8: raise ValueError('Terrain station mismatch')
    first=pd.Timestamp(p['first_issue'],tz='UTC'); last=pd.Timestamp(p['last_issue'],tz='UTC')
    eligible=list(pd.date_range(first,min(last,now-pd.Timedelta(days=p['archive_lag_days'])),freq='D')) if now-pd.Timedelta(days=p['archive_lag_days'])>=first else []
    if smoke: eligible=[pd.Timestamp('2026-11-19',tz='UTC')] if now>=pd.Timestamp('2026-11-20',tz='UTC') else []
    cache.mkdir(parents=True,exist_ok=True); out.mkdir(parents=True,exist_ok=True)
    for sub in ['om','directions']: (cache/sub).mkdir(exist_ok=True)
    records={}; failures=[]; ds=None
    for issue in eligible:
        day=issue.strftime('%Y%m%d'); path=cache/(day+'.json')
        if path.exists():
            r=json.loads(path.read_text())
            if r['lock_sha256']!=LOCK_SHA or r['issue']!=str(issue): raise ValueError('Checkpoint provenance mismatch')
            records[day]=r
    pending=[i for i in eligible if not records.get(i.strftime('%Y%m%d'),{}).get('complete',False)]
    # Fixed retry budget sorted by attempts, never by performance. Prefer unattempted dates.
    pending.sort(key=lambda i:(records.get(i.strftime('%Y%m%d'),{}).get('attempts',0),i))
    try:
        for issue in pending[:12]:
            day=issue.strftime('%Y%m%d'); path=cache/(day+'.json'); old=records.get(day,{})
            r={'issue':str(issue),'lock_sha256':LOCK_SHA,'attempts':old.get('attempts',0)+1,'complete':False}
            try:
                fp=cache/(day+'_forecasts.csv')
                if fp.exists(): f=pd.read_csv(fp,dtype={'station_id':str})
                else:
                    raw=[]; values=om_rows(issue,raw,cache/'om')
                    if ds is None:
                        ds=dynamical_catalog.open(PRODUCT,chunks=None)
                        if 'degree_Celsius' not in ds.temperature_2m.attrs.get('units','') or ds.wind_speed_10m.attrs.get('units') not in ('m s-1','m/s'): raise ValueError('WeatherNext units')
                    for lead in LEADS: values.extend(forecast_rows(ds,issue,lead))
                    f=pd.DataFrame(values); wide_forecasts(f,issue); f.to_csv(fp,index=False)
                w=wide_forecasts(f,issue)
                direction=directions(w[w.variable==VARS[1]],cache/'directions')
                pred=predict(w,direction,lock,terrain)
                pred.to_csv(cache/(day+'_predictions.csv'),index=False)
                # Observation retrieval occurs only after all model predictions are computed.
                obs,raw,queries=collect_observations([issue],LEADS)
                paired=pair(pred,obs)
                paired.to_csv(cache/(day+'_paired.csv'),index=False)
                r.update(paired_cases=len(paired),direction_cases=int(pred.direction_available.eq(True).sum()),complete=len(paired)==18 and pred.direction_available.eq(True).sum()==9,paired_sha256=sha(cache/(day+'_paired.csv')))
                r['queries']=queries
                print(day,'paired',len(paired),'direction cases',r['direction_cases'],flush=True)
            except Exception as ex:
                # Keep previously verified pairs if a retry fails; no selection by error.
                r.update({k:v for k,v in old.items() if k in ['paired_cases','direction_cases','paired_sha256','queries']})
                r['error']=f'{type(ex).__name__}: {ex}'[:400]; failures.append({'issue':str(issue),'error':r['error']}); print(day,r['error'],flush=True)
            atomic_json(path,r); records[day]=r
    finally:
        if ds is not None: ds.close()
    parts=[]
    for day,r in sorted(records.items()):
        path=cache/(day+'_paired.csv')
        if 'paired_sha256' not in r or r.get('paired_cases',0)==0: continue
        if sha(path)!=r['paired_sha256']: raise ValueError('Paired checkpoint hash mismatch')
        v=pd.read_csv(path,dtype={'station_id':str}); v['init_time']=pd.to_datetime(v.init_time,utc=True,format='ISO8601'); v['valid_time']=pd.to_datetime(v.valid_time,utc=True,format='ISO8601')
        if len(v)!=r['paired_cases'] or not v.init_time.eq(pd.Timestamp(r['issue'])).all(): raise ValueError('Paired checkpoint identity')
        parts.append(v)
    status={'status':'preflight_only' if smoke else 'collecting','lock_sha256':LOCK_SHA,'planned_dates':84,'eligible_dates':len(eligible),'dates_attempted':len(records),'complete_dates':sum(r.get('complete',False) for r in records.values()),'failures':failures,'bigquery_queries':0,'historical_archive_only':True,'protocol':p}
    if parts:
        v=pd.concat(parts,ignore_index=True)
        if v.duplicated(KEY).any(): raise ValueError('Duplicated verification cases')
        status['paired_dates']=dates(v); status['pairs_by_variable']={k:int(n) for k,n in v.groupby('variable').size().items()}
        if not smoke and now>=pd.Timestamp(p['finalize_after'],tz='UTC'):
            status['status']='finalized'; status['evaluation']=evaluate(v,lock); v.to_csv(out/'paired.csv',index=False)
    elif not smoke and now>=pd.Timestamp(p['finalize_after'],tz='UTC'):
        status.update(status='finalized_insufficient',evaluation={'temperature_status':'insufficient','specialist_status':'insufficient'})
    atomic_json(out/'status.json',status)
    print(json.dumps(status,indent=2),flush=True)
    return status

def main():
    parser=argparse.ArgumentParser(); parser.add_argument('--replay'); parser.add_argument('--smoke',action='store_true'); parser.add_argument('--cache',default='winter-cache'); parser.add_argument('--out',default='outputs/fwa-winter'); args=parser.parse_args()
    lock=load_lock(); terrain=load_terrain(lock)
    if args.replay: print(json.dumps(replay(args.replay,lock,terrain),indent=2)); return
    run(Path(args.out),Path(args.cache),lock,terrain,args.smoke)
if __name__=='__main__': main()
