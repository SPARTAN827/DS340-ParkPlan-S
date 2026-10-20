**Data credit: TouringPlans.com — historical Animal Kingdom posted-wait records and published park-hour listings.**

# Frozen study design — 2026-10-19, before new candidate results

Status: user authorized algorithm research; no candidate validation/evaluation outcome inspected when this protocol was written. Prior165 evaluation dates and baseline outputs HAVE been inspected in earlier work and baseline diagnostics. This is a new, pre-specified **retrospective exploratory comparison**, not a pristine confirmatory holdout.

## Question and first-principles hypothesis

Minimize total time to finish the same six rides. Current D0 enumerates every remaining order under a single predicted waiting trajectory, executes one ride, and replans. Hypothesis: choosing the next ride by averaging the cost of **subsequently following D0 with updated observations** over correlated historical-day waiting scenarios may improve next-action decisions compared with certainty-equivalent D0. This is a policy-rollout adaptation, not a newly invented algorithm or a guarantee of improvement.

State includes current location/time, remaining rides, incumbent order and available observations. Action is next ride. Cost is walking + posted-wait proxy + service minutes. No change-count penalty, satisfaction or money objective. Each hypothetical continuation only observes its simulated current/past; a scenario-wise hindsight-optimal tail is forbidden.

## Data and split

- Same archive commit933161b8bebb7cd50e0d54bcb3578484875487fa, SHA25623eca800b048aecd4b3a2469e78f63f24f64637eb785c8401386e219a177f812; loader preserves legacy same-timestamp file-order handling.
-550 raw-common dates, sorted: first270 fit; next115 validation; last165 evaluation. These counts must match the old385/165 boundary. No outcome-dependent date exclusions. Exact dates are emitted by prepare.py before candidate evaluation.
- Validation curves/scenarios use first270 dates only; evaluation curves/scenarios refit on preceding385 after candidate settings are frozen. No evaluation-day future stream or completed outcome enters a decision/scenario pool.
- Try obtaining public source-listed validation park hours without changing old source files. Failed retrieval dates retain a declared20:00 analysis deadline (not claimed as real hours), identically all policies; exact status/provenance is stored BEFORE validation. Evaluation reuses all165 existing published-hours records unchanged.
- Fresh as-of posted maximum age15minutes; no interpolation in REAL outcome scoring. Predicted model paths may impute historical missing/closed posts using fitted time-bin curves; these are simulated assumptions, not observed actual queues.

## Main candidate and controls

All methods share one D0-generated initial order at10:00 (including the same first ride), input config and execution rules. Fixed does not change that order. No forced order change if a recalculation retains it.

-F `fixed`: optimized once, then fixed.
-D0 `dynamic`: existing60-minute-decay point forecast, exhaustive order scoring, incumbent preserved on ties; no finite candidate retains incumbent, matching original behavior.
-C `calibrated`: same planner with decay selected from15/30/60/120 on validation, and60 explicitly retained as a candidate. This is a simple forecast-control, not automatically the proposed winner.
-R `rollout`:8 deterministic nearest-current-snapshot training-day scenarios (no K tuning), sharing one whole historical date across rides/times. Anchor each scenario to available current waits with60-minute decaying offsets. For each admissible next action, simulate it then use D0 at each later completion; minimize mean remaining time over the SAME8 scenarios. Ties prefer D0 action. Tail is initialized from D0's current order with the forced action moved first.
-S `scenario_open_loop`: identical scenario model, but choose ONE shared full order minimizing mean model cost; it may not select a different clairvoyant order per scenario. Replan again on the next REAL completion. This isolates the contribution of simulated future feedback from distribution-aware route evaluation.

Historical scenarios model waiting variability, not future ride closure probability. Historical missing/closed samples are curve-imputed. Currently known closures retain their observed timestamp until its15-minute freshness expires; thereafter the model uses prior/history, as with D0. No arbitrary failed-scenario time penalties or survivor-only means. Any nonfinite scenario cost makes that candidate unsupported; if all unsupported, fall back to D0 and log. Predictive rollouts may extrapolate after the fitted grid and do not enforce published close as a new constraint (same limitation as D0); real execution enforces the shared deadline.

## Configuration and robustness

