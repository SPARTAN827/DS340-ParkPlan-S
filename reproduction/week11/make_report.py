#!/usr/bin/env python3
"""Create transparent tables and scientific plots from an audited benchmark.

The experiment and verifier require only Python's standard library. This optional
report builder additionally needs matplotlib; it never changes experiment files.
"""
import argparse
import csv
import hashlib
import json
import math
from pathlib import Path
import statistics

ORDER = ('Offline', 'DoNothing', 'WeightedAvg', 'Bayesian')
LABELS = dict(zip(ORDER, ('Offline', 'ROMP', 'WeightedErr', 'ADAPT')))
SCENARIOS = ('mean90_std110', 'mean110_std110')
TITLES = {'mean90_std110': 'Power mean -10%, SD +10%',
          'mean110_std110': 'Power mean +10%, SD +10%'}


def wilson(k, n):
    if n == 0:
        return None, None
    z = 1.959963984540054
    p = k / n
    center = (p + z*z/(2*n)) / (1 + z*z/n)
    half = z * math.sqrt(p*(1-p)/n + z*z/(4*n*n)) / (1+z*z/n)
    return max(0., center-half), min(1., center+half)


def mean(values):
    return statistics.mean(values) if values else None


def sd(values):
    return statistics.stdev(values) if len(values) > 1 else None


def fmt(value, digits=3):
    return 'N/A' if value is None else f'{value:.{digits}f}'


def comparison(results, references):
    rows = []
    for scenario in SCENARIOS:
        for strategy in ORDER:
            cases = [r for r in results if r['scenario'] == scenario and r['strategy'] == strategy]
            good = [r for r in cases if r['status'] == 'success']
            reference = references[scenario, strategy]
            lo, hi = wilson(len(good), len(cases))
            row = dict(scenario=scenario, strategy=strategy, label=LABELS[strategy],
                       attempted=len(cases), successful=len(good),
                       mission_failures=sum(r['status'] == 'mission_failure' for r in cases),
                       harness_errors=sum(r['status'] == 'harness_error' for r in cases),
                       measured_msr_pct=100*len(good)/len(cases),
                       measured_msr_wilson95_low_pct=100*lo,
                       measured_msr_wilson95_high_pct=100*hi,
                       paper_msr_pct=float(reference['paper_msr_pct']))
            row['msr_difference_percentage_points'] = row['measured_msr_pct']-row['paper_msr_pct']
            for metric, key in [('P', 'charged_energy_kJ'), ('C', 'consumed_energy_kJ')]:
                values = [r[key] for r in good]
                paper = reference[f'paper_{metric}_success_kJ']
                paper = float(paper) if paper else None
                actual = mean(values)
                row[f'measured_{metric}_success_mean_kJ'] = actual
                row[f'measured_{metric}_success_sd_kJ'] = sd(values)
                row[f'paper_{metric}_success_mean_kJ'] = paper
                row[f'{metric}_difference_kJ'] = actual-paper if actual is not None and paper is not None else None
            row['charged_energy_all_attempts_mean_kJ'] = mean([r['charged_energy_kJ'] for r in cases])
            row['failure_types'] = dict((outcome, sum(r['outcome'] == outcome for r in cases))
                                        for outcome in sorted({r['outcome'] for r in cases if r['status'] != 'success'}))
            rows.append(row)
    return rows


def paired(results):
    output = []
    for scenario in SCENARIOS:
        adapt = {r['trial']: r for r in results if r['scenario'] == scenario and r['strategy'] == 'Bayesian'}
        for strategy in ORDER[:-1]:
            baseline = {r['trial']: r for r in results if r['scenario'] == scenario and r['strategy'] == strategy}
            common = sorted(adapt.keys() & baseline.keys())
            both = [i for i in common if adapt[i]['status'] == baseline[i]['status'] == 'success']
            output.append({'scenario': scenario, 'baseline': strategy, 'paired_attempts': len(common),
                           'both_successful': len(both),
                           'only_ADAPT_successful': sum(adapt[i]['status'] == 'success' and baseline[i]['status'] != 'success' for i in common),
                           'only_baseline_successful': sum(adapt[i]['status'] != 'success' and baseline[i]['status'] == 'success' for i in common),
                           'neither_successful': sum(adapt[i]['status'] != 'success' and baseline[i]['status'] != 'success' for i in common),
                           'mean_ADAPT_minus_baseline_prize_kJ_both_successful': mean([adapt[i]['charged_energy_kJ']-baseline[i]['charged_energy_kJ'] for i in both]),
                           'note': 'Same trial environment; algorithm RNG is not paired. Conditional differences use only joint successes.'})
    return output


