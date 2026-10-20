# TouringPlans.com credit — historical park-window sensitivity

Wait data: [TouringPlans/DisneyAnimalKingdomWaitTimes](https://github.com/TouringPlans/DisneyAnimalKingdomWaitTimes), pinned commit `933161b8bebb7cd50e0d54bcb3578484875487fa`. Historical public-hours listings: TouringPlans date pages, recorded in [hours CSV](../../data/verified_inputs/historical_park_hours.csv). No raw wait-time CSV is redistributed here.

Source wait-data license terms:

> You're free to use these data however you see fit, subject to the following:
>
> 1) Any publications or redistributions credit TouringPlans.com clearly at the beginning of those publications or distributions
>
> 2) Any redistributions include these license terms

## What this new step answers

The original route pilot arbitrarily ended every day at 17:00. We retrieved date-specific historical public-hours listings and tested how the completion window affects that pilot. **This is a source-specific sensitivity experiment, not a more accurate real-visitor trial and not a new route optimization algorithm.** The tested policies remain simple fixed, replan-after-each-ride, and a provisional 10-minute predicted-improvement switching rule. None implements KOWCPI or a confidence-triggered ParkPlan-S policy.

## Verified inputs and remaining assumptions

- All **165** later test dates, 2018-07-26–2019-01-06, have extracted TouringPlans normal public park hours. Each fetched page's full weekday/date heading matches its CSV date. Early-entry Extra Magic Hours are excluded. URLs, retrieval date, response hashes and numeric opening/closing times are retained. CSV SHA-256: `599b375a726567b63550826a236fac6877b1fb866375f145aa5bfa3ed36a8f27`.
- These are **secondary-source historical schedule listings**, not Disney's actual operating logs. Independent spot checks of ten dates found seven agreements and three conflicts with WDWinfo calendars. Both versions are retained. The alternate-schedule scenario substitutes WDWinfo's closing time on **2018-07-26, 2018-08-26 and 2018-12-24 only**. It is not a bound on all possible schedule errors. See [source research](../../writing/research/parkplan-input-sources-2026-10-14.md).
- Start remains **10:00 US Eastern**, after all listed public opening times. Every walking leg and every ride service still takes an **artificial 10 minutes**. The synthetic gate, absence of a spatial path matrix, same six rides and as-of maximum-15-minute posted-wait rule are unchanged. Fresh closure or missing/stale data still causes immediate failure; there is no closure recovery.
- A successful route must finish every ride **by the scenario's deadline**. For the historical scenario this is the listed park close, a conservative modeling rule. Actual queue entry can sometimes occur before closing with ride completion afterward. Conversely, individual rides can close before the park. Complete per-ride operating windows remain unavailable. Thus neither direction of realism error is resolved.
- For a controlled comparison, **both** new scenarios learn the same 10:00–24:00 train-only time-bin curves from the first **385** raw-common dates. The existing policy functions are reused unchanged. The frequent-replan baseline can also change to a lexicographically selected tied-best suffix; a final stronger baseline should retain the incumbent on equal predicted cost so arbitrary tie swaps do not inflate claimed stability gains. The initial pilot trained only to 17:00; consequently this new 17:00 control is not byte-identical to its original 45/63/55 completion counts. The extended curve is the only forecast change and is shared by all scenarios/policies.
- Changing the deadline does not change route scoring; it changes when a route must stop and whether it completes. These are previously examined exploratory test dates, **not a pristine final holdout**. No threshold was tuned in this experiment.

## Results over all 165 attempted dates

| Completion deadline | Fixed successes | Replan successes | Threshold-10 successes |
|---|---:|---:|---:|
| 17:00 control, extended training grid | 45 | 64 | 54 |
| TouringPlans-listed historical park close | **120** | **126** | **128** |
| Same, substituting the three known alternate closes | 120 | 126 | 128 |

For the historical park-close scenario, failures were:

| Policy | Fresh closure | Finished after deadline | No fresh posted wait | Mean route changes, all attempts |
|---|---:|---:|---:|---:|
| Fixed | 43 | 1 | 1 | 0.00 |
| Replan | 36 | 2 | 1 | 2.43 |
| Threshold-10 | 35 | 1 | 1 | 1.05 |

**The large jump in completions shows that the arbitrary 17:00 window mattered. It does not show that our algorithm suddenly improved.** The known-calendar alternatives leave all reported aggregate metrics unchanged here; untested schedule disagreements and individual ride hours could still matter.

## Paired posted-wait proxy time, with explicit conditioning

Fixed vs replan: both complete on **105** days; fixed only on 15, replan only on 21, neither on 24. On those 105 shared-success days, fixed minus replan elapsed proxy time averages **+15.48 minutes**, median **10**, exploratory date-bootstrap 95% interval **+9.10 to +22.00**. Replan is faster on 63 days, tied on 9, slower on 33. This interval conditions on a success-selected subset and does not account for potential serial correlation across dates or uncertain model inputs. It is **not evidence of measured visitor savings**.

Fixed vs threshold-10 has a different shared-success subset:109 days and mean **+9.04 minutes**, interval **+3.53 to +14.63**. Do not compare the two paired means as if their days were identical.

### A fairer illustration of the time-versus-changes trade-off

On the **same 101 dates when all three rules complete**:

| Policy | Mean elapsed proxy minutes | Mean fixed-minus-policy minutes | Mean route changes |
|---|---:|---:|---:|
| Fixed | 440.50 | 0.00 | 0.00 |
| Replan after each ride | 424.26 | 16.24 | 2.39 |
| Provisional threshold-10 | 431.34 | 9.16 | 0.86 |

The threshold rule changes the remaining order less often, but takes about **7.08 more proxy minutes** than frequent replanning on this shared subset. This is the research trade-off we need to explain: **fewer changes are not automatically a time improvement.** A future uncertainty-aware rule must beat an appropriate simple baseline rather than merely look more complicated. The 101-day comparison is still selected on completion, not an unconditional effect.

Every successful route has exactly60 modeled walking and60 service minutes, so elapsed differences are entirely from posted-wait values at different arrival times. We still cannot claim reduced spatial walking, backtracking, cognitive burden, or real queue duration.

## Reproduce and inspect

```bash
python3 experiments/hours_replay_pilot/run.py
```

Requires the SHA-256-pinned archive at `/tmp/parkplan-ak-933161b.tar.gz`, the stable hours CSV and independent spot-check CSV. Scripts use Python standard library only. Outputs: `parameters.json`, `train_curves.json`, `per_day.csv`, `summary.json`, and `first_test_day_trace.json`. The trace date is the predetermined first test date, not selected for a favorable result. The original pilot files remain unchanged. In `per_day.csv`, `public_close` retains the TouringPlans-listed value even in the alternate scenario; `deadline_minutes` and `deadline_source` record the deadline actually used.

Checks include source hash/date validation, no date dropped for missing hours, all-day/policy accounting, completed-six-ride time arithmetic, as-of chronology, deadline satisfaction and unchanged input hashes. Independent read-only QA and rerun findings are recorded in `QA.md`.

## What this changes in the project

We now have a better documented **benchmark input** and evidence about sensitivity, not a final ParkPlan-S improvement. Before the final study: establish defensible path/service assumptions and ride-specific closing behavior; freeze a shared comparison protocol; evaluate forecast errors and an uncertainty-aware switching rule on declared evaluation periods; report minutes, all-attempt completion and route changes together. Do not relabel the source-extracted historical schedule as fully verified actual operations.
