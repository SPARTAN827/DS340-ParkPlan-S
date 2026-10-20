**TouringPlans.com — Disney Animal Kingdom attraction wait-time data.** Source: [TouringPlans/DisneyAnimalKingdomWaitTimes](https://github.com/TouringPlans/DisneyAnimalKingdomWaitTimes), pinned commit `933161b8bebb7cd50e0d54bcb3578484875487fa` (archive SHA-256 in `parameters.json`). This pilot does not redistribute the source CSV files.

Source `LICENSE.md` terms, reproduced verbatim:

> You're free to use these data however you see fit, subject to the following:
>
> 1) Any publications or redistributions credit TouringPlans.com clearly at the beginning of those publications or distributions
>
> 2) Any redistributions include these license terms

# ParkPlan-S: limited posted-wait replay smoke pilot

**Status:** Exploratory implementation check, **not** a final ParkPlan-S evaluation and **not** measured visitor time savings. Run on 2026-10-13. No outcome was selected to make the dynamic policy look positive.

## Why this pilot exists

The six fixed attractions are Kilimanjaro Safaris (`AK07`), Expedition Everest (`AK11`), Kali River Rapids (`AK14`), Dinosaur (`AK18`), Na'Vi River Journey (`AK85`), and Avatar: Flight of Passage (`AK86`). The project asks whether new posted-wait observations justify changing an itinerary. ADAPT motivates recalculating candidate routes as information changes; Shiri et al. motivate the fixed-route versus iterative-route comparison and a provisional switching threshold. This code **does not** reproduce ADAPT's ACS/IACS or Shiri et al.'s original algorithms. KOWCPI's calibrated prediction intervals and coverage-aware decision rule are **not implemented**. The bootstrap interval below is sampling uncertainty for the paired mean, not a KOWCPI prediction interval.

## Exact scenario and leakage boundary

- Population: all **550** dates with any CSV rows for each of the six rides. Chronological train/test split: first **385** dates, 2017-05-26–2018-07-25, to learn wait curves; final **165** dates, 2018-07-26–2019-01-06, attempted as test days. No filtering by a policy's success, by fresh-wait coverage, or by observed savings. Some raw-common dates lack usable contemporaneous waits and can fail.
- Every policy begins at a **synthetic gate** at 10:00 Eastern and must complete **the same six rides** by 17:00. This is an artificial **analysis window**, **not historical park opening hours**. No actual park-hours or walking graph is supplied by the source archive. In the base scenario, every gate-to-ride and ride-to-ride leg is assumed to take **10 minutes**, and every ride's non-wait service takes **10 minutes**. Thus every successful six-ride day has 60 modeled walking and 60 service minutes. This is not a spatially realistic route optimizer; sequence differences arise from wait timing and closure timing only.
- Train-only forecast: per ride, take the median posted wait within each 15-minute time-of-day slot for each train day, then the median across train days. A missing slot inherits the nearest available train slot. At a decision, the latest posted wait no more than **15 minutes old** can shift future slot medians by its deviation from the current-slot median, decayed as `exp(-horizon / 60 minutes)` and floored at zero. A fresh `-999` closure makes a candidate immediate arrival infeasible; beyond the 15-minute state window, reopening is unknown and the train prior is used. No observations after the decision enter route scoring. **Both policies use the same forecast and same initial optimal permutation.** All six-ride permutations are enumerated (maximum 720), with deterministic lexicographic tie-breaks.
- `fixed`: follow the 10:00 initial permutation. `replan`: after each completed ride, rescore all permutations of the remaining rides and change suffix when the best order differs. `threshold10`: provisional alternative, change suffix only for ≥10 modeled minutes of predicted finish-time improvement. The threshold is not calibrated and is **not KOWCPI**.
- Realized *proxy* wait on arrival: last `SPOSTMIN >= 0` observed at or before arrival and at most 15 minutes old. A fresh `-999` means closed; absent fresh posted value means missing. A policy fails immediately on closure, stale/missing wait, arrival after 17:00, or completion after 17:00; it neither retries nor waits for reopening. `SACTMIN` (actual individual waits) is not used: those observations are sparse and cannot provide complete six-ride counterfactual journeys. Posted wait is a proxy and may over/understate actual queue time.
- The outcome `fixed elapsed minutes − dynamic elapsed minutes` is computed **only on dates where both complete all six**. Every attempted date is separately counted in completion and failure rates; a route never gets time-saving credit for skipping a ride. The paired-completion subset is selected by outcomes, so its mean is **not** an unconditional population effect. Date-resampled 10,000-bootstrap 95% intervals are conditional on that subset and are exploratory.