def plots(rows, output):
    import matplotlib
    matplotlib.use('Agg')
    import matplotlib.pyplot as plt
    plt.rcParams.update({'font.family': 'DejaVu Sans', 'font.size': 10,
                         'axes.spines.top': False, 'axes.spines.right': False,
                         'pdf.fonttype': 42, 'svg.fonttype': 'none'})
    blue, gray = '#235b8e', '#b5b5b5'
    fig, axes = plt.subplots(1, 2, figsize=(11.4, 4.6), sharey=True)
    for ax, scenario in zip(axes, SCENARIOS):
        data = [r for r in rows if r['scenario'] == scenario]
        x = list(range(4))
        for offset, field, color, label in [(-.19, 'paper_msr_pct', gray, 'Paper (Fig. 5)'),
                                           (.19, 'measured_msr_pct', blue, 'New run')]:
            values = [r[field] for r in data]
            ax.bar([i+offset for i in x], values, .34, color=color, label=label, zorder=2)
        actual = [r['measured_msr_pct'] for r in data]
        lower = [r['measured_msr_pct']-r['measured_msr_wilson95_low_pct'] for r in data]
        upper = [r['measured_msr_wilson95_high_pct']-r['measured_msr_pct'] for r in data]
        ax.errorbar([i+.19 for i in x], actual, yerr=[lower, upper], fmt='none', ecolor='#18364e', capsize=3, zorder=3)
        for i, r in enumerate(data):
            ax.text(i+.19, 105, f"{r['successful']}/{r['attempted']}", ha='center', fontsize=9, color=blue)
        ax.set_xticks(x, [LABELS[s] for s in ORDER])
        ax.set_title(TITLES[scenario], fontsize=11, pad=16)
        ax.set_ylim(0, 112)
        ax.set_yticks([0,20,40,60,80,100])
        ax.grid(axis='y', color='#e6e6e6', zorder=0)
    axes[0].set_ylabel('Successful return to depot (%)')
    axes[0].legend(frameon=False, loc='lower left', bbox_to_anchor=(0,-.28), ncol=2)
    fig.suptitle('ADAPT author-code rerun: mission success', fontsize=15, y=.98)
    fig.text(.51,.035, 'New-run whiskers: 95% Wilson intervals. Counts include every attempted mission.', ha='center', fontsize=9)
    fig.subplots_adjust(left=.075, right=.985, bottom=.24, top=.82, wspace=.12)
    for extension in ('png','pdf','svg'):
        fig.savefig(output/f'mission-success.{extension}', dpi=180)
    plt.close(fig)

    fig, axes = plt.subplots(2, 2, figsize=(11.4, 7.5))
    for column, scenario in enumerate(SCENARIOS):
        data = [r for r in rows if r['scenario'] == scenario]
        for line, metric in enumerate(('P','C')):
            ax = axes[line,column]
            for i, r in enumerate(data):
                actual = r[f'measured_{metric}_success_mean_kJ']
                paper = r[f'paper_{metric}_success_mean_kJ']
                spread = r[f'measured_{metric}_success_sd_kJ']
                if paper is not None:
                    ax.scatter(i-.09,paper,marker='D',facecolors='white',edgecolors='#555555',s=48,zorder=3,label='Paper mean' if i==1 else None)
                if actual is not None:
                    ax.errorbar(i+.09,actual,yerr=spread,fmt='o',color=blue,capsize=4,ms=6,zorder=4,label='New mean +/- sample SD' if i==1 else None)
                if actual is None and paper is None:
                    ax.text(i,.45,'No successes',ha='center',va='center',rotation=90,fontsize=9,color='#666666',transform=ax.get_xaxis_transform())
            ax.set_xticks(range(4),[f"{LABELS[r['strategy']]}\n(n={r['successful']})" for r in data])
            ax.set_xlim(-.5,3.5)
            ax.set_ylabel('Delivered energy P* (kJ)' if metric=='P' else 'Consumed energy C* (kJ)')
            ax.grid(axis='y',color='#e6e6e6',zorder=0)
            if line==0: ax.set_title(TITLES[scenario],fontsize=11)
    axes[0,0].legend(frameon=False, fontsize=9, loc='best')
    fig.suptitle('Quality among successful missions only',fontsize=15,y=.98)
    fig.text(.5,.035,'Counts are new-run successes. Conditional means can refer to different trial subsets; they do not rank all-attempt performance.',ha='center',fontsize=9)
    fig.subplots_adjust(left=.075,right=.985,top=.89,bottom=.12,hspace=.38,wspace=.22)
    for extension in ('png','pdf','svg'):
        fig.savefig(output/f'success-conditioned-quality.{extension}',dpi=180)
    plt.close(fig)


