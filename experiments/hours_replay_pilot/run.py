#!/usr/bin/env python3
"""TouringPlans.com credited historical-park-window sensitivity, not real trips.

Reuse the frozen first pilot's policy/forecast code without changing it. Set its
window constants serially: load/train once over 10:00–24:00, then change only the
completion deadline between a 17:00 control and sourced per-date public close.
Walking and service remain artificial 10-minute values. See REPORT.md.
"""
from __future__ import annotations
import argparse
import csv
import hashlib
import json
import math
from pathlib import Path
import statistics
import sys

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / 'experiments' / 'replay_pilot'))
import replay as core

POLICIES = ('fixed', 'replan', 'threshold10')


def minutes(value: str) -> int:
    hour, minute = map(int, value.split(':'))
    return hour * 60 + minute


def read_hours(path: Path) -> dict:
    with path.open(encoding='utf-8-sig', newline='') as stream:
        rows = list(csv.DictReader(stream))
    result = {}
    for row in rows:
        day = row['date']
        if day in result:
            raise ValueError(f'Duplicate hours for {day}')
        opening, closing = minutes(row['opening_local']), minutes(row['closing_local'])
        if not 0 <= opening <= 600 < closing <= 1440:
            raise ValueError(f'Incompatible public hours for 10:00 start: {row}')
        if not row['source_url'].startswith('https://'):
            raise ValueError(f'Missing public source for {day}')
        if row.get('date_header_verified') != 'True' or not row['source_url'].endswith(day):
            raise ValueError(f'Source-date check missing for {day}')
        result[day] = {**row, 'opening_minutes': opening, 'closing_minutes': closing}
    return result


def common_success(rows: list[dict]) -> dict:
    keys = {(r['date'], r['policy']): r for r in rows}
    dates = sorted({r['date'] for r in rows})
    complete = [d for d in dates if all(keys[d, p]['success'] for p in POLICIES)]
    out = {'days': len(complete), 'by_policy': {}}
    if not complete:
        return out
    for policy in POLICIES:
        selected = [keys[d, policy] for d in complete]
        out['by_policy'][policy] = {
            'mean_elapsed_proxy_minutes': statistics.mean(r['elapsed_min'] for r in selected),
            'mean_route_changes': statistics.mean(r['route_changes'] for r in selected),
            'mean_fixed_minus_policy_minutes': statistics.mean(
                keys[d, 'fixed']['elapsed_min'] - keys[d, policy]['elapsed_min'] for d in complete),
        }
    return out


def check_rows(rows: list[dict], expected_dates: list[str]) -> None:
    assert len(rows) == len(expected_dates) * len(POLICIES)
    assert len({(r['date'], r['policy']) for r in rows}) == len(rows)
    for row in rows:
        assert 0 <= row['completed'] <= 6
        if row['success']:
            assert row['completed'] == 6
            assert len(set(row['completed_order'].split('|'))) == 6
            assert abs(row['elapsed_min'] - row['total_posted_wait_min']
                       - row['total_walk_min'] - row['total_service_min']) < .001
            assert core.START + row['elapsed_min'] <= row['deadline_minutes'] + 1e-8
            assert row['total_walk_min'] == row['total_service_min'] == 60
        for event in row['trace']:
            if event['type'] == 'visit' and event['posted_observed_at'] is not None:
                assert event['posted_observed_at'] <= event['arrival'] + .001
                assert event['arrival'] - event['posted_observed_at'] <= core.MAX_AGE + .001


