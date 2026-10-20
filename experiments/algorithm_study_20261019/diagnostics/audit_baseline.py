#!/usr/bin/env python3
"""Baseline-only forensic audit; no policy fitting, tuning, or candidate evaluation.

Reads preserved historical-hours outcomes and tie-preserving decision traces.
Independent raw parser/forecast arithmetic, not an import of replay.py. Source
TouringPlans.com archive is read in place; only derived aggregates are exported.
"""
from __future__ import annotations

import argparse
import bisect
from collections import Counter, defaultdict
import csv
from datetime import datetime
import hashlib
import io
import itertools
import json
import math
from pathlib import Path
import statistics
import tarfile

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
RIDES = ('AK07', 'AK11', 'AK14', 'AK18', 'AK85', 'AK86')
SOURCE_ROOT = 'TouringPlans-DisneyAnimalKingdomWaitTimes-933161b'
SOURCE_SHA = '23eca800b048aecd4b3a2469e78f63f24f64637eb785c8401386e219a177f812'
SCENARIO = 'historical_park_close_completion'


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def describe(values):
    if not values:
        return {'n': 0}
    return {'n': len(values), 'mean': statistics.mean(values),
            'median': statistics.median(values), 'min': min(values), 'max': max(values)}


def read_csv(path):
    with path.open(newline='') as stream:
        return list(csv.DictReader(stream))


def write_csv(name, rows):
    if not rows:
        return
    with (HERE / name).open('w', newline='') as stream:
        writer = csv.DictWriter(stream, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)


def load_source(archive, eval_dates):
    assert digest(archive) == SOURCE_SHA
    states = defaultdict(dict)
    raw_values = defaultdict(lambda: defaultdict(list))
    raw_dates = defaultdict(set)
    counts = Counter()
    with tarfile.open(archive, 'r:gz') as source:
        for ride in RIDES:
            member = source.extractfile(f'{SOURCE_ROOT}/{ride}.csv')
            with io.TextIOWrapper(member, encoding='utf-8-sig', newline='') as stream:
                for row in csv.DictReader(stream):
                    date = datetime.strptime(row['date'], '%m/%d/%Y').date().isoformat()
                    raw_dates[ride].add(date)
                    if date not in eval_dates:
                        continue
                    counts['evaluation_source_rows'] += 1
                    if not row['SPOSTMIN'].strip():
                        counts['evaluation_nonposted_rows'] += 1
                        continue
                    if row['datetime'][:10] != date:
                        counts['evaluation_posted_date_mismatch_rows'] += 1
                        continue
                    hour, minute, second = map(int, row['datetime'][11:].split(':'))
                    at = 60 * hour + minute + second / 60
                    if not 585 <= at <= 1440:
                        counts['evaluation_posted_outside_read_window_rows'] += 1
                        continue
                    value = int(row['SPOSTMIN'])
                    counts['evaluation_posted_rows_in_read_window'] += 1
                    counts['evaluation_closure_rows_in_read_window'] += value == -999
                    states[date, ride][at] = value  # exact legacy final-file-row tie rule
                    raw_values[date, ride][at].append(value)
    times = {key: sorted(value) for key, value in states.items()}
    common = sorted(set.intersection(*(raw_dates[r] for r in RIDES)))
    assert len(common) == 550 and common[-165:] == sorted(eval_dates)
    for groups in raw_values.values():
        for values in groups.values():
            counts['unique_posted_timestamps'] += 1
            counts['duplicate_timestamp_groups'] += len(values) > 1
            counts['conflicting_timestamp_groups'] += len(set(values)) > 1
            counts['closure_open_conflicting_timestamp_groups'] += -999 in values and any(v >= 0 for v in values)
            counts['first_vs_last_source_value_disagreements'] += values[0] != values[-1]

    def asof(date, ride, at):
        ts = times.get((date, ride), [])
        ix = bisect.bisect_right(ts, at + 1e-9) - 1
        if ix < 0:
            return None
        observed = ts[ix]
        if at - observed > 15 + 1e-9:
            return None
        return observed, states[date, ride][observed]

    return asof, raw_values, dict(counts)


