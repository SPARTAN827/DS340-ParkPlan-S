"""TouringPlans.com credited, reproducible study input preparation (stdlib only)."""
from __future__ import annotations
import argparse
import csv
import gzip
import hashlib
import importlib.util
import json
from pathlib import Path
import sys

ROOT=Path(__file__).resolve().parents[2]
HERE=Path(__file__).resolve().parent
ARCHIVE=Path('/tmp/parkplan-ak-933161b.tar.gz')

def digest(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()

def core_module():
    name='parkplan_frozen_core'
    if name in sys.modules:
        return sys.modules[name]
    path=ROOT/'experiments/tie_preserving_pilot/replay.py'
    spec=importlib.util.spec_from_file_location(name,path)
    core=importlib.util.module_from_spec(spec)
    sys.modules[name]=core
    spec.loader.exec_module(core)
    core.START,core.END=600.,1440.
    return core

def load_data(archive=ARCHIVE):
    core=core_module()
    assert digest(archive)==core.SOURCE_SHA256,'Source snapshot differs'
    cache=Path('/tmp')/('parkplan-study-'+core.SOURCE_SHA256[:12]+'.json.gz')
    if cache.exists():
        with gzip.open(cache,'rt',encoding='utf-8') as f:
            saved=json.load(f)
        assert saved['sha256']==core.SOURCE_SHA256 and saved['window']==[585,1440]
        data={r:{d:core.DayRide([core.Observation(t,v) for t,v in events]) for d,events in days.items()}
              for r,days in saved['data'].items()}
    else:
        data=core.read_source(archive)
        plain={r:{d:[[e.minute,e.value] for e in stream.events] for d,stream in days.items()}
               for r,days in data.items()}
        with gzip.open(cache,'wt',encoding='utf-8') as f:
            json.dump({'sha256':core.SOURCE_SHA256,'window':[585,1440],'data':plain},f,separators=(',',':'))
    dates=sorted(set.intersection(*(set(data[r]) for r in core.RIDES)))
    assert len(dates)==550
    return core,data,dates

def get_hours():
    sources=[ROOT/'data/verified_inputs/historical_park_hours.csv', HERE/'inputs/validation_park_hours.csv']
    out={}
    for path in sources:
        if path.exists():
            with path.open(newline='',encoding='utf-8-sig') as f:
                for row in csv.DictReader(f):
                    h,m=map(int,row['closing_local'].split(':'))
                    out[row['date']]={'deadline':h*60+m,'source':row['source_url'],'status':row.get('status','source_listed')}
    return out

def main():
    parser=argparse.ArgumentParser()
    parser.add_argument('--archive',type=Path,default=ARCHIVE)
    args=parser.parse_args()
    core,data,dates=load_data(args.archive)
    splits={'fit':dates[:270],'validation':dates[270:385],'evaluation':dates[385:]}
    old=json.loads((ROOT/'experiments/hours_replay_pilot/parameters.json').read_text())
    assert [splits['evaluation'][0],splits['evaluation'][-1]]==old['test_range']
    out={'source_sha256':core.SOURCE_SHA256,'splits':splits,
         'status':'Retrospective exploratory; evaluation dates previously inspected',
         'credit':'TouringPlans.com',
         'counts':{k:len(v) for k,v in splits.items()}}
    (HERE/'inputs').mkdir(exist_ok=True)
    (HERE/'inputs/splits.json').write_text(json.dumps(out,indent=2)+'\n')
    print(json.dumps({k:{'count':len(v),'range':[v[0],v[-1]]} for k,v in splits.items()},indent=2))

if __name__=='__main__':
    main()
