**Data credit: TouringPlans.com — historical Disney Animal Kingdom posted waits and source-listed park hours.**

# ParkPlan-S: first-principles algorithm study

Date: 2026-10-19. Status: bounded study completed; **no improved algorithm established**. This report supersedes pre-study candidate recommendations as a performance conclusion, not the frozen protocol or selection record. No slides, visitor trial, commercial comparison or external submission were performed in this stage.

## Executive finding

We tested whether evaluating future adaptive decisions with historical-day scenarios improves upon the existing certainty-equivalent dynamic planner. The study did not establish an advantage; it does not prove equivalence or general inferiority. On 118 jointly completed evaluation dates, existing dynamic D0 minus adaptive rollout R was **−6.356 modeled minutes**, with a 95% seven-date moving-block bootstrap interval **[−13.730, +0.357]**. R finished on 128/165 attempted dates and D0 on 126/165, but their failures differed: D0 alone completed 8 dates, R alone 10, and neither completed 29. These conditional time estimates do not identify an all-attempt benefit.

A validation-selected 30-minute forecast calibration C also failed to retain its earlier gain. A same-scenario shared-order ablation S did not establish improvement. All candidate-versus-D0 block intervals crossed zero across the six input settings. We retain D0 as the working comparator, not as a proven real-world optimum, and do not promote a tested candidate to a validated superior method.

Read the [Chinese explanation](../../writing/research/ParkPlan-S-Algorithm-Study-2026-10-19-zh.md), [frozen protocol](PROTOCOL.md), [independent QA](QA.md), [reproduction guide](REPRODUCE.md), and [sources/license](SOURCES-AND-LICENSE.md).

## 1. Decision problem and existing method

The task is to finish the same six rides in one park, minimizing walking + waiting + service minutes from a 10:00 start through completion of ride six, with no exit leg. The state contains location, time, remaining rides, currently available observations with timestamps, and the incumbent order. The incumbent matters because ties preserve it. An action is the next ride; no optional skipping, intentional waiting or mid-walk/queue diversion is introduced.

For next ride a, arrival is `t + walk(location,a)`; completion adds its arrival-time wait and service duration. The ideal decision compares immediate cost plus expected future policy cost. Future observations can change later actions. Searching all permutations under one point forecast is not equivalent to solving this stochastic policy problem.

D0 already enumerates every remaining order, propagates arrival times, and uses historical time-bin medians plus a current residual decaying with a 60-minute scale. It executes one ride and replans on completion. Therefore arrival-aware forecasts and exhaustive route search are existing features, not new contributions. At most 720 initial orders exist; after a shared first ride there are at most 120 remaining orders. A completed six-ride trip has at most four post-ride decision states with more than one remaining option. Replanning does not force a route change.

The baseline audit independently recomputed all 800 logged replan minimum scores. There were 645 genuine choice states; 401 suffix changes comprised 314 next-ride changes and 87 tail-only changes. Thirty-six of 39 D0 failures were closed-at-arrival, including 27 at the final ride. These are diagnostic counts, not an additional stability objective.

## 2. Implemented policies and novelty boundary

| Code | Policy | Internal evaluation |
|---|---|---|
| F / `fixed` | One common initially optimized order | No subsequent reorder |
| D0 / `dynamic` | Existing 60-minute-decay planner | Exact deterministic permutation scoring at every real completion |
| C / `calibrated` | Same planner, selected decay of 30 minutes | Validation chooses from 15/30/60/120; 60 retained as control |
| R / `rollout` | Primary candidate | For each next action, execute it and subsequently follow nonanticipative D0 in each of 8 historical-day scenarios |
| S / `scenario_open_loop` | Feedback ablation | Same scenarios; evaluate one shared full order across all scenarios, then execute its first action |

All policies receive the same D0-generated initial order and first ride. R/S use the same historical-day template across all rides/times, selected from training dates by current-snapshot distance; no future evaluation observations select neighbors. Offsets anchor the historical scenarios to current observations and decay over 60 minutes. All action candidates share the same eight scenarios and weights. R's hypothetical D0 sees only simulated observations available at its simulated current time; it cannot optimize a tail using the scenario's revealed future. S minimizes the average cost of **one shared order**, not the average of independently hindsight-optimized orders. S still recomputes after each real ride.

Both R/S return a selected first action with a D0-tail incumbent convention. S's logged `shared_best_order` is the order scored internally; it is not necessarily the returned tail. Nonfinite scenario cost makes an action unsupported, without averaging only its successful scenarios; if all actions are unsupported the method falls back to D0.

Historical missing/closed scenario observations are filled with training curves. Thus these are transformed waiting scenarios, not a reliable future closure/reopening model. A currently known closure retains its original timestamp and 15-minute freshness; thereafter the model allows reopening using its prior/template assumptions. Predictive continuation scoring does not impose park close, whereas real execution does. No claim of exact stochastic optimality, safety guarantee or theoretical dominance is made.

