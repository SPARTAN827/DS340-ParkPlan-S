#!/usr/bin/env python3
"""TouringPlans.com credited, genuine five-policy historical replay demo.

Runs frozen policy code on the first evaluation date, never selected for results.
Python 3.10+, standard library only. No historical study output is overwritten.
"""
from __future__ import annotations

import argparse
import csv
from datetime import datetime, timezone
import hashlib
import importlib.util
import json
import math
from pathlib import Path
import sys
import tempfile
import time

ROOT = Path(__file__).resolve().parents[2]
HERE = Path(__file__).resolve().parent
STUDY = ROOT / "experiments/algorithm_study_20261019"
ARCHIVE_NAME = "parkplan-ak-933161b.tar.gz"
ARCHIVE_URL = "https://api.github.com/repos/TouringPlans/DisneyAnimalKingdomWaitTimes/tarball/933161b8bebb7cd50e0d54bcb3578484875487fa"
SOURCE_SHA256 = "23eca800b048aecd4b3a2469e78f63f24f64637eb785c8401386e219a177f812"
LOCK_SHA256 = "17294dc8ee9c0e373c5df4f48863ee94c876222efa2ff3c392e526bceb7731f1"
POLICIES = ("fixed", "dynamic", "calibrated", "rollout", "scenario_open_loop")
LABELS = dict(zip(POLICIES, ("F", "D0", "C", "R", "S")))


def digest(path):
    h = hashlib.sha256()
    with Path(path).open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            h.update(block)
    return h.hexdigest()


def require(condition, message):
    if not condition:
        raise ValueError(message)


def verify_inputs(root, archive):
    root, archive = Path(root), Path(archive)
    require(archive.is_file(), f"Pinned archive missing: {archive}\nDownload {ARCHIVE_URL}\nRequired SHA256: {SOURCE_SHA256}")
    require(digest(archive) == SOURCE_SHA256, "Dataset checksum mismatch; do not substitute a newer snapshot.")
    lock_path = root / "experiments/algorithm_study_20261019/evaluation_lock.json"
    require(lock_path.is_file(), "Run from a complete ParkPlan-S repository, retaining its experiments/ and data/ folders.")
    require(digest(lock_path) == LOCK_SHA256, "Frozen evaluation lock changed.")
    expected = json.loads(lock_path.read_text(encoding="utf-8"))["files"]
    for relative, checksum in expected.items():
        path = root / relative
        require(path.is_file(), f"Missing frozen dependency: {relative}")
        require(digest(path) == checksum, f"Frozen dependency changed: {relative}")
    return expected


def select_demo_date(splits):
    """No outcome files or policy performance participate in date selection."""
    evaluation = splits["evaluation"]
    require(bool(evaluation), "No evaluation dates.")
    date = min(evaluation)
    train = splits["fit"] + splits["validation"]
    require(len(train) == len(set(train)), "Duplicate training dates.")
    require(all(d < date for d in train), "Training dates must precede the demo date.")
    require(len(set(evaluation).intersection(train)) == 0, "Split overlap.")
    return date, train


def clean(value):
    if isinstance(value, float) and not math.isfinite(value):
        return None
    if isinstance(value, dict):
        return {k: clean(v) for k, v in value.items()}
    if isinstance(value, (list, tuple)):
        return [clean(v) for v in value]
    return value


def save_json(path, value):
    Path(path).write_text(json.dumps(clean(value), indent=2, ensure_ascii=False, allow_nan=False) + "\n", encoding="utf-8")


def check_outcomes(rows, day, rides):
    """Independent bookkeeping checks; not a proof of scientific superiority."""
    require(tuple(r["policy"] for r in rows) == POLICIES, "Missing/duplicate policy result.")
    require(len({r["initial_order"] for r in rows}) == 1, "Different initial plans.")
    visit_count = 0
    for row in rows:
        completed = row["completed_order"].split("|") if row["completed_order"] else []
        require(len(completed) == row["completed"], "Completed count mismatch.")
        require(len(set(completed)) == len(completed), "Repeated ride.")
        if row["success"]:
            require(set(completed) == set(rides), "Success without the same six rides.")
            total = sum(row[k] for k in ("total_walk_min", "total_posted_wait_min", "total_service_min"))
            require(abs(total - row["elapsed_min"]) < 1e-7, "Elapsed-time arithmetic mismatch.")
            require(not row["failure"], "Success marked with failure.")
        else:
            require(row["elapsed_min"] is None and bool(row["failure"]), "Failure must retain its reason and cannot receive zero trip time.")
        for event in row["events"]:
            if event["type"] == "visit":
                visit_count += 1
                actual = day[event["ride"]].asof(event["arrival"])
                require(event["posted_wait"] == (actual.value if actual else None), "Arrival outcome differs from raw as-of source.")
                require(event["posted_observed_at"] == (actual.minute if actual else None), "Arrival observation timestamp differs.")
            elif event["type"] == "decision":
                for obs in event["snapshot"].values():
                    if obs is not None:
                        require(obs["minute"] <= event["at"] + 1e-9, "Future observation at an online decision.")
                        require(event["at"] - obs["minute"] <= 15 + 1e-9, "Stale online observation.")
    return {"policy_records_checked": len(rows), "raw_source_arrivals_checked": visit_count, "shared_initial_plan": True}


