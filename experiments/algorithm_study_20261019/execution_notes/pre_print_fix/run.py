"""TouringPlans.com credited retrospective algorithm study; stdlib only.

Run prepare.py, source validation hours, then validate -> select -> reference ->
evaluate -> sensitivity. No old experiment is overwritten. PROTOCOL.md defines
the candidate, assumptions, selection and reporting rules before outcomes.
"""
from __future__ import annotations
import argparse
from collections import Counter
import csv
from dataclasses import asdict
from datetime import datetime, timezone
import hashlib
import json
import math
import multiprocessing as mp
from pathlib import Path
import statistics
import time

from prepare import ROOT,HERE,ARCHIVE,digest,load_data,get_hours
import engine as e

G={}

def clean(value):
    if isinstance(value,float) and not math.isfinite(value): return None
    if isinstance(value,dict): return {k:clean(v) for k,v in value.items()}
    if isinstance(value,(list,tuple)): return [clean(v) for v in value]
    return value

def save(path,value):
    Path(path).write_text(json.dumps(clean(value),indent=2,ensure_ascii=False,allow_nan=False)+'\n')

def configuration(name):
    if name=='reference': return e.Config.uniform(10,10)
    if name=='uniform5': return e.Config.uniform(5,5)
    if name=='uniform15': return e.Config.uniform(15,15)
    # Explicitly illustrative topology, NOT measured2018 park travel times.
    edges=[('GATE','HUB',5),('HUB','AFRICA',7),('HUB','ASIA',6),
           ('HUB','DINO',5),('HUB','PANDORA',6),('AFRICA','ASIA',8),
           ('ASIA','DINO',5),('PANDORA','AFRICA',7),
           ('AFRICA','AK07',2),('ASIA','AK11',2),('ASIA','AK14',3),
           ('DINO','AK18',2),('PANDORA','AK85',1),('PANDORA','AK86',2)]
    nodes=sorted(set(a for a,b,w in edges)|set(b for a,b,w in edges))
    d={a:{b:(0.0 if a==b else math.inf) for b in nodes} for a in nodes}
    for a,b,w in edges: d[a][b]=d[b][a]=float(w)
    for k in nodes:
        for a in nodes:
            for b in nodes: d[a][b]=min(d[a][b],d[a][k]+d[k][b])
    scale={'illustrative':1.,'illustrative_fast':.8,'illustrative_slow':1.2}[name]
    walks={a:{b:d[a][b]*scale for b in e.RIDES} for a in ('GATE',)+e.RIDES}
    # Published nominal duration labels only, not full-service measurements.
    service=dict(zip(e.RIDES,(20.,4.,10.,4.,5.,6.)))
    return e.Config(walk=walks,service=service)

def snapshot(day,now):
    return {r:day[r].asof(now) for r in e.RIDES}

def replay(date,policy,config_name,curves,bank,data,hours,decay=60):
    cfg=configuration(config_name)
    predictor=e.Predictor(curves,decay)
    day={r:data[r][date] for r in e.RIDES}
    start_snapshot=snapshot(day,cfg.start)
    initial,initial_finish=e.base_order(e.RIDES,'GATE',cfg.start,start_snapshot,cfg,e.Predictor(curves,60))
    deadline_record=hours.get(date,{'deadline':1200,'source':'declared20:00 analysis fallback','status':'not sourced park hours'})
    row={'date':date,'policy':policy,'configuration':config_name,'decay':decay,
         'initial_order':'|'.join(initial),'initial_predicted_finish':initial_finish,
         'deadline':deadline_record['deadline'],'deadline_source':deadline_record['source'],
         'success':False,'failure':'','completed':0,'elapsed_min':None,'total_walk_min':0.,
         'total_posted_wait_min':0.,'total_service_min':0.,'replans':0,'route_changes':0,
         'next_changes':0,'planning_seconds':0.,'completed_order':'','events':[]}
    if not math.isfinite(initial_finish):
        row['failure']='no_route_from_available_predictions'
        return row
    now=cfg.start;location='GATE';remaining=tuple(initial);completed=[]
    method='dynamic' if policy.startswith('calibrated') else policy
    while remaining:
        ride,remaining=remaining[0],remaining[1:]
        travel=cfg.walk[location][ride]
        arrival=now+travel
        obs=day[ride].asof(arrival)
        failure=''
        if arrival>row['deadline']+e.EPS: failure='arrival_after_window'
        elif obs is None: failure='no_fresh_posted_at_arrival'
        elif obs.value==-999: failure='closed_at_arrival'
        elif arrival+obs.value+cfg.service[ride]>row['deadline']+e.EPS: failure='completion_after_window'
        visit={'type':'visit','ride':ride,'from':location,'depart':now,'arrival':arrival,
               'walk':travel,'posted_observed_at':obs.minute if obs else None,
               'posted_wait':obs.value if obs else None,'service':cfg.service[ride],
               'status':failure or 'completed'}
        row['events'].append(visit); row['total_walk_min']+=travel
        if failure:
            row['failure']=failure
            break
        now=arrival+obs.value+cfg.service[ride]
        visit['finish']=now
        row['total_posted_wait_min']+=obs.value;row['total_service_min']+=cfg.service[ride]
        completed.append(ride);row['completed']=len(completed);location=ride
        if remaining and method!='fixed':
            incumbent=remaining;current=snapshot(day,now)
            began=time.perf_counter()
            remaining,meta=e.plan(method,incumbent,location,now,current,cfg,predictor,bank)
            duration=time.perf_counter()-began
            row['planning_seconds']+=duration;row['replans']+=1
            row['route_changes']+=remaining!=incumbent
            row['next_changes']+=remaining[0]!=incumbent[0]
            row['events'].append({'type':'decision','at':now,'location':location,
                'incumbent':incumbent,'selected':remaining,'compute_seconds':duration,
                'snapshot':{r:None if o is None else {'minute':o.minute,'value':o.value} for r,o in current.items()},
                **meta})
    row['completed_order']='|'.join(completed)
    if len(completed)==6:
        row['success']=True;row['elapsed_min']=now-cfg.start
        assert len(set(completed))==6
        assert abs(row['elapsed_min']-sum(row[k] for k in ['total_walk_min','total_posted_wait_min','total_service_min']))<1e-7
    return row

