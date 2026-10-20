"""TouringPlans.com credited paired retrospective analysis; no policy tuning."""
from __future__ import annotations
import argparse
from collections import Counter
import csv
import json
import math
from pathlib import Path
import random
import statistics as st

HERE=Path(__file__).resolve().parent
SEED=20261019
B=5000

def read_rows(folder):
    with (folder/'per_day.csv').open(newline='') as f: rows=list(csv.DictReader(f))
    for r in rows:
        r['success']=r['success']=='True'
        for k in ['elapsed_min','planning_seconds','total_walk_min','total_posted_wait_min','total_service_min']:
            r[k]=float(r[k]) if r[k] else None
    return rows

def mean(xs): return st.mean(xs) if xs else None

def quantile(xs,q):
    if not xs:return None
    v=sorted(xs);p=(len(v)-1)*q;i=math.floor(p);j=math.ceil(p)
    return v[i]+(v[j]-v[i])*(p-i)

def draw_indices(n,block):
    rng=random.Random(SEED+(0 if block==1 else 7))
    draws=[]
    for _ in range(B):
        if block==1: draws.append([rng.randrange(n) for _ in range(n)])
        else:
            indices=[]
            while len(indices)<n:
                start=rng.randrange(n-block+1)
                indices.extend(range(start,start+block))
            draws.append(indices[:n])
    return draws

def interval(values,draws):
    res=[];undefined=0
    for indices in draws:
        v=[values[i] for i in indices if values[i] is not None]
        if v: res.append(sum(v)/len(v))
        else: undefined+=1
    return {'percentile_95':[quantile(res,.025),quantile(res,.975)],'undefined_resamples':undefined,'resamples':len(draws)}

def analyze(folder):
    rows=read_rows(folder);dates=sorted({r['date'] for r in rows})
    policies=list(dict.fromkeys(r['policy'] for r in rows))
    keys={(r['date'],r['policy']):r for r in rows}
    assert len(keys)==len(rows)==len(dates)*len(policies)
    iid=draw_indices(len(dates),1);blocks=draw_indices(len(dates),7)
    out={'credit':'TouringPlans.com','attempted_days':len(dates),'date_range':[dates[0],dates[-1]],
         'by_policy':{},'paired':{},'common_success':{},
         'inference':'Retrospective exploratory conditional posted-wait-proxy time; not real visitor or all-attempt causal benefit',
         'bootstrap':{'seed':SEED,'replicates':B,'interval':'two-sided95%percentile','block':'7 overlapping noncircular consecutive dates, sample full date records then truncate'}}
    for p in policies:
        rr=[keys[d,p] for d in dates]
        out['by_policy'][p]={'success_days':sum(r['success'] for r in rr),
            'completion_rate':sum(r['success'] for r in rr)/len(dates),
            'failures':dict(Counter(r['failure'] for r in rr if not r['success'])),
            'mean_planning_seconds_per_attempt':mean([r['planning_seconds'] for r in rr]),
            'median_planning_seconds_per_attempt':st.median(r['planning_seconds'] for r in rr)}
    comparisons=[('dynamic','rollout'),('fixed','rollout'),('fixed','dynamic'),
                 ('dynamic','calibrated'),('dynamic','scenario_open_loop'),('scenario_open_loop','rollout'),('calibrated','rollout')]
    for a,b in comparisons:
        if a not in policies or b not in policies:continue
        shared=[d for d in dates if keys[d,a]['success'] and keys[d,b]['success']]
        daily=[keys[d,a]['elapsed_min']-keys[d,b]['elapsed_min'] if d in shared else None for d in dates]
        delta=[v for v in daily if v is not None]
        runtime_adjusted=[keys[d,a]['elapsed_min']+keys[d,a]['planning_seconds']/60-keys[d,b]['elapsed_min']-keys[d,b]['planning_seconds']/60 for d in shared]
        out['paired'][a+'_minus_'+b]={
            'first':a,'second':b,'paired_success_days':len(shared),'shared_dates':shared,
            'mean_first_minutes':mean([keys[d,a]['elapsed_min'] for d in shared]),
            'mean_second_minutes':mean([keys[d,b]['elapsed_min'] for d in shared]),
            'mean_saved_minutes':mean(delta),'median_saved_minutes':st.median(delta) if delta else None,
            'positive_zero_negative':[sum(v>1e-9 for v in delta),sum(abs(v)<=1e-9 for v in delta),sum(v< -1e-9 for v in delta)],
            'min_max_saved_minutes':[min(delta),max(delta)] if delta else None,
            'first_only_success':sum(keys[d,a]['success'] and not keys[d,b]['success'] for d in dates),
            'second_only_success':sum(keys[d,b]['success'] and not keys[d,a]['success'] for d in dates),
            'neither_success':sum(not keys[d,a]['success'] and not keys[d,b]['success'] for d in dates),
            'iid_date_bootstrap':interval(daily,iid),'block7_date_bootstrap':interval(daily,blocks),
            'compute_overhead_adjusted_mean_saved_minutes':mean(runtime_adjusted),
            'daily_saved_minutes':dict(zip(dates,daily))}
    groups={'all':policies,'fixed_dynamic_rollout':['fixed','dynamic','rollout'],'dynamic_calibrated_rollout':['dynamic','calibrated','rollout']}
    for name,pp in groups.items():
        if not all(p in policies for p in pp):continue
        dd=[d for d in dates if all(keys[d,p]['success'] for p in pp)]
        out['common_success'][name]={'policies':pp,'days':len(dd),'mean_minutes':{p:mean([keys[d,p]['elapsed_min'] for d in dd]) for p in pp}}
    (folder/'summary.json').write_text(json.dumps(out,indent=2)+'\n')
    headline={k:{x:v[x] for x in ['paired_success_days','mean_saved_minutes','first_only_success','second_only_success','block7_date_bootstrap']} for k,v in out['paired'].items()}
    print(json.dumps({'folder':str(folder),'completion':{p:v['success_days'] for p,v in out['by_policy'].items()},'comparisons':headline},indent=2))
    return out

if __name__=='__main__':
    parser=argparse.ArgumentParser()
    parser.add_argument('folders',nargs='+',type=Path)
    args=parser.parse_args()
    for folder in args.folders: analyze(folder)