def main(archive):
    old_path = ROOT / 'experiments/hours_replay_pilot/per_day.csv'
    new_path = ROOT / 'experiments/tie_preserving_pilot/per_day_new_policy.csv'
    trace_path = ROOT / 'experiments/tie_preserving_pilot/all_decision_traces.json'
    curve_path = ROOT / 'experiments/hours_replay_pilot/train_curves.json'
    traces = json.loads(trace_path.read_text())
    old = {(r['date'], r['policy']): r for r in read_csv(old_path) if r['scenario'] == SCENARIO}
    dynamic = {r['date']: r for r in read_csv(new_path)}
    curves = json.loads(curve_path.read_text())
    assert len(dynamic) == len(traces) == 165 and len(old) == 495
    for date, row in dynamic.items():
        assert all(row[k] == old[date, 'replan'][k] for k in row if k != 'policy')
    asof, raw_values, source_counts = load_source(archive, set(dynamic))

    def historical(ride, at):
        slot = max(0, min(len(curves[ride]) - 1, int((at - 600) // 15)))
        return curves[ride][slot]

    def forecast(date, ride, arrival, now):
        current = asof(date, ride, now)
        if current and current[1] == -999:
            return math.inf if arrival - current[0] <= 15 + 1e-9 else historical(ride, arrival)
        prior = historical(ride, arrival)
        if current is None:
            return prior
        return max(0, prior + (current[1] - historical(ride, current[0])) * math.exp(-(arrival - now) / 60))

    def route_score(date, order, now):
        finish = now
        route = []
        for ride in order:
            arrival = finish + 10
            prediction = forecast(date, ride, arrival, now)
            route.append((ride, arrival, prediction))
            finish = arrival + prediction + 10
            if not math.isfinite(finish):
                return finish, route
        return finish, route

    result = {
        'scope': 'Baseline-only descriptive audit of already-examined 165 evaluation dates; no candidate tuning or evidence of new-policy superiority.',
        'inputs_sha256': {str(p.relative_to(ROOT)): digest(p) for p in (old_path, new_path, trace_path, curve_path)},
        'source_sha256': SOURCE_SHA,
        'raw_source': source_counts,
    }
    outcome_rows = []
    for date in sorted(dynamic):
        a, b = old[date, 'fixed'], dynamic[date]
        paired = a['success'] == b['success'] == 'True'
        outcome_rows.append({
            'date': date, 'fixed_success': a['success'], 'dynamic_success': b['success'],
            'fixed_failure': a['failure'], 'dynamic_failure': b['failure'],
            'fixed_elapsed': a['elapsed_min'], 'dynamic_elapsed': b['elapsed_min'],
            'paired_fixed_minus_dynamic': float(a['elapsed_min']) - float(b['elapsed_min']) if paired else '',
            'paired_walk_difference': float(a['total_walk_min']) - float(b['total_walk_min']) if paired else '',
            'paired_service_difference': float(a['total_service_min']) - float(b['total_service_min']) if paired else '',
            'paired_wait_difference': float(a['total_posted_wait_min']) - float(b['total_posted_wait_min']) if paired else '',
        })
    pairs = [r for r in outcome_rows if r['paired_fixed_minus_dynamic'] != '']
    differences = [r['paired_fixed_minus_dynamic'] for r in pairs]
    assert len(pairs) == 105
    assert all(r['paired_walk_difference'] == r['paired_service_difference'] == 0 for r in pairs)
    assert all(r['paired_wait_difference'] == r['paired_fixed_minus_dynamic'] for r in pairs)
    result['paired_time_decomposition'] = {
        'both_complete': len(pairs), 'fixed_only': sum(r['fixed_success'] == 'True' and r['dynamic_success'] != 'True' for r in outcome_rows),
        'dynamic_only': sum(r['dynamic_success'] == 'True' and r['fixed_success'] != 'True' for r in outcome_rows),
        'neither': sum(r['dynamic_success'] != 'True' and r['fixed_success'] != 'True' for r in outcome_rows),
        'fixed_mean_elapsed': statistics.mean(float(r['fixed_elapsed']) for r in pairs),
        'dynamic_mean_elapsed': statistics.mean(float(r['dynamic_elapsed']) for r in pairs),
        'fixed_minus_dynamic_minutes': describe(differences),
        'dynamic_faster_equal_slower_days': [sum(x > 0 for x in differences), sum(x == 0 for x in differences), sum(x < 0 for x in differences)],
        'all_time_difference_is_posted_wait_proxy': True,
        'all_success_walk_minutes': 60, 'all_success_service_minutes': 60,
    }
    result['failure_counts'] = {p: dict(Counter(r['failure'] for (date, policy), r in old.items() if policy == p and r['success'] != 'True')) for p in ('fixed', 'replan', 'threshold10')}
    dc, by_remaining = Counter(), defaultdict(Counter)
    visits, decisions, horizon_rows, closure_rows = [], [], [], []
    input_counts = Counter()
    exact_checked = 0
    for trace in traces:
        date = trace['date']
        completed_count = 0
        deadline = float(dynamic[date]['deadline_minutes'])
        init_order = dynamic[date]['initial_order'].split('|')
        score, _ = route_score(date, init_order, 600)
        assert abs(score - float(dynamic[date]['initial_predicted_finish'])) <= .00051
        moments = [{'at': 600, 'order': init_order, 'remaining': 6, 'kind': 'initial'}]
        for event in trace['events']:
            if event['type'] == 'visit':
                ride, now, arrival = event['ride'], event['depart'], event['arrival']
                realized = asof(date, ride, arrival)
                assert (None if realized is None else realized[1]) == event['posted_wait']
                current = asof(date, ride, now)
                prediction = forecast(date, ride, arrival, now)
                err = prediction - realized[1] if realized and realized[1] >= 0 and math.isfinite(prediction) else None
                visits.append({'date': date, 'ride': ride, 'depart': now, 'arrival': arrival,
                    'remaining_at_departure': 6 - completed_count,
                    'status': event['status'], 'predicted_next_wait': prediction if math.isfinite(prediction) else '',
                    'realized_posted_wait': event['posted_wait'], 'predicted_minus_realized': err if err is not None else '',
                    'departure_latest_state': 'missing_or_stale' if current is None else 'closed' if current[1] == -999 else 'open',
                    'departure_state_age': now - current[0] if current else '',
                    'arrival_timestamp_conflict': realized is not None and len(set(raw_values[date, ride][realized[0]])) > 1})
                input_counts['visits'] += 1
                input_counts['visit_arrival_conflicting_timestamp'] += visits[-1]['arrival_timestamp_conflict']
                if event['status'] == 'closed_at_arrival':
                    closure_rows.append(visits[-1].copy())
                if event['status'] == 'completed':
                    completed_count += 1
                continue
            n = len(event['incumbent'])
            dc['post_ride_calls'] += 1
            dc['real_choice_calls' if n >= 2 else 'forced_last_ride_calls'] += 1
            by_remaining[n]['calls'] += 1
            switch_kind = 'not_switched'
            if event['switched']:
                switch_kind = 'next_ride_changed' if event['incumbent'][0] != event['proposed'][0] else 'suffix_only_changed'
                dc[switch_kind] += 1
                by_remaining[n][switch_kind] += 1
            order = event['proposed'] if event['switched'] else event['incumbent']
            now = event['at']
            inc_score, _ = route_score(date, event['incumbent'], now)
            predicted_score, _ = route_score(date, order, now)
            if event['incumbent_pred_finish'] is not None:
                assert abs(inc_score - event['incumbent_pred_finish']) <= .00051
            best_score = min(route_score(date, perm, now)[0] for perm in itertools.permutations(sorted(order)))
            if math.isfinite(best_score):
                assert event['proposed_pred_finish'] is not None
                assert abs(best_score - event['proposed_pred_finish']) <= .00051
            else:
                assert event['proposed_pred_finish'] is None
            exact_checked += 1
            decisions.append({'date': date, 'at': now, 'remaining': n, 'switch_kind': switch_kind,
                'incumbent_next': event['incumbent'][0], 'selected_next': order[0],
                'predicted_gain_minutes': event['predicted_gain_min'],
                'incumbent_order': '|'.join(event['incumbent']), 'selected_order': '|'.join(order)})
            moments.append({'at': now, 'order': order, 'remaining': n, 'kind': 'post_ride'})
        for moment in moments:
            now = moment['at']
            for ride in moment['order']:
                current = asof(date, ride, now)
                input_counts['remaining_ride_state_reads'] += 1
                input_counts['missing_or_stale_remaining_ride_reads'] += current is None
                input_counts['closed_remaining_ride_reads'] += current is not None and current[1] == -999
                input_counts['conflicting_remaining_ride_state_reads'] += current is not None and len(set(raw_values[date, ride][current[0]])) > 1
            _, plan = route_score(date, moment['order'], now)
            for position, (ride, arrival, prediction) in enumerate(plan, 1):
                if not math.isfinite(arrival):
                    continue
                target = asof(date, ride, arrival)
                valid = target is not None and target[1] >= 0 and math.isfinite(prediction) and arrival <= deadline
                horizon = arrival - now
                band = '0-15' if horizon <= 15 else '15-60' if horizon <= 60 else '60-120' if horizon <= 120 else '120+'
                horizon_rows.append({'date': date, 'decision_at': now, 'kind': moment['kind'], 'position': position,
                    'ride': ride, 'forecast_arrival': arrival, 'horizon': horizon, 'horizon_band': band,
                    'predicted_wait': prediction if math.isfinite(prediction) else '',
                    'observed_target_wait': target[1] if target else '', 'eligible_open_fresh_in_hours': valid,
                    'forecast_minus_target': prediction - target[1] if valid else '',
                    'target_time_conflict': target is not None and len(set(raw_values[date, ride][target[0]])) > 1})
    result['decision_audit'] = dict(dc)
    result['decision_audit']['by_remaining_rides'] = {str(k): dict(v) for k, v in sorted(by_remaining.items(), reverse=True)}
    result['decision_audit']['independently_exact_optimal_scores_verified'] = exact_checked
    result['decision_audit']['full_completed_trip_postride_calls'] = 5
    result['decision_audit']['full_completed_trip_real_postride_choice_points'] = 4
    result['decision_audit']['initial_permutations'] = math.factorial(6)
    result['decision_audit']['complete_trip_postride_permutations'] = sum(math.factorial(n) for n in range(1, 6))
    result['decision_audit']['limitation'] = 'Exact enumeration minimizes a frozen point-forecast open-loop suffix, not a stochastic policy that conditions later decisions on newly observed states. Exact search does not establish optimality under real waits, spatial walking, closures, or uncertain forecasts.'
    result['information_use_counts'] = dict(input_counts)
    errors = [v['predicted_minus_realized'] for v in visits if v['predicted_minus_realized'] != '']
    result['immediate_next_ride_forecast'] = {'signed_error_forecast_minus_posted': describe(errors),
        'absolute_error': describe([abs(v) for v in errors]),
        'horizon_minutes': 10, 'scope': 'On-policy next-ride visits; available finite forecasts and fresh open posted targets; not actual visitor wait error.'}
    result['selected_plan_horizon_error'] = {}
    for band in ('0-15', '15-60', '60-120', '120+'):
        selected = [r for r in horizon_rows if r['horizon_band'] == band]
        errors = [r['forecast_minus_target'] for r in selected if r['eligible_open_fresh_in_hours']]
        result['selected_plan_horizon_error'][band] = {'planned_targets': len(selected), 'eligible_targets': len(errors),
            'signed_error': describe(errors), 'absolute_error': describe([abs(x) for x in errors])}
    result['selected_plan_horizon_error_note'] = 'Retrospective target is posted wait at the suffix forecast arrival, not actual realized arrival; endogenous selected-route targets overlap and are correlated. Diagnostic only, not a held-out forecast benchmark or candidate score.'
    result['closure_failures'] = {
        'count': len(closure_rows),
        'departure_information': dict(Counter(r['departure_latest_state'] for r in closure_rows)),
        'finite_immediate_forecast_despite_known_current_closure': sum(r['departure_latest_state'] == 'closed' and r['predicted_next_wait'] != '' for r in closure_rows),
        'infinite_immediate_forecast_but_no_finite_alternative_or_forced': sum(r['predicted_next_wait'] == '' for r in closure_rows),
        'arrival_timestamp_conflicts': sum(r['arrival_timestamp_conflict'] for r in closure_rows),
        'by_remaining_ride_count': dict(sorted(Counter(r['remaining_at_departure'] for r in closure_rows).items())),
        'by_ride': dict(sorted(Counter(r['ride'] for r in closure_rows).items())),
    }
    worst = min(pairs, key=lambda r: (r['paired_fixed_minus_dynamic'], r['date']))
    first_loss = next(r for r in pairs if r['paired_fixed_minus_dynamic'] < 0)
    known = next((r for r in closure_rows if r['departure_latest_state'] == 'closed'), None)
    result['diagnostic_examples'] = {
        'selection_warning': 'Selected after observing baseline outcomes solely to explain failures; not representative evidence or new-policy benefit.',
        'largest_paired_dynamic_loss_tie_broken_earliest': worst,
        'earliest_paired_dynamic_loss': first_loss,
        'earliest_known_closure_failure': known,
    }
    example_rows = []
    for example_name, date in [('largest_paired_loss', worst['date']), ('earliest_paired_loss', first_loss['date'])]:
        fixed_row = old[date, 'fixed']
        now = 600
        fixed = {}
        for ride in fixed_row['initial_order'].split('|'):
            arrival = now + 10
            post = asof(date, ride, arrival)
            assert post is not None and post[1] >= 0
            fixed[ride] = {'arrival': arrival, 'wait': post[1]}
            now = arrival + post[1] + 10
        assert now - 600 == float(fixed_row['elapsed_min'])
        dynamic_visits = {r['ride']: r for r in visits if r['date'] == date}
        for ride in RIDES:
            rv = dynamic_visits[ride]
            example_rows.append({'example': example_name, 'date': date, 'ride': ride,
                'fixed_arrival': fixed[ride]['arrival'], 'dynamic_arrival': rv['arrival'],
                'fixed_posted_wait': fixed[ride]['wait'], 'dynamic_posted_wait': rv['realized_posted_wait'],
                'dynamic_minus_fixed_wait': rv['realized_posted_wait'] - fixed[ride]['wait'],
                'dynamic_immediate_forecast_wait': rv['predicted_next_wait'],
                'dynamic_immediate_forecast_error': rv['predicted_minus_realized']})
        result['diagnostic_examples'][example_name + '_orders'] = {'date': date,
            'fixed': fixed_row['completed_order'], 'dynamic': dynamic[date]['completed_order']}
    assert sum(dc[k] for k in ('next_ride_changed', 'suffix_only_changed')) == sum(int(r['route_changes']) for r in dynamic.values())
    assert len(closure_rows) == result['failure_counts']['replan']['closed_at_arrival']
    result['checks'] = {'baseline_rows_unchanged': True, 'source_sha256_verified': True,
        'all_dynamic_daily_fields_match_old_replan_except_label': True,
        'decision_exact_optima_reconstructed': exact_checked,
        'candidate_policies_run': 0, 'training_or_tuning_performed': False}
    for name, rows in [('paired_decomposition.csv', outcome_rows), ('decision_audit.csv', decisions),
                       ('visit_forecast_diagnostics.csv', visits), ('selected_plan_horizon_diagnostics.csv', horizon_rows),
                       ('closure_failures.csv', closure_rows), ('selected_loss_examples.csv', example_rows)]:
        write_csv(name, rows)
    (HERE / 'baseline_diagnostics.json').write_text(json.dumps(result, indent=2, allow_nan=False) + '\n')
    print(json.dumps(result, indent=2, allow_nan=False))


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--archive', type=Path, default=Path('/tmp/parkplan-ak-933161b.tar.gz'))
    main(parser.parse_args().archive)
