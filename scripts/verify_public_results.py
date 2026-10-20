#!/usr/bin/env python3
"""Public-scoped independent result audit; imports no experiment implementation.

Derived from the unchanged original verifier; see PUBLIC-ADAPTER-PROVENANCE.md.
Twenty included legacy hashes are verified; eleven historical meeting/archive
files are intentionally absent. This never reissues the original31-file audit.

TouringPlans.com source attribution. Only derived audit outputs are written.
Existing completed phase triplets are checked; absent phases remain explicitly
unverified. This program never runs policies, fits predictors, or tunes choices.
"""
from __future__ import annotations

import argparse
import bisect
from collections import Counter, defaultdict
import csv
from datetime import datetime, timezone
import hashlib
import io
import json
import math
from pathlib import Path
import random
import statistics
import tarfile

from public_integrity import check_frozen_entrypoints, check_public_preservation

ROOT = Path(__file__).resolve().parents[1]
HERE = ROOT / "experiments/algorithm_study_20261019"
RIDES = ('AK07', 'AK11', 'AK14', 'AK18', 'AK85', 'AK86')
SOURCE_SHA = '23eca800b048aecd4b3a2469e78f63f24f64637eb785c8401386e219a177f812'
SOURCE_ROOT = 'TouringPlans-DisneyAnimalKingdomWaitTimes-933161b'
PHASES = ['validation', 'reference_check', 'evaluation'] + ['sensitivity/' + name for name in
          ['uniform5', 'uniform15', 'illustrative', 'illustrative_fast', 'illustrative_slow']]
EPS = 1e-7


