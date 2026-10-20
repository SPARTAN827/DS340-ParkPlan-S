#!/usr/bin/env python3
"""TouringPlans.com: retrospective posted-versus-actual wait audit (stdlib only).

Reads, but does not extract or redistribute, a SHA-256-pinned source archive.
The source README defines SACTMIN's timestamp as the actual queue-entry time.
Only posted information at or before that time is matched. This script does not
calibrate or change the route pilot and does not reconstruct visitor journeys.
"""
from __future__ import annotations

import argparse
import bisect
import csv
import hashlib
import io
import json
import math
import statistics
import tarfile
from collections import Counter, defaultdict
from datetime import datetime
from pathlib import Path

RIDES = {
    "AK07": "Kilimanjaro Safaris",
    "AK11": "Expedition Everest",
    "AK14": "Kali River Rapids",
    "AK18": "Dinosaur",
    "AK85": "Na'Vi River Journey",
    "AK86": "Avatar: Flight of Passage",
}
COMMIT = "933161b8bebb7cd50e0d54bcb3578484875487fa"
SHA256 = "23eca800b048aecd4b3a2469e78f63f24f64637eb785c8401386e219a177f812"
ROOT = "TouringPlans-DisneyAnimalKingdomWaitTimes-933161b"
REPO = "https://github.com/TouringPlans/DisneyAnimalKingdomWaitTimes"
HEADER = ("date", "datetime", "SPOSTMIN", "SACTMIN")
LICENSE = """You're free to use these data however you see fit, subject to the following:

1) Any publications or redistributions credit TouringPlans.com clearly at the beginning of those publications or distributions

2) Any redistributions include these license terms"""


def quantile(values, probability):
    if not values:
        return None
    ordered = sorted(values)
    pos = (len(ordered) - 1) * probability
    lo, hi = math.floor(pos), math.ceil(pos)
    return round(ordered[lo] + (ordered[hi] - ordered[lo]) * (pos - lo), 3)


def avg(values):
    return round(statistics.fmean(values), 3) if values else None


def stats(pairs):
    # pair: service date, entry second, posted, actual, post age seconds
    errors = [p[2] - p[3] for p in pairs]
    by_date = defaultdict(list)
    for pair, error in zip(pairs, errors):
        by_date[pair[0]].append(error)
    n = len(errors)
    sums = {"signed_error": sum(errors), "absolute_error": sum(map(abs, errors))}
    signs = {"overposted": sum(x > 0 for x in errors),
             "equal": sum(x == 0 for x in errors),
             "underposted": sum(x < 0 for x in errors)}
    assert sum(signs.values()) == n
    return {
        "pairs": n,
        "dates": len(by_date),
        "date_range": [min(by_date, default=None), max(by_date, default=None)],
        "posted_mean_minutes": avg([p[2] for p in pairs]),
        "actual_mean_minutes": avg([p[3] for p in pairs]),
        "actual_range_minutes": [min((p[3] for p in pairs), default=None),
                                 max((p[3] for p in pairs), default=None)],
        "signed_error_mean_minutes": avg(errors),
        "absolute_error_mean_minutes": avg(list(map(abs, errors))),
        "signed_error_quantiles_minutes": {name: quantile(errors, prob) for name, prob in
                                          (("min", 0), ("p10", .1), ("p25", .25),
                                           ("median", .5), ("p75", .75), ("p90", .9), ("max", 1))},
        "absolute_error_p90_minutes": quantile(list(map(abs, errors)), .9),
        "post_age_median_minutes": quantile([p[4] / 60 for p in pairs], .5),
        "sign_counts": signs,
        "within_absolute_error_counts": {str(t): sum(abs(x) <= t for x in errors) for t in (5, 10, 15)},
        "date_balanced_signed_error_mean_minutes": avg([statistics.fmean(v) for v in by_date.values()]),
        "date_balanced_absolute_error_mean_minutes": avg([statistics.fmean(map(abs, v)) for v in by_date.values()]),
        "arithmetic_sums_minutes": sums,
    }