def run(archive: Path, hours_path: Path, output: Path) -> None:
    output.mkdir(parents=True, exist_ok=True)
    hours_digest = hashlib.sha256(hours_path.read_bytes()).hexdigest()
    hours = read_hours(hours_path)
    spot_path = ROOT/'data/verified_inputs/hours_independent_spot_checks.csv'
    spot_digest = hashlib.sha256(spot_path.read_bytes()).hexdigest()
    with spot_path.open(encoding='utf-8-sig', newline='') as stream:
        alternates = {r['date']: r for r in csv.DictReader(stream) if r['status'] == 'source_conflict'}
    for row in alternates.values():
        assert minutes(row['alternate_opening']) <= 600 < minutes(row['alternate_closing'])
    core.START, core.END = 600., 1440.
    by_ride = core.read_source(archive)
    all_dates = sorted(set.intersection(*(set(by_ride[r]) for r in core.RIDES)))
    n_test = math.ceil(len(all_dates) * core.TEST_FRACTION)
    train, test = all_dates[:-n_test], all_dates[-n_test:]
    missing = sorted(set(test) - set(hours))
    if missing:
        raise ValueError(f'Cannot drop unsupported dates: missing hours for {missing}')
    curves = core.train_curves(by_ride, train)
    # Historical profiles share the same full-day training grid in both scenarios.
    summaries, all_rows, traces = {}, [], []
    for scenario in ('control_17_completion', 'historical_park_close_completion',
                     'historical_close_known_alternates'):
        rows = []
        for day in test:
            core.END = 1020. if scenario.startswith('control') else float(hours[day]['closing_minutes'])
            deadline_source = 'artificial 17:00' if scenario.startswith('control') else hours[day]['source_url']
            if scenario == 'historical_close_known_alternates' and day in alternates:
                core.END = float(minutes(alternates[day]['alternate_closing']))
                deadline_source = alternates[day]['alternate_source_url']
            for policy in POLICIES:
                row = core.replay_day(day, policy, by_ride, curves, 10., 10., trace=True)
                row.update(scenario=scenario, deadline_minutes=core.END,
                           deadline_source=deadline_source,
                           public_open=hours[day]['opening_local'], public_close=hours[day]['closing_local'])
                rows.append(row)
        check_rows(rows, test)
        summary = core.summarize(rows)
        summary['three_policy_common_success'] = common_success(rows)
        for policy in POLICIES:
            record = summary['by_policy'][policy]
            assert record['success_days'] + sum(record['failures_by_reason'].values()) == len(test)
        summaries[scenario] = summary
        all_rows.extend(rows)
        # Fixed predetermined trace date: first test day. Never select for a benefit.
        traces.extend(r for r in rows if r['date'] == test[0])
    parameters = {
        'credit': 'TouringPlans.com — wait archive and published historical park-hours pages',
        'source_archive_sha256': core.SOURCE_SHA256,
        'hours_csv_sha256': hours_digest,
        'spot_check_csv_sha256': spot_digest,
        'alternate_dates': sorted(alternates),
        'alternate_scope': 'Only three known conflicting dates; not a bound on other schedule uncertainty',
        'reused_policy_code_sha256': hashlib.sha256((ROOT/'experiments/replay_pilot/replay.py').read_bytes()).hexdigest(),
        'all_common_days': len(all_dates), 'train_days': len(train), 'test_days': len(test),
        'train_range': [train[0], train[-1]], 'test_range': [test[0], test[-1]],
        'train_grid_local': '10:00–24:00; train-only 15-minute medians',
        'start_local': '10:00 US Eastern; every sourced public opening is at or before 10:00',
        'deadline': 'Finish all six rides by listed public park close (conservative modeling rule, not queue-entry policy)',
        'attraction_hours': 'Not independently verified for every date; park close is not each ride closing time',
        'source_status': 'TouringPlans-listed historical secondary-source schedule, not guaranteed actual hours; independent spot checks found conflicts',
        'walk_per_leg_minutes': 10, 'service_per_ride_minutes': 10,
        'remaining_assumptions': 'Synthetic gate and uniform walk/service; closure/stale-data failure unchanged',
        'control_note': 'Control also uses extended training grid, so not identical to the original 17:00 pilot',
        'status': 'Exploratory historical-window sensitivity; these dates were examined in prior pilots, not a pristine final holdout',
    }
    assert hashlib.sha256(hours_path.read_bytes()).hexdigest() == hours_digest, 'Input changed during run'
    assert hashlib.sha256(spot_path.read_bytes()).hexdigest() == spot_digest, 'Spot-check input changed during run'
    fields = [k for k in all_rows[0] if k != 'trace']
    with (output/'per_day.csv').open('w', newline='', encoding='utf-8') as stream:
        writer = csv.DictWriter(stream, fieldnames=fields)
        writer.writeheader()
        writer.writerows({k:r[k] for k in fields} for r in all_rows)
    for filename, data in [('parameters.json', parameters), ('summary.json', summaries),
                           ('train_curves.json', curves), ('first_test_day_trace.json', traces)]:
        (output/filename).write_text(json.dumps(data, indent=2, ensure_ascii=False)+'\n', encoding='utf-8')
    print(json.dumps(summaries, indent=2))


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--archive', type=Path, default=Path('/tmp/parkplan-ak-933161b.tar.gz'))
    parser.add_argument('--hours', type=Path, default=ROOT/'data/verified_inputs/historical_park_hours.csv')
    parser.add_argument('--output', type=Path, default=Path(__file__).resolve().parent)
    args = parser.parse_args()
    run(args.archive, args.hours, args.output)
