# TouringPlans.com data credit — posted-versus-actual wait audit

Source: [TouringPlans Animal Kingdom Wait Times](https://github.com/TouringPlans/DisneyAnimalKingdomWaitTimes), commit `933161b8bebb7cd50e0d54bcb3578484875487fa`. Source archive SHA-256: `23eca800b048aecd4b3a2469e78f63f24f64637eb785c8401386e219a177f812`. Only derived aggregates are distributed here; no raw user observations or inferred visitor journeys are exported.

Source license terms:

You're free to use these data however you see fit, subject to the following:

1) Any publications or redistributions credit TouringPlans.com clearly at the beginning of those publications or distributions

2) Any redistributions include these license terms

## Plain-language conclusion

We checked whether the number on the ride sign is a faithful measure of the wait a visitor actually experienced. It is not interchangeable with actual queue time. The six files contain **21,137 actual-user wait observations**, but **zero rows contain both a posted and actual wait**. The source explicitly says actual timestamps are queue-entry times, so we can instead compare each visitor's realized wait with the latest posted observation at or before their entry time (at most 10 minutes old). This is a retrospective proxy check, not a claim that realized waits were known to a planner at queue entry.

In the route pilot's 165 held-out dates and 10:00–17:00 analysis window, **887 matched observations** show a mean posted-minus-actual difference of **+7.54 minutes** and a mean absolute difference of **14.53 minutes**. The median signed difference is **8.00 minutes**. These are sample-level proxy errors, **not route savings**. They do not establish the error in a difference between two full routes: biases can cancel, accumulate, or differ by ride and time.

## What was verified