## Held-out results (10-minute walk per leg, 10-minute service per ride)

| Policy | Six-ride successes / all attempted | Success rate | Failures: after-window arrival / closure / after-window completion / no fresh post | Mean route changes over all attempts |
|---|---:|---:|---|---:|
| Fixed initial route | 45 / 165 | 27.3% | 9 / 36 / 74 / 1 | 0 |
| Replan after each ride | 63 / 165 | 38.2% | 5 / 20 / 76 / 1 | 2.35 |
| Provisional 10-minute switching threshold | 55 / 165 | 33.3% | 9 / 22 / 78 / 1 | 1.08 |

Full fixed-versus-replan completion table over **all 165** dates:

| Both complete | Fixed only | Replan only | Neither |
|---:|---:|---:|---:|
| 38 | 7 | 25 | 95 |

On the **38 jointly successful dates** (23.0% of all attempts), fixed minus replan elapsed proxy time averaged **+3.95 minutes**, median **0**, with date-bootstrap 95% interval **−4.34 to +12.24 minutes**. Replan was faster on 18 dates, tied on 5, and slower on 15. Because successful routes have identical assumed walking/service totals, the 3.95-minute difference is entirely from **posted-wait proxy values**, not walking gains. The interval crosses zero and the subset is small and selected: **this does not establish positive mean visitor savings**.

The provisional threshold policy had 38 paired-success dates versus fixed (7 fixed-only, 17 threshold-only, 103 neither), mean proxy difference **+7.63 minutes**, median **0**, bootstrap interval **−0.13 to +15.53 minutes**. It cannot be directly declared better than replan from these differently selected paired subsets.

## Assumption sensitivity

All three scenarios use the same 165 dates and train curves. The walking and service assumptions are changed *together*, not estimated from source data.

| Assumed walk + service (minutes each) | Fixed / replan completions | Paired completions | Mean fixed − replan proxy minutes | Conditional bootstrap 95% interval |
|---|---:|---:|---:|---:|
| 5 + 5 | 84 / 104 | 76 | +10.00 | +3.42 to +16.64 |
| **10 + 10** (base) | **45 / 63** | **38** | **+3.95** | **−4.34 to +12.24** |
| 15 + 15 | 24 / 29 | 19 | +5.79 | −3.68 to +15.53 |

The number of six-ride successes changes dramatically with unmeasured walking/service assumptions. A positive result in the most permissive 5+5 scenario does not rescue the base scenario or justify a real-world savings claim.

## One audited hand trace

`hand_trace.json` contains the first held-out day where both policies completed, the dynamic policy changed order, and the elapsed proxy times differed. This was selected **after** inspecting outcomes solely to illustrate arithmetic, not for inference. On 2018-08-17, both start with `AK14→AK85→AK11→AK86→AK07→AK18`. Fixed finishes with that order in **415 minutes**: 295 posted-wait proxy + 60 assumed walking + 60 assumed service. Replan changes its remaining order three times and completes `AK14→AK18→AK85→AK86→AK11→AK07` in **405 minutes**: 285 + 60 + 60. The illustrative proxy difference is **10 minutes**. The saved trace lists each arrival, latest posted timestamp and value, and route-change decision; assertions verify the arithmetic, six completions and that every used observation precedes arrival by no more than 15 minutes.

## Reproduce and next research gate

From the workspace root, with the pinned archive at `/tmp/parkplan-ak-933161b.tar.gz`:

```sh
python3 experiments/replay_pilot/replay.py
```

Outputs: `parameters.json`, `train_curves.json`, `per_day.csv` (one row per date/policy for the base scenario), `summary.json`, `sensitivity.json`, and `hand_trace.json`. The script checks the archive SHA-256 and uses only Python's standard library. The CSV contains policy summaries, **not** raw source waits. The source tarball must be obtained separately from the credited repository at the pinned commit.

Before claiming a final ParkPlan-S result: obtain defensible walking times, ride durations and historical operating windows; decide how to handle closure/reopening without artificially discarding feasible days; validate or calibrate posted-versus-actual wait error; then add a separately tested uncertainty-aware switching rule inspired by KOWCPI. The primary quantification remains **minutes saved per six-ride itinerary, paired on days both methods complete**, accompanied by completion rates and failures over **all attempted days**. Money savings cannot yet be inferred from this source.