Rollout is established prior work. Bertsekas et al. (1997), Bertsekas and Castañon (1999), and Goodson et al. (2013) motivate base-policy continuation and dynamic-route rollout; Brown et al. (2010) clarify information constraints. Elmachtoub and Grigas motivate evaluating predictions through decision costs rather than forecast error alone. These papers do not establish this implementation's superiority. In particular, exact policy-improvement arguments require an appropriately specified conditional model and exact base-policy value evaluation; our finite, transformed historical scenarios do not provide those conditions. No matching ready-made licensed six-ride implementation was verified; we wrote a small standard-library adaptation around the existing replay core. This is neither a full replication of those papers nor TouringPlans' proprietary algorithm. See the [theory/source audit](../../writing/research/parkplan-algorithm-first-principles-2026-10-19.md).

## 3. Data, split and frozen design

Pinned dataset: TouringPlans/DisneyAnimalKingdomWaitTimes commit `933161b8bebb7cd50e0d54bcb3578484875487fa`; archive SHA256 `23eca800b048aecd4b3a2469e78f63f24f64637eb785c8401386e219a177f812`. The six source IDs are AK07, AK11, AK14, AK18, AK85 and AK86. Source same-timestamp file-order handling is preserved. The baseline diagnostic identified 101 conflicting timestamp groups among 105,859 groups, including 11 open/closed conflicts; effects on the old executed streams were small but remain a source limitation.

| Split | Dates | Use |
|---|---|---|
| Fit: 270 dates | 2017-05-26–2018-04-01 | Curves and scenario pool for validation |
| Validation: 115 dates | 2018-04-02–2018-07-25 | Frozen candidate selection rules |
| Evaluation: 165 dates | 2018-07-26–2019-01-06 | Retrospective comparison after refitting on the preceding 385 dates |

The evaluation period had already been inspected in earlier project work. The study was specified before **new candidate outcomes**, but this is **not an untouched confirmatory test**. Chronological separation avoids direct future-observation use; it does not eliminate prior analyst knowledge, seasonal shifts or model misspecification.

All 115 validation park-hour source pages were retrieved with matching date/title checks, with zero deadline fallbacks. The 165 evaluation hour listings were reused unchanged. Listings are not independently established ride-operation logs. Real scoring uses the latest observation at or before arrival, at most 15 minutes old; it does not interpolate forward or use scenario imputation. Closure, stale/missing posts and deadline violations produce identical failure handling for all methods.

The main setting uses uniform 10-minute walking legs and 10-minute service. This preserves the old experiment exactly, but is synthetic geometry: for completed six-ride trips walking and service each total 60 minutes, so differences come from queue timing. Shared sensitivities use 5/5 and 15/15 minutes, a labeled illustrative nonuniform graph with nominal ride-specific service values, and 0.8/1.2 walking scales. The graph is not a measured historical map, and nominal ride durations are not complete measured service cycles.

`protocol_lock.json` records pre-validation sources; `selection.json` was frozen before new evaluation outcomes; `evaluation_lock.json` adds ten full dependency/selection hashes before evaluation. An initial post-write console error passed `flush=True` to `json.dumps`; the only repair moved it to `print`. Original code and outputs were preserved, and the final reference/validation runs were repeated. Independent QA confirms the exact print-only delta and 31 unchanged protected artifacts. See `execution_notes/pre_print_fix/NOTE.md`.

## 4. Validation selection

On the 94 dates jointly completed by D0 and all decay variants, mean times were D0: 478.617, τ=15: 477.500, τ=30: 476.223, τ=60: 478.617, and τ=120: 482.606 minutes. D0 and τ=30 each completed 95/115 dates, but exchanged one success-only date each. The 30-minute decay was selected by the predeclared common-success/no-lower-completion rule.

The within-replay recommendation among D0/C30/R used 89 common-success dates: 480.449/477.753/483.090 minutes, with 95/95/93 completions. C30 was recorded as the validation candidate; R failed the no-lower-completion condition. This was not a deployment superiority claim. R versus D0 remained the primary hypothesis irrespective of the recommendation. The evaluation does not retrospectively alter this selection record.

## 5. Primary evaluation and denominators

Positive saving = comparator time minus candidate time. Time estimates are conditional on the pair both finishing all six rides. Failures are never assigned zero time or silently removed from all-attempt counts.

