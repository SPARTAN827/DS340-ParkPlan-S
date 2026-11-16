Data credit: TouringPlans.com — historical Disney Animal Kingdom posted waits and published park-hour listings.

# ParkPlan-S

A DS 340W project by **Jesse Zhang and Yongqi Sheng**.

We study a simple question: if a visitor wants to finish the same six rides, does changing the remaining order after each ride save time? ParkPlan-S compares a fixed plan with several replanning methods using historical Animal Kingdom wait data. The goal is to reduce total walking, waiting, and ride-service time.

## Paper and code

- [Week 12 paper and presentation notes](coursework/week12/README.md)
- [Run the five-method demo](experiments/week12_demo_20261115/README.md)
- [Full experiment report](experiments/algorithm_study_20261019/REPORT.md)
- [Setup and reproduction commands](RUNNING.md)
- [Week 11 ADAPT reproduction](reproduction/week11/README.md)

## Methods

| Method | How it chooses the remaining route |
|---|---|
| F: fixed | Keeps the order chosen at the start. |
| D0: dynamic baseline | Uses arrival-time wait estimates and searches all remaining orders after each ride. |
| C: calibrated | Changes how quickly a current wait observation loses influence; the decay is selected on validation dates. |
| R: rollout | Tests each next ride across eight historical-day scenarios and lets D0 make later decisions within each scenario. |
| S: shared-order control | Uses the same scenarios as R but scores one shared remaining order, then replans after the next real ride. |

Every method starts with the same order and first ride and uses the same observation and execution rules. C, R, and S were evaluated in the October study. The Week 12 update adds a short execution demo and expands the paper's Contribution and Evaluation sections.

## Results

Ordinary replanning helped relative to the fixed plan, but the modifications did not establish an advantage over D0.

| Comparison | Dates when both finished | Mean time saved | 95% seven-date block interval |
|---|---:|---:|---:|
| F minus D0 | 105 | 15.48 min | [6.89, 23.38] |
| D0 minus R | 118 | -6.36 min | [-13.73, 0.36] |

Positive values favor the second method. Across all 165 attempted dates, F completed 120, D0 completed 126, and R completed 128. The successful dates differ, so the paired time comparisons use different subsets. We keep D0 as the working comparator.

These are simulated trips using posted waits and assumed walking and service times. The evaluation dates had already been examined in earlier work, so the analysis is exploratory. We have not measured visitor time savings or compared against proprietary TouringPlans software. The [report](experiments/algorithm_study_20261019/REPORT.md) includes failed attempts, calibration and ablation results, and all six input settings.

## Run a short example

The core code uses Python 3.10+ and the standard library. Start with the [demo instructions](experiments/week12_demo_20261115/README.md) to download the pinned data, then run from the repository root:

```bash
python3 experiments/week12_demo_20261115/run_demo.py --archive /tmp/parkplan-ak-933161b.tar.gz
```

The demo runs all five methods on July 26, 2018, the first evaluation date, and saves a new result folder. All five encounter a closed attraction on that date. Those failures are part of the output; the full 165-date study provides the performance comparison.

The recorded environment is Linux/Python 3.12. WSL can run the Linux commands; native Windows execution has not been tested. For the full study, use the public entry points in [RUNNING.md](RUNNING.md). The original workspace runner expects additional archived files that are not included here.

## Repository layout

| Location | Contents |
|---|---|
| `experiments/algorithm_study_20261019/` | Planner, data preparation, saved comparisons, diagnostics and tests |
| `experiments/week12_demo_20261115/` | One-date demo, tests and example output |
| `scripts/run_public_study.py` | Full-study runner for this repository |
| `scripts/verify_public_results.py` | Checks the included experiment records and source hashes |
| `data/verified_inputs/` | Input assumptions and source information |
| `coursework/week12/` | Paper, editable source and presentation notes |
| `reproduction/week11/` | Separate ADAPT author-code experiment |

The [public verification record](experiments/algorithm_study_20261019/QA-public.md) covers 6,200 policy-day records and the 20 included legacy artifacts. Eleven older meeting/archive files are outside this repository's verification scope. Original scientific code, results and hash locks remain unchanged.

## Data and parent papers

The dataset is [TouringPlans/DisneyAnimalKingdomWaitTimes](https://github.com/TouringPlans/DisneyAnimalKingdomWaitTimes), pinned to commit `933161b8bebb7cd50e0d54bcb3578484875487fa`. We use six historical series: AK07, AK11, AK14, AK18, AK85 and AK86, with 270 fit dates, 115 validation dates and 165 evaluation dates. Raw CSVs are downloaded separately. Attraction names refer to the historical dataset.

ADAPT motivates updating a route after new observations. Our separate [400-mission reproduction](reproduction/week11/results/REPORT.md) uses the authors' UAV code on California20 under two power settings. In the higher-mean setting, Offline, ROMP, WeightedErr and ADAPT return-home counts are 0, 8, 25 and 50 out of 50; in the lower-mean setting, all four complete 50/50. This recovers the selected reliability pattern with numerical differences from the paper. It is a partial reproduction, and its drone results do not measure park performance. The original author source remains unchanged.

KOWCPI and Shiri et al. inform the research framing; their original systems are not implemented in this park planner. The [September README](README-2026-09-12.md) records the earlier project direction. Our next research question is whether better next-action value estimates, developed on earlier dates, can improve performance on genuinely unused dates.

## Project development

Jesse Zhang and Yongqi Sheng are the project and paper authors. AI tools assisted with code, documentation editing, and checks during development. The experiment records and source references document the basis for the reported results.

## Data-use terms

You're free to use these data however you see fit, subject to the following:

1. Any publications or redistributions credit TouringPlans.com clearly at the beginning of those publications or distributions.
2. Any redistributions include these license terms.

See [SOURCES-AND-LICENSE.md](experiments/algorithm_study_20261019/SOURCES-AND-LICENSE.md). Third-party materials retain their original licenses.
