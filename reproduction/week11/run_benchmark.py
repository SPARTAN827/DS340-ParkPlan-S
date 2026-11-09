#!/usr/bin/env python3
"""Bounded, paired-environment ADAPT benchmark using the unmodified C++ programs.

Standard library only; Linux/WSL exit-code semantics. No seed injection, retries,
source patches, or selection of successful missions. See manifest.json for scope.
"""
import argparse
import csv
from datetime import datetime, timezone
import hashlib
import json
import math
from pathlib import Path
import platform
import shutil
import statistics
import subprocess
import sys
import time
import traceback

ROOT = Path(__file__).resolve().parent.parent
STRATEGIES = ("Offline", "DoNothing", "WeightedAvg", "Bayesian")
BINARIES = ("offline-planning", "online-planning", "simulation")
MISSION_FIELDS = ("x", "y", "z", "t_arrive", "E_arrive", "t_leave", "E_leave", "E_chrg")
# These follow the actual return branches, NOT the swapped upstream WARN labels.
MISSION_CODES = {0: "continue", 1: "success", 255: "service_failed",
                 254: "visit_failed", 253: "return_home_failed"}
MAIN_TEXT_OVERRIDES = {"num_iters_acs": 250, "max_no_impr_acs": 25, "tol": 0.0001}
REFERENCE_COMMIT = "e9967bf0d7a42c9051bdb1759bebeeac42d30681"


class HarnessError(RuntimeError):
    """An execution/data problem, not an algorithmic mission failure."""


def require(condition, message):
    if not condition:
        raise HarnessError(message)


def utc_now():
    return datetime.now(timezone.utc).isoformat()


def save_json(path, value):
    path.write_text(json.dumps(value, indent=2, allow_nan=False) + "\n", encoding="utf-8")