def write_report(rows, pairs, output, results_path):
    text = ['# Week 11: selected ADAPT running results','',
            'This report compares new runs of the original author code with two selected California20 settings in the paper. The formal profile is `main-text-aligned`; the known upstream sliding-window no-op is preserved. This is a bounded author-code reproduction with disclosed differences, not an exact or full-paper replication.','',
            '## Success rate: all attempts','',
            '| Power mean / SD change | Method | New successes | New MSR | 95% Wilson interval | Paper MSR | Difference (percentage points) |',
            '|---|---|---:|---:|---:|---:|---:|']
    for r in rows:
        setting='-10% / +10%' if r['scenario']=='mean90_std110' else '+10% / +10%'
        text.append(f"| {setting} | {r['label']} | {r['successful']}/{r['attempted']} | {r['measured_msr_pct']:.1f}% | [{r['measured_msr_wilson95_low_pct']:.1f}%, {r['measured_msr_wilson95_high_pct']:.1f}%] | {r['paper_msr_pct']:.0f}% | {r['msr_difference_percentage_points']:+.1f} |")
    text += ['', 'Paper MSR is from arXiv v2, p. 7, Figure 5, with 50 executions per method/setting. Paper success counts in the reference CSV are inferred from the displayed percentages and 50-trial denominator. New intervals describe finite-sample uncertainty; 50/50 is not a guarantee of universal success.','',
             '## Prize and cost: successful missions only','',
             '| Setting | Method | Successful n | Paper P* | New P* | Difference | Paper C* | New C* | Difference |',
             '|---|---|---:|---:|---:|---:|---:|---:|---:|']
    for r in rows:
        setting='-10% / +10%' if r['scenario']=='mean90_std110' else '+10% / +10%'
        fields=[r['paper_P_success_mean_kJ'],r['measured_P_success_mean_kJ'],r['P_difference_kJ'],r['paper_C_success_mean_kJ'],r['measured_C_success_mean_kJ'],r['C_difference_kJ']]
        text.append(f"| {setting} | {r['label']} | {r['successful']} | "+' | '.join(fmt(x) for x in fields)+' |')
    text += ['', 'All values in this table are kJ. P* is actual sensor energy delivered, summed from `mission_log.csv`; C* is 359.64 kJ minus terminal arrival energy. The paper values come from p. 15, Table VII. N/A means there were no successful missions, not zero energy. Sample SDs and exact values are in `comparison.csv`. The two means can condition on different successful cases.','',
             '## Outcome accounting','']
    for r in rows:
        text.append(f"- {r['scenario']} / {r['label']}: {r['attempted']} attempted, {r['successful']} successful, {r['mission_failures']} mission failures, {r['harness_errors']} harness errors. Failure types: {json.dumps(r['failure_types'],sort_keys=True)}.")
    text += ['', '## Paired trial checks','', '| Setting | Baseline | Both succeed | Only ADAPT succeeds | Only baseline succeeds | Neither succeeds | ADAPT minus baseline P*, joint successes (kJ) |',
             '|---|---|---:|---:|---:|---:|---:|']
    for p in pairs:
        text.append(f"| {p['scenario']} | {LABELS[p['baseline']]} | {p['both_successful']} | {p['only_ADAPT_successful']} | {p['only_baseline_successful']} | {p['neither_successful']} | {fmt(p['mean_ADAPT_minus_baseline_prize_kJ_both_successful'])} |")
    text += ['', 'These pairs share initial states, initial offline plans and physical edge costs. The C++ optimizer randomness is not seed-controlled. Do not interpret conditional differences as all-attempt policy benefit.','',
             '## Scope and remaining differences','',
             '- Two of the paper\'s power settings, one instance, and four methods were rerun; California30/40, other settings, MCGreedy and other paper experiments were not reproduced.',
             '- Only separate run configurations changed. The profile aligns three offline solver parameters to Section V-A. Appendix C and repository defaults differ; the exact original table-generating setup was not recovered.',
             '- The upstream 900-second sliding-window script is a no-op; Bayesian observations accumulate. Other original sampling and state-update behavior is preserved.',
             '- Fresh generated environments and uncontrolled optimizer RNG mean values need not match exactly. No post-hoc matching tolerance, tuning-to-target or guaranteed ADAPT superiority is asserted.',
             '- The original author result archive was checked for public availability but was not downloaded and re-aggregated. Reference values were checked against the paper.',
             '- These are UAV charging simulations. They do not establish ParkPlan-S time savings or a new improvement to ADAPT.','',
             '## Reproducible evidence','',
             'See the accompanying raw-evidence archive, protocol, source snapshot, manifest, comparison CSV and independent verification report. Live demonstration runs must use a separate fresh output directory and must not overwrite the frozen formal batch.','']
    (output/'REPORT.md').write_text('\n'.join(text),encoding='utf-8')


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--results',type=Path,required=True)
    parser.add_argument('--output',type=Path,required=True)
    parser.add_argument('--paper-reference',type=Path,default=Path(__file__).with_name('paper_reference.csv'))
    parser.add_argument('--expected-attempts',type=int,default=400)
    parser.add_argument('--no-plots',action='store_true')
    args=parser.parse_args()
    source=args.results/'missions.json'
    results=json.loads(source.read_text())
    completion=json.loads((args.results/'completion.json').read_text())
    manifest=json.loads((args.results/'manifest.json').read_text())
    if len(results)!=args.expected_attempts or completion.get('attempts')!=args.expected_attempts or not completion.get('all_scheduled_attempts_recorded'):
        raise SystemExit('The complete expected batch must be present before report generation.')
    if manifest.get('profile')!='main-text-aligned' or manifest.get('instance')!='california20':
        raise SystemExit('This report template is specifically for the declared main-text-aligned California20 experiment.')
    if not results or any(r['status']=='harness_error' for r in results):
        raise SystemExit('Cannot label a report ready while experiment/harness errors remain; inspect raw evidence.')
    with args.paper_reference.open(newline='') as handle:
        references={(r['scenario'],r['strategy']):r for r in csv.DictReader(handle)}
    rows=comparison(results,references)
    pairs=paired(results)
    args.output.mkdir(parents=True,exist_ok=True)
    (args.output/'comparison.json').write_text(json.dumps(rows,indent=2,allow_nan=False)+'\n')
    (args.output/'paired_comparisons.json').write_text(json.dumps(pairs,indent=2,allow_nan=False)+'\n')
    with (args.output/'comparison.csv').open('w',newline='') as handle:
        writer=csv.DictWriter(handle,fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(dict(r,failure_types=json.dumps(r['failure_types'],sort_keys=True)) for r in rows)
    write_report(rows,pairs,args.output,args.results)
    if not args.no_plots: plots(rows,args.output)
    receipt={'missions_json_sha256':hashlib.sha256(source.read_bytes()).hexdigest(),
             'paper_reference_sha256':hashlib.sha256(args.paper_reference.read_bytes()).hexdigest(),
             'report_builder_sha256':hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
             'reported_missions':len(results),'plots_created':not args.no_plots}
    (args.output/'report-provenance.json').write_text(json.dumps(receipt,indent=2)+'\n')
    print(json.dumps(receipt,indent=2))


if __name__=='__main__':
    main()