def digest(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def read_json(path):
    return json.loads(Path(path).read_text())


def read_csv(path):
    with Path(path).open(encoding='utf-8-sig', newline='') as stream:
        return list(csv.DictReader(stream))


def close(a, b, label='numeric agreement'):
    assert abs(float(a) - float(b)) <= EPS, (label, a, b)


def raw_source(archive):
    assert digest(archive) == SOURCE_SHA
    observations = defaultdict(dict)
    raw_dates = defaultdict(set)
    with tarfile.open(archive, 'r:gz') as source:
        for ride in RIDES:
            with io.TextIOWrapper(source.extractfile(f'{SOURCE_ROOT}/{ride}.csv'),
                                  encoding='utf-8-sig', newline='') as stream:
                for row in csv.DictReader(stream):
                    date = datetime.strptime(row['date'], '%m/%d/%Y').date().isoformat()
                    raw_dates[ride].add(date)
                    if not row['SPOSTMIN'].strip() or row['datetime'][:10] != date:
                        continue
                    hour, minute, second = map(int, row['datetime'][11:].split(':'))
                    at = 60 * hour + minute + second / 60
                    if 585 <= at <= 1440:
                        # Preserve the declared legacy last-source-row tie rule.
                        observations[date, ride][at] = int(row['SPOSTMIN'])
    times = {key: sorted(value) for key, value in observations.items()}
    common = sorted(set.intersection(*(raw_dates[r] for r in RIDES)))

    def asof(date, ride, at):
        ts = times.get((date, ride), [])
        index = bisect.bisect_right(ts, at + 1e-9) - 1
        if index < 0 or at - ts[index] > 15 + 1e-9:
            return None
        stamp = ts[index]
        return {'minute': stamp, 'value': observations[date, ride][stamp]}

    return common, asof


def typed(rows):
    output = []
    for original in rows:
        row = dict(original)
        row['success'] = row['success'] == 'True'
        for key in ('completed', 'replans', 'route_changes', 'next_changes'):
            row[key] = int(row[key])
        for key in ('deadline', 'decay', 'total_walk_min', 'total_service_min',
                    'total_posted_wait_min', 'planning_seconds'):
            row[key] = float(row[key])
        row['elapsed_min'] = float(row['elapsed_min']) if row['elapsed_min'] else None
        output.append(row)
    return output


def paired_summary(rows, first, second):
    keys = {(r['date'], r['policy']): r for r in rows}
    dates = sorted({r['date'] for r in rows})
    joint = [d for d in dates if keys[d, first]['success'] and keys[d, second]['success']]
    diff = [keys[d, first]['elapsed_min'] - keys[d, second]['elapsed_min'] for d in joint]
    return {'attempted_days': len(dates), 'both_success': len(joint),
            'first_only_success': sum(keys[d, first]['success'] and not keys[d, second]['success'] for d in dates),
            'second_only_success': sum(not keys[d, first]['success'] and keys[d, second]['success'] for d in dates),
            'neither_success': sum(not keys[d, first]['success'] and not keys[d, second]['success'] for d in dates),
            'mean_first_minus_second': statistics.mean(diff) if diff else None,
            'median_first_minus_second': statistics.median(diff) if diff else None,
            'second_faster_equal_slower': [sum(x > 1e-9 for x in diff), sum(abs(x) <= 1e-9 for x in diff), sum(x < -1e-9 for x in diff)]}


def independent_selection(rows, policies, preference):
    keys = {(r['date'], r['policy']): r for r in rows}
    dates = sorted({r['date'] for r in rows})
    joint = [d for d in dates if all(keys[d, p]['success'] for p in policies)]
    counts = {p: sum(keys[d, p]['success'] for d in dates) for p in policies}
    means = {p: statistics.mean(keys[d, p]['elapsed_min'] for d in joint) if joint else None for p in policies}
    qualified = [p for p in preference if p in policies and counts[p] >= counts['dynamic'] and joint]
    winner = min(qualified, key=lambda p: (means[p], preference.index(p))) if qualified else 'dynamic'
    if not joint or means[winner] >= means['dynamic'] - 1e-9:
        winner = 'dynamic'
    discordance = {p: {'baseline_only': sum(keys[d, 'dynamic']['success'] and not keys[d, p]['success'] for d in dates),
                      'candidate_only': sum(not keys[d, 'dynamic']['success'] and keys[d, p]['success'] for d in dates)} for p in policies}
    return {'selected': winner, 'shared_success_days': len(joint), 'success_counts': counts,
            'common_mean_minutes': means, 'completion_discordance': discordance}


def independent_primary_bootstrap(daily_values, block):
    """Independent frequency-weight formulation of full-date resampling.

    The analysis uses base seed 20261019 and the derived block stream +7.
    Ineligible dates retain sampling weight but contribute no defined paired
    time; they are not replaced with zero. Failed-day records are not pre-dropped.
    """
    n = len(daily_values)
    generator = random.Random(20261019 if block == 1 else 20261026)
    answers, undefined = [], 0
    for replicate in range(5000):
        weights = [0] * n
        if block == 1:
            for draw in range(n):
                weights[generator.randrange(n)] += 1
        else:
            filled = 0
            for draw in range(math.ceil(n / block)):
                begin = generator.randrange(n - block + 1)
                length = min(block, n - filled)
                for offset in range(length):
                    weights[begin + offset] += 1
                filled += length
        denominator = sum(weight for weight, value in zip(weights, daily_values) if value is not None)
        if denominator:
            numerator = sum(weight * value for weight, value in zip(weights, daily_values) if value is not None)
            answers.append(numerator / denominator)
        else:
            undefined += 1
    answers.sort()
    def percentile(fraction):
        if not answers:
            return None
        left, fraction_part = divmod((len(answers) - 1) * fraction, 1)
        ix = int(left)
        return answers[ix] * (1 - fraction_part) + answers[min(ix + 1, len(answers) - 1)] * fraction_part
    return {'percentile_95': [percentile(.025), percentile(.975)],
            'undefined_resamples': undefined, 'resamples': 5000}


def verify_reported_summary(folder, rows):
    summary = read_json(folder / 'summary.json')
    dates = sorted({row['date'] for row in rows})
    policies = {row['policy'] for row in rows}
    keys = {(row['date'], row['policy']): row for row in rows}
    assert summary['attempted_days'] == len(dates)
    assert summary['date_range'] == [dates[0], dates[-1]]
    assert set(summary['by_policy']) == policies
    for policy, reported in summary['by_policy'].items():
        group = [keys[date, policy] for date in dates]
        successes = sum(row['success'] for row in group)
        assert reported['success_days'] == successes
        close(reported['completion_rate'], successes / len(dates))
        assert reported['failures'] == dict(Counter(row['failure'] for row in group if not row['success']))
        close(reported['mean_planning_seconds_per_attempt'], statistics.mean(row['planning_seconds'] for row in group))
        close(reported['median_planning_seconds_per_attempt'], statistics.median(row['planning_seconds'] for row in group))
    for name, reported in summary['paired'].items():
        first, second = reported['first'], reported['second']
        assert name == first + '_minus_' + second
        recomputed = paired_summary(rows, first, second)
        for a, b in [('paired_success_days', 'both_success'), ('first_only_success', 'first_only_success'),
                     ('second_only_success', 'second_only_success'), ('neither_success', 'neither_success')]:
            assert reported[a] == recomputed[b], (name, a)
        for a, b in [('mean_saved_minutes', 'mean_first_minus_second'), ('median_saved_minutes', 'median_first_minus_second')]:
            if recomputed[b] is None:
                assert reported[a] is None
            else:
                close(reported[a], recomputed[b], name + ' ' + a)
        assert reported['positive_zero_negative'] == recomputed['second_faster_equal_slower']
        shared = [date for date in dates if keys[date, first]['success'] and keys[date, second]['success']]
        assert reported['shared_dates'] == shared
        daily = {date: keys[date, first]['elapsed_min'] - keys[date, second]['elapsed_min'] if date in shared else None for date in dates}
        assert set(reported['daily_saved_minutes']) == set(dates)
        for date, value in daily.items():
            if value is None:
                assert reported['daily_saved_minutes'][date] is None
            else:
                close(reported['daily_saved_minutes'][date], value)
        if shared:
            for policy, field in [(first, 'mean_first_minutes'), (second, 'mean_second_minutes')]:
                close(reported[field], statistics.mean(keys[date, policy]['elapsed_min'] for date in shared))
            close(reported['compute_overhead_adjusted_mean_saved_minutes'], statistics.mean(
                daily[date] + (keys[date, first]['planning_seconds'] - keys[date, second]['planning_seconds']) / 60 for date in shared))
    for group in summary['common_success'].values():
        shared = [date for date in dates if all(keys[date, policy]['success'] for policy in group['policies'])]
        assert group['days'] == len(shared)
        for policy, value in group['mean_minutes'].items():
            if not shared:
                assert value is None
            else:
                close(value, statistics.mean(keys[date, policy]['elapsed_min'] for date in shared))
    bootstrap_results = {}
    if 'dynamic_minus_rollout' in summary['paired']:
        primary = summary['paired']['dynamic_minus_rollout']
        daily_values = [primary['daily_saved_minutes'][date] for date in dates]
        for block, field in [(1, 'iid_date_bootstrap'), (7, 'block7_date_bootstrap')]:
            value = independent_primary_bootstrap(daily_values, block)
            reported = primary[field]
            assert value['undefined_resamples'] == reported['undefined_resamples']
            assert value['resamples'] == reported['resamples']
            for left, right in zip(value['percentile_95'], reported['percentile_95']):
                if left is None:
                    assert right is None
                else:
                    close(left, right, 'independent primary bootstrap')
            bootstrap_results[field] = value
    return {'status': 'PASS', 'all_reported_pair_comparisons': len(summary['paired']),
            'all_common_success_groups': len(summary['common_success']),
            'primary_bootstrap_independently_recomputed': bootstrap_results,
            'reported_summary_sha256': digest(folder / 'summary.json')}


def verify_phase(name, splits, asof, hours, current_hashes, selection):
    folder = HERE / name
    metadata = read_json(folder / 'metadata.json')
    # Original outputs recorded31 local artifacts at their creation. Public
    # verification checks20 included artifacts now, not those11 absent files.
    public_scope = metadata.get('public_distribution')
    if public_scope is None:
        assert metadata['old_artifacts_unchanged'] == 31, (name, 'historical preservation count')
    else:
        assert metadata['old_artifacts_unchanged'] == 20, (name, 'public preservation count')
        expected_scope = check_public_preservation(ROOT)
        for field in ['included_legacy_artifacts_verified', 'historical_artifacts_intentionally_not_distributed',
                      'included_paths', 'omitted_paths', 'historical_31_artifact_certificate_reissued']:
            assert public_scope[field] == expected_scope[field], (name, 'public scope', field)
    rows = typed(read_csv(folder / 'per_day.csv'))
    trace_list = read_json(folder / 'traces.json')
    traces = {(t['date'], t['policy']): t['events'] for t in trace_list}
    assert len(traces) == len(trace_list) == len(rows)
    is_validation = name == 'validation'
    expected_dates = splits['validation'] if is_validation else splits['evaluation']
    training = splits['fit'] if is_validation else splits['fit'] + splits['validation']
    assert metadata['evaluation_dates'] == expected_dates
    assert metadata['train_dates'] == training
    assert max(training) < min(expected_dates)
    assert metadata['source_sha256'] == SOURCE_SHA
    for field, file in [('protocol_sha256', 'PROTOCOL.md'), ('engine_sha256', 'engine.py'), ('runner_sha256', 'run.py')]:
        assert metadata[field] == current_hashes[file], (name, field)
    assert metadata['validation_hours_sha256'] == current_hashes['inputs/validation_park_hours.csv']
    if name not in ('validation', 'reference_check'):
        assert selection is not None
        assert metadata['selection_sha256'] == digest(HERE / 'selection.json')
    configured = dict(metadata['policy_decay'])
    expected_policy_names = (['fixed', 'dynamic'] if name == 'reference_check' else
        ['fixed', 'dynamic', 'calibrated_15', 'calibrated_30', 'calibrated_60', 'calibrated_120', 'rollout', 'scenario_open_loop']
        if is_validation else ['fixed', 'dynamic', 'calibrated', 'rollout', 'scenario_open_loop'])
    assert set(configured) == set(expected_policy_names)
    expected_keys = {(d, p) for d in expected_dates for p in configured}
    assert {(r['date'], r['policy']) for r in rows} == expected_keys
    assert len(rows) == len(expected_keys)
    assert set(traces) == expected_keys
    cfg = metadata['config']
    visits = decisions = scenario_decisions = 0
    declared_fallbacks = []
    for date in expected_dates:
        group = [r for r in rows if r['date'] == date]
        assert len({r['initial_order'] for r in group}) == 1
        assert len({r['initial_predicted_finish'] for r in group}) == 1
        assert all(r['configuration'] == metadata['configuration'] for r in group)
        if date not in hours:
            declared_fallbacks.append(date)
        for row in group:
            key = (date, row['policy'])
            expected_deadline = hours.get(date, {'deadline': 1200, 'source': 'declared20:00 analysis fallback'})
            close(row['deadline'], expected_deadline['deadline'], 'shared sourced deadline')
            assert row['deadline_source'] == expected_deadline['source']
            close(row['decay'], configured[row['policy']], 'policy decay')
            remaining = row['initial_order'].split('|')
            assert sorted(remaining) == sorted(RIDES)
            done = []
            now, location = float(cfg['start']), 'GATE'
            totals = Counter()
            failure = ''
            for event in traces[key]:
                assert not failure, (name, key, 'events after failure')
                if event['type'] == 'visit':
                    visits += 1
                    assert event['ride'] == remaining.pop(0)
                    ride = event['ride']
                    assert event['from'] == location
                    close(event['depart'], now, 'departure chronology')
                    travel = cfg['walk'][location][ride]
                    close(event['walk'], travel, 'configuration travel')
                    close(event['service'], cfg['service'][ride], 'configuration service')
                    arrival = now + travel
                    close(event['arrival'], arrival, 'arrival arithmetic')
                    obs = asof(date, ride, arrival)
                    if obs is None:
                        assert event['posted_observed_at'] is None and event['posted_wait'] is None
                    else:
                        close(event['posted_observed_at'], obs['minute'], 'raw as-of timestamp')
                        close(event['posted_wait'], obs['value'], 'raw posted value')
                        assert event['posted_observed_at'] <= arrival + 1e-9
                        assert arrival - event['posted_observed_at'] <= 15 + 1e-9
                    if arrival > row['deadline'] + 1e-9:
                        failure = 'arrival_after_window'
                    elif obs is None:
                        failure = 'no_fresh_posted_at_arrival'
                    elif obs['value'] == -999:
                        failure = 'closed_at_arrival'
                    elif arrival + obs['value'] + cfg['service'][ride] > row['deadline'] + 1e-9:
                        failure = 'completion_after_window'
                    assert event['status'] == (failure or 'completed')
                    totals['walk'] += travel
                    if failure:
                        assert 'finish' not in event
                    else:
                        now = arrival + obs['value'] + cfg['service'][ride]
                        close(event['finish'], now, 'finish arithmetic')
                        totals['posted_wait'] += obs['value']
                        totals['service'] += cfg['service'][ride]
                        done.append(ride)
                        location = ride
                else:
                    assert event['type'] == 'decision' and row['policy'] != 'fixed'
                    decisions += 1
                    totals['replans'] += 1
                    close(event['at'], now, 'decision chronology')
                    assert event['location'] == location
                    assert event['incumbent'] == remaining
                    assert sorted(event['selected']) == sorted(remaining)
                    assert len(set(event['selected'])) == len(remaining)
                    assert event['chosen_next'] == event['selected'][0]
                    assert set(event['snapshot']) == set(RIDES)
                    for ride, stored in event['snapshot'].items():
                        expected = asof(date, ride, now)
                        assert stored == expected, (name, key, 'decision snapshot', ride, stored, expected)
                        if stored is not None:
                            assert stored['minute'] <= now + 1e-9 and now - stored['minute'] <= 15 + 1e-9
                    ids = event['scenario_ids']
                    if row['policy'] in ('rollout', 'scenario_open_loop'):
                        scenario_decisions += 1
                        assert len(ids) == len(set(ids)) == metadata['scenario_count'] == 8
                        assert set(ids) <= set(training) and all(d < date for d in ids)
                        assert set(event['scenario_distances']) == set(ids)
                        assert set(event['scenario_query_audit']) == set(ids)
                        assert set(event['predicted_costs']) == set(remaining)
                        if not event['fallback']:
                            costs = {a: c for a, c in event['predicted_costs'].items() if c is not None}
                            assert costs and all(c >= 0 for c in costs.values())
                            close(costs[event['chosen_next']], min(costs.values()), 'minimum logged scenario action cost')
                            tied = [a for a, cost in costs.items() if abs(cost - min(costs.values())) <= 1e-9]
                            assert event['chosen_next'] == (event['base_next'] if event['base_next'] in tied else min(tied))
                    else:
                        assert not ids
                    totals['route_changes'] += event['selected'] != remaining
                    totals['next_changes'] += event['selected'][0] != remaining[0]
                    totals['planning_seconds'] += event['compute_seconds']
                    remaining = event['selected'].copy()
            if not traces[key]:
                assert row['failure'] == 'no_route_from_available_predictions'
                failure = row['failure']
            assert row['failure'] == failure
            assert row['completed_order'] == '|'.join(done)
            assert row['completed'] == len(done)
            assert len(done) == len(set(done))
            assert row['success'] == (len(done) == 6)
            for total, column in [('walk', 'total_walk_min'), ('service', 'total_service_min'),
                                  ('posted_wait', 'total_posted_wait_min'), ('replans', 'replans'),
                                  ('route_changes', 'route_changes'), ('next_changes', 'next_changes'),
                                  ('planning_seconds', 'planning_seconds')]:
                close(totals[total], row[column], column)
            if row['success']:
                assert sorted(done) == sorted(RIDES)
                close(row['elapsed_min'], now - cfg['start'], 'total elapsed')
                close(row['elapsed_min'], totals['walk'] + totals['service'] + totals['posted_wait'], 'elapsed decomposition')
                assert now <= row['deadline'] + 1e-9
            else:
                assert row['elapsed_min'] is None and failure
    assert metadata['deadline_fallback_dates'] == declared_fallbacks
    out = {'status': 'PASS', 'rows_verified': len(rows), 'dates_verified': len(expected_dates),
        'visits_raw_verified': visits, 'decisions_snapshot_verified': decisions,
        'scenario_decisions_training_ids_verified': scenario_decisions,
        'training_dates': len(training), 'deadline_fallback_dates': declared_fallbacks,
        'policies': {p: {'attempts': sum(r['policy'] == p for r in rows),
                        'completions': sum(r['policy'] == p and r['success'] for r in rows),
                        'failures': dict(Counter(r['failure'] for r in rows if r['policy'] == p and not r['success']))}
                     for p in configured},
        'input_hashes': {f: digest(folder / f) for f in ['metadata.json', 'per_day.csv', 'traces.json']},
        'paired': {}}
    for first, second in [('fixed', 'dynamic'), ('dynamic', 'rollout'), ('dynamic', 'calibrated'),
                          ('scenario_open_loop', 'rollout')]:
        if first in configured and second in configured:
            out['paired'][first + '_minus_' + second] = paired_summary(rows, first, second)
    if name == 'reference_check':
        legacy = {(r['date'], r['policy']): r for r in read_csv(ROOT / 'experiments/hours_replay_pilot/per_day.csv')
                  if r['scenario'] == 'historical_park_close_completion'}
        for row in rows:
            old = legacy[row['date'], 'replan' if row['policy'] == 'dynamic' else 'fixed']
            for field in ('initial_order', 'completed_order', 'failure'):
                assert row[field] == old[field]
            assert row['success'] == (old['success'] == 'True')
            for field in ('completed', 'route_changes', 'replans', 'total_walk_min', 'total_service_min', 'total_posted_wait_min'):
                close(row[field], old[field], 'reference parity ' + field)
            if row['success']:
                close(row['elapsed_min'], old['elapsed_min'], 'reference parity elapsed')
        out['legacy_rows_independently_matched'] = len(rows)
    return out, rows


def main(archive, require_complete=False):
    result = {'checked_at_utc': datetime.now(timezone.utc).isoformat(),
        'scope': 'Independent raw-source, chronology, arithmetic, denominators, split/hash and validation-selection audit. No engine, runner, preparation or analysis imports. No policy runs or tuning.',
        'status': 'PARTIAL', 'errors': [], 'pending': [], 'phases': {}}
    rows_by_phase = {}
    try:
        common, asof = raw_source(archive)
        manifest = read_json(HERE / 'inputs/splits.json')
        splits = manifest['splits']
        assert len(common) == 550
        assert splits == {'fit': common[:270], 'validation': common[270:385], 'evaluation': common[385:]}
        assert manifest['source_sha256'] == SOURCE_SHA
        result['split_reconstruction'] = {'fit': 270, 'validation': 115, 'evaluation': 165, 'status': 'PASS'}
        check_frozen_entrypoints(ROOT)
        result['public_distribution'] = check_public_preservation(ROOT)
        result['preserved_old_artifacts'] = result['public_distribution']['included_legacy_artifacts_verified']
        result['historical_metadata_note'] = ('Frozen original metadata may record31 artifacts verified at original run time. '
            'This public audit verifies only the20 distributed legacy artifacts;11 omitted historical files are not checked.')
        lock = read_json(HERE / 'protocol_lock.json')
        hashes = {name: digest(HERE / name) for name in lock['files']}
        exceptions = []
        for name, original_hash in lock['files'].items():
            if hashes[name] == original_hash:
                continue
            assert name == 'run.py', ('unexpected frozen-file change', name)
            old_runner = HERE / 'execution_notes/pre_print_fix/run.py'
            assert digest(old_runner) == original_hash
            original = old_runner.read_text()
            before, after = 'for p in policies}},flush=True))', 'for p in policies}}),flush=True)'
            assert original.count(before) == 1
            assert original.replace(before, after) == (HERE / name).read_text()
            assert (old_runner.parent / 'NOTE.md').exists()
            exceptions.append({'file': name, 'original_sha256': original_hash, 'current_sha256': hashes[name],
                'verified_only_change': 'Move flush=True from json.dumps to print; archived original retained; no policy or data logic changed.'})
        result['protocol_lock'] = {'status': 'PASS', 'current_hashes': hashes, 'documented_output_only_exceptions': exceptions}
        eval_lock_path = HERE / 'evaluation_lock.json'
        if eval_lock_path.exists():
            eval_lock = read_json(eval_lock_path)
            for name, expected in eval_lock['files'].items():
                assert digest(ROOT / name) == expected, ('evaluation lock mismatch', name)
            result['evaluation_lock'] = {'status': 'PASS', 'locked_file_hashes_verified': len(eval_lock['files']),
                'created_at_utc': eval_lock['created_at_utc'], 'sha256': digest(eval_lock_path)}
        else:
            result['pending'].append('evaluation_lock.json integrity check')
        hours = {}
        for path in [ROOT / 'data/verified_inputs/historical_park_hours.csv', HERE / 'inputs/validation_park_hours.csv']:
            for row in read_csv(path):
                hours[row['date']] = {'deadline': float(row['closing_minutes']), 'source': row['source_url']}
        source_status = read_json(HERE / 'inputs/validation_hours_status.json')
        assert source_status['csv_sha256'] == hashes['inputs/validation_park_hours.csv']
        assert datetime.fromisoformat(source_status['finished_at_utc']) < datetime.fromisoformat(lock['locked_at_utc'])
        result['hours_sources_frozen_before_protocol_lock'] = True
        selection_path = HERE / 'selection.json'
        selection = read_json(selection_path) if selection_path.exists() else None
        for name in PHASES:
            folder = HERE / name
            if not all((folder / f).exists() for f in ['metadata.json', 'per_day.csv', 'traces.json']):
                result['pending'].append(name + ': complete CSV/metadata/traces not yet available')
                continue
            try:
                out, rows = verify_phase(name, splits, asof, hours, hashes, selection)
                result['phases'][name] = out
                rows_by_phase[name] = rows
            except Exception as error:
                result['errors'].append({'phase': name, 'error': repr(error)})
        if selection is None or 'validation' not in rows_by_phase:
            result['pending'].append('validation-only selection verification')
        else:
            for field, file in [('protocol_sha256', 'PROTOCOL.md'), ('engine_sha256', 'engine.py'), ('runner_sha256', 'run.py')]:
                assert selection[field] == hashes[file], ('selection hash', field)
            assert selection['validation_csv_sha256'] == digest(HERE / 'validation/per_day.csv')
            validation_rows = rows_by_phase['validation']
            decay = independent_selection(validation_rows,
                ['dynamic', 'calibrated_15', 'calibrated_30', 'calibrated_60', 'calibrated_120'],
                ['dynamic', 'calibrated_60', 'calibrated_15', 'calibrated_30', 'calibrated_120'])
            assert decay == selection['decay_selection']
            selected_decay = 60 if decay['selected'] == 'dynamic' else int(decay['selected'].split('_')[1])
            assert selected_decay == selection['selected_decay']
            recommendation = independent_selection(validation_rows, ['dynamic', f'calibrated_{selected_decay}', 'rollout'],
                                                   ['dynamic', f'calibrated_{selected_decay}', 'rollout'])
            assert recommendation == selection['within_replay_recommendation']
            result['validation_selection'] = {'status': 'PASS', 'selected_decay': selected_decay,
                'recommendation': recommendation['selected'], 'validation_dates_used': len(splits['validation']),
                'evaluation_outcomes_used_by_verifier_selection': 0, 'selection_sha256': digest(selection_path)}
        for name, out in result['phases'].items():
            if name == 'reference_check':
                continue
            path = HERE / name / 'summary.json'
            if not path.exists():
                result['pending'].append(name + ': parent summary.json comparison')
            else:
                try:
                    out['reported_summary_verification'] = verify_reported_summary(HERE / name, rows_by_phase[name])
                except Exception as error:
                    result['errors'].append({'phase': name + '/summary', 'error': repr(error)})
    except Exception as error:
        result['errors'].append({'phase': 'global', 'error': repr(error)})
    result['status'] = 'FAIL' if result['errors'] else 'PARTIAL' if result['pending'] else 'PASS'
    result['verified_totals'] = {field: sum(phase[field] for phase in result['phases'].values()) for field in
        ['rows_verified', 'visits_raw_verified', 'decisions_snapshot_verified', 'scenario_decisions_training_ids_verified']}
    evaluation = result['phases'].get('evaluation')
    if evaluation and 'reported_summary_verification' in evaluation:
        primary = evaluation['paired']['dynamic_minus_rollout']
        intervals = evaluation['reported_summary_verification']['primary_bootstrap_independently_recomputed']
        result['primary_result_interpretation'] = {
            'comparison': 'D0 elapsed minus rollout elapsed; positive would favor rollout',
            'both_success_dates': primary['both_success'],
            'mean_minutes_saved_by_rollout': primary['mean_first_minus_second'],
            'block7_95_interval': intervals['block7_date_bootstrap']['percentile_95'],
            'dynamic_completions': evaluation['policies']['dynamic']['completions'],
            'rollout_completions': evaluation['policies']['rollout']['completions'],
            'supported_time_improvement': bool(intervals['block7_date_bootstrap']['percentile_95'][0] > 0),
            'meaning_of_QA_PASS': 'Integrity and arithmetic pass; not a claim the proposed algorithm is better.'}
    result['limits'] = [
        'Recorded real visit streams and decision snapshots are fully checked; this verifier does not rerun scenario rollouts or independently prove all simulated continuation decisions nonanticipative.',
        'Scenario IDs are checked against chronological training pools; engine interface tests and code review separately cover simulated-policy information boundaries.',
        'Planning overhead is measured replanning wall-clock time under parallel execution, excludes the shared initial-order search, and is not pure CPU time or measured phone/network latency.',
        'Primary bootstrap intervals are independently reproduced: IID seed20261019; block7 derived seed20261026;5000full-date resamples. Secondary-pair bootstrap intervals are not independently recalculated.',
        'The retrospective evaluation dates were previously examined; integrity checks do not make them an untouched confirmatory test.',
        'Park-hour sources, synthetic geometry and posted-wait proxy limitations remain; no true visitor benefit or commercial superiority is validated.'
    ]
    (HERE / 'verification-public.json').write_text(json.dumps(result, indent=2, allow_nan=False) + '\n')
    lines = ['# Public-distribution independent result QA', '', '**Status: ' + result['status'] + '**', '', result['scope'], '',
             '## Completed phase checks', '', '| Phase | Policy-days | Raw visits | Decision snapshots | Scenario-ID checks |',
             '|---|---:|---:|---:|---:|']
    for name, out in result['phases'].items():
        lines.append(f"| {name} | {out['rows_verified']} | {out['visits_raw_verified']} | {out['decisions_snapshot_verified']} | {out['scenario_decisions_training_ids_verified']} |")
    totals = result['verified_totals']
    lines.append(f"| **Total** | **{totals['rows_verified']}** | **{totals['visits_raw_verified']}** | **{totals['decisions_snapshot_verified']}** | **{totals['scenario_decisions_training_ids_verified']}** |")
    if 'primary_result_interpretation' in result:
        finding = result['primary_result_interpretation']
        lines += ['', '## Algorithm finding: QA pass is not a performance win', '',
            f"On {finding['both_success_dates']} jointly successful evaluation dates, D0 minus rollout is **{finding['mean_minutes_saved_by_rollout']:.3f} minutes**: rollout is slower on average in this conditional subset.",
            f"The independently reproduced 7-day block-bootstrap 95% interval is **[{finding['block7_95_interval'][0]:.3f}, {finding['block7_95_interval'][1]:.3f}] minutes**. It does not support a positive rollout time advantage.",
            f"Completion counts are D0 **{finding['dynamic_completions']}/165**, rollout **{finding['rollout_completions']}/165**. Different failed dates and success-selection prevent treating the conditional time mean as an all-attempt causal effect.",
            '', 'The result is a reproducible negative primary-hypothesis finding, not an algorithm-superiority certificate.']
    lines += ['', '## Integrity and accounting checks', '',
        '- Independently parsed pinned raw CSV data; every executed arrival and real decision snapshot agrees with the declared latest-as-of/15-minute freshness rule.',
        '- Reconstructed route chronology, same-six completion, failures/deadlines, elapsed decomposition, and walking including the failed arrival leg.',
        '- Checked one common initial order per date/configuration, full attempted-day denominators, training-only scenario IDs, and scenario action choice against logged costs.',
        '- Recomputed all reported policy completion/failure counts, paired means/medians/signs/discordances, common-success groups and planning-overhead adjustments without importing the experiment summarizer.',
        '- Recomputed primary IID and block7 bootstrap intervals for all seven analyzed phase/configuration folders with independent frequency-weight resampling.',
        '- Reproduced validation-only decay selection and recommendation; confirmed330 legacy reference outcomes,20 included legacy-artifact hashes and10 pre-evaluation locked-file hashes.',
        '- Eleven historical meeting/archive artifacts are intentionally omitted, not verified. Original metadata values of31 are historical records, not a claim by this public audit.',
        '- Verified the documented original-runner exception is exactly a one-line relocation of `flush=True` from `json.dumps` to `print`; no policy/data logic changed.']
    if result['pending']:
        lines += ['', '## Unverified / pending', ''] + ['- ' + x for x in result['pending']]
    if result['errors']:
        lines += ['', '## Errors', ''] + ['- `' + json.dumps(x) + '`' for x in result['errors']]
    lines += ['', '## Limits', ''] + ['- ' + x for x in result['limits']]
    lines += ['', 'Reproduce: `python3 scripts/verify_public_results.py --require-complete`.',
              '', 'The public verifier writes only `QA-public.md` and `verification-public.json`; original QA is unchanged. Unexpected missing outputs are never treated as passed.', '']
    (HERE / 'QA-public.md').write_text('\n'.join(lines))
    print(json.dumps({'status': result['status'], 'verified_phases': list(result['phases']),
                      'errors': result['errors'], 'pending': result['pending']}, indent=2))
    return 1 if result['errors'] or (require_complete and result['pending']) else 0


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--archive', type=Path, default=Path('/tmp/parkplan-ak-933161b.tar.gz'))
    parser.add_argument('--require-complete', action='store_true')
    args = parser.parse_args()
    raise SystemExit(main(args.archive, args.require_complete))