| Comparison | Both complete n | Mean saving, min | 95% 7-day block interval | Candidate faster / equal / slower |
|---|---:|---:|---|---|
| D0−R (primary) | 118 | **−6.356** | [−13.730, +0.357] | 35 / 27 / 56 |
| D0−C | 119 | −2.815 | [−6.881, +0.935] | 11 / 84 / 24 |
| D0−S | 114 | −1.360 | [−5.509, +2.248] | 43 / 28 / 43 |
| F−D0 | 105 | +15.476 | [+6.886, +23.384] | 63 / 9 / 33 |
| F−R | 106 | +8.066 | [+1.068, +13.929] | 53 / 17 / 36 |
| S−R | 119 | −5.126 | [−11.639, +1.106] | 34 / 35 / 50 |

| Policy | Completed / 165 | Closed on arrival | No fresh arrival post | Completion after window |
|---|---:|---:|---:|---:|
| F | 120 | 43 | 1 | 1 |
| D0 | 126 | 36 | 1 | 2 |
| C | 126 | 35 | 1 | 3 |
| R | 128 | 34 | 1 | 2 |
| S | 123 | 41 | 1 | 0 |

For D0/R, both completed 118 dates, D0 alone 8, R alone 10, and neither 29. In that same order (both / first policy alone / second policy alone / neither), D0/C counts are 119/7/7/32; D0/S: 114/12/9/30; F/D0: 105/15/21/24. More completions do not by themselves establish a time-efficient improvement, especially when the successful dates differ.

F and D0 average 439.429/423.952 minutes on their 105 common dates; D0 and R average 429.407/435.763 minutes on their 118 common dates. Do not compare these different conditional means as if they describe one cohort. On the 95 dates all five finish, mean times are F: 440.474, D0: 424.684, C: 427.474, R: 431.000, and S: 424.000 minutes. S's slightly lower mean on that restricted subset is not the primary pairwise result and does not establish a general winner.

Both IID-date and moving-block percentile intervals use 5,000 resamples. The block method samples overlapping noncircular seven-date blocks, concatenates and truncates to the original date count, retaining joint-success masks. Empty-success resamples would be undefined, never zero. The IID seed is 20261019; the block seed is the derived value 20261026. R's IID interval is [−12.119, −0.541], whereas the predeclared temporal-dependence-aware block interval crosses zero. The inferential conclusion uses the block interval. These intervals omit input/model/selection uncertainty and longer temporal dependence; only R versus D0 was primary, with all other comparisons exploratory. An interval crossing zero is not evidence of equivalence.

## 6. Shared-input sensitivity

| Configuration | R/D0 paired n | D0−R minutes | 95% 7-day block interval | D0 / R completions, each / 165 |
|---|---:|---:|---|---|
| Uniform 10/10 | 118 | −6.356 | [−13.730, +0.357] | 126 / 128 |
| Uniform 5/5 | 139 | −2.374 | [−6.455, +1.836] | 145 / 147 |
| Uniform 15/15 | 97 | +1.495 | [−3.654, +7.150] | 112 / 108 |
| Illustrative nonuniform | 124 | −2.218 | [−7.415, +1.945] | 130 / 129 |
| Illustrative walking ×0.8 | 128 | −2.331 | [−7.483, +2.701] | 138 / 136 |
| Illustrative walking ×1.2 | 110 | −3.598 | [−8.358, +1.669] | 122 / 119 |

All 18 candidate-versus-D0 block intervals across three candidates and six configurations cross zero. The positive R mean under 15/15 comes with four fewer completions and a wide interval. It cannot be selected as proof of superiority. These are correlated sensitivity analyses on the same dates, not independent replications or measured walking scenarios.

## 7. Post-result explanation, not further tuning

The [rollout-error audit](diagnostics/rollout_error_audit.md) examines states actually reached by R. It clones each state, forces either R's next action or the contemporaneous D0 action, then follows the same D0 policy on both branches under real replay scoring. At each simulated decision, D0 only receives records available by that simulated time; later records are reserved for subsequent replay outcomes and observations. Diagnostic results never feed back into the original planner. Choices, eight scenario IDs and action scores were reproduced exactly from frozen traces; no candidate was changed.

Of 805 replans, 154 had only one remaining ride, leaving 651 choice states from 164 dates. R differed from D0 at 230 states. Of these, both counterfactual continuations completed at 175 states; only the R-first branch completed at 14, only the D0-first branch at 12, and neither at 29. Among the 175 comparable changes, the model predicted an 8.719-minute average saving, while the realized conditional mean was −3.686 minutes; favorable/tied/unfavorable counts were 71/19/85. Predicted-versus-realized gain correlation was 0.0296, and mean absolute gain error was 25.274 minutes.

This supports a diagnosis of poor realized action-value discrimination for the current scenario adaptation. It does not show that all rollout is ineffective, establish the causal source of the error, or identify the true conditional expectation from one realized day. States are selected by R's trajectory, and states within a date overlap and are correlated; these gains cannot be summed into trip savings or treated as independent visitors. The two forced-action branches both follow D0 afterward, so this is not a comparison of complete R and D0 policies.

