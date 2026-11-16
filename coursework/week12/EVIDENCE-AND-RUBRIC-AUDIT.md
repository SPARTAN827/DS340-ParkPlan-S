Data credit: TouringPlans.com — historical Animal Kingdom posted waits and source-listed park hours.

# Comparison checks and assignment coverage

November 15, 2026

## Checking the reported numbers

A separate aggregation of the main and five sensitivity CSV files checked 4,950 policy-day rows: 165 dates × five policies × six settings. It did not import the planner or study summarizer. Completion counts, paired sample sizes and mean differences agreed with the saved summaries. This check reused the saved bootstrap limits; the earlier full verifier documents its separate interval checks in the [public QA record](../../experiments/algorithm_study_20261019/QA-public.md).

| Comparison | Both complete | Mean saving, min | Saved 95% seven-date block interval |
|---|---:|---:|---|
| F minus D0 | 105 | +15.476 | [+6.886, +23.384] |
| D0 minus C | 119 | -2.815 | [-6.881, +0.935] |
| D0 minus R | 118 | -6.356 | [-13.730, +0.357] |
| D0 minus S | 114 | -1.360 | [-5.509, +2.248] |
| S minus R | 119 | -5.126 | [-11.639, +1.106] |

Saving means the first policy's time minus the second's; positive values favor the second. F, D0, C, R and S complete 120, 126, 126, 128 and 123 of 165 attempts. For D0/R, both finish on 118 dates, D0 alone on eight, R alone on ten, and neither on 29. Different pairs use different successful-date subsets.

All 18 candidate-versus-D0 block intervals across the six settings include zero. This does not establish equivalence or a candidate improvement. The [study report](../../experiments/algorithm_study_20261019/REPORT.md) explains the full comparisons and limitations.

## Implementation scope

D0 already uses historical median curves, a 60-minute decaying residual, arrival-time forecasts and exhaustive remaining-order search. C changes the decay using validation data. R adds eight training-day scenarios and information-limited D0 continuation. S uses the same scenarios to score one shared order, while still replanning after each real ride.

The methods share the initial order, first ride, observation rules and execution inputs. Unsupported scenario actions are not averaged over only successful outcomes; all-unsupported choices fall back to D0. Scenario imputation does not provide a reliable future-closure model, and predictive scoring omits the park-close deadline that actual replay enforces.

ADAPT supplies the observation-driven replanning idea. The park code uses a different objective, predictor and search mechanism. Its Bayesian power estimator and ant-colony optimizer are not part of this implementation.

## Assignment coverage

| Area | Where it is addressed |
|---|---|
| Multiple modifications | C/R/S against F/D0; same-scenario ablation and six shared input settings |
| Method and contribution | Paper Section 3, including inherited ideas, changed components and execution rules |
| Comparative evaluation | Paper Section 4, including negative findings, all-attempt failures and uncertainty |
| Reproducibility | Pinned source, saved traces, tests, verification commands and a one-date live demo |
| References and formatting | Six references and official ICML template; see the paper build notes |
| Code and commits | [Week 12 implementation commit](https://github.com/SPARTAN827/DS340-ParkPlan-S/commit/96d65e4f80b4115ea1a5904076769a0ce297c603) |

The strongest rubric tier for original/modified-dataset comparisons is not established by these same-record sensitivities. No similarity-check score is available. The recording and course upload are separate submission steps listed in the [checklist](DEMO-AND-SUBMISSION.md).

TouringPlans terms: clearly credit TouringPlans.com at the beginning of publications or redistributions and include these terms in redistributions. This document contains derived aggregates, not raw wait CSVs.
