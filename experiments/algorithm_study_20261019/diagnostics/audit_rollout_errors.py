#!/usr/bin/env python3
"""TouringPlans.com credited offline explanation of frozen rollout decisions.

No tuning, new policy, or planner feedback: on recorded evaluation-rollout states,
force its action or D0's action and then execute the same D0 continuation against
the original historical as-of stream. Both counterfactual completions are needed
for a time difference. A counting-only reconstruction of the frozen rollout logs
template-query denominators and asserts unchanged decisions, scores and numerators.
"""
from __future__ import annotations

from collections import Counter
import csv
from datetime import date
import hashlib
import json
import math
from pathlib import Path
import statistics
import sys

sys.dont_write_bytecode = True
HERE = Path(__file__).resolve().parent
STUDY = HERE.parent
sys.path.insert(0, str(STUDY))
import engine as e
from prepare import load_data, get_hours, digest


class CountingScenario(e.Scenario):
    def _template(self, ride, minute):
        self.audit['total_template_queries'] += 1
        return super()._template(ride, minute)


class CountingBank(e.ScenarioBank):
    def select(self, now, snapshot):
        chosen = super().select(now, snapshot)
        return [CountingScenario(s.date, s.streams, self.curves, now,
                                 snapshot, s.distance) for s in chosen]


def describe(values):
    values = [float(x) for x in values if x is not None]
    if not values:
        return {'n': 0, 'mean': None, 'median': None, 'min': None, 'max': None}
    return {'n': len(values), 'mean': statistics.mean(values),
            'median': statistics.median(values), 'min': min(values), 'max': max(values)}


def corr(xs, ys):
    if len(xs) < 2 or len(set(xs)) == 1 or len(set(ys)) == 1:
        return None
    return statistics.correlation(xs, ys)


def value(snapshot, ride):
    obs = snapshot[ride]
    return None if obs is None else {'minute': obs.minute, 'value': obs.value}


def snapshot(day, now):
    return {r: day[r].asof(now) for r in e.RIDES}


def factual_continuation(order, location, now, day, deadline, cfg, predictor):
    """Offline executor sees arrival outcomes; future D0 sees as-of current only."""
    start = now
    remaining = tuple(order)
    completed = []
    visits = []
    decisions = []
    while remaining:
        ride, remaining = remaining[0], remaining[1:]
        travel = cfg.walk[location][ride]
        arrival = now + travel
        obs = day[ride].asof(arrival)
        failure = ''
        if arrival > deadline + e.EPS:
            failure = 'arrival_after_window'
        elif obs is None:
            failure = 'no_fresh_posted_at_arrival'
        elif obs.value == -999:
            failure = 'closed_at_arrival'
        elif arrival + obs.value + cfg.service[ride] > deadline + e.EPS:
            failure = 'completion_after_window'
        visit = {'ride': ride, 'from': location, 'depart': now, 'arrival': arrival,
                 'walk': travel, 'service': cfg.service[ride],
                 'posted_observed_at': obs.minute if obs else None,
                 'posted_wait': obs.value if obs else None,
                 'status': failure or 'completed'}
        visits.append(visit)
        if failure:
            return {'success': False, 'failure': failure,
                    'completed_suffix': completed, 'elapsed_minutes': None,
                    'visits': visits, 'decisions': decisions}
        now = arrival + obs.value + cfg.service[ride]
        visit['finish'] = now
        completed.append(ride)
        location = ride
        if remaining:
            current = snapshot(day, now)
            incumbent = remaining
            remaining, finish = e.base_order(remaining, location, now, current,
                                             cfg, predictor)
            decisions.append({'at': now, 'location': location,
                'incumbent': list(incumbent), 'selected': list(remaining),
                'predicted_finish': finish if math.isfinite(finish) else None,
                'snapshot': {r: value(current, r) for r in e.RIDES}})
    assert len(completed) == len(order) == len(set(completed))
    assert abs(now - start - sum(v['walk'] + v['posted_wait'] + v['service']
                                for v in visits)) < 1e-7
    return {'success': True, 'failure': '', 'completed_suffix': completed,
            'elapsed_minutes': now - start, 'visits': visits, 'decisions': decisions}


def classify(chosen, base):
    if chosen['success'] and base['success']:
        return 'both_success'
    if chosen['success']:
        return 'chosen_only_success'
    if base['success']:
        return 'base_only_success'
    return 'both_failed'