def sha256(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def reserve_output(path):
    path = Path(path).resolve()
    if path.exists():
        require(path.is_dir() and not any(path.iterdir()),
                f"Refusing to overwrite a nonempty output or file: {path}")
    else:
        path.mkdir(parents=True)
    return path


def decode_output(value):
    if isinstance(value, bytes):
        return value.decode("utf-8", errors="replace")
    return value or ""


class ProcessRecorder:
    """Persist each command, both streams, and timeout evidence before raising."""

    def __init__(self, directory, timeout=180):
        self.directory = Path(directory)
        self.timeout = timeout
        self.events = []
        (self.directory / "process-logs").mkdir(exist_ok=True)

    def run(self, args, accepted=(0,), allow_mission_warnings=False):
        argv = [str(value) for value in args]
        seq = len(self.events) + 1
        event = {"sequence": seq, "argv": argv, "cwd": str(self.directory),
                 "started_utc": utc_now(), "timeout_seconds": self.timeout,
                 "returncode": None, "timed_out": False,
                 "stdout_file": f"process-logs/{seq:04d}.stdout.txt",
                 "stderr_file": f"process-logs/{seq:04d}.stderr.txt"}
        self.events.append(event)
        save_json(self.directory / "processes.json", self.events)
        started = time.monotonic()
        stdout, stderr, error = "", "", None
        try:
            process = subprocess.run(argv, cwd=self.directory, text=True,
                                     stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                                     timeout=self.timeout)
            event["returncode"] = process.returncode
            stdout, stderr = process.stdout, process.stderr
        except subprocess.TimeoutExpired as exc:
            stdout, stderr = decode_output(exc.stdout), decode_output(exc.stderr)
            event["timed_out"] = True
            error = f"Command timed out after {self.timeout}s: {argv}"
        except OSError as exc:
            error = f"Cannot execute command: {exc}"
        finally:
            event["wall_seconds"] = round(time.monotonic() - started, 6)
            event["finished_utc"] = utc_now()
            if error:
                event["error"] = error
            (self.directory / event["stdout_file"]).write_text(stdout, encoding="utf-8")
            (self.directory / event["stderr_file"]).write_text(stderr, encoding="utf-8")
            save_json(self.directory / "processes.json", self.events)
            with (self.directory / "console.log").open("a", encoding="utf-8") as log:
                log.write("$ " + " ".join(argv) + "\n" + stdout)
                if stderr:
                    log.write("\n[stderr]\n" + stderr)
                log.write(f"\n[returncode={event['returncode']}; timed_out={event['timed_out']}]\n")
        require(error is None, error)
        require(event["returncode"] in accepted,
                f"Unexpected return code {event['returncode']}: {argv}")
        require("[ERROR]" not in stdout + stderr, f"Upstream ERROR output: {argv}")
        if not (allow_mission_warnings and event["returncode"] in (253, 254, 255)):
            require("[WARN]" not in stdout + stderr, f"Unexpected upstream WARN output: {argv}")
        return event["returncode"]


def numeric_rows(path):
    with path.open(newline="", encoding="utf-8") as handle:
        rows = [[float(cell) for cell in row] for row in csv.reader(handle)]
    require(rows and all(row and all(math.isfinite(x) for x in row) for row in rows),
            f"Empty/non-finite numeric CSV: {path}")
    return rows


def read_mission(path):
    with path.open(newline="", encoding="utf-8") as handle:
        reader = csv.DictReader(handle)
        require(tuple(reader.fieldnames or ()) == MISSION_FIELDS, "Invalid mission CSV header")
        rows = []
        for row in reader:
            require(None not in row and all(row.get(key) is not None for key in MISSION_FIELDS),
                    "Invalid mission CSV column count")
            rows.append({key: float(row[key]) for key in MISSION_FIELDS})
    require(rows and all(math.isfinite(v) for row in rows for v in row.values()),
            "Empty/non-finite mission CSV")
    return rows


def read_plans(path, node_count):
    rows = numeric_rows(path)
    for row in rows:
        require(len(row) >= 6 and row[0] >= 0 and row[2] >= 0 and row[3] >= 0,
                "Invalid plan fields")
        path_nodes = row[4:]
        require(all(x.is_integer() and 0 <= x < node_count for x in path_nodes),
                "Invalid plan node index")
        require(path_nodes[-1] == 1 and 1 not in path_nodes[:-1]
                and 0 not in path_nodes[1:] and len(set(path_nodes)) == len(path_nodes),
                "Invalid plan endpoints or repeated nodes")
    return rows


def read_instance(path):
    with path.open(newline="", encoding="utf-8") as handle:
        reader = csv.reader(handle)
        require(next(reader, None) == ["lat", "lon", "alt", "volt"], "Invalid instance header")
        rows = [[float(cell) for cell in row] for row in reader]
    require(len(rows) >= 2 and all(len(row) == 4 and all(math.isfinite(v) for v in row)
                                  for row in rows), "Invalid instance rows")
    return rows


def validate_initial_edges(path, node_count):
    rows = numeric_rows(path)
    pairs = set()
    for row in rows:
        require(len(row) >= 7, "Real edge file is not average-power layout")
        require(all(x.is_integer() and 0 <= x < node_count for x in row[:2]),
                "Invalid real edge indices")
        pair = tuple(map(int, row[:2]))
        require(pair not in pairs and row[2] > 0 and row[3] > 0,
                "Duplicate/nonpositive real edge")
        require(all(x > 0 for x in row[4:]), "Invalid average-power sample")
        pairs.add(pair)
    return pairs


def close_serialized(a, b):
    # Upstream C++ streams use six significant digits. This is a validation
    # tolerance for serialized values, NOT a change to the optimizer tolerance.
    return math.isclose(a, b, rel_tol=1e-5, abs_tol=1e-3)


def summarize_mission(directory, strategy, steps, instance_name, initial_uav):
    """Validate a completed simulator outcome; never infer success from a log alone."""
    inp = directory / "input"
    instance = read_instance(inp / "instance" / f"{instance_name}_0.csv")
    mission = read_mission(inp / "mission_log.csv")
    plans = read_plans(inp / "exp_chrg_list.csv", len(instance))
    require(steps and steps[-1]["returncode"] in (1, 253, 254, 255), "Missing terminal outcome")
    require(len(mission) == len(steps) + 1, "Mission row count differs from simulation steps")
    require(len(plans) == len(steps), "Plan history differs from simulation steps")
    require(all(step["returncode"] == 0 for step in steps[:-1]), "Nonterminal failure")
    require(plans[0][4] == 0, "Initial plan does not start at depot 0")
    require(close_serialized(mission[0]["E_leave"], initial_uav["E"])
            and close_serialized(mission[0]["t_leave"], initial_uav["t"]),
            "Initial mission status differs from UAV configuration")
    require(all(close_serialized(mission[0][key], initial_uav[key]) for key in ("x", "y", "z")),
            "Initial UAV coordinates differ")
    targets = [step["target"] for step in steps]
    require(len(targets) == len(set(targets)), "Repeated attempted node")
    previous = 0
    for index, (step, row, plan) in enumerate(zip(steps, mission[1:], plans)):
        target = step["target"]
        require(plan[4] == previous and plan[5] == target, "Plan/route mismatch")
        require(target == 1 or 2 <= target < len(instance), "Invalid attempted node")
        require(all(close_serialized(row[key], instance[target][axis])
                    for axis, key in enumerate(("x", "y", "z"))), "Mission target coordinates differ")
        require(row["t_arrive"] >= mission[index]["t_leave"] - 0.02,
                "Mission time goes backwards")
        require(row["E_arrive"] <= mission[index]["E_leave"] + 0.002,
                "Energy increased in flight")
        require(row["E_chrg"] >= 0, "Negative charged energy")
        if step["returncode"] == 0:
            require(target != 1 and row["E_arrive"] > 0 and row["E_leave"] > 0,
                    "Invalid successful intermediate energy/target")
            require(row["t_leave"] >= row["t_arrive"] - 0.02
                    and row["E_leave"] <= row["E_arrive"] + 0.002,
                    "Invalid service time/energy")
        else:
            require(row["t_leave"] == -1 and row["E_leave"] == -1 and row["E_chrg"] == 0,
                    "Invalid terminal status fields")
        if index > 0:
            if strategy == "Bayesian":
                require(75 <= plan[1] <= 99.9, "Invalid Bayesian belief")
            else:
                require(plan[1] == 0, "Unexpected baseline belief")
        previous = target
    terminal = steps[-1]["returncode"]
    last = mission[-1]
    success = terminal == 1
    if success:
        require(targets[-1] == 1 and last["E_arrive"] > 0, "Invalid successful return home")
        require(all(close_serialized(last[key], initial_uav[key]) for key in ("x", "y", "z")),
                "Terminal depot differs from initial UAV position")
    else:
        require(last["E_arrive"] <= 1e-7, "Failure did not exhaust its simulated budget")
        require((terminal == 253) == (targets[-1] == 1), "Failure code/target mismatch")
    charged = sum(row["E_chrg"] for row in mission)
    return {"status": "success" if success else "mission_failure",
            "outcome": MISSION_CODES[terminal], "terminal_code": terminal,
            "terminal_target": targets[-1], "return_home": success,
            "route": [0] + targets, "attempted_sensor_nodes": sum(t != 1 for t in targets),
            "serviced_nodes": sum(step["returncode"] == 0 for step in steps),
            "charged_energy_kJ": charged, "initial_energy_kJ": initial_uav["E"],
            "remaining_energy_kJ": last["E_arrive"] if success else None,
            "consumed_energy_kJ": initial_uav["E"] - last["E_arrive"] if success else None,
            "last_logged_energy_kJ": last["E_arrive"],
            "simulated_duration_s": last["t_arrive"] - initial_uav["t"],
            "online_replans": 0 if strategy == "Offline" else len(plans) - 1,
            "online_algorithm_seconds": 0 if strategy == "Offline" else sum(row[0] for row in plans[1:]),
            "offline_algorithm_seconds": plans[0][0]}


def partial_metrics(directory, steps):
    """Keep observed work after a harness error; missing data is null, never zero."""
    result = {"route": [0] + [step["target"] for step in steps],
              "serviced_nodes": sum(step["returncode"] == 0 for step in steps),
              "return_home": False, "remaining_energy_kJ": None,
              "consumed_energy_kJ": None, "charged_energy_kJ": None,
              "last_logged_energy_kJ": None}
    try:
        rows = read_mission(directory / "input/mission_log.csv")
        result["charged_energy_kJ"] = sum(row["E_chrg"] for row in rows)
        result["last_logged_energy_kJ"] = rows[-1]["E_arrive"] if len(rows) > 1 else rows[0]["E_leave"]
    except (OSError, ValueError, HarnessError) as exc:
        result["partial_metrics_error"] = str(exc)
    return result


def shared_hashes(initial_input, instance_name):
    names = ("exp_chrg_list.csv", "offline_edge_costs.csv", "real_edge_costs.csv",
             "mission_log.csv", f"instance/{instance_name}_0.csv", "avg_power_log.csv")
    return {name: sha256(initial_input / name) for name in names}


def verify_shared_inputs(input_dir, expected):
    actual = {name: sha256(input_dir / name) for name in expected}
    require(actual == expected, "Paired-input sharing contract violated")
    return actual


def prepare_trial(directory, upstream, build, scenario, profile, instance_name, timeout):
    directory.mkdir()
    inp = directory / "input"
    (inp / "instance").mkdir(parents=True)
    (directory / "output").mkdir()
    (directory / "initial-config").mkdir()
    for source in (upstream / "input").glob("*.json"):
        shutil.copy2(source, inp / source.name)
    instance = upstream / "instances" / f"{instance_name}_0.csv"
    shutil.copy2(instance, inp / "instance" / instance.name)
    configs = {}
    for name in ("offline", "online", "simulation"):
        configs[name] = json.loads((inp / f"{name}_config.json").read_text())
        configs[name]["instance"]["sensor_fname"] = f"{instance_name}_0"
        configs[name]["print_result"] = True
    if profile == "main-text-aligned":
        configs["offline"]["ACS"].update(MAIN_TEXT_OVERRIDES)
    configs["simulation"]["simulation"].update(log_power=True, use_avg_power=True)
    configs["online"]["online"]["strategy"]["name"] = "Bayesian"
    powers = json.loads((inp / "real_power_config.json").read_text())
    matches = [v for v in powers.values()
               if v["mean_offset"] == scenario[0] and v["std_offset"] == scenario[1]]
    require(len(matches) == 1, f"Unknown/duplicate power scenario: {scenario}")
    configs["simulation"]["simulation"]["normal"] = matches[0]
    for name, config in configs.items():
        save_json(inp / f"{name}_config.json", config)
        save_json(directory / "initial-config" / f"{name}_config.json", config)
    uav = json.loads((inp / "uav0_status.json").read_text())["drone"]
    with (inp / "mission_log.csv").open("w", newline="", encoding="utf-8") as handle:
        writer = csv.writer(handle)
        writer.writerow(MISSION_FIELDS)
        writer.writerow([uav["x"], uav["y"], uav["z"], 0, 0, uav["t"], uav["E"], 0])
    recorder = ProcessRecorder(directory, timeout)
    recorder.run([build / "offline-planning", "offline_config.json"])
    recorder.run([build / "simulation", "simulation_config.json", "1"])
    node_count = len(read_instance(inp / "instance" / instance.name))
    plans = read_plans(inp / "exp_chrg_list.csv", node_count)
    require(len(plans) == 1 and plans[0][4] == 0, "Invalid initial offline plan")
    matrix = numeric_rows(inp / "offline_edge_costs.csv")
    require(len(matrix) == node_count and all(len(row) == node_count for row in matrix),
            "Invalid offline edge matrix dimensions")
    validate_initial_edges(inp / "real_edge_costs.csv", node_count)
    hashes = shared_hashes(inp, instance_name)
    save_json(directory / "shared-inputs.json", hashes)
    save_json(directory / "summary.json", {"status": "initialized", "shared_hashes": hashes})
    return hashes, uav


def run_strategy(directory, initial, strategy, upstream, build, instance_name,
                 shared, uav, timeout, metadata):
    directory.mkdir()
    steps = []
    summary = dict(metadata, strategy=strategy, started_utc=utc_now())
    started = time.monotonic()
    try:
        shutil.copytree(initial / "input", directory / "input")
        shutil.copytree(initial / "output", directory / "output")
        actual_shared = verify_shared_inputs(directory / "input", shared)
        configs = {name: json.loads((directory / "input" / f"{name}_config.json").read_text())
                   for name in ("online", "simulation")}
        configs["online"]["online"]["strategy"]["name"] = strategy
        configs["simulation"]["simulation"].update(log_power=strategy == "Bayesian", use_avg_power=True)
        (directory / "initial-config").mkdir()
        for name, config in configs.items():
            save_json(directory / "input" / f"{name}_config.json", config)
            save_json(directory / "initial-config" / f"{name}_config.json", config)
        save_json(directory / "manifest.json", dict(metadata, strategy=strategy,
                  shared_initial_sha256=actual_shared, shared_contract_verified=True,
                  configuration_sha256={name: sha256(directory / "initial-config" / f"{name}_config.json")
                                        for name in configs}))
        recorder = ProcessRecorder(directory, timeout)
        instance = read_instance(directory / "input/instance" / f"{instance_name}_0.csv")
        edge_pairs = validate_initial_edges(directory / "input/real_edge_costs.csv", len(instance))
        for iteration in range(len(instance)):
            plans = read_plans(directory / "input/exp_chrg_list.csv", len(instance))
            source, target = map(int, plans[-1][4:6])
            require((source, target) in edge_pairs or (source, target) == (0, 1),
                    "Target physical edge missing")
            require(source == (steps[-1]["target"] if steps else 0), "Stale plan start")
            configs["simulation"]["instance"]["sensor_fname"] = f"{instance_name}_{iteration}"
            save_json(directory / "input/simulation_config.json", configs["simulation"])
            code = recorder.run([build / "simulation", "simulation_config.json", "0"],
                                accepted=tuple(MISSION_CODES), allow_mission_warnings=True)
            steps.append({"iteration": iteration, "source": source, "target": target,
                          "returncode": code, "outcome": MISSION_CODES[code]})
            save_json(directory / "steps.json", steps)
            if code != 0:
                break
            if strategy == "Offline":
                recorder.run([sys.executable, upstream / "scripts/offline_path_delete_one_visit.py",
                              "--sol_fname", "input/exp_chrg_list.csv"])
            else:
                if strategy == "Bayesian":
                    recorder.run([sys.executable, upstream / "scripts/window_sliding_power.py",
                                  "--config", "input/simulation_config.json", "--duration", "900"])
                configs["online"]["instance"]["sensor_fname"] = f"{instance_name}_{iteration + 1}"
                save_json(directory / "input/online_config.json", configs["online"])
                recorder.run([build / "online-planning", "online_config.json"])
        else:
            raise HarnessError("Mission exceeded maximum possible visits")
        summary.update(summarize_mission(directory, strategy, steps, instance_name, uav))
        summary["shared_contract_verified"] = True
    except Exception as exc:
        summary.update(partial_metrics(directory, steps))
        summary.update(status="harness_error", outcome="harness_error", error=str(exc),
                       error_type=type(exc).__name__)
        (directory / "harness-error.txt").write_text(traceback.format_exc(), encoding="utf-8")
    finally:
        summary["wall_seconds"] = round(time.monotonic() - started, 6)
        summary["finished_utc"] = utc_now()
        save_json(directory / "summary.json", summary)
    return summary


def descriptive(values):
    return {"n": len(values), "mean": statistics.mean(values) if values else None,
            "sample_std": statistics.stdev(values) if len(values) > 1 else None,
            "min": min(values) if values else None, "max": max(values) if values else None}


def aggregate_results(results):
    groups = {}
    for result in results:
        groups.setdefault((result["scenario"], result["strategy"]), []).append(result)
    aggregates = []
    for (scenario, strategy), rows in sorted(groups.items()):
        successful = [row for row in rows if row["status"] == "success"]
        failures = {}
        for row in rows:
            if row["status"] != "success":
                failures[row["outcome"]] = failures.get(row["outcome"], 0) + 1
        charged = [row["charged_energy_kJ"] for row in rows if row.get("charged_energy_kJ") is not None]
        aggregates.append({"scenario": scenario, "strategy": strategy,
                           "attempted": len(rows), "successful": len(successful),
                           "mission_failures": sum(row["status"] == "mission_failure" for row in rows),
                           "harness_errors": sum(row["status"] == "harness_error" for row in rows),
                           "failure_counts": failures,
                           "MSR_all_attempts": len(successful) / len(rows),
                           "P_star_success_conditioned_kJ": descriptive([row["charged_energy_kJ"] for row in successful]),
                           "C_star_success_conditioned_kJ": descriptive([row["consumed_energy_kJ"] for row in successful]),
                           "remaining_energy_success_conditioned_kJ": descriptive([row["remaining_energy_kJ"] for row in successful]),
                           "charged_energy_all_attempted_kJ": {
                               "attempted": len(rows), "observed": len(charged),
                               "unobserved": len(rows) - len(charged),
                               "sum_observed": sum(charged),
                               "mean": statistics.mean(charged) if len(charged) == len(rows) else None,
                               "note": "Includes energy actually delivered before mission/harness failure; mean null if any missing."},
                           "online_algorithm_seconds_success_conditioned": descriptive([
                               row["online_algorithm_seconds"] for row in successful])})
    return {"aggregates": aggregates,
            "definitions": {"P_star": "Mean actual delivered energy among successful missions only, kJ",
                            "C_star": "Mean initial minus return energy among successful missions only, kJ",
                            "MSR_all_attempts": "Successful validated missions / all scheduled strategy attempts; harness errors retained",
                            "failure_codes": MISSION_CODES,
                            "scope": "Finite local paired-environment runs, not exact paper replication; no seed control or superiority claim."}}


def save_results(output, results):
    save_json(output / "missions.json", results)
    save_json(output / "aggregate.json", aggregate_results(results))
    keys = ("scenario", "trial", "strategy", "status", "outcome", "terminal_code",
            "terminal_target", "return_home", "serviced_nodes", "charged_energy_kJ",
            "remaining_energy_kJ", "consumed_energy_kJ", "last_logged_energy_kJ",
            "simulated_duration_s", "online_replans", "online_algorithm_seconds",
            "wall_seconds", "evidence_directory", "error")
    with (output / "missions.csv").open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=keys, extrasaction="ignore")
        writer.writeheader()
        writer.writerows(results)


