**Data credit: TouringPlans.com — Disney Animal Kingdom wait-time archive and listed historical park hours.** This audit reports derived statistics only. Source data terms:

> You're free to use these data however you see fit, subject to the following:
>
> 1) Any publications or redistributions credit TouringPlans.com clearly at the beginning of those publications or distributions
>
> 2) Any redistributions include these license terms

# Independent QA — 2026-10-14

**Result: no blocking arithmetic, pairing, or observed lookahead defect found.** This verifies implementation and reproducibility, not historical schedule truth or real visitor benefits. The reviewer did not change either experiment script.

## Checks completed

- Read `run.py` and reused `../replay_pilot/replay.py`. Source loading and train-only profile fitting occur once with the same 10:00–24:00 grid for all scenarios. The per-date deadline is set before every policy run. `historical()` uses profile length, so later `END` mutation does not truncate the profile. Serial execution is consistent; this global-state design is not thread-safe.
- Recomputed aggregate counts, failure reasons, completed-ride averages, route-change averages, paired mean/median/sign counts, four-way completion counts, and three-policy common-success metrics directly from all **1,485 CSV rows** (3 scenarios × 165 dates × 3 policies), without calling the experiment's summarizer.
- All successful rows visit six distinct rides, satisfy elapsed = posted-wait proxy + walking + service, have 60 walking and 60 service minutes, and finish by the configured deadline.
- All **163 successful policy-days** in the new 17:00 control remain successful under the longer listed-close window, with identical elapsed time, visit order and route-change counts. This is the expected deadline-extension invariant.
- The three known alternate-calendar dates change deadline metadata but no realized policy outcome or aggregate result in this run. That checks only these three alternatives, not all possible schedule errors.
- Independently parsed raw source CSVs and verified all **18 visit events** in the 9 first-test-day traces against the latest available posted observation and the 15-minute freshness rule.
- Independently reran `python3 -B experiments/hours_replay_pilot/run.py --output /tmp/parkplan-hours-qa`. All five generated artifacts were **byte-identical**: parameters, train curves, per-day CSV, summary and first-test-day traces. The seeded bootstrap outputs therefore also reproduce.

## Confirmed headline arithmetic

| Scenario | Fixed / replan / threshold completions | Three-policy common successes |
|---|---:|---:|
| New 17:00 control, extended profile | 45 / 64 / 54 | 35 |
| TouringPlans-listed closing times | 120 / 126 / 128 | 101 |
| Three known alternate closing times | 120 / 126 / 128 | 101 |

For the listed-close scenario, fixed vs replan has **105** jointly complete days, **+15.476** mean posted-wait proxy minutes (fixed minus replan), and completion table 105 both / 15 fixed-only / 21 replan-only / 24 neither. On the same **101** days where all three finish, replan changes the remaining order **2.386** times on average and threshold10 changes it **0.861** times; threshold10 takes **7.079 more modeled minutes** than replan. Thus fewer changes are not free time savings.

## Interpretation boundaries

- This is **source-specific completion-window sensitivity**, not an improved route-generation algorithm: the deadline does not enter candidate-route scoring; it controls stopping/success. Extending the training profile also changes the control relative to the first pilot, so use the new control for this comparison.
- No test-date future wait enters route decisions: source histories are queried with `asof(now)`, and arrival observations are used only to realize proxy outcomes. The dates were already explored in earlier pilots; this is not a fresh confirmatory holdout.
- The source hours are secondary-source listings with known conflicts; park hours are not individual attraction operating hours. Successful simulated completion does not establish a physically feasible historical visit.
- Uniform artificial walking/service and posted-wait proxies remain. Pairwise/common-success results condition on outcomes; they are not unconditional effects across all attempted dates. Date-bootstrap intervals do not address serial date dependence, source errors or modeling uncertainty.
- `threshold10` is an exploratory deterministic margin, **not KOWCPI** or a calibrated probability of savings. Route-change count is not measured visitor annoyance or satisfaction.
- In the alternate scenario, CSV `public_open/public_close` retain the primary-source listing. Use **`deadline_minutes` and `deadline_source`** to identify the actual alternate deadline applied; do not read `public_close` alone as that scenario's deadline.

Input hours SHA-256: `599b375a726567b63550826a236fac6877b1fb866375f145aa5bfa3ed36a8f27`.

Reproduced summary SHA-256: `4204bdccdd880194360be66f14e1d36e1ffb40839fec32aa5366aa50a3539429`.

Reproduced per-day CSV SHA-256: `d7d0c40b5882a4efcd85c86bd3ff958cb6589272cf152713b209d17b38a5009d`.