def summarize(rows):
    both = [r for r in rows if r['completion_status'] == 'both_success']
    scored = [r for r in both if r['predicted_gain_minutes'] is not None]
    xs = [r['predicted_gain_minutes'] for r in scored]
    ys = [r['actual_gain_minutes'] for r in scored]
    total = sum(r['template_queries'] for r in rows)
    imputed = sum(r['imputation_queries'] for r in rows)
    return {
        'decision_states': len(rows),
        'distinct_dates': len({r['date'] for r in rows}),
        'completion_status': dict(Counter(r['completion_status'] for r in rows)),
        'chosen_failure_reasons': dict(Counter(r['chosen_failure'] for r in rows if not r['chosen_success'])),
        'base_failure_reasons': dict(Counter(r['base_failure'] for r in rows if not r['base_success'])),
        'both_success_actual_gain_minutes': describe(r['actual_gain_minutes'] for r in both),
        'both_success_sign_counts': {
            'helpful': sum(r['actual_gain_minutes'] > e.EPS for r in both),
            'tied': sum(abs(r['actual_gain_minutes']) <= e.EPS for r in both),
            'harmful': sum(r['actual_gain_minutes'] < -e.EPS for r in both)},
        'finite_prediction_and_both_success_states': len(scored),
        'predicted_gain_minutes_on_scored_states': describe(xs),
        'actual_gain_minutes_on_scored_states': describe(ys),
        'gain_error_predicted_minus_actual_minutes': describe(x-y for x,y in zip(xs,ys)),
        'gain_error_mean_absolute_minutes': statistics.mean(abs(x-y) for x,y in zip(xs,ys)) if xs else None,
        'gain_pearson_correlation': corr(xs, ys),
        'chosen_cost_error_real_minus_model_minutes': describe(
            r['chosen_actual_minutes'] - r['chosen_model_minutes'] for r in both
            if r['chosen_model_minutes'] is not None),
        'base_cost_error_real_minus_model_minutes': describe(
            r['base_actual_minutes'] - r['base_model_minutes'] for r in both
            if r['base_model_minutes'] is not None),
        'template_queries': total,
        'imputation_queries': imputed,
        'query_weighted_imputation_fraction': imputed / total if total else None,
        'missing_curve_queries': sum(r['missing_queries'] for r in rows),
        'historical_closure_curve_queries': sum(r['closed_queries'] for r in rows),
        'after_midnight_curve_queries': sum(r['after_midnight_queries'] for r in rows),
        'scenario_age_days': describe(
            age for r in rows for age in r['_scenario_age_days']),
    }