def verify_source_snapshot(upstream, snapshot_path):
    snapshot = json.loads(snapshot_path.read_text())
    require(snapshot.get("commit") == REFERENCE_COMMIT, "Snapshot reference commit mismatch")
    expected = snapshot.get("sha256", {})
    require(expected, "Empty upstream source snapshot")
    actual = {str(path.relative_to(upstream)): sha256(path)
              for path in sorted(upstream.rglob("*"))
              if path.is_file() and path.relative_to(upstream).parts[0] not in (".git", ".idea")}
    missing = sorted(set(expected) - set(actual))
    extra = sorted(set(actual) - set(expected))
    modified = sorted(name for name in set(expected) & set(actual) if expected[name] != actual[name])
    require(not missing and not extra and not modified,
            f"Upstream snapshot mismatch: missing={missing}; extra={extra}; modified={modified}")
    return actual


def source_provenance(upstream, build, profile):
    snapshot_path = upstream.parent / "UPSTREAM_SNAPSHOT.json"
    if not snapshot_path.is_file():
        snapshot_path = ROOT / "UPSTREAM_SNAPSHOT.json"
    require(snapshot_path.is_file(), "Missing UPSTREAM_SNAPSHOT.json; cannot verify original source")
    files = verify_source_snapshot(upstream, snapshot_path)
    record = {"upstream_url": "https://github.com/sysal-bruce-publication/Uncertain-Dynamic-OP",
              "reference_upstream_commit": REFERENCE_COMMIT,
              "reference_commit_note": "Complete vendored source file set verified against UPSTREAM_SNAPSHOT.json; git HEAD also checked if available.",
              "source_snapshot_sha256": sha256(snapshot_path),
              "source_snapshot_verified": True,
              "source_snapshot_files_verified": len(files),
              "source_sha256": files, "binary_sha256": {name: sha256(build / name) for name in BINARIES},
              "runner_sha256": sha256(Path(__file__)), "platform": platform.platform(),
              "python": sys.version, "profile": profile,
              "offline_ACS_overrides": MAIN_TEXT_OVERRIDES if profile == "main-text-aligned" else {},
              "profile_note": "main-text-aligned changes only offline ACS max iterations/no-improvement/tolerance to main text Sec. V-A; Appendix C tolerance differs. Not exact paper configuration.",
              "randomness": "Unchanged upstream random_device; each trial regenerates offline plan and physical edges. Shared within trial, algorithm RNG not paired or seed-controlled.",
              "power_layout": "Average-power edges generated once per trial before cloning, including upstream overlapping whole-cruise sample.",
              "power_window": "Original 900-second script invoked unchanged; known self-subtraction makes it a no-op, so observations accumulate.",
              "exit_code_caveat": "Upstream printed visit/service failure labels are swapped; outcomes use actual return branches.",
              "configuration_policy": "Only instance, print_result, named profile fields, scenario, strategy, and log/layout flags are selected; no C++ changes.",
              "validation_tolerance": "Coordinates: 1e-5 relative/1e-3 absolute; time .02s and energy .002kJ account for upstream six-significant-digit CSV output, not algorithm changes."}
    if (upstream / ".git").exists():
        record["upstream_git_commit"] = subprocess.check_output(
            ["git", "-C", str(upstream), "rev-parse", "HEAD"], text=True).strip()
        require(record["upstream_git_commit"] == REFERENCE_COMMIT, "Upstream git HEAD differs from pinned reference")
        record["upstream_git_status"] = subprocess.check_output(
            ["git", "-C", str(upstream), "status", "--porcelain"], text=True)
        require(not record["upstream_git_status"], "Upstream checkout modified; refusing unchanged-source claim")
    return record


