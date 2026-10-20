#!/usr/bin/env python3
"""Small, explicitly synthetic six-attraction posted-wait replay.

TouringPlans.com — Disney Animal Kingdom attraction wait-time data.
Source and license are documented in README.md. No source CSV is redistributed.
"""

from __future__ import annotations

import argparse
import bisect
import csv
import hashlib
import io
import itertools
import json
import math
import random
import statistics
import tarfile
from collections import defaultdict
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path


RIDES = ("AK07", "AK11", "AK14", "AK18", "AK85", "AK86")
SOURCE_ROOT = "TouringPlans-DisneyAnimalKingdomWaitTimes-933161b"
SOURCE_SHA256 = "23eca800b048aecd4b3a2469e78f63f24f64637eb785c8401386e219a177f812"
START, END = 600.0, 1020.0  # 10:00–17:00, an analysis window, NOT park hours.
MAX_AGE = 15.0
SLOT = 15
DECAY = 60.0
THRESHOLD = 10.0
TEST_FRACTION = 0.30


@dataclass(frozen=True)
class Observation:
    minute: float
    value: int  # >=0 posted wait; -999 temporarily offline


class DayRide:
    def __init__(self, events: list[Observation]):
        # File-order tie-break: the final observation at an identical timestamp wins.
        by_minute = {event.minute: event for event in events}
        self.events = [by_minute[t] for t in sorted(by_minute)]
        self.times = [event.minute for event in self.events]

    def asof(self, minute: float) -> Observation | None:
        ix = bisect.bisect_right(self.times, minute + 1e-9) - 1
        if ix < 0:
            return None
        event = self.events[ix]
        if minute - event.minute > MAX_AGE + 1e-9:
            return None
        assert event.minute <= minute + 1e-9  # No lookahead.
        return event


def read_source(archive_path: Path) -> dict[str, dict[str, DayRide]]:
    digest = hashlib.sha256(archive_path.read_bytes()).hexdigest()
    if digest != SOURCE_SHA256:
        raise ValueError(f"Unexpected source SHA256: {digest}")
    by_ride: dict[str, dict[str, DayRide]] = {}
    with tarfile.open(archive_path, "r:gz") as archive:
        for ride in RIDES:
            member = archive.extractfile(f"{SOURCE_ROOT}/{ride}.csv")
            if member is None:
                raise ValueError(f"Missing {ride}.csv")
            events: dict[str, list[Observation]] = defaultdict(list)
            raw_dates: set[str] = set()
            with io.TextIOWrapper(member, encoding="utf-8-sig", newline="") as stream:
                reader = csv.DictReader(stream)
                if tuple(reader.fieldnames or ()) != ("date", "datetime", "SPOSTMIN", "SACTMIN"):
                    raise ValueError(f"Unexpected CSV header for {ride}")
                for row in reader:
                    date = datetime.strptime(row["date"], "%m/%d/%Y").date().isoformat()
                    raw_dates.add(date)
                    stamp = datetime.strptime(row["datetime"], "%Y-%m-%d %H:%M:%S")
                    if stamp.date().isoformat() != date:
                        # Source has next-day observations attributed to prior CSV
                        # date; none can affect our 10:00–17:00 analysis window.
                        continue
                    raw = row["SPOSTMIN"].strip()
                    if not raw:
                        continue  # SACTMIN-only row does not replace latest posted state.
                    value = int(raw)
                    if value < 0 and value != -999:
                        raise ValueError(f"Unexpected negative posted value: {value}")
                    minute = stamp.hour * 60 + stamp.minute + stamp.second / 60
                    if START - MAX_AGE <= minute <= END:
                        events[date].append(Observation(minute, value))
            by_ride[ride] = {day: DayRide(events.get(day, [])) for day in raw_dates}
    return by_ride