Primary reference: historical listed park-close completion window; uniform10-minute walking legs and10-minute service. This deliberately preserves exact old comparisons; it is **synthetic geometry**, not a realistic park-time claim.

Predeclared common-model sensitivities after main evaluation: uniform5/5 and15/15 walk/service; a clearly labeled nonuniform illustrative travel-time graph with gate/ride nodes and ride-specific nominal service labels, plus0.8x/1.2x graph walking scale if main findings warrant. The graph is a structural sensitivity only, not a measured or fully sourced2018 matrix. All compared policies receive each identical config; changes in shared inputs are not algorithm innovations. Do not label a geometry-sensitive advantage as proven real-park benefit.

## Selection and acceptance rules (before evaluation)

Validation records all decay candidates, D0, R and S. For decay selection use the fixed common-success subset across ALL four decay variants plus D0, disclose every attempt, and require candidate success count not lower than D0. Select the eligible decay with lowest mean joint-success time; ties prefer60 then simpler numerical order. If no improvement or subset empty, retain60.

The primary research hypothesis remains R versus D0, with S as the feedback ablation. Before evaluation, record a validation-only **within-replay candidate recommendation**, not real deployment superiority, among D0, selected C and R using their common-success times and requiring no fewer completions than D0. Keep D0 if no eligible positive saving. Equal or higher success counts can still exchange different failed dates, so all discordances must be shown. This recommendation is frozen to a hashed selection.json before evaluating165 dates; do not relabel the evaluation winner as preselected. S remains an ablation even if it wins.

For each evaluation comparison: report BOTH-success n, means/median of comparator-minus-candidate minutes, faster/tied/slower counts, date-level uncertainty, plus all-attempt completion and failure reasons, paired completion discordances and three/main-policy common-success summaries. A positive paired-success result with more failures does not establish a preferable overall method. Even positive time and completion counts do not identify an all-user causal average.

Compute ordinary paired date bootstrap and7-consecutive-date moving-block bootstrap (sample full date records including joint-success masks, not ride rows). Use fixed seed20261019 and5000 resamples, two-sided95% percentile intervals. Moving blocks overlap, do not wrap, are sampled uniformly from valid7-date starts, concatenated and truncated to the original date count. Zero-joint-success samples are counted and omitted as undefined, never replaced by zero minutes. A conditional time advantage is statistically supported within this exploratory model only if the7-day block interval is strictly positive; otherwise describe the observed mean without claiming clear superiority. This interval does not include input/model/selection uncertainty, season shifts or longer-than7-day dependence. R versusD0 is the one primary hypothesis; other comparisons are exploratory. No guaranteed minimum benefit, no selective day dropping.

Scenario matching is frozen as mean squared difference over currently observed nonnegative ride waits, each divided by max(15,that ride's training median at current time). Current missing/closed rides contribute no distance term. Historical current missing/closed states use that same training curve. Equal distances tie by date; choose min(8,number of training dates), without future-coverage filtering. Model snapshots use a5-minute issuance-relative grid, never rounding observations forward.

Record decision compute time and total planning overhead on this machine, separately from modeled visitor minutes; show a time-overhead sensitivity if relevant, not a new user objective. CPU milliseconds are not measured phone/app latency.

## Integrity and outputs

- Verify the frozen reference predictor/replayer reproduces legacy165 fixed and dynamic outcomes before claiming new results; preserve31 old-artifact hashes.
- Tests: no-future-information interfaces, closures/ties, deterministic and finite-horizon cases, nonanticipative continuation, identical scenarios across actions, correct time arithmetic, common initial route, same-six completion and split boundary.
- Log exact config/source/code hashes, scenario IDs/action costs for decision traces, all daily outcomes, selection and negative findings.
- Independent raw-result verifier must not merely call the analysis summarizer. Test parser/time accounting and recompute key outcomes separately.
- Deliver Chinese research explanation, English technical report, reproducible scripts, derived results and standalone figures. No PPT or external publication in this stage.

License terms: You're free to use these data however you see fit, subject to the following:1) Any publications or redistributions credit TouringPlans.com clearly at the beginning of those publications or distributions.2) Any redistributions include these license terms. No source archive/raw bulk CSV is included in a deliverable.