def main():
    trace_path = STUDY / 'evaluation/traces.json'
    metadata_path = STUDY / 'evaluation/metadata.json'
    daily_path = STUDY / 'evaluation/per_day.csv'
    metadata = json.loads(metadata_path.read_text())
    assert metadata['engine_sha256'] == digest(STUDY / 'engine.py')
    before_hashes = {str(p.relative_to(STUDY)): digest(p)
                     for p in [trace_path, metadata_path, daily_path, STUDY/'engine.py', STUDY/'run.py']}
    config = metadata['config']
    cfg = e.Config(start=config['start'], walk=config['walk'], service=config['service'])
    core, data, _ = load_data()
    train_dates = metadata['train_dates']
    assert set(train_dates).isdisjoint(metadata['evaluation_dates'])
    assert max(train_dates) < min(metadata['evaluation_dates'])
    curves = core.train_curves(data, train_dates)
    predictor = e.Predictor(curves, 60)
    bank = CountingBank(data, train_dates, curves, k=8)
    traces = json.loads(trace_path.read_text())
    with daily_path.open(newline='') as f:
        daily = {(r['date'],r['policy']):r for r in csv.DictReader(f)}
    rows = []
    example_records = {}
    all_rollout_decisions = 0
    singleton_decisions = 0
    verified_first_visits = 0
    verified_two_remaining_suffixes = 0
    for trip in traces:
        if trip['policy'] != 'rollout':
            continue
        day = {r:data[r][trip['date']] for r in e.RIDES}
        deadline = float(daily[trip['date'],'rollout']['deadline'])
        completed_prefix = []
        for event_index, event in enumerate(trip['events']):
            if event['type'] == 'visit':
                if event['status'] == 'completed':
                    completed_prefix.append(event['ride'])
                continue
            all_rollout_decisions += 1
            if len(event['incumbent']) < 2:
                singleton_decisions += 1
                continue
            now = float(event['at'])
            location = event['location']
            current = snapshot(day, now)
            assert {r:value(current,r) for r in e.RIDES} == event['snapshot']
            assert set(completed_prefix).isdisjoint(event['incumbent'])
            assert set(completed_prefix) | set(event['incumbent']) == set(e.RIDES)
            base_order, _ = e.base_order(event['incumbent'], location, now,
                                          current, cfg, predictor)
            base_action = base_order[0]
            chosen_action = event['chosen_next']
            assert base_action == event['base_next']
            assert chosen_action == event['selected'][0]
            forced_chosen = (chosen_action,) + tuple(r for r in base_order if r != chosen_action)
            forced_base = tuple(base_order)
            chosen = factual_continuation(forced_chosen, location, now, day,
                                           deadline, cfg, predictor)
            base = factual_continuation(forced_base, location, now, day,
                                         deadline, cfg, predictor)
            actual_suffix = [v for v in trip['events'][event_index+1:] if v['type']=='visit']
            # The real R trip necessarily executed this same immediate action.
            visit_keys = ('ride','from','depart','arrival','walk','service',
                          'posted_observed_at','posted_wait','status','finish')
            assert all(chosen['visits'][0].get(k)==actual_suffix[0].get(k) for k in visit_keys)
            verified_first_visits += 1
            # With two rides remaining there is no subsequent route-choice freedom,
            # so this independent executor must reproduce the full real R suffix.
            if len(event['incumbent']) == 2:
                assert len(chosen['visits']) == len(actual_suffix)
                assert all(a.get(k)==b.get(k) for a,b in zip(chosen['visits'],actual_suffix)
                           for k in visit_keys)
                verified_two_remaining_suffixes += 1
            if chosen_action == base_action:
                assert chosen == base
            # Recount the already-frozen policy, not a newly tuned candidate.
            repeated_order, repeated_meta = e.plan('rollout', event['incumbent'],
                location, now, current, cfg, predictor, bank)
            assert list(repeated_order) == event['selected']
            assert repeated_meta['scenario_ids'] == event['scenario_ids']
            query_counts = Counter()
            for scenario_date, counts in repeated_meta['scenario_query_audit'].items():
                original_counts = {k:v for k,v in counts.items() if k != 'total_template_queries'}
                assert original_counts == event['scenario_query_audit'][scenario_date]
                query_counts.update(counts)
            for ride, cost in repeated_meta['predicted_costs'].items():
                old = event['predicted_costs'][ride]
                assert (old is None and not math.isfinite(cost)) or (
                    old is not None and abs(cost-old)<1e-7)
            chosen_cost = event['predicted_costs'][chosen_action]
            base_cost = event['predicted_costs'][base_action]
            predicted_gain = (base_cost-chosen_cost if base_cost is not None and chosen_cost is not None else None)
            status = classify(chosen, base)
            actual_gain = (base['elapsed_minutes']-chosen['elapsed_minutes']
                           if status == 'both_success' else None)
            imputed = query_counts['missing_curve_imputation_queries'] + query_counts['historical_closure_curve_imputation_queries']
            total = query_counts['total_template_queries']
            ages = [(date.fromisoformat(trip['date'])-date.fromisoformat(d)).days
                    for d in event['scenario_ids']]
            row = {'date':trip['date'], 'event_index':event_index, 'at':now,
                'location':location, 'prefix_count':len(completed_prefix),
                'remaining_count':len(event['incumbent']),
                'base_next':base_action, 'chosen_next':chosen_action,
                'changed_next':chosen_action!=base_action,
                'predicted_gain_minutes':predicted_gain, 'actual_gain_minutes':actual_gain,
                'chosen_model_minutes':chosen_cost, 'base_model_minutes':base_cost,
                'chosen_actual_minutes':chosen['elapsed_minutes'],
                'base_actual_minutes':base['elapsed_minutes'],
                'completion_status':status, 'chosen_success':chosen['success'],
                'base_success':base['success'], 'chosen_failure':chosen['failure'],
                'base_failure':base['failure'],
                'chosen_completed_suffix':'|'.join(chosen['completed_suffix']),
                'base_completed_suffix':'|'.join(base['completed_suffix']),
                'fallback':event['fallback'], 'fallback_reason':event['fallback_reason'],
                'scenario_ids':'|'.join(event['scenario_ids']),
                'mean_scenario_age_days':statistics.mean(ages) if ages else None,
                'template_queries':total, 'imputation_queries':imputed,
                'query_weighted_imputation_fraction':imputed/total if total else None,
                'missing_queries':query_counts['missing_curve_imputation_queries'],
                'closed_queries':query_counts['historical_closure_curve_imputation_queries'],
                'after_midnight_queries':query_counts['beyond_midnight_curve_queries'],
                '_scenario_age_days':ages}
            rows.append(row)
            if row['changed_next'] and status == 'both_success':
                example_records[trip['date'],event_index] = {
                    'row':{k:v for k,v in row.items() if not k.startswith('_')},
                    'completed_prefix':list(completed_prefix),
                    'recorded_decision':event,
                    'chosen_action_then_D0':chosen, 'base_action_then_D0':base}
        if len(rows) and len(rows) % 50 < 5:
            print(f'Audited {trip["date"]}: {len(rows)} recorded choice states', flush=True)
    changed = [r for r in rows if r['changed_next']]
    common_changed = [r for r in changed if r['completion_status']=='both_success']
    helpful = [r for r in common_changed if r['actual_gain_minutes']>e.EPS]
    harmful = [r for r in common_changed if r['actual_gain_minutes'] < -e.EPS]
    losses = sorted(common_changed, key=lambda r:r['actual_gain_minutes'])[:5]
    out = {
        'credit':'TouringPlans.com', 'diagnostic_type':'post-outcome explanation, no tuning or candidate search',
        'estimand':'At real rollout-visited states, force R action versus D0 action, then D0 in both branches; conditional remaining-time difference only when both finish.',
        'sign':'positive = chosen R action helpful; actual = D0-branch remaining time minus R-forced-branch remaining time',
        'limitations':[
            'States are selected by actual rollout policy, not by a neutral policy; not a trip-average policy effect.',
            'Decisions from one date overlap and are dependent; no iid significance tests or bootstrap performed here.',
            'Historical future outcomes are read only by this offline executor; none feed the original or future planner.',
            'Both-success restriction excludes failed counterfactuals; all completion discordances disclosed separately.',
            'One realized day is not the conditional expectation: discrepancy measures realized action-value prediction error, not a proof of bias at every state.',
            'Query-weighted imputation is repeated model _template calls, not fraction of source records, unique times, or real visitor minutes.',
            'After-midnight curve fallback is counted separately from missing/closure imputation.',
            'Poor results diagnose this finite historical model/implementation; they do not prove future-replanning value is absent or isolate a causal source of error.'
        ],
        'input_hashes':before_hashes, 'audit_code_sha256':digest(Path(__file__)),
        'source_sha256':core.SOURCE_SHA256,
        'all_recorded_rollout_replans':all_rollout_decisions,
        'excluded_singleton_replans':singleton_decisions,
        'reconstructed_choices_and_model_costs_verified':len(rows),
        'immediate_visits_verified_against_original_trace':verified_first_visits,
        'two_remaining_suffixes_verified_against_original_trace':verified_two_remaining_suffixes,
        'all_choice_states':summarize(rows),
        'changed_vs_D0_states':summarize(changed),
        'unchanged_vs_D0_states':summarize([r for r in rows if not r['changed_next']]),
        'helpful_changed_states':summarize(helpful),
        'harmful_changed_states':summarize(harmful),
        'changed_by_remaining_count':{str(n):summarize([r for r in changed if r['remaining_count']==n]) for n in range(2,6)},
        'changed_by_evaluation_month':{m:summarize([r for r in changed if r['date'][:7]==m]) for m in sorted({r['date'][:7] for r in rows})},
        'largest_losses':[example_records[r['date'],r['event_index']] for r in losses],
    }
    for name, old_hash in before_hashes.items():
        assert digest(STUDY/name)==old_hash, 'Unexpected mutation: '+name
    with (HERE/'rollout_error_audit.csv').open('w',newline='') as f:
        fieldnames=[k for k in rows[0] if not k.startswith('_')]
        writer=csv.DictWriter(f,fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows({k:r[k] for k in fieldnames} for r in rows)
    (HERE/'rollout_error_audit.json').write_text(json.dumps(out,ensure_ascii=False,indent=2,allow_nan=False)+'\n')
    write_report(out)
    print(json.dumps({'states':len(rows),'changed':out['changed_vs_D0_states'],
                      'worst':out['largest_losses'][0]['row'] if losses else None},
                     ensure_ascii=False,indent=2),flush=True)


def write_report(out):
    changed=out['changed_vs_D0_states']
    all_states=out['all_choice_states']
    signs=changed['both_success_sign_counts']
    state_counts=changed['completion_status']
    def f(x):
        return '未定义' if x is None else f'{x:.3f}'
    lines=[
        '**Data credit: TouringPlans.com — historical Animal Kingdom posted waits.**', '',
        '# Rollout 为什么没有胜出：冻结决策的离线条件性误差诊断', '',
        '本分析在看到候选主结果后执行，只解释现有方法，不改参数、不训练、不测试新候选。', '',
        '## 1. 问的是什么', '',
        '在实际 rollout 已经到达的每个选择状态，复制游客位置、时刻、已完成集合与 incumbent。分别强制 rollout 选出的下一项、当时 D0 会选的下一项；之后两条分支都使用同一个真实 D0，每次仅看模拟当前时刻及以前的观测。到达后由独立执行逻辑用历史公布等待评分。', '',
        '**正值表示 rollout 当下选项更好。** 这是“同一状态的一次动作替换后都跟随 D0”的剩余时间差，不是两种完整策略的整趟平均收益；同日多个状态重叠、相关，不能相加，也不能当独立游客。', '',
        f'共记录 {out["all_recorded_rollout_replans"]} 次重算；排除只剩一项的 {out["excluded_singleton_replans"]} 次，审查 {all_states["decision_states"]} 个真实选择状态，来自 {all_states["distinct_dates"]} 天。逐状态重建的选择、8 情景 ID、所有动作成本与原 trace 一致；{out["immediate_visits_verified_against_original_trace"]} 个强制首项的真实到达/等待/状态与原 trace 一致，且只剩两项时 {out["two_remaining_suffixes_verified_against_original_trace"]} 条完整尾部也逐步一致。', '',
        '## 2. 下一项与 D0 不同的状态', '',
        f'- 不同下一项：{changed["decision_states"]} 个状态，来自 {changed["distinct_dates"]} 天。',
        f'- 两分支都完成：{state_counts.get("both_success",0)}；只有 rollout 首项分支完成：{state_counts.get("chosen_only_success",0)}；只有 D0 首项分支完成：{state_counts.get("base_only_success",0)}；两者都失败：{state_counts.get("both_failed",0)}。',
        f'- 双方完成的改变中：有利 {signs["helpful"]}，相同 {signs["tied"]}，不利 {signs["harmful"]}。',
        f'- 有限预测且双方完成的 {changed["finite_prediction_and_both_success_states"]} 个状态：预计平均省 {f(changed["predicted_gain_minutes_on_scored_states"]["mean"])} 分钟，实际条件性差值平均 {f(changed["actual_gain_minutes_on_scored_states"]["mean"])} 分钟。',
        f'- 预计差值与实际差值的 Pearson 相关：{f(changed["gain_pearson_correlation"])}；差值平均绝对误差：{f(changed["gain_error_mean_absolute_minutes"])} 分钟。', '',
        '这些数字是描述性误差诊断。一个历史日实现值不等于其条件期望；因此不能仅凭单次差值宣布某状态的期望价值估计有偏。', '',
        '## 3. 模型填补的暴露程度', '',
        f'所有选择状态共计 {all_states["template_queries"]:,} 次模型模板查询，缺报/历史关闭填补 {all_states["imputation_queries"]:,} 次，占 {100*all_states["query_weighted_imputation_fraction"]:.2f}%。其中缺报 {all_states["missing_curve_queries"]:,}、历史关闭 {all_states["historical_closure_curve_queries"]:,}；另有跨午夜曲线尾部查询 {all_states["after_midnight_curve_queries"]:,} 次。', '',
        '**分母是计算过程重复访问的查询次数**，包括锚定、情景评分与未来快照生成，不是原始记录缺失率，不是独立时间点比例，也不是游客排队时间占比。计数型复算只增加计数器，已断言原选择、成本与已有填补计数不变。', '',
        '这一暴露说明“整日历史轨迹”在计算中有一部分实际来自训练中位曲线；它限制情景真实性，但不能证明填补导致全部损失。', '',
        '## 4. 按剩余项目数拆分（描述性）', '',
        '| 剩余项目 | 改变状态 | 两分支完成 | 有利/平/不利 | 预计省时均值 | 实现差值均值 |',
        '|---|---:|---:|---|---:|---:|'
    ]
    for n,group in out['changed_by_remaining_count'].items():
        sg=group['both_success_sign_counts']
        lines.append(f'| {n} | {group["decision_states"]} | {group["completion_status"].get("both_success",0)} | {sg["helpful"]}/{sg["tied"]}/{sg["harmful"]} | {f(group["predicted_gain_minutes_on_scored_states"]["mean"])} | {f(group["actual_gain_minutes_on_scored_states"]["mean"])} |')
    lines += ['', '更长剩余行程的改变在本样本里损失较大，与长跨度动作价值误差的解释相容，但不是控制其他因素后的因果比较。', '',
              '### 时间段与历史情景距离', '',
              f'所有状态的情景选择共 {all_states["scenario_age_days"]["n"]} 个重复计数的“状态—历史日”条目，距评估日的中位数为 {f(all_states["scenario_age_days"]["median"])} 天、均值为 {f(all_states["scenario_age_days"]["mean"])} 天。这个数字刻画模板时间距离，不意味着越近必然越好。', '',
              '| 评估月份 | 改变状态 | 两分支完成 | 实现差值均值 |',
              '|---|---:|---:|---:|']
    for month,group in out['changed_by_evaluation_month'].items():
        lines.append(f'| {month} | {group["decision_states"]} | {group["completion_status"].get("both_success",0)} | {f(group["actual_gain_minutes_on_scored_states"]["mean"])} |')
    lines += ['', '月份差异是事后描述，只提示可能存在时间变化/情景失配；状态组成、节假日、预测跨度等也同时变化，不能据此确认季节漂移是损失原因，更不能据此挑月份报告。']
    lines+=['','## 5. 透明展示：最大单状态损失','','以下按实现差值排序选择，目的是解释错误，不是代表性展示；完整逐状态表同时提供。']
    if out['largest_losses']:
        ex=out['largest_losses'][0]
        row=ex['row']
        lines += ['',f'- 日期 {row["date"]}，时刻 {row["at"]} 分钟，位置 {row["location"]}；已完成 {", ".join(ex["completed_prefix"])}。',
                  f'- D0 下一项 {row["base_next"]}；rollout 改选 {row["chosen_next"]}。',
                  f'- 情景预计省 {f(row["predicted_gain_minutes"])} 分钟；实际同状态两分支差值 {f(row["actual_gain_minutes"])} 分钟。',
                  f'- 强制 rollout 首项后跟随 D0：{row["chosen_completed_suffix"]}，剩余 {f(row["chosen_actual_minutes"])} 分钟。',
                  f'- 强制 D0 首项后跟随 D0：{row["base_completed_suffix"]}，剩余 {f(row["base_actual_minutes"])} 分钟。',
                  '', '| 分支 | 项目 | 到达分钟 | 公布等待 | 完成分钟 |', '|---|---|---:|---:|---:|']
        for label,key in [('R首项后D0','chosen_action_then_D0'),('D0首项后D0','base_action_then_D0')]:
            for visit in ex[key]['visits']:
                lines.append(f'| {label} | {visit["ride"]} | {f(visit["arrival"])} | {visit["posted_wait"]} | {f(visit.get("finish"))} |')
    lines += ['', '## 6. 可以得出的解释与不能得出的结论', '',
              '- 若模型认为改善、实现却经常变慢，支持“当前动作价值排序未可靠泛化”的诊断；模型误差、有限情景与选优噪声都可能参与。',
              '- 相似的当前快照不足以保证相似的后半天轨迹。训练历史跨不同日期/季节、填补、固定衰减、模型观测频率与随机到达都可能造成错配；本分析没有识别它们各自的因果贡献。',
              '- 结果不能证明未来重规划没有价值、所有 rollout 都无效，也不能证明更大情景数或新参数一定有效。本轮不追加调参。',
              '- 公布等待仅为时间代理；失败分支未被赋予虚构分钟，也未被隐藏。',
              '', '## 7. 文件与复现', '',
              '- `rollout_error_audit.csv`：每个真实选择状态的完整结果和失败状态。',
              '- `rollout_error_audit.json`：分组统计、输入 hashes、五个最大损失状态及两分支完整轨迹。',
              '- `audit_rollout_errors.py`：仅离线诊断脚本；从本目录运行 `python3 -B audit_rollout_errors.py`。',
              '', '没有改变原策略、候选配置、输入资料或正式评估输出；运行前后核对关键输入与 engine/runner hashes。', '']
    (HERE/'rollout_error_audit.md').write_text('\n'.join(lines))


if __name__ == '__main__':
    main()