def train_curves(by_ride: dict[str, dict[str, DayRide]], train_dates: list[str]) -> dict[str, list[float]]:
    """Date-balanced 15-minute medians, based on train dates only."""
    curves = {}
    for ride in RIDES:
        slot_day_values: dict[int, list[float]] = defaultdict(list)
        for day in train_dates:
            data = by_ride[ride].get(day)
            if data is None:
                continue
            values: dict[int, list[int]] = defaultdict(list)
            for event in data.events:
                if START <= event.minute < END and event.value >= 0:
                    values[int((event.minute - START) // SLOT)].append(event.value)
            for slot, daily_values in values.items():
                slot_day_values[slot].append(statistics.median(daily_values))
        known = {slot: statistics.median(values) for slot, values in slot_day_values.items()}
        if not known:
            raise ValueError(f"No train waits for {ride}")
        curves[ride] = [known[min(known, key=lambda s: (abs(s - target), s))]
                        for target in range(int((END - START) / SLOT))]
    return curves


def clock(minute: float) -> str:
    hour = int(minute // 60)
    rest = minute - hour * 60
    return f"{hour:02d}:{rest:05.2f}"


def historical(ride: str, minute: float, curves: dict[str, list[float]]) -> float:
    slot = max(0, min(len(curves[ride]) - 1, int((minute - START) // SLOT)))
    return curves[ride][slot]


def predicted_wait(ride: str, arrival: float, now: float,
                   day: dict[str, DayRide], curves: dict[str, list[float]]) -> float:
    current = day[ride].asof(now)
    if current is not None and current.value == -999:
        # A known current closure rules out entering while the state is fresh.
        # Beyond 15 minutes, reopening is unknown, so use the train prior.
        return math.inf if arrival - current.minute <= MAX_AGE + 1e-9 else historical(ride, arrival, curves)
    baseline = historical(ride, arrival, curves)
    if current is None:
        return baseline
    residual = current.value - historical(ride, current.minute, curves)
    return max(0.0, baseline + residual * math.exp(-(arrival - now) / DECAY))


def route_prediction(order: tuple[str, ...], now: float,
                     day: dict[str, DayRide], curves: dict[str, list[float]],
                     walk: float, service: float) -> float:
    finish = now
    for ride in order:
        arrival = finish + walk
        wait = predicted_wait(ride, arrival, now, day, curves)
        if not math.isfinite(wait):
            return math.inf
        finish = arrival + wait + service
    return finish


def best_route(remaining: tuple[str, ...], now: float,
               day: dict[str, DayRide], curves: dict[str, list[float]],
               walk: float, service: float) -> tuple[tuple[str, ...] | None, float]:
    best_order = None
    best_finish = math.inf
    for order in itertools.permutations(sorted(remaining)):
        finish = route_prediction(order, now, day, curves, walk, service)
        if finish < best_finish - 1e-9:
            best_order, best_finish = order, finish
    return best_order, best_finish


def replay_day(date: str, policy: str, by_ride: dict[str, dict[str, DayRide]],
               curves: dict[str, list[float]], walk: float, service: float,
               trace: bool = False) -> dict:
    day = {ride: by_ride[ride].get(date, DayRide([])) for ride in RIDES}
    order, initial_pred_finish = best_route(RIDES, START, day, curves, walk, service)
    result = {"date": date, "policy": policy, "walk_per_leg": walk,
              "service_per_ride": service, "initial_order": "|".join(order or ()),
              "initial_predicted_finish": round(initial_pred_finish, 3) if math.isfinite(initial_pred_finish) else "",
              "success": False, "failure": "", "completed": 0,
              "elapsed_min": "", "total_posted_wait_min": 0,
              "total_walk_min": 0, "total_service_min": 0,
              "route_changes": 0, "replans": 0, "finish_clock": "",
              "completed_order": "", "trace": []}
    if order is None:
        result["failure"] = "no_route_from_available_predictions"
        return result
    now = START
    remaining = list(order)
    completed = []
    while remaining:
        ride = remaining.pop(0)
        arrival = now + walk
        event = day[ride].asof(arrival)
        failure = None
        if arrival > END + 1e-9:
            failure = "arrival_after_window"
        elif event is None:
            failure = "no_fresh_posted_at_arrival"
        elif event.value == -999:
            failure = "closed_at_arrival"
        elif arrival + event.value + service > END + 1e-9:
            failure = "completion_after_window"
        if trace:
            result["trace"].append({"type": "visit", "ride": ride,
                "depart": round(now, 3), "arrival": round(arrival, 3),
                "posted_observed_at": round(event.minute, 3) if event else None,
                "posted_wait": event.value if event else None,
                "status": failure or "completed"})
        result["total_walk_min"] += walk
        if failure:
            result["failure"] = failure
            break
        result["total_posted_wait_min"] += event.value
        result["total_service_min"] += service
        now = arrival + event.value + service
        completed.append(ride)
        result["completed"] = len(completed)
        if remaining and policy != "fixed":
            result["replans"] += 1
            incumbent = tuple(remaining)
            incumbent_finish = route_prediction(incumbent, now, day, curves, walk, service)
            proposed, proposed_finish = best_route(incumbent, now, day, curves, walk, service)
            switch = proposed is not None and proposed != incumbent
            if policy == "threshold10":
                switch = switch and incumbent_finish - proposed_finish >= THRESHOLD - 1e-9
            if trace:
                result["trace"].append({"type": "decision", "at": round(now, 3),
                    "incumbent": list(incumbent), "incumbent_pred_finish":
                        round(incumbent_finish, 3) if math.isfinite(incumbent_finish) else None,
                    "proposed": list(proposed) if proposed else None,
                    "proposed_pred_finish": round(proposed_finish, 3) if math.isfinite(proposed_finish) else None,
                    "switched": bool(switch)})
            if switch:
                remaining = list(proposed)
                result["route_changes"] += 1
    result["completed_order"] = "|".join(completed)
    if len(completed) == len(RIDES):
        result["success"] = True
        result["elapsed_min"] = round(now - START, 3)
        result["finish_clock"] = clock(now)
    return result


def quantile(values: list[float], q: float) -> float | None:
    if not values:
        return None
    ordered = sorted(values)
    at = (len(ordered) - 1) * q
    low = int(math.floor(at))
    high = int(math.ceil(at))
    return ordered[low] + (ordered[high] - ordered[low]) * (at - low)


def summarize(rows: list[dict]) -> dict:
    dates = sorted({row["date"] for row in rows})
    by_key = {(row["date"], row["policy"]): row for row in rows}
    summary = {"attempted_days": len(dates), "by_policy": {}, "paired": {}}
    for policy in ("fixed", "replan", "threshold10"):
        subset = [by_key[date, policy] for date in dates]
        successful = [r for r in subset if r["success"]]
        failures = defaultdict(int)
        for row in subset:
            if not row["success"]:
                failures[row["failure"]] += 1
        summary["by_policy"][policy] = {
            "success_days": len(successful), "completion_rate": len(successful) / len(dates),
            "failures_by_reason": dict(sorted(failures.items())),
            "mean_completed_rides_all_days": statistics.mean(r["completed"] for r in subset),
            "mean_route_changes_all_days": statistics.mean(r["route_changes"] for r in subset),
        }
    for policy in ("replan", "threshold10"):
        fixed_only = sum(by_key[date, "fixed"]["success"] and not by_key[date, policy]["success"]
                         for date in dates)
        policy_only = sum(not by_key[date, "fixed"]["success"] and by_key[date, policy]["success"]
                          for date in dates)
        neither = sum(not by_key[date, "fixed"]["success"] and not by_key[date, policy]["success"]
                      for date in dates)
        paired = [(by_key[date, "fixed"], by_key[date, policy]) for date in dates
                  if by_key[date, "fixed"]["success"] and by_key[date, policy]["success"]]
        savings = [a["elapsed_min"] - b["elapsed_min"] for a, b in paired]
        randomizer = random.Random(20261013)
        boot_means = [statistics.mean(randomizer.choices(savings, k=len(savings)))
                      for _ in range(10000)] if savings else []
        summary["paired"][policy] = {
            "paired_success_days": len(paired), "fraction_of_attempted_days": len(paired) / len(dates),
            "fixed_only_success_days": fixed_only,
            "policy_only_success_days": policy_only,
            "neither_success_days": neither,
            "mean_proxy_minutes_saved": statistics.mean(savings) if savings else None,
            "mean_proxy_minutes_saved_bootstrap_95pct":
                [quantile(boot_means, .025), quantile(boot_means, .975)],
            "median_proxy_minutes_saved": statistics.median(savings) if savings else None,
            "p25_proxy_minutes_saved": quantile(savings, .25),
            "p75_proxy_minutes_saved": quantile(savings, .75),
            "days_positive": sum(s > 1e-9 for s in savings),
            "days_zero": sum(abs(s) <= 1e-9 for s in savings),
            "days_negative": sum(s < -1e-9 for s in savings),
            "mean_wait_minutes_saved": statistics.mean(
                a["total_posted_wait_min"] - b["total_posted_wait_min"] for a, b in paired) if paired else None,
            "mean_route_changes_on_paired_days": statistics.mean(b["route_changes"] for _, b in paired) if paired else None,
        }
    return summary


def run(archive: Path, output: Path) -> None:
    output.mkdir(parents=True, exist_ok=True)
    by_ride = read_source(archive)
    # Every date with any source CSV row for each ride, regardless of wait
    # availability, closure, or potential outcome. No outcome-selected days.
    all_dates = sorted(set.intersection(*(set(by_ride[ride]) for ride in RIDES)))
    n_test = math.ceil(len(all_dates) * TEST_FRACTION)
    train_dates, test_dates = all_dates[:-n_test], all_dates[-n_test:]
    curves = train_curves(by_ride, train_dates)
    params = {"source": "TouringPlans.com — Disney Animal Kingdom posted waits",
              "source_sha256": SOURCE_SHA256,
              "six_rides": RIDES, "all_common_dates": len(all_dates),
              "train_dates": len(train_dates), "test_dates": len(test_dates),
              "train_range": [train_dates[0], train_dates[-1]],
              "test_range": [test_dates[0], test_dates[-1]],
              "split": "chronological last 30% raw-common CSV dates held out",
              "analysis_window_local_eastern": "10:00–17:00 (not park opening hours)",
              "start_location": "synthetic gate; every ride reached by same per-leg walking time",
              "max_asof_posted_age_minutes": MAX_AGE,
              "historical_curve": "train-only date-balanced median of within-day waits, 15-minute slots",
              "forecast": "train curve at future arrival + latest fresh posted deviation times exp(-forecast_horizon/60), clipped at zero",
              "closure": "last fresh -999 closes ride at arrival; known current closure excludes candidate arrivals while fresh",
              "threshold10": "switch suffix only if predicted finish improves by >=10 minutes",
              "test_scenarios": [{"walk_per_leg": w, "service_per_ride": s}
                                 for w, s in ((5, 5), (10, 10), (15, 15))],
              "outcome": "modeled elapsed minutes using as-of posted wait at arrival, not actual visitor time"}
    params["bootstrap"] = "10,000 date-resampled paired-success mean savings; seed 20261013; conditional on paired successes"
    (output / "parameters.json").write_text(json.dumps(params, indent=2) + "\n")
    (output / "train_curves.json").write_text(json.dumps(curves, indent=2) + "\n")
    base_rows = []
    sensitivity = []
    for walk, service in ((5, 5), (10, 10), (15, 15)):
        rows = [replay_day(date, policy, by_ride, curves, walk, service)
                for date in test_dates for policy in ("fixed", "replan", "threshold10")]
        summary = summarize(rows)
        sensitivity.append({"walk_per_leg": walk, "service_per_ride": service,
                            "summary": summary})
        if (walk, service) == (10, 10):
            base_rows = rows
            (output / "summary.json").write_text(json.dumps(summary, indent=2) + "\n")
    assert base_rows
    fields = [key for key in base_rows[0] if key != "trace"]
    with (output / "per_day.csv").open("w", newline="") as stream:
        writer = csv.DictWriter(stream, fieldnames=fields)
        writer.writeheader()
        writer.writerows({key: row[key] for key in fields} for row in base_rows)
    (output / "sensitivity.json").write_text(json.dumps(sensitivity, indent=2) + "\n")
    # Post-hoc example for manual inspection, not an inferential sample.
    by_key = {(row["date"], row["policy"]): row for row in base_rows}
    example = next((day for day in test_dates if by_key[day, "fixed"]["success"]
                    and by_key[day, "replan"]["success"]
                    and by_key[day, "replan"]["route_changes"] > 0
                    and by_key[day, "fixed"]["elapsed_min"] != by_key[day, "replan"]["elapsed_min"]), None)
    if example:
        traces = [replay_day(example, p, by_ride, curves, 10, 10, trace=True)
                  for p in ("fixed", "replan")]
        for traced in traces:
            base = by_key[example, traced["policy"]]
            assert all(traced[k] == base[k] for k in fields)
            assert traced["success"] and traced["completed"] == 6
            assert abs(traced["elapsed_min"] - (traced["total_walk_min"] +
                traced["total_service_min"] + traced["total_posted_wait_min"])) < .001
            for event in traced["trace"]:
                if event["type"] == "visit" and event["posted_observed_at"] is not None:
                    assert event["posted_observed_at"] <= event["arrival"] + 1e-9
                    assert event["arrival"] - event["posted_observed_at"] <= MAX_AGE + 1e-9
        (output / "hand_trace.json").write_text(json.dumps({"selection":
            "first held-out paired-success day with a replan route change and nonzero difference; post-hoc illustration only",
            "date": example, "policies": traces}, indent=2) + "\n")
    print(json.dumps({"parameters": {"train_dates": len(train_dates),
        "test_dates": len(test_dates), "test_range": params["test_range"]},
        "base_summary": summarize(base_rows), "hand_trace_date": example}, indent=2))


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--archive", type=Path, default=Path("/tmp/parkplan-ak-933161b.tar.gz"))
    parser.add_argument("--output", type=Path, default=Path(__file__).resolve().parent)
    args = parser.parse_args()
    run(args.archive, args.output)