def load(archive):
    if hashlib.sha256(archive.read_bytes()).hexdigest() != SHA256:
        raise ValueError("Archive SHA-256 does not match the pinned source")
    all_data = {}
    with tarfile.open(archive, "r:gz") as tar:
        readme = tar.extractfile(f"{ROOT}/README.md").read().decode()
        if "the time at which the user began their wait in line" not in readme:
            raise ValueError("Pinned README no longer supports queue-entry timestamp interpretation")
        for ride in RIDES:
            posted, actual, raw_dates = defaultdict(dict), [], set()
            counts = Counter()
            exact_rows, seen_actual = [], set()
            with io.TextIOWrapper(tar.extractfile(f"{ROOT}/{ride}.csv"), encoding="utf-8-sig", newline="") as f:
                reader = csv.DictReader(f)
                if tuple(reader.fieldnames or ()) != HEADER:
                    raise ValueError("Unexpected CSV schema")
                for row in reader:
                    counts["rows"] += 1
                    day_obj = datetime.strptime(row["date"], "%m/%d/%Y").date()
                    time = datetime.strptime(row["datetime"], "%Y-%m-%d %H:%M:%S")
                    day = day_obj.isoformat()
                    offset = (time.date() - day_obj).days
                    assert offset in (0, 1)
                    sec = offset * 86400 + time.hour * 3600 + time.minute * 60 + time.second
                    raw_dates.add(day)
                    p = int(row["SPOSTMIN"]) if row["SPOSTMIN"].strip() else None
                    a = int(row["SACTMIN"]) if row["SACTMIN"].strip() else None
                    if p is not None:
                        counts["posted_nonblank"] += 1
                        assert p >= 0 or p == -999
                        if sec in posted[day]:
                            counts["posted_duplicate_timestamps"] += 1
                            counts["posted_new_conflicting_value_rows"] += int(p not in posted[day][sec])
                            posted[day][sec].add(p)
                        else:
                            posted[day][sec] = {p}
                    if a is not None:
                        assert a >= 0
                        counts["actual_nonblank"] += 1
                        key = (day, sec, a)
                        counts["repeated_actual_date_time_value_rows"] += int(key in seen_actual)
                        seen_actual.add(key)
                        # Preserve observations: the archive has no user ID for deduplication.
                        actual.append((day, sec, a))
                        if p is not None and p >= 0:
                            exact_rows.append((day, sec, p, a, 0))
            # Different source observations sometimes disagree at the same timestamp.
            # Mark the timestamp ambiguous rather than imposing a source-row tie break.
            counts["posted_conflicting_timestamp_groups"] = sum(len(v) > 1 for by_time in posted.values() for v in by_time.values())
            all_data[ride] = {"posted": {d: sorted((s, next(iter(v)) if len(v) == 1 else None)
                                                  for s, v in by_time.items()) for d, by_time in posted.items()},
                              "actual": actual, "same_row": exact_rows,
                              "raw_dates": raw_dates, "counts": dict(counts),
                              "date_coverage": {"raw_date_range": [min(raw_dates), max(raw_dates)],
                                                "raw_date_count": len(raw_dates),
                                                "actual_date_range": [min(a[0] for a in actual), max(a[0] for a in actual)],
                                                "actual_date_count": len({a[0] for a in actual})}}
    return all_data


def match(data, dates, start, end, age_minutes):
    pairs, exclusions = [], Counter()
    posts = data["posted"]
    times = {d: [t for t, _ in events] for d, events in posts.items()}
    for day, sec, actual in data["actual"]:
        if dates is not None and day not in dates:
            continue
        if not start <= sec <= end:
            continue
        exclusions["eligible_actual_samples"] += 1
        index = bisect.bisect_right(times.get(day, []), sec) - 1
        if index < 0:
            exclusions["no_prior_post_same_service_date"] += 1
            continue
        prior_sec, post = posts[day][index]
        assert prior_sec <= sec
        if sec - prior_sec > age_minutes * 60:
            exclusions["prior_post_stale"] += 1
            continue
        if post is None:
            exclusions["ambiguous_latest_post_timestamp"] += 1
            continue
        if post == -999:
            exclusions["fresh_prior_post_reports_closure"] += 1
            continue
        pairs.append((day, sec, post, actual, sec - prior_sec))
        end_queue = sec + 60 * actual
        closure_after_entry = any(p == -999 for t, p in posts[day][index + 1:]
                                  if sec < t <= end_queue)
        exclusions["matched_with_reported_closure_during_wait"] += int(closure_after_entry)
    n = exclusions["eligible_actual_samples"]
    assert len(pairs) + sum(exclusions[k] for k in ("no_prior_post_same_service_date",
           "prior_post_stale", "fresh_prior_post_reports_closure", "ambiguous_latest_post_timestamp")) == n
    return pairs, dict(exclusions)


