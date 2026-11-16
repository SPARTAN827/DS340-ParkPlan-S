Data credit: TouringPlans.com — historical Animal Kingdom posted waits and source-listed park hours.

# Week 12 evidence and rubric audit

Independent review dated November 15, 2026. This is an evidence audit, not a new scientific trial, grade guarantee, or record of submission.

## Numerical cross-check

`numerical-audit.json` independently aggregates all **4,950 policy-day CSV rows** from the main evaluation and five sensitivity settings (825 rows per setting: 165 dates × 5 policies). No planner or study summarizer is imported. All saved completion counts, pairwise sample sizes and pairwise means agree. The saved bootstrap limits are copied for comparison, not independently recomputed in this review. The earlier study's independent verifier covers 6,200 total records including validation/reference, with its separately documented scope.

| Comparison | Both complete | Comparator minus candidate, modeled minutes | Saved 95% seven-date block interval |
|---|---:|---:|---|
| F − D0 | 105 | +15.476 | [+6.886, +23.384] |
| D0 − C | 119 | −2.815 | [−6.881, +0.935] |
| D0 − R (primary) | 118 | −6.356 | [−13.730, +0.357] |
| D0 − S | 114 | −1.360 | [−5.509, +2.248] |
| S − R | 119 | −5.126 | [−11.639, +1.106] |

All-attempt completions are F 120, D0 126, C 126, R 128 and S 123, each out of 165. D0/R jointly finish 118 dates; D0 only 8, R only 10, neither 29. Different comparisons use different date subsets. The F–D0 benefit cannot be reported as an R improvement. A block interval crossing zero is not evidence of equivalence. Across the six input settings, all 18 saved candidate-versus-D0 block intervals cross zero.

## Implementation and lineage

Reviewed `engine.py`, `run.py`, the previous Method, and `REPORT.md`/`REPRODUCE.md` in `experiments/algorithm_study_20261019/`.

- **Inherited idea:** commitment versus observation-driven replanning, motivated by the parent routing papers. ADAPT's original setting is UAV orienteering with energy constraints and collected reward.
- **Project baseline D0:** data-fitted historical median curves plus a current residual decaying over 60 minutes; exhaustive permutation scoring at projected arrival times; execute one ride and replan. Arrival-aware forecasting and exhaustive search are already baseline features.
- **C:** validation-selected residual decay, 30 minutes, from 15/30/60/120; the planning mechanism is unchanged. Selection uses chronological validation and completion checks.
- **R:** choose among admissible next rides using eight training-day scenarios. Force one action and then follow D0, exposing only as-of simulated observations to that continuation. This is an adaptation of established rollout, not invention of rollout or an exact stochastic optimum.
- **S:** same scenarios but one shared complete order, with real-world replanning still allowed after every completed ride. It does not optimize a different hindsight route for each scenario. The returned incumbent tail follows the D0 convention rather than necessarily the internally scored shared order.
- **Fairness:** same initial D0 order and first action, ride set, observation rules, synthetic inputs and real replay failure rules. R/S never average only successful scenarios; all-unsupported actions fall back to D0.
- **Limitations visible in code:** historical missing/closed scenario values are curve-imputed; current closure freshness expires from its original timestamp; predictive scoring omits the park-close deadline while actual execution enforces it. No reliable future-closure model or measured visitor trajectory is implemented.

## Rubric mapping and remaining evidence

| Requirement | Supported evidence / action | Boundary |
|---|---|---|
| Multiple modifications and comparison | C/R/S, F/D0 controls, same-scenario ablation and six shared input settings | Existing October study; do not relabel as new November science |
| Contribution and Method | Explicit inherited-versus-project components, exact state, forecast, scenario, action and fallback rules | Not original ADAPT Bayesian estimator/ant-colony implementation; no KOWCPI implementation |
| Evaluation and critical discussion | Conditional paired means, all-attempt failures, uncertainty and negative findings | No verified superior candidate, measured visitor saving or all-attempt causal benefit |
| Reproducibility | Pinned dataset, hashes, code, saved raw-derived traces, standard-library pipeline, tests and independent audit | A one-day fresh demo is not a rerun of all 6,200 records; exact timing bytes vary |
| Original/modified datasets | Parent ADAPT run exists separately; park adaptation uses a different domain | Not a controlled cross-dataset comparison; sensitivities reuse wait records |
| Tables/figures and structure | Final manuscript should introduce each item, define signs and denominators, retain official template | Final PDF visual/build review remains a separate check |
| References/originality | Preserve traceable citations and credit data at the beginning | No similarity-check result or top-decile score is established |
| GitHub and commits | Existing public team repository and prior verified commits | New Week 12 additions must be published and checked before claiming they are online |
| Kaltura and group explanation | Prepare executable demo and two-person explanation | Actual recording, URL, playback/access and submission are not established by scripts |

The best supported conclusion is to retain D0 as the working comparator and report why these candidate modifications did not establish a reliable advantage. A future calibrated action-value/closure model is a research proposal, not an implemented result.

TouringPlans terms: data may be used subject to (1) clearly crediting TouringPlans.com at the beginning of publications or redistributions and (2) including these terms in redistributions. This audit contains derived aggregates, not raw wait CSVs.
