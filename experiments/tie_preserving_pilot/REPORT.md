**Data credit: TouringPlans.com — Disney Animal Kingdom wait-time archive and published historical park-hour listings.** Derived results only; source license terms are in `SOURCE-CREDIT.txt`.

# Tie-preserving comparator check — 2026-10-14

## Bottom line

The stronger frequent-replanning comparator is implemented: **keep the current remaining order unless a different candidate has a strictly lower predicted finishing time**, with a 1e-9-minute numerical tolerance. This is not the proposed uncertainty-aware ParkPlan-S rule.

**All 165 new daily records match the old frequent-replanning records in every field except the policy name.** Among 800 replanning decisions on the new trajectories, no different tied-cost candidate required retaining the incumbent. Consequently, this correction changes neither completion, route order, elapsed time nor route-change counts in this particular scenario. It closes a comparator-design gap; it does not establish a performance improvement or guarantee that ties cannot matter in other scenarios.

## What was preserved and what was computed

- All original experiment scripts/results, the v2 briefing and the v2 ZIP remain unchanged. `preserved_artifacts_sha256.json` records 31 protected artifact hashes.
- Reused the 495 completed baseline rows for fixed/replan/threshold10 under `historical_park_close_completion`; did not rerun them.
- Reused the existing 56-slot-per-ride train-only curves; did not refit, tune a threshold, change data, or change eligibility.
- Computed only 165 new `replan_keep_ties` policy-days, on the already-examined dates 2018-07-26 to 2019-01-06.
- `replay.py` here is a frozen copy of `../replay_pilot/replay.py`, with only a two-line conditional for the new policy plus a full-precision gain field in decision traces. The targeted tests verify that exact source difference. Original files are not edited.
- Candidate generation and initial-route tie breaking remain unchanged. If the incumbent has infinite predicted cost and a finite candidate exists, the new rule can switch. No available finite candidate means no switch.

## Results

All-attempt completions: fixed **120/165**, original replan **126/165**, tie-preserving replan **126/165**, threshold10 **128/165**. The new rule has 36 failures on a fresh closure, two on completion after the deadline, and one on missing fresh posted information; identical to the original replan. Mean changes across all attempts: fixed 0, both replan variants 2.430, threshold10 1.048.

On the **same 101 dates when all four policies complete**:

| Policy | Mean elapsed proxy minutes | Mean changes of remaining order |
|---|---:|---:|
| Fixed initial order | 440.50 | 0.000 |
| Original frequent replan | 424.26 | 2.386 |
| Replan, retaining incumbent on ties | 424.26 | 2.386 |
| Provisional 10-minute threshold | 431.34 | 0.861 |

The threshold policy makes **1.525 fewer changes**, but takes **7.079 more modeled minutes**, versus either replan comparator on these 101 dates. The prior illustrative trade-off is therefore unchanged by tie handling. These common-success means are conditional on completion, not an average effect across all attempts.

The new and old replan policies both finish on the same 126 dates, both fail on the same 39, and have zero elapsed-time difference on all 126 paired successes. Fixed versus the new replan has 105 paired successes and mean fixed-minus-replan 15.476 minutes, matching the old result. New replan versus threshold has 117 paired successes, with threshold 7.692 minutes slower on average; **that is a different subset from the 101-day table** and must not be mixed with it.

## Verification and reproducibility

```bash
python3 experiments/tie_preserving_pilot/test_ties.py
python3 experiments/tie_preserving_pilot/run.py
python3 experiments/tie_preserving_pilot/verify.py
```

The runner needs the SHA-256-pinned wait archive at `/tmp/parkplan-ak-933161b.tar.gz`, the unchanged original artifact paths, and the sourced hours CSV. Use `run.py`, not the copied core's inherited standalone CLI. The source has not been repackaged here. Dependencies are Python standard library only. The supplemental kit is an overlay for the existing workspace/v2 evidence kit, not a new standalone raw-data distribution.

Nine targeted regression tests cover tied costs, numerical tolerance, small genuine gains, unavailable/infinite predictions, unchanged legacy behavior and the exact copy delta. `verify.py` does not import the simulator: it compares every non-policy CSV field, independently recomputes common-success means, parses raw source rows, verifies visit chronology/as-of values, reconstructs decisions and totals, and checks old artifact hashes. Counts and outcome are in `verification.json`. This is a separate checking method within this session, not an external reviewer or a visitor trial. No completed old experiment was rerun.

## Limits and next action

No new claim about true waits, walking distance, physical feasibility or visitor satisfaction follows. Uniform artificial 10-minute walk and service legs, posted-wait proxies, published park-close deadlines, no verified ride-level hours, and fail-on-closure behavior remain. Same-timestamp posted conflicts still use the legacy file-order rule; that input assumption was not fixed in this audit. The final uncertainty-aware rule and KOWCPI implementation remain pending. These dates are exploratory, not a fresh final holdout.

Use the tie-preserving comparator in future comparisons. Next, define shared walking/service/closure scenarios and a route-level reliability test; freeze evaluation and a time-versus-changes success criterion before claiming a final improvement. Keep the professor questions from v2: whether historical simulation suffices, what trade-off counts as success, and how much original parent-method implementation is required.