- Re-downloaded the public pinned archive on 2026-10-14 and verified its exact SHA-256. The [pinned README](https://github.com/TouringPlans/DisneyAnimalKingdomWaitTimes/blob/933161b8bebb7cd50e0d54bcb3578484875487fa/README.md) says `SACTMIN` is actual time in the queue and its `datetime` is when the visitor entered the queue. `SPOSTMIN` is the external posted wait; `-999` denotes unexpected closure. The source's example intentionally places posted and actual measurements on separate rows.

- Matched only a same-service-date posted observation at or before queue entry. We do not average the previous and next observation, even though the repository supplies a two-sided ±10-minute matching example. The primary audit uses a 10-minute freshness bound; 5 and 15 minutes are sensitivity checks.

- A fresh most-recent closure code blocks the match; we do not skip backward across it to an earlier open observation. If different posted values share the latest timestamp, that timestamp is ambiguous and the match is excluded rather than choosing a convenient value. No-prior, stale, closure and ambiguity exclusions sum exactly with accepted matches to the eligible actual sample count. The original values are retained without outlier trimming. Same timestamp matches assume the source timestamp represents information availability; no ingestion timestamps are available.

- The 550 common dates and chronological 385/165 split independently reproduce the existing route pilot. 10:00–17:00 is its arbitrary analysis window, not a claim about historical operating hours.

## Coverage and matched-sample counts (10-minute freshness)

| Scope | Actual samples | Matched samples | Mean posted − actual (min) | Mean absolute error (min) | Dates with ≥1 matched actual for all six |
|---|---:|---:|---:|---:|---:|
| All available per-ride dates | 21,137 | 19,650 | +7.434 | 12.806 | 120 |
| 550 six-ride common dates | 7,179 | 6,932 | +10.028 | 18.263 | 120 |
| 165 route test dates, all times | 2,139 | 2,079 | +7.342 | 16.091 | 36 |
| 165 route test dates, 10:00–17:00 | 916 | 887 | +7.536 | 14.534 | 4 |

A day with six independent actual observations is not a six-ride visitor itinerary. Users are not linked in this archive, and the six samples need not correspond to the route's arrival times.

## By attraction: route test dates, queue entry 10:00–17:00

| Ride | Actual samples | Matched | Mean posted − actual | MAE | Median signed error | Signed error p10 / p90 | Within ±10 min |
|---|---:|---:|---:|---:|---:|---:|---:|
| AK07 Kilimanjaro Safaris | 130 | 130 | +11.05 | 16.35 | 9.00 | -11.30 / 35.10 | 54/130 |
| AK11 Expedition Everest | 187 | 181 | +6.42 | 10.93 | 6.00 | -8.00 / 22.00 | 112/181 |
| AK14 Kali River Rapids | 81 | 78 | +5.35 | 13.22 | 6.00 | -14.00 / 24.00 | 40/78 |
| AK18 Dinosaur | 269 | 254 | +6.45 | 11.49 | 8.00 | -9.00 / 19.00 | 140/254 |
| AK85 Na'Vi River Journey | 79 | 78 | +12.87 | 19.23 | 8.00 | -9.00 / 42.50 | 33/78 |
| AK86 Avatar: Flight of Passage | 170 | 166 | +6.17 | 20.11 | 8.00 | -25.00 / 35.00 | 60/166 |

Pooled signs: 627 posted > actual; 25 equal; 235 posted < actual. Pooled actual range: 0–217 minutes. Absolute-error p90: 31.00 minutes. Date-balanced mean signed/absolute errors (each observed date has equal weight) are 6.93/14.64 minutes; pooled values instead give every observation equal weight.

Identical-row sensitivity: treating each identical ride/date/entry-time/actual-wait combination as one record leaves 836 matches, mean signed difference +7.60 minutes, and MAE 14.60 minutes. This is only a robustness check; without user identifiers we cannot determine whether repeated identical records represent duplicate records or different visitors.

## Freshness sensitivity: same held-out 10:00–17:00 window

| Latest prior posted age allowed | Matched | Mean posted − actual (min) | MAE (min) |
|---|---:|---:|---:|
| ≤5 min | 820 | +7.491 | 14.470 |
| ≤10 min | 887 | +7.536 | 14.534 |
| ≤15 min | 887 | +7.536 | 14.534 |

These are overlapping samples with different coverage, not independent experiments. Full distributions, match exclusions, per-ride counts, arithmetic sums and all scopes are recorded in `results.json`.

## Interpretation and limits

1. **A stronger claim is now possible:** we empirically checked the proxy against separate actual-user samples, rather than only assuming posted waits represent time spent. The posted-wait replay remains an exploratory historical simulation and should not be described as proven real visitor savings.

2. **No universal correction is justified.** The actual-user sample is sparse and self-selected, with unequal coverage across rides, dates and times. The archive contains no user ID, queue type, explicit treatment assignment, or complete visitor journeys. It cannot establish that the same bias holds at each simulated arrival, or represent all park visitors. Repeated identical actual date/time/value rows are counted and retained because without IDs we cannot distinguish duplicate records from different users.

3. **The timestamp question is resolved for pairing, not for live learning.** Actual queue-entry timestamps are explicitly documented. But the realized wait would only become known after the wait ended (and submission latency is unrecorded). Any future online calibration must delay actual labels accordingly and use training-only/strictly prior labels. This audit does not fit a correction or use actual waits as planner inputs.

4. **Closure events during a measured wait remain part of that realized outcome.** They are counted in `results.json`, not removed to make results look better. An entry later than 17:00 is excluded from the 10–17 subset, but a queue ending after 17:00 is not: this subset evaluates entries in the window, not completed itineraries.

5. **Do not compare 4 minutes of route savings directly with this per-ride MAE as a significance test.** They are different statistical quantities. A positive per-ride posted bias can partly cancel in paired route comparisons; differing ride/time exposure can also distort those differences. Only a suitable paired simulation with justified error/uncertainty modeling or a prospective study can resolve the real-time benefit.

## Concrete next step

Keep two explicitly separate evaluation layers: (A) validate waiting-time forecasts against actual-user observations on chronologically held-out data, respecting delayed labels; (B) report route replay as estimated posted-wait-proxy outcomes with coverage, completion and walking sensitivity. Do not automatically subtract the measured mean bias from every ride or present constructed six-ride actual trajectories as observed data. A later train-only actual-wait model can be compared against posted persistence, but would remain a sparse-sample model requiring coverage checks and uncertainty.

## Reproduce

```bash
curl -L --fail -o /tmp/parkplan-ak-933161b.tar.gz \
  https://api.github.com/repos/TouringPlans/DisneyAnimalKingdomWaitTimes/tarball/933161b8bebb7cd50e0d54bcb3578484875487fa
python3 experiments/posted_actual_audit/audit.py --archive /tmp/parkplan-ak-933161b.tar.gz
```

The script uses Python standard library only, verifies source semantics and checksum, and asserts no future posted matches, exclusion of ambiguous latest timestamps, split reproduction, count conservation and pooled error-sum arithmetic. It changes no other experiment.