def task(date):
    return [replay(date,policy,G['config'],G['curves'],G['bank'],G['data'],G['hours'],decay)
            for policy,decay in G['policies']]

def write_rows(folder,rows,metadata):
    folder.mkdir(exist_ok=True,parents=True)
    fields=[k for k in rows[0] if k!='events']
    with (folder/'per_day.csv').open('w',newline='') as f:
        writer=csv.DictWriter(f,fieldnames=fields);writer.writeheader()
        writer.writerows({k:row[k] for k in fields} for row in rows)
    save(folder/'traces.json',[{k:row[k] for k in ['date','policy','events']} for row in rows])
    save(folder/'metadata.json',metadata)
    policies=list(dict.fromkeys(r['policy'] for r in rows))
    print(json.dumps({'configuration':metadata['configuration'],'rows':len(rows),
        'completed':{p:sum(r['success'] for r in rows if r['policy']==p) for p in policies}},flush=True))

def read_rows(folder):
    with (Path(folder)/'per_day.csv').open(newline='') as f: rows=list(csv.DictReader(f))
    for r in rows:
        r['success']=r['success']=='True'
        r['completed']=int(r['completed'])
        r['elapsed_min']=float(r['elapsed_min']) if r['elapsed_min'] else None
    return rows

def choose(rows,policies,tie_order):
    dates=sorted({r['date'] for r in rows});keys={(r['date'],r['policy']):r for r in rows}
    common=[d for d in dates if all(keys[d,p]['success'] for p in policies)]
    counts={p:sum(keys[d,p]['success'] for d in dates) for p in policies}
    means={p:statistics.mean(keys[d,p]['elapsed_min'] for d in common) if common else None for p in policies}
    eligible=[p for p in policies if counts[p]>=counts['dynamic'] and common]
    winner=min(eligible,key=lambda p:(means[p],tie_order.index(p))) if eligible else 'dynamic'
    if not common or means[winner]>=means['dynamic']-1e-9: winner='dynamic'
    return {'selected':winner,'shared_success_days':len(common),'success_counts':counts,'common_mean_minutes':means,
            'completion_discordance':{p:{'baseline_only':sum(keys[d,'dynamic']['success'] and not keys[d,p]['success'] for d in dates),
                                         'candidate_only':sum(keys[d,p]['success'] and not keys[d,'dynamic']['success'] for d in dates)} for p in policies}}

def select():
    rows=read_rows(HERE/'validation')
    decay_policies=['dynamic']+[f'calibrated_{v}' for v in [15,30,60,120]]
    decay_choice=choose(rows,decay_policies,['dynamic','calibrated_60','calibrated_15','calibrated_30','calibrated_120'])
    chosen_decay=60 if decay_choice['selected']=='dynamic' else int(decay_choice['selected'].split('_')[-1])
    rec=choose(rows,['dynamic',f'calibrated_{chosen_decay}','rollout'],['dynamic',f'calibrated_{chosen_decay}','rollout'])
    out={'frozen_at_utc':datetime.now(timezone.utc).isoformat(),'selected_decay':chosen_decay,
         'decay_selection':decay_choice,'within_replay_recommendation':rec,
         'primary_hypothesis':'rollout vs dynamic regardless of validation recommendation',
         'protocol_sha256':digest(HERE/'PROTOCOL.md'),'validation_csv_sha256':digest(HERE/'validation/per_day.csv'),
         'engine_sha256':digest(HERE/'engine.py'),'runner_sha256':digest(__file__),
         'status':'Frozen before new evaluation outcomes; old evaluation dates already examined'}
    save(HERE/'selection.json',out);print(json.dumps(out,indent=2))