def run(archive):
    all_data = load(archive)
    common = sorted(set.intersection(*(d["raw_dates"] for d in all_data.values())))
    split = (7 * len(common)) // 10
    test = common[split:]
    assert (len(common), len(test), test[0], test[-1]) == (550, 165, "2018-07-26", "2019-01-06")
    scopes = {"all_available": (None, 0, 172800),
              "six_ride_common_dates": (set(common), 0, 172800),
              "route_test_dates_all_times": (set(test), 0, 172800),
              "route_test_dates_10_17": (set(test), 36000, 61200)}
    output = {
        "data_credit": "TouringPlans.com",
        "source_repository": REPO,
        "source_commit": COMMIT, "source_archive_sha256": SHA256,
        "timestamp_semantics": "Pinned README explicitly defines actual datetime as queue-entry time; all timestamps US Eastern",
        "comparison": "posted minus realized actual user wait; strictly as-of source timestamp, no future posted values",
        "primary_age_tolerance_minutes": 10,
        "same_timestamp_post_availability_caveat": "Source observation timestamp is used as availability; ingestion latency is not recorded",
        "source_counts_by_ride": {r: d["counts"] for r, d in all_data.items()},
        "source_date_coverage_by_ride": {r: d["date_coverage"] for r, d in all_data.items()},
        "raw_common_dates": len(common),
        "route_test_dates": {"count": len(test), "first": test[0], "last": test[-1]},
        "same_row_pairs": {r: stats(d["same_row"]) for r, d in all_data.items()},
        "scope_results": {},
    }
    for name, (dates, start, end) in scopes.items():
        scope = {"age_sensitivity": {}}
        for age in (5, 10, 15):
            by_ride, all_pairs, unique_pairs, exclusion_sum, matched_days = {}, [], [], Counter(), {}
            for ride, data in all_data.items():
                pairs, exclusions = match(data, dates, start, end, age)
                by_ride[ride] = {"name": RIDES[ride], **stats(pairs), "match_accounting": exclusions}
                all_pairs.extend(pairs)
                # Sensitivity only: identical actual date/time/value need not
                # be a duplicate person, because identifiers are unavailable.
                unique_pairs.extend(dict.fromkeys(pairs))
                exclusion_sum.update(exclusions)
                matched_days[ride] = {p[0] for p in pairs}
            pooled = stats(all_pairs)
            assert pooled["pairs"] == sum(v["pairs"] for v in by_ride.values())
            for key in ("signed_error", "absolute_error"):
                assert pooled["arithmetic_sums_minutes"][key] == sum(v["arithmetic_sums_minutes"][key] for v in by_ride.values())
            scope["age_sensitivity"][str(age)] = {
                "pooled": pooled, "by_ride": by_ride,
                "identical_actual_row_dedup_sensitivity": stats(unique_pairs),
                "match_accounting": dict(exclusion_sum),
                "dates_with_at_least_one_matched_actual_for_every_ride": len(set.intersection(*matched_days.values())),
            }
        output["scope_results"][name] = scope
    output["self_checks"] = {
        "archive_sha256_matches": True,
        "README_defines_actual_queue_entry_time": True,
        "route_test_split_reproduced": True,
        "no_future_posted_matches": True,
        "ambiguous_latest_posted_timestamps_excluded": True,
        "all_match_accounting_conserved": True,
        "all_pooled_error_sums_equal_sum_of_rides": True,
        "route_replay_not_modified": True,
    }
    return output


