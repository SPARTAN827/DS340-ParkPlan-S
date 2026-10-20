# Algorithm-study research figures

These are standalone research graphics, **not a PowerPoint deck**. Each figure is
available as editable-text SVG, 180-dpi PNG, and vector PDF. All three rendered PNGs
were visually inspected for legibility, clipping, numeric labels, and honest
separation of conditional time differences from all-attempt completion.

## Figures

- `01_candidate_comparison`: Each candidate's paired mean against existing D0 and
  its own joint-success sample size, with the summary's 95% seven-date block
  bootstrap interval. A separate panel shows completion/noncompletion for all 165
  attempts. All three intervals cross zero; none establishes a clear time gain.
- `02_input_sensitivity`: Six shared-input settings. Every cell shows minutes,
  the same type of interval, its own paired sample size, and candidate/D0
  noncompletion counts. Neutral colors deliberately do not turn a positive
  conditional mean into an automatic overall victory.
- `03_feedback_first_principles`: Current snapshot → choose next action → execute
  one ride → new snapshot → repeat. The comparison distinguishes existing D0 from
  scenario rollout, without implying a guarantee or displaying synthetic toy
  numbers as dataset evidence.

## Reproduce

From the repository root:

```bash
/tmp/parkplan-plot-venv/bin/python experiments/algorithm_study_20261019/make_figures.py
```

`figure_manifest.json` records the exact input-summary and script hashes. The
renderer reads existing summaries; it does not tune algorithms or recompute
statistical analyses. Matplotlib uses a task-specific temporary cache directory.

## Interpretation and credit

Data source: **TouringPlans.com**. These are retrospective exploratory posted-wait
proxy simulations, not measured savings for real visitors. Travel geometry and
service assumptions are synthetic; the illustrative nonuniform graph is not a
measured 2018 park map. Different comparisons have different joint-success dates.
Failed attempts are shown separately, not assigned zero time. Bootstrap intervals
do not incorporate model/input uncertainty or all possible temporal dependence.
The 30-minute calibration decay was selected using earlier validation data, but
the evaluation dates had already been examined in previous work: they are not a
pristine new holdout.