def preserved():
    manifest=json.loads((ROOT/'experiments/tie_preserving_pilot/preserved_artifacts_sha256.json').read_text())
    for name,expected in manifest.items(): assert digest(ROOT/name)==expected,name
    return len(manifest)

def run(phase,workers):
    core,data,dates=load_data()
    splits=json.loads((HERE/'inputs/splits.json').read_text())['splits']
    validation=phase=='validate'
    train=splits['fit'] if validation else splits['fit']+splits['validation']
    target=splits['validation'] if validation else splits['evaluation']
    curves=core.train_curves(data,train)
    hours=get_hours()
    if validation:
        assert (HERE/'inputs/validation_hours_status.json').exists(),'Source hours status must be frozen first'
        policies=[('fixed',60),('dynamic',60)]+[(f'calibrated_{v}',v) for v in [15,30,60,120]]+[(p,60) for p in ['rollout','scenario_open_loop']]
    elif phase=='reference': policies=[('fixed',60),('dynamic',60)]
    else:
        selected=json.loads((HERE/'selection.json').read_text())
        assert selected['protocol_sha256']==digest(HERE/'PROTOCOL.md'),'Protocol changed after selection'
        assert selected['engine_sha256']==digest(HERE/'engine.py'),'Engine changed after selection; document and rerun selection'
        assert selected['runner_sha256']==digest(__file__),'Runner changed after selection'
        policies=[('fixed',60),('dynamic',60),('calibrated',selected['selected_decay']),('rollout',60),('scenario_open_loop',60)]
    configs=['reference'] if phase!='sensitivity' else ['uniform5','uniform15','illustrative','illustrative_fast','illustrative_slow']
    for conf in configs:
        G.update(data=data,curves=curves,bank=e.ScenarioBank(data,train,curves,k=8),hours=hours,config=conf,policies=policies)
        began=time.perf_counter();rows=[]
        if workers>1 and 'fork' in mp.get_all_start_methods():
            with mp.get_context('fork').Pool(workers) as pool:
                for i,batch in enumerate(pool.imap(task,target),1):
                    rows.extend(batch)
                    if i%20==0: print(f'{phase} {conf}: {i}/{len(target)} dates',flush=True)
        else:
            for i,date in enumerate(target,1):
                rows.extend(task(date))
                if i%20==0: print(f'{phase} {conf}: {i}/{len(target)} dates',flush=True)
        folder=HERE/('validation' if validation else ('reference_check' if phase=='reference' else 'evaluation'))
        if phase=='sensitivity': folder=HERE/'sensitivity'/conf
        metadata={'credit':'TouringPlans.com','phase':phase,'configuration':conf,'config':asdict(configuration(conf)),
            'train_dates':train,'evaluation_dates':target,'policy_decay':policies,
            'scenario_count':8,'elapsed_runtime_seconds':time.perf_counter()-began,
            'deadline_fallback_dates':[d for d in target if d not in hours],
            'source_sha256':core.SOURCE_SHA256,'protocol_sha256':digest(HERE/'PROTOCOL.md'),
            'engine_sha256':digest(HERE/'engine.py'),'runner_sha256':digest(__file__),
            'validation_hours_sha256':digest(HERE/'inputs/validation_park_hours.csv') if (HERE/'inputs/validation_park_hours.csv').exists() else None,
            'old_artifacts_unchanged':preserved(),'status':'retrospective exploratory, not real visitor benefit'}
        if not validation and phase!='reference': metadata['selection_sha256']=digest(HERE/'selection.json')
        write_rows(folder,rows,metadata)
        if phase=='reference':
            with (ROOT/'experiments/hours_replay_pilot/per_day.csv').open(newline='') as f:
                old={(r['date'],r['policy']):r for r in csv.DictReader(f) if r['scenario']=='historical_park_close_completion'}
            for row in rows:
                r=old[row['date'],'replan' if row['policy']=='dynamic' else 'fixed']
                for k in ['initial_order','completed_order','failure']: assert row[k]==r[k],(row['date'],k,row[k],r[k])
                assert row['success']==(r['success']=='True')
                assert row['completed']==int(r['completed'])
                assert row['route_changes']==int(r['route_changes'])
                if row['success']: assert abs(row['elapsed_min']-float(r['elapsed_min']))<1e-7
            save(folder/'verification.json',{'rows_matched':len(rows),'all_fields_checked':['initial_order','completed_order','failure','success','completed','route_changes','elapsed_min'],'old_artifact_hashes':preserved()})
            print('Reference parity PASS:330 old fixed/dynamic outcomes',flush=True)

if __name__=='__main__':
    parser=argparse.ArgumentParser()
    parser.add_argument('phase',choices=['validate','select','reference','evaluate','sensitivity'])
    parser.add_argument('--workers',type=int,default=2)
    args=parser.parse_args()
    if args.phase=='select': select()
    else: run(args.phase,args.workers)