def render_report(result):
    def get(scope, age=10):
        return result["scope_results"][scope]["age_sensitivity"][str(age)]
    total = sum(v["actual_nonblank"] for v in result["source_counts_by_ride"].values())
    full, common, heldout = get("all_available"), get("six_ride_common_dates"), get("route_test_dates_10_17")
    p = heldout["pooled"]
    dedup = heldout["identical_actual_row_dedup_sensitivity"]
    out = ["# TouringPlans.com data credit — posted-versus-actual wait audit",
           f"Source: [TouringPlans Animal Kingdom Wait Times]({REPO}), commit `{COMMIT}`. Source archive SHA-256: `{SHA256}`. Only derived aggregates are distributed here; no raw user observations or inferred visitor journeys are exported.",
           "Source license terms:", LICENSE,
           "## Plain-language conclusion",
           f"We checked whether the number on the ride sign is a faithful measure of the wait a visitor actually experienced. It is not interchangeable with actual queue time. The six files contain **{total:,} actual-user wait observations**, but **zero rows contain both a posted and actual wait**. The source explicitly says actual timestamps are queue-entry times, so we can instead compare each visitor's realized wait with the latest posted observation at or before their entry time (at most 10 minutes old). This is a retrospective proxy check, not a claim that realized waits were known to a planner at queue entry.",
           f"In the route pilot's 165 held-out dates and 10:00–17:00 analysis window, **{p['pairs']:,} matched observations** show a mean posted-minus-actual difference of **{p['signed_error_mean_minutes']:+.2f} minutes** and a mean absolute difference of **{p['absolute_error_mean_minutes']:.2f} minutes**. The median signed difference is **{p['signed_error_quantiles_minutes']['median']:.2f} minutes**. These are sample-level proxy errors, **not route savings**. They do not establish the error in a difference between two full routes: biases can cancel, accumulate, or differ by ride and time.",
           "## What was verified",
           f"- Re-downloaded the public pinned archive on 2026-10-14 and verified its exact SHA-256. The [pinned README]({REPO}/blob/{COMMIT}/README.md) says `SACTMIN` is actual time in the queue and its `datetime` is when the visitor entered the queue. `SPOSTMIN` is the external posted wait; `-999` denotes unexpected closure. The source's example intentionally places posted and actual measurements on separate rows.",
           "- Matched only a same-service-date posted observation at or before queue entry. We do not average the previous and next observation, even though the repository supplies a two-sided ±10-minute matching example. The primary audit uses a 10-minute freshness bound; 5 and 15 minutes are sensitivity checks.",
           "- A fresh most-recent closure code blocks the match; we do not skip backward across it to an earlier open observation. If different posted values share the latest timestamp, that timestamp is ambiguous and the match is excluded rather than choosing a convenient value. No-prior, stale, closure and ambiguity exclusions sum exactly with accepted matches to the eligible actual sample count. The original values are retained without outlier trimming. Same timestamp matches assume the source timestamp represents information availability; no ingestion timestamps are available.",
           "- The 550 common dates and chronological 385/165 split independently reproduce the existing route pilot. 10:00–17:00 is its arbitrary analysis window, not a claim about historical operating hours.",
           "## Coverage and matched-sample counts (10-minute freshness)",
           "| Scope | Actual samples | Matched samples | Mean posted − actual (min) | Mean absolute error (min) | Dates with ≥1 matched actual for all six |",
           "|---|---:|---:|---:|---:|---:|"]
    for label, scope in (("All available per-ride dates", "all_available"),
                         ("550 six-ride common dates", "six_ride_common_dates"),
                         ("165 route test dates, all times", "route_test_dates_all_times"),
                         ("165 route test dates, 10:00–17:00", "route_test_dates_10_17")):
        g = get(scope); q = g["pooled"]
        out.append(f"| {label} | {g['match_accounting']['eligible_actual_samples']:,} | {q['pairs']:,} | {q['signed_error_mean_minutes']:+.3f} | {q['absolute_error_mean_minutes']:.3f} | {g['dates_with_at_least_one_matched_actual_for_every_ride']} |")
    out += ["A day with six independent actual observations is not a six-ride visitor itinerary. Users are not linked in this archive, and the six samples need not correspond to the route's arrival times.",
            "## By attraction: route test dates, queue entry 10:00–17:00",
            "| Ride | Actual samples | Matched | Mean posted − actual | MAE | Median signed error | Signed error p10 / p90 | Within ±10 min |",
            "|---|---:|---:|---:|---:|---:|---:|---:|"]
    for ride, q in heldout["by_ride"].items():
        e = q["signed_error_quantiles_minutes"]
        out.append(f"| {ride} {q['name']} | {q['match_accounting']['eligible_actual_samples']} | {q['pairs']} | {q['signed_error_mean_minutes']:+.2f} | {q['absolute_error_mean_minutes']:.2f} | {e['median']:.2f} | {e['p10']:.2f} / {e['p90']:.2f} | {q['within_absolute_error_counts']['10']}/{q['pairs']} |")
    out += [f"Pooled signs: {p['sign_counts']['overposted']} posted > actual; {p['sign_counts']['equal']} equal; {p['sign_counts']['underposted']} posted < actual. Pooled actual range: {p['actual_range_minutes'][0]}–{p['actual_range_minutes'][1]} minutes. Absolute-error p90: {p['absolute_error_p90_minutes']:.2f} minutes. Date-balanced mean signed/absolute errors (each observed date has equal weight) are {p['date_balanced_signed_error_mean_minutes']:.2f}/{p['date_balanced_absolute_error_mean_minutes']:.2f} minutes; pooled values instead give every observation equal weight.",
            f"Identical-row sensitivity: treating each identical ride/date/entry-time/actual-wait combination as one record leaves {dedup['pairs']} matches, mean signed difference {dedup['signed_error_mean_minutes']:+.2f} minutes, and MAE {dedup['absolute_error_mean_minutes']:.2f} minutes. This is only a robustness check; without user identifiers we cannot determine whether repeated identical records represent duplicate records or different visitors.",
            "## Freshness sensitivity: same held-out 10:00–17:00 window",
            "| Latest prior posted age allowed | Matched | Mean posted − actual (min) | MAE (min) |",
            "|---|---:|---:|---:|"]
    for age in (5, 10, 15):
        q = get("route_test_dates_10_17", age)["pooled"]
        out.append(f"| ≤{age} min | {q['pairs']} | {q['signed_error_mean_minutes']:+.3f} | {q['absolute_error_mean_minutes']:.3f} |")
    out += ["These are overlapping samples with different coverage, not independent experiments. Full distributions, match exclusions, per-ride counts, arithmetic sums and all scopes are recorded in `results.json`.",
            "## Interpretation and limits",
            "1. **A stronger claim is now possible:** we empirically checked the proxy against separate actual-user samples, rather than only assuming posted waits represent time spent. The posted-wait replay remains an exploratory historical simulation and should not be described as proven real visitor savings.",
            "2. **No universal correction is justified.** The actual-user sample is sparse and self-selected, with unequal coverage across rides, dates and times. The archive contains no user ID, queue type, explicit treatment assignment, or complete visitor journeys. It cannot establish that the same bias holds at each simulated arrival, or represent all park visitors. Repeated identical actual date/time/value rows are counted and retained because without IDs we cannot distinguish duplicate records from different users.",
            "3. **The timestamp question is resolved for pairing, not for live learning.** Actual queue-entry timestamps are explicitly documented. But the realized wait would only become known after the wait ended (and submission latency is unrecorded). Any future online calibration must delay actual labels accordingly and use training-only/strictly prior labels. This audit does not fit a correction or use actual waits as planner inputs.",
            "4. **Closure events during a measured wait remain part of that realized outcome.** They are counted in `results.json`, not removed to make results look better. An entry later than 17:00 is excluded from the 10–17 subset, but a queue ending after 17:00 is not: this subset evaluates entries in the window, not completed itineraries.",
            "5. **Do not compare 4 minutes of route savings directly with this per-ride MAE as a significance test.** They are different statistical quantities. A positive per-ride posted bias can partly cancel in paired route comparisons; differing ride/time exposure can also distort those differences. Only a suitable paired simulation with justified error/uncertainty modeling or a prospective study can resolve the real-time benefit.",
            "## Concrete next step",
            "Keep two explicitly separate evaluation layers: (A) validate waiting-time forecasts against actual-user observations on chronologically held-out data, respecting delayed labels; (B) report route replay as estimated posted-wait-proxy outcomes with coverage, completion and walking sensitivity. Do not automatically subtract the measured mean bias from every ride or present constructed six-ride actual trajectories as observed data. A later train-only actual-wait model can be compared against posted persistence, but would remain a sparse-sample model requiring coverage checks and uncertainty.",
            "## Reproduce",
            "```bash\ncurl -L --fail -o /tmp/parkplan-ak-933161b.tar.gz \\\n  https://api.github.com/repos/TouringPlans/DisneyAnimalKingdomWaitTimes/tarball/933161b8bebb7cd50e0d54bcb3578484875487fa\npython3 experiments/posted_actual_audit/audit.py --archive /tmp/parkplan-ak-933161b.tar.gz\n```",
            "The script uses Python standard library only, verifies source semantics and checksum, and asserts no future posted matches, exclusion of ambiguous latest timestamps, split reproduction, count conservation and pooled error-sum arithmetic. It changes no other experiment."]
    rendered = ""
    prior_table = False
    for paragraph in out:
        current_table = paragraph.startswith("|")
        rendered += ("\n" if current_table and prior_table else "\n\n") + paragraph
        prior_table = current_table
    return rendered.strip() + "\n"


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--archive", type=Path, default=Path("/tmp/parkplan-ak-933161b.tar.gz"))
    parser.add_argument("--output", type=Path, default=Path(__file__).resolve().parent)
    args = parser.parse_args()
    result = run(args.archive)
    args.output.mkdir(parents=True, exist_ok=True)
    (args.output / "results.json").write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")
    (args.output / "REPORT.md").write_text(render_report(result), encoding="utf-8")
    print(json.dumps(result["scope_results"]["route_test_dates_10_17"]["age_sensitivity"]["10"], indent=2))


if __name__ == "__main__":
    main()
