# Baseline-only algorithm diagnostics — 2026-10-19

## Scope and reproducibility

This is a new forensic analysis of **old baseline outcomes**, not a new-policy experiment. It uses the preserved historical-park-close scenario, 165 already-examined dates (2018-07-26–2019-01-06), the tie-preserving D0 traces, and the checksum-pinned TouringPlans.com archive. It does not fit parameters, select an improved policy, change the 385/165 split, alter old files, or claim algorithm superiority.

```bash
python3 experiments/algorithm_study_20261019/diagnostics/audit_baseline.py \
  --archive /tmp/parkplan-ak-933161b.tar.gz
```

The independent parser and forecast arithmetic do **not** import the old simulator. Assertions verify the source SHA-256, original split, exact match of D0 with old replan daily records, every recorded visit's posted value, 800 post-ride exact minimum permutation scores, selected initial scores, time decomposition, and counts. Input file hashes are retained in `baseline_diagnostics.json`. This is an independent implementation check within the same project, not an external validation or a visitor study.

## 1. What the baseline search does—and does not—optimize

For a state after finishing a ride, D0 scores all permutations of remaining rides. Its forecast uses a historical time-bin median plus the current wait's residual, exponentially decaying with a fixed 60-minute scale. A whole suffix is scored using **one frozen information set**; only the first action is executed, then D0 receives new information and recalculates.

- Initial search: at most `6! = 720` permutations.
- A full completed trip has five post-ride recalculation calls, evaluating `5! + 4! + 3! + 2! + 1! = 153` suffixes in total.
- Only **four post-ride calls offer a real next-ride choice**; with one ride remaining the action is forced. Including the initial choice gives five genuine choices over the whole trip.
- Enumeration finds the exact best **frozen point-forecast suffix**. It does not prove optimality over real unknown waits or over adaptive policies that condition future choices on new information.

The plausible decision-layer opportunity is therefore not a more sophisticated permutation search. It is a better estimate of the future value of taking the next action **and then continuing to replan**. This diagnosis motivates testing feedback-aware rollout, but does not establish that any proposed rollout will improve performance. Scenario quality and non-anticipation must be checked.

## 2. Recorded route changes are not all executed next-ride changes

| Remaining rides | Recorded calls | Changed next ride | Changed only later suffix |
|---:|---:|---:|---:|
| 5 | 164 | 85 | 46 |
| 4 | 161 | 102 | 23 |
| 3 | 160 | 80 | 18 |
| 2 | 160 | 47 | 0 |
| 1 | 155 | 0 | 0 |
| **Total** | **800** | **314** | **87** |

There are 645 real-choice calls and 155 forced-final-ride calls. Of 401 stored suffix switches, **87 (21.7%) leave the next ride unchanged**. Those are provisional later-order edits, not immediate changes to the visitor's next destination. This is especially important for animations or statements about how often a visitor is redirected; a full-suffix change count must not be labeled an executed next-stop change count.

## 3. Old time advantage comes entirely from posted-wait proxies

On the same 105 dates where both methods complete all six rides:

| Quantity | Fixed | D0 dynamic |
|---|---:|---:|
| Mean elapsed proxy minutes | 439.43 | 423.95 |
| Walking per completed trip | 60 | 60 |
| Service per completed trip | 60 | 60 |

Fixed minus D0 averages **15.48 minutes**, median 10, with 63 dynamic-faster / 9 equal / 33 dynamic-slower dates. Every paired elapsed difference exactly equals the paired posted-wait difference; paired walking and service differences are zero. The full attempt table remains 105 both-complete, 15 fixed-only, 21 D0-only, 24 neither.

This benchmark has constant ten-minute travel legs, constant ten-minute service durations, no exit leg, and no physical location dependence. Consequently it is currently a **time-dependent visit-sequencing benchmark**, not evidence of spatial walking optimization. Genuine route-distance effects require shared verified distances or clearly labeled synthetic spatial scenarios. A common-success mean is conditional and cannot represent all 165 attempted trips.

## 4. Prediction uncertainty increases over the selected suffix

We reconstruct selected-plan forecast arrivals and retrospectively look up fresh posted waits at those nominal arrival times. These are **not necessarily the eventual actual arrival times** after later replans. Targets are endogenous to D0's selection, repeated/overlapping, and correlated; this table is descriptive, not an independent forecasting benchmark.

| Forecast horizon | Eligible fresh, open, in-hours targets | MAE of forecast vs posted wait |
|---|---:|---:|
| 0–15 min (all immediate targets are 10 min) | 928 | 6.55 min |
| >15–60 min | 291 | 11.17 min |
| >60–120 min | 455 | 18.84 min |
| >120 min | 1,556 | 24.40 min |

