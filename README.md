**Data credit: TouringPlans.com — historical Disney Animal Kingdom posted waits and published park-hour listings.**

# ParkPlan-S: time-efficient six-ride replanning

DS340 project by **Jesse Zhang and Yongqi Sheng**.

## Current project

For one park and the same six required rides, compare a fixed initial order with replanning after every completed ride. The user objective is total elapsed walking + waiting + service time. Completing the same six rides is a comparison-validity condition, not a separate optimization objective.

The current Python implementation and experiments are in [`experiments/algorithm_study_20261019/`](experiments/algorithm_study_20261019/). The earlier ADAPT parent-paper reproduction remains in [`reproduction/`](reproduction/). It is preserved; it is not the current park planner.

| Policy | Meaning |
|---|---|
| F | Keep the common initial order. |
| D0 | Existing arrival-aware dynamic planner; replan after each completed ride. |
| C | Validation-selected residual-decay calibration. |
| R | Test each next action across eight historical scenarios, with later D0 feedback. |
| S | Same-scenario shared-order control. |

All policies use the same start, information access, six rides and execution rules. Current implementations are research replay code, not a deployed visitor application.

## Current finding

- F minus D0: **+15.48 modeled minutes saved** on 105 jointly completed evaluation dates.
- D0 minus R: **−6.36 modeled minutes saved** on a different set of 118 jointly completed dates; 95% seven-date block interval **[−13.73, +0.36]**.
- All-attempt completions: F **120/165**, D0 **126/165**, R **128/165**.
- **The new rollout has not established an improvement over D0.** QA PASS is an integrity result, not a performance win.

The evaluation dates had been inspected previously: this is retrospective, exploratory analysis, not an untouched final holdout. Posted waits are a proxy, not measured visitor journeys. Walking and service assumptions are synthetic; no real-world saving or superiority to proprietary TouringPlans software is claimed.

Read the [study report](experiments/algorithm_study_20261019/REPORT.md), [frozen protocol](experiments/algorithm_study_20261019/PROTOCOL.md), and [action-value diagnostic](experiments/algorithm_study_20261019/diagnostics/rollout_error_audit.md).

## Dataset

- Public dataset: [TouringPlans / DisneyAnimalKingdomWaitTimes](https://github.com/TouringPlans/DisneyAnimalKingdomWaitTimes).
- Pinned commit: `933161b8bebb7cd50e0d54bcb3578484875487fa`.
- Six historical series: `AK07`, `AK11`, `AK14`, `AK18`, `AK85`, `AK86`.
- Chronological split: 270 fit dates, 115 validation dates, 165 exploratory evaluation dates.
- Raw wait CSVs and downloaded archives are not bundled. Download the pinned source as documented in [RUNNING.md](RUNNING.md).

Attraction names reflect the historical dataset, not a claim about current park operations.

## Code you can inspect and develop

| File | Role |
|---|---|
| [`engine.py`](experiments/algorithm_study_20261019/engine.py) | Route scoring, policies and historical-scenario continuation logic. |
| [`prepare.py`](experiments/algorithm_study_20261019/prepare.py) | Shared inputs and chronological splits. |
| [`run.py`](experiments/algorithm_study_20261019/run.py) | Frozen original experiment runner. Use the public entry point below. |
| [`analyze.py`](experiments/algorithm_study_20261019/analyze.py) | Paired summaries and uncertainty intervals. |
| [`test_engine.py`](experiments/algorithm_study_20261019/test_engine.py) | Constructed engine checks, not evidence of superiority. |
| [`scripts/run_public_study.py`](scripts/run_public_study.py) | Public-distribution runner; original scientific implementation retained. |
| [`scripts/verify_public_results.py`](scripts/verify_public_results.py) | Public-scope independent verification of the included frozen evidence. |

Core code uses Python's standard library; optional figure regeneration uses the study's `requirements-plot.txt`.

### Quick engine check

From the repository root with Python 3.10+:

```bash
python3 -m unittest discover -s experiments/algorithm_study_20261019 -p test_engine.py -v
```

See [RUNNING.md](RUNNING.md) for source download, full included-results verification and replay commands. The recorded execution environment is Linux/Python 3.12; full native-Windows policy execution is not claimed tested. Windows users can use WSL for the Linux-oriented replay.

The reduced public snapshot was checked in a fresh Linux copy:12 engine tests and8 public-adapter tests passed; all6,200 policy-days,35,082 replay arrivals,23,268 decision snapshots and10,416 training-scenario-ID checks passed. See [public QA](experiments/algorithm_study_20261019/QA-public.md). This packaging check did not rerun policy simulations or establish a new performance result.

## Public package versus original preservation audit

The historical workspace audit checked 31 old artifacts, including 11 meeting-note/archival files that are not needed to explain the algorithms and are not distributed here. This public package strictly verifies the **20 included legacy artifacts**, explicitly records the **11 omissions**, and retains the original algorithm, runner, protocol and locks unchanged.

Use the separately named public entry points, not the original workspace-only preservation command. Public verification writes `QA-public.md` and `verification-public.json`; it does not overwrite the historical certificate. No missing included file is silently ignored. Details and exact adapter scope are in [`scripts/`](scripts/).

Original study reports/QA records describe their historical execution context. They are not claims that omitted meeting material is present in this repository.

## Earlier ADAPT work

The existing [`reproduction/`](reproduction/) directory and its third-party source/license are unchanged. [The previous README](README-2026-09-12.md) is preserved as a dated historical record. Its earlier route-stability proposal and coursework status are superseded by the current time-only scope above.

ADAPT original code was exercised in a limited smoke test, not fully replicated statistically or transplanted into the park algorithm. KOWCPI and Shiri et al. contribute conceptual guidance; neither original system is claimed reproduced here.

## Next research step

Investigate better next-action value prediction using earlier chronological development data, then freeze the method and evaluate on genuinely unused dates. That improvement is a hypothesis, not an implemented or validated winner.

## Data-use terms

You're free to use these data however you see fit, subject to the following:

1. Any publications or redistributions credit TouringPlans.com clearly at the beginning of those publications or distributions.
2. Any redistributions include these license terms.

See [SOURCES-AND-LICENSE.md](experiments/algorithm_study_20261019/SOURCES-AND-LICENSE.md). No blanket license is imposed on third-party materials.