def parse_scenario(value):
    try:
        mean, std = (int(part) for part in value.split(":"))
        if mean <= 0 or std <= 0:
            raise ValueError
        return mean, std
    except ValueError as exc:
        raise argparse.ArgumentTypeError("Use mean:std percentages, e.g. 90:110") from exc


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--upstream", type=Path, default=ROOT / "ADAPT-upstream")
    parser.add_argument("--build-dir", type=Path, default=ROOT / "build")
    parser.add_argument("--output", type=Path,
                        default=ROOT / "runs" / datetime.now().strftime("week11-%Y%m%d-%H%M%S"))
    parser.add_argument("--repeats", type=int, default=50)
    parser.add_argument("--scenarios", nargs="+", type=parse_scenario, default=[(90, 110), (110, 110)])
    parser.add_argument("--profile", choices=("author-default", "main-text-aligned"), default="main-text-aligned")
    parser.add_argument("--instance", default="california20", choices=("california20", "california30", "california40"))
    parser.add_argument("--timeout", type=float, default=180)
    args = parser.parse_args(argv)
    require(args.repeats > 0 and math.isfinite(args.timeout) and args.timeout > 0,
            "repeats and timeout must be positive")
    require(len(args.scenarios) == len(set(args.scenarios)), "Duplicate scenarios")
    upstream, build = args.upstream.resolve(), args.build_dir.resolve()
    for binary in BINARIES:
        require((build / binary).is_file(), f"Missing binary: {build / binary}")
    require((upstream / "instances" / f"{args.instance}_0.csv").is_file(), "Missing input instance")
    provenance = source_provenance(upstream, build, args.profile)
    output = reserve_output(args.output)
    manifest = dict(provenance, started_utc=utc_now(), repeats=args.repeats,
                    scenarios=args.scenarios, strategies=STRATEGIES, instance=args.instance,
                    output=str(output), upstream_path=str(upstream), build_path=str(build),
                    expected_attempts=len(args.scenarios) * args.repeats * len(STRATEGIES),
                    invocation=sys.argv if argv is None else [str(Path(__file__))] + list(argv))
    save_json(output / "manifest.json", manifest)
    results = []
    for scenario in args.scenarios:
        scenario_name = f"mean{scenario[0]}_std{scenario[1]}"
        scenario_dir = output / scenario_name
        scenario_dir.mkdir()
        for trial in range(1, args.repeats + 1):
            trial_dir = scenario_dir / f"trial-{trial:04d}"
            trial_dir.mkdir()
            initial = trial_dir / "initial"
            try:
                shared, uav = prepare_trial(initial, upstream, build, scenario, args.profile,
                                            args.instance, args.timeout)
            except Exception as exc:
                initial.mkdir(exist_ok=True)
                save_json(initial / "summary.json", {"status": "harness_error", "error": str(exc),
                                                     "error_type": type(exc).__name__})
                (initial / "harness-error.txt").write_text(traceback.format_exc(), encoding="utf-8")
                for strategy in STRATEGIES:
                    arm = trial_dir / strategy
                    arm.mkdir()
                    summary = {"scenario": scenario_name, "trial": trial, "strategy": strategy,
                               "status": "harness_error", "outcome": "initialization_error",
                               "simulation_started": False, "error": str(exc),
                               "charged_energy_kJ": None, "remaining_energy_kJ": None,
                               "consumed_energy_kJ": None, "return_home": False,
                               "evidence_directory": str(arm.relative_to(output))}
                    save_json(arm / "summary.json", summary)
                    results.append(summary)
            else:
                for strategy in STRATEGIES:
                    arm = trial_dir / strategy
                    metadata = {"scenario": scenario_name, "trial": trial, "profile": args.profile,
                                "evidence_directory": str(arm.relative_to(output))}
                    results.append(run_strategy(arm, initial, strategy, upstream, build, args.instance,
                                                shared, uav, args.timeout, metadata))
            save_results(output, results)
            save_json(scenario_dir / "aggregate.json", aggregate_results([
                row for row in results if row["scenario"] == scenario_name]))
            print(f"{scenario_name} trial {trial}/{args.repeats}: " + ", ".join(
                f"{r['strategy']}={r['outcome']}" for r in results[-len(STRATEGIES):]), flush=True)
    harness_errors = sum(row["status"] == "harness_error" for row in results)
    save_json(output / "completion.json", {"finished_utc": utc_now(), "attempts": len(results),
                                           "harness_errors": harness_errors,
                                           "all_scheduled_attempts_recorded": len(results) == manifest["expected_attempts"],
                                           "status": "complete" if not harness_errors else "complete_with_harness_errors"})
    print(f"Evidence: {output}; attempted={len(results)}; harness_errors={harness_errors}", flush=True)
    return 2 if harness_errors else 0


if __name__ == "__main__":
    try:
        sys.exit(main())
    except HarnessError as error:
        print(f"Benchmark setup error: {error}", file=sys.stderr)
        sys.exit(2)