The immediate forecast has mean forecast-minus-posted error −0.50 minutes and worst underprediction −99.42 minutes. Long-range point forecasts are uncertain, even though the search finds their exact minimum. This supports investigating uncertainty and future information; it does **not** prove lower MAE automatically produces lower trip time, or that uncertainty penalties would help. The approved objective remains expected total time, without an extra route-change or risk penalty.

## 5. Closure behavior is the largest feasibility issue

| Failure reason | Fixed | D0 |
|---|---:|---:|
| Closed at arrival | 43 | 36 |
| No fresh posted data | 1 | 1 |
| Completion after deadline | 1 | 2 |

**36 of D0's 39 failures are closure failures.** Among those 36:

- **27 occur with only the final ride remaining**; rearranging the remaining order cannot help at that moment.
- 28 already have a fresh known closure at departure and an infinite immediate forecast. The existing code keeps following the incumbent when no finite permutation exists, rather than waiting/recovering.
- Eight were fresh open at departure and became closed by arrival.
- Remaining-ride counts at failure are: 27 with one, five with two, one with four, and three with five.

The 27 forced-final failures and 28 known-at-departure failures are overlapping classifications, not additive counts. Shared waiting/closure-recovery rules, or genuinely earlier anticipation, matter. Granting recovery only to an improved method would confound the comparison. An experiment can retain fail-on-closure as a clearly declared shared limitation, or add the same justified recovery behavior to all methods and treat it as a new benchmark, but must not silently mix the two.

## 6. Data quality and timestamp ties

For the 165 evaluation dates and the loader's 09:45–24:00 window:

- 106,329 posted rows, including 12,120 closure-coded rows, collapse to 105,859 distinct ride/date/time observations.
- 423 timestamp groups contain duplicate source rows; **101 groups have conflicting values**, including 11 with both closure and open values.
- The legacy parser resolves all equal timestamps by the **last row in the source file**. All 101 conflicting groups disagree between the first and last source value.
- One of 965 executed visit arrivals reads a conflicting timestamp. Two of 3,409 remaining-ride information reads do so.
- There are zero missing/stale current remaining-ride state reads at the observed decision moments; one arrival fails due to absent fresh data. This does not imply full future coverage.

These are data-availability assumptions, not algorithmic tie-breaking. The source row order does not establish which conflicting measurement is true. Low observed exposure does **not** prove a different resolution rule would leave whole trajectories unchanged: changed actions can cause later divergence. Any new study must use a shared declared rule and preferably a sensitivity or ambiguity exclusion check. Raw source data are read only; the files here contain derived audit results.

## 7. Transparently selected loss examples

Examples are selected **after** seeing baseline outcomes solely to explain possible failure modes; they are not representative evidence or proof a proposed method would win. Selection rules are deterministic.

1. **Largest paired D0 loss**, earliest date breaking ties: 2018-10-15. Fixed takes 445 minutes; D0 takes 525 (+80). Both end with AK18, but D0 reaches it at 16:15 and reads 140 minutes versus fixed at 17:00 and 15 minutes. This ride contributes +125 minutes; other rides net −45, yielding +80 overall. D0's immediate ten-minute-ahead forecast for AK18 is only 40.58 minutes. The archive value is retained, not trimmed as an inconvenient extreme. It is a posted-wait proxy, not an observed visitor's 140-minute wait.
2. **Earliest paired D0 loss**: 2018-07-27. D0 loses five minutes overall. Its earlier AK07 visit saves 50 proxy wait minutes, but AK86 costs 65 more; AK85 and AK11 contribute −15/+5. A locally attractive next action is not proof of a faster full trip.
3. **Earliest closure failure already known at departure**: 2018-07-28, final AK11. At 16:50 a five-minute-old closure is known, the next-arrival forecast is infinite, and D0 still attempts arrival at 17:00 and fails. No alternate remaining ride exists.

The full per-ride decompositions for the two time-loss examples are in `selected_loss_examples.csv`. No example is presented as a counterfactual result for an untested improved method.

## Deliverables

- `audit_baseline.py`: reproducible audit; standard library only.
- `baseline_diagnostics.json`: counts, hashes, assertions, and summary.
- `paired_decomposition.csv`: all 165 dates, success/failure plus paired decomposition when defined.
- `decision_audit.csv`: 800 decisions, actual-next versus suffix-only changes.
- `visit_forecast_diagnostics.csv`: 965 arrival/state checks and immediate forecast errors when defined.
- `selected_plan_horizon_diagnostics.csv`: 3,407 frozen-plan forecast targets, eligibility and horizon errors.
- `closure_failures.csv`: all 36 D0 closure failures and departure information.
- `selected_loss_examples.csv`: deterministic explanatory loss examples.

**Bottom line:** The old search is already exact for its assumed forecasts. The defensible research opportunity is estimating adaptive continuation value under uncertain future waits, while resolving or explicitly holding constant closure and data semantics. These diagnostics identify opportunities; only a separately frozen, fairly evaluated candidate comparison can establish added value.