def load_runner():
    sys.path.insert(0, str(STUDY))
    spec = importlib.util.spec_from_file_location("parkplan_week12_frozen_runner", STUDY / "run.py")
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def compare_saved(rows):
    """Compare only after fresh execution; saved rows are never execution inputs."""
    path = STUDY / "evaluation/per_day.csv"
    if not path.is_file():
        return {"status": "not_checked", "reason": "Frozen per_day.csv unavailable"}
    with path.open(newline="", encoding="utf-8") as stream:
        saved = {(r["date"], r["policy"]): r for r in csv.DictReader(stream)}
    fields = ("initial_order", "completed_order", "failure", "success", "completed", "elapsed_min", "total_walk_min", "total_posted_wait_min", "total_service_min", "replans", "route_changes", "next_changes")
    for row in rows:
        old = saved[row["date"], row["policy"]]
        for field in fields:
            actual = row[field]
            if isinstance(actual, float):
                require(abs(float(old[field]) - actual) < 1e-7, f"Saved parity mismatch: {row['policy']} {field}")
            else:
                require(old[field] == ("" if actual is None else str(actual)), f"Saved parity mismatch: {row['policy']} {field}")
    return {"status": "PASS", "records": len(rows), "fields": fields, "saved_csv_sha256": digest(path), "timing_excluded": True}


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--archive", type=Path, default=Path(tempfile.gettempdir()) / ARCHIVE_NAME)
    parser.add_argument("--output-root", type=Path, default=HERE / "runs")
    args = parser.parse_args(argv)
    try:
        print("Data credit: TouringPlans.com", flush=True)
        print("Fresh one-date execution of F, D0, C, R and S; not a new 165-date benchmark.", flush=True)
        hashes = verify_inputs(ROOT, args.archive)
        splits = json.loads((STUDY / "inputs/splits.json").read_text(encoding="utf-8"))["splits"]
        date, train = select_demo_date(splits)
        selected = json.loads((STUDY / "selection.json").read_text(encoding="utf-8"))
        print(f"Date: {date}; selected by chronological first-date rule, not performance.", flush=True)
        print(f"Training dates: {len(train)}; calibration decay: {selected['selected_decay']} min; scenarios: 8.", flush=True)
        print("Parsing the checksum-verified archive directly (no parsed-cache dependency)...", flush=True)
        began = time.perf_counter()
        runner = load_runner()
        core = runner.core if hasattr(runner, "core") else sys.modules["prepare"].core_module()
        data = core.read_source(args.archive)
        dates = sorted(set.intersection(*(set(data[r]) for r in core.RIDES)))
        require(len(dates) == 550 and date in dates, "Unexpected source date coverage.")
        curves = core.train_curves(data, train)
        bank = runner.e.ScenarioBank(data, train, curves, k=8)
        hours = runner.get_hours()
        require(date in hours, "Demo requires the frozen sourced park-close record, not fallback hours.")
        print("Uniform 10-minute walking and service inputs; historical posted waits, not actual visitor waits.", flush=True)
        rows = []
        for policy in POLICIES:
            decay = selected["selected_decay"] if policy == "calibrated" else 60
            row = runner.replay(date, policy, "reference", curves, bank, data, hours, decay)
            rows.append(row)
            elapsed = f"{row['elapsed_min']:.3f}" if row["success"] else "N/A"
            print(f"{LABELS[policy]:>2}  {policy:18}  complete={row['completed']}/6  trip_minutes={elapsed:>8}  failure={row['failure'] or 'none'}", flush=True)
        audit = check_outcomes(rows, {r: data[r][date] for r in core.RIDES}, core.RIDES)
        parity = compare_saved(rows)
        for relative, checksum in hashes.items():
            require(digest(ROOT / relative) == checksum, f"Frozen dependency changed during execution: {relative}")
        args.output_root.mkdir(parents=True, exist_ok=True)
        folder = Path(tempfile.mkdtemp(prefix=datetime.now(timezone.utc).strftime("demo-%Y%m%dT%H%M%SZ-"), dir=args.output_root))
        save_json(folder / "traces.json", rows)
        fields = [k for k in rows[0] if k != "events"]
        with (folder / "comparison.csv").open("w", newline="", encoding="utf-8") as stream:
            writer = csv.DictWriter(stream, fieldnames=fields)
            writer.writeheader()
            writer.writerows({k: row[k] for k in fields} for row in rows)
        metadata = {"credit": "TouringPlans.com", "status": "Fresh demonstration, not a new benchmark or participant trial", "date": date,
                    "date_selection": "Chronologically first frozen evaluation date; no outcome-based selection", "training_dates": train,
                    "created_at_utc": datetime.now(timezone.utc).isoformat(), "python": sys.version, "platform": sys.platform,
                    "source_sha256": SOURCE_SHA256, "source_url": ARCHIVE_URL, "wrapper_sha256": digest(__file__),
                    "frozen_dependency_sha256": hashes, "config": "reference: uniform 10-minute walking and service", "selected_decay": selected["selected_decay"],
                    "scenario_count": 8, "runtime_seconds": time.perf_counter() - began, "audit": audit, "frozen_one_date_parity": parity,
                    "limitations": ["One date cannot establish comparative performance", "Previously inspected retrospective evaluation period", "Synthetic walking and service inputs", "Posted waits are not measured whole-trip visitor time"]}
        save_json(folder / "verification.json", metadata)
        save_json(folder / "manifest.json", {p.name: digest(p) for p in sorted(folder.iterdir())})
        print(f"Audit PASS: {audit['policy_records_checked']} fresh records, {audit['raw_source_arrivals_checked']} source arrivals; frozen scientific parity: {parity['status']}.", flush=True)
        print(f"Saved new evidence: {folder.resolve()}", flush=True)
        print("Use the full 165-date comparison for conclusions. This one-date demonstration cannot establish a winner.", flush=True)
        return 0
    except (OSError, ValueError, KeyError, AssertionError) as exc:
        print(f"Demo stopped: {exc}", file=sys.stderr, flush=True)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