A counting-only rescore recorded 397,144 template queries with 17,444 imputations (4.39%): 4,927 for missing observations and 12,517 for historical closures, with no beyond-midnight query. This is a repeated computational query fraction, not a raw missingness rate or causal decomposition of loss. The model's imputation/reopening assumptions remain plausible limitations, not proven sole causes.

Mean online replanning wall-clock time per attempted main-setting day was D0: 0.000584 s, C: 0.000582 s, R: 0.022215 s, and S: 0.016827 s. It excludes the common initial search, was measured during parallel execution, and is not pure CPU time or phone/network latency. Adding recorded planning time changes the primary saving only to −6.356303 minutes. Computation overhead cannot explain the observed minute-scale gap.

## 8. Verification, deliverables and decision

The engine's 12 tests passed, including legacy parity, tie/closure handling, information timing, training-only scenarios, deterministic continuation and a constructed feedback toy. Toy performance is not empirical evidence. The independent verifier does not import the engine, runner or summarizer; it checks 6,200 study policy-day records, 35,082 raw-source arrivals, 23,268 decision snapshots and 10,416 training-only scenario decisions. It confirms 330 legacy outcomes, 31 preserved artifact hashes, 10 evaluation-lock hashes, selection and all summary means/counts. Primary IID/block intervals are independently recomputed for seven analyzed folders; secondary-pair intervals are not independently recalculated. QA PASS certifies integrity, not a policy win or real-input validity.

Three [standalone figures](figures/README.md) are supplied in PNG/SVG/PDF and visually inspected. Daily CSVs, full decision traces, summaries, locks, source provenance, diagnostic scripts and a derived-evidence bundle support review. The 6,200 records comprise 920 validation, 330 reference, 825 main evaluation and 4,125 sensitivity records; they are not 6,200 independent trials.

**Decision:** retain D0; do not promote R/C/S as superior. A defensible next hypothesis is improved action-value calibration using earlier chronological training/validation states, observation age/trends and reliable closure information. Check next-action ranking and whole-trip minutes, not forecast MAE alone. Any new model should be frozen before genuinely unused evaluation dates. Shared input repairs must apply equally to all policies. These follow-ups are proposed, not implemented findings; no extra parameter search was conducted to turn this evaluation positive.

The approved next deliverable is the midterm presentation. It can honestly show the existing fixed-versus-dynamic result, the proposed mechanism, its negative evaluation and the next hypothesis. A new-method performance advantage and actual visitor benefit remain unestablished.

## References and credit

Primary-method sources and exact implementation boundaries are documented in the [theory audit](../../writing/research/parkplan-algorithm-first-principles-2026-10-19.md):

1. Bertsekas, D. P., Tsitsiklis, J. N., & Wu, C. (1997). Rollout algorithms for combinatorial optimization. *Journal of Heuristics, 3*, 245–262. [Author PDF](https://www.mit.edu/~jnt/Papers/J066-97-rollout.pdf).
2. Bertsekas, D. P., & Castañon, D. A. (1999). Rollout algorithms for stochastic scheduling problems. *Journal of Heuristics, 5*, 89–108. [Author PDF](https://web.mit.edu/dimitrib/www/quiz.pdf), especially Section 4 for stochastic base-policy rollout.
3. Goodson, J. C., Ohlmann, J. W., & Thomas, B. W. (2013). Rollout policies for dynamic solutions to the multivehicle routing problem with stochastic demand and duration limits. *Operations Research, 61*(1), 138–154. [Journal record](https://doi.org/10.1287/opre.1120.1127); [author manuscript](https://justin-goodson.com/papers/GoodsonRolloutVRPSDL.pdf).
4. Brown, D. B., Smith, J. E., & Sun, P. (2010). Information relaxations and duality in stochastic dynamic programs. *Operations Research, 58*(4-part-1), 785–801. [Journal record](https://doi.org/10.1287/opre.1090.0796). Official abstract consulted for the nonanticipativity distinction; its dual-bound method was not implemented.
5. Elmachtoub, A. N., & Grigas, P. (2022 issue; first published online 2021). Smart “Predict, then Optimize.” *Management Science, 68*(1), 9–26. [Journal record](https://doi.org/10.1287/mnsc.2020.3922). The decision-focused evaluation motivation is used here, not an implementation of SPO+ or its guarantees.

TouringPlans data license terms: You're free to use these data however you see fit, subject to the following: 1) Any publications or redistributions credit TouringPlans.com clearly at the beginning of those publications or distributions. 2) Any redistributions include these license terms. Raw source archives/CSV bulk are excluded from the deliverable.
