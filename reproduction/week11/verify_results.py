#!/usr/bin/env python3
"""Independent, read-only audit of the Week 11 ADAPT experiment artifacts.

This module deliberately does not import run_benchmark or use its summary as an
input to metric calculation. The simulation equations below were independently
read from the pinned upstream simulation/{main.cpp,drone.cpp,sensor.h} sources.
"""
from __future__ import annotations

import argparse
import collections
import copy
import csv
import hashlib
import json
import math
from pathlib import Path
import statistics
import sys

EPS = 1e-7
E_MAX = 8.82
CAPACITANCE = 10.0
CURRENT_A = 0.825
DECAY_KJ_S = 2.19444e-6
MISSION_COLUMNS = ("x", "y", "z", "t_arrive", "E_arrive", "t_leave", "E_leave", "E_chrg")
ARMS = ("Offline", "DoNothing", "WeightedAvg", "Bayesian")


class AuditError(ValueError):
    """A concrete inconsistency in the recorded artifacts."""


def require(condition, message):
    if not condition:
        raise AuditError(message)


def file_hash(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def json_read(path):
    with Path(path).open(encoding="utf-8") as stream:
        return json.load(stream)


def finite(value, context):
    value = float(value)
    require(math.isfinite(value), f"{context}: non-finite number {value}")
    return value


def csv_rounding(value):
    """Maximum absolute rounding of upstream's default six-significant-digit CSV.

    This is a local serialization bound, not a blanket percent tolerance. Each
    simulation invocation rereads prior rounded mission and sensor CSV values.
    """
    return 0.0 if value == 0 else 0.500001 * 10.0 ** (math.floor(math.log10(abs(value))) - 5)


def near(actual, expected, context, extra=0.0):
    actual, expected = finite(actual, context), finite(expected, context)
    bound = csv_rounding(expected) + extra + 1e-8
    require(abs(actual - expected) <= bound,
            f"{context}: got {actual:.12g}, expected {expected:.12g} (bound {bound:.3g})")


def number_rows(path, header=False, columns=None):
    with Path(path).open(newline="", encoding="utf-8") as stream:
        reader = csv.reader(stream)
        if header:
            names = next(reader, [])
            if columns is not None:
                require(tuple(names) == tuple(columns), f"{path}: wrong header {names}")
        rows = []
        for lineno, row in enumerate(reader, 2 if header else 1):
            require(bool(row), f"{path}:{lineno}: blank CSV row")
            if columns is not None:
                require(len(row) == len(columns), f"{path}:{lineno}: wrong column count")
            rows.append([finite(x, f"{path}:{lineno}") for x in row])
    return rows


def sensor_rows(path):
    rows = number_rows(path, header=True)
    require(len(rows) >= 3 and all(len(r) == 4 for r in rows), f"{path}: invalid sensors")
    require(all(0 <= r[3] <= 42.0001 for r in rows[2:]), f"{path}: invalid sensor voltage")
    return rows


def is_close_sensor(a, b):
    return all(abs(a[i] - b[i]) <= 1.0 for i in range(3))


def audit_edges(path, sensors, averaged=True):
    """Check every directed realization and independent geometry/power identities."""
    edges = {}
    for rowno, row in enumerate(number_rows(path), 1):
        require(len(row) >= 7, f"{path}:{rowno}: missing power samples")
        a, b = int(row[0]), int(row[1])
        require((a, b) not in edges and row[:2] == [a, b], f"{path}: duplicate/noninteger edge")
        require(0 <= a < len(sensors) and 0 <= b < len(sensors), f"{path}: bad edge index")
        source, target = sensors[a], sensors[b]
        takeoff_t = 10.0
        cruise_t = math.hypot(source[0] - target[0], source[1] - target[1]) / 10.0
        landing_t = abs(source[2] + 30.0 - target[2]) / 2.0
        near(row[2], takeoff_t + cruise_t + landing_t, f"{path}: edge {a}->{b} time")
        require(row[3] > 0 and row[2] > 0, f"{path}: nonpositive edge cost")
        if averaged:
            # vector layout: takeoff, interval cruise samples, overall cruise, landing
            p_takeoff, p_cruise, p_landing = row[4], row[-2], row[-1]
            expected = (p_takeoff * takeoff_t + p_cruise * cruise_t + p_landing * landing_t) / 1000.0
            extra = (csv_rounding(p_takeoff) * takeoff_t + csv_rounding(p_cruise) * cruise_t
                     + csv_rounding(p_landing) * landing_t) / 1000.0
            near(row[3], expected, f"{path}: edge {a}->{b} power/energy", extra)
        else:
            require(len(row) == 10, f"{path}: wrong min/max power columns")
            durations = [takeoff_t, cruise_t, landing_t]
            lower = sum(t * p for t, p in zip(durations, row[4:7])) / 1000.0
            upper = sum(t * p for t, p in zip(durations, row[7:10])) / 1000.0
            require(lower - 0.001 <= row[3] <= upper + 0.001, f"{path}: energy outside power bounds")
        edges[a, b] = row
    expected = {(i, j) for i in range(len(sensors)) for j in range(len(sensors))
                if i != 1 and j != 0 and i != j and not is_close_sensor(sensors[i], sensors[j])}
    require(set(edges) == expected, f"{path}: edge coverage missing={expected - set(edges)}, extra={set(edges) - expected}")
    return edges


def audit_trajectory(mission, plans, codes, snapshots, edges, config):
    """Reconstruct every step from raw commands, edge table, and sensor snapshots.

    Actual upstream return mapping is 255=service failure, 254=visit failure,
    253=return failure (its printed labels for the first two are reversed).
    Preserve the upstream double-flight-decay behavior for unserved sensors.
    """
    require(len(mission) >= 2, "mission: no attempted transition")
    require(len(codes) == len(mission) - 1, "mission/command transition count mismatch")
    require(len(plans) >= len(codes), "missing per-transition plans")
    require(len(snapshots) == len(mission), "missing per-transition sensor snapshots")
    require(all(len(row) == 8 for row in mission), "mission: wrong column count")
    for row in mission:
        for x in row:
            finite(x, "mission")
    eta_ipt = finite(config["simulation"]["eta_ipt"], "eta_ipt")
    eta_chrg = finite(config["simulation"]["eta_chrg"], "eta_chrg")
    require(0 < eta_ipt <= 1 and 0 < eta_chrg <= 1, "invalid charging efficiencies")
    previous_target = 0
    serviced = []
    outcomes = []
    charge_sum = 0.0
    for step, (previous, observed, plan, code) in enumerate(zip(mission, mission[1:], plans, codes)):
        label = f"step {step}"
        require(len(plan) >= 6, f"{label}: short plan")
        source, target = int(plan[4]), int(plan[5])
        require([source, target] == plan[4:6], f"{label}: noninteger path")
        require(source == previous_target, f"{label}: discontinuous path {source} != {previous_target}")
        require(target != source and 0 < target < len(snapshots[step]), f"{label}: invalid target")
        current_sensors = snapshots[step]
        next_sensors = snapshots[step + 1]
        require(len(current_sensors) == len(next_sensors), f"{label}: sensor count changed")
        for axis in range(3):
            near(previous[axis], current_sensors[source][axis], f"{label}: source coordinate", csv_rounding(current_sensors[source][axis]))
            near(observed[axis], current_sensors[target][axis], f"{label}: target coordinate")
        if (source, target) in edges:
            flight_t, flight_e = edges[source, target][2:4]
        else:
            # Upstream intentionally omits co-located depots; readVisitCost leaves zero.
            require(is_close_sensor(current_sensors[source], current_sensors[target]), f"{label}: missing nonzero edge")
            flight_t, flight_e = 0.0, 0.0
        arrive_t = previous[5] + flight_t
        arrive_e = previous[6] - flight_e
        require(previous[5] >= 0 and previous[6] > EPS, f"{label}: continued after terminal state")
        expected_volt = [r[3] for r in current_sensors]
        if arrive_e > EPS:
            energies = [CAPACITANCE * v * v / 2000 for v in expected_volt]
            for i in range(2, len(energies)):
                energies[i] -= DECAY_KJ_S * flight_t
                require(energies[i] >= 0, f"{label}: invalid sensor energy")
                expected_volt[i] = math.sqrt(2000 * energies[i] / CAPACITANCE)
            if target == 1:
                expected_code, state = 1, "success"
                expected_row = [*current_sensors[target][:3], arrive_t, arrive_e, -1.0, -1.0, 0.0]
            else:
                prize = E_MAX - energies[target]
                charge_t = CAPACITANCE * (42.0 - expected_volt[target]) / CURRENT_A / eta_chrg
                leave_t, leave_e = arrive_t + charge_t, arrive_e - prize / eta_ipt
                if leave_e > EPS:
                    expected_code, state = 0, "continue"
                    expected_row = [*current_sensors[target][:3], arrive_t, arrive_e, leave_t, leave_e, prize]
                    expected_volt[target] = 42.0
                    for i in range(2, len(energies)):
                        if i != target:
                            # Deliberately match upstream: getDeltaTime includes flight.
                            energies[i] -= DECAY_KJ_S * (flight_t + charge_t)
                            expected_volt[i] = math.sqrt(2000 * energies[i] / CAPACITANCE)
                    serviced.append(target)
                else:
                    expected_code, state = 255, "service_failure"
                    expected_row = [*current_sensors[target][:3], leave_t, leave_e, -1.0, -1.0, 0.0]
        else:
            expected_code = 253 if target == 1 else 254
            state = "return_failure" if target == 1 else "visit_failure"
            expected_row = [*current_sensors[target][:3], arrive_t, arrive_e, -1.0, -1.0, 0.0]
        require(code == expected_code, f"{label}: exit {code}, independently expected {expected_code} ({state})")
        require(step == len(codes) - 1 or code == 0, f"{label}: execution after terminal return")
        for col, (actual, expected) in enumerate(zip(observed, expected_row)):
            near(actual, expected, f"{label} {MISSION_COLUMNS[col]}")
        for i, (original, after, voltage) in enumerate(zip(current_sensors, next_sensors, expected_volt)):
            for axis in range(3):
                near(after[axis], original[axis], f"{label}: sensor {i} coordinate")
            near(after[3], voltage, f"{label}: sensor {i} voltage")
        charge_sum += observed[7]
        outcomes.append(state)
        previous_target = target
    require(outcomes[-1] != "continue", "mission ended without simulator terminal result")
    require(len(serviced) == len(set(serviced)), "sensor serviced more than once")
    success = outcomes[-1] == "success"
    last = mission[-1]
    require(not success or (previous_target == 1 and last[4] > EPS), "success without depot/positive energy")
    return {"success": success, "status": outcomes[-1], "terminal_return_code": codes[-1],
            "simulation_steps": len(codes), "serviced_nodes": len(serviced),
            "charged_energy_kj": charge_sum, "remaining_energy_kj": last[4],
            "consumed_energy_kj": mission[0][6] - last[4],
            "duration_s": last[3] - mission[0][5], "visited_path": [0] + [int(p[5]) for p in plans[:len(codes)]]}


def exact_or_float(actual, expected, label):
    """Compare published statistics, with only floating-point evaluation tolerance."""
    if isinstance(expected, dict):
        require(isinstance(actual, dict), f"{label}: expected object")
        for key, value in expected.items():
            require(key in actual, f"{label}: missing {key}")
            exact_or_float(actual[key], value, f"{label}.{key}")
    elif isinstance(expected, list):
        require(isinstance(actual, list) and len(actual) == len(expected), f"{label}: list length mismatch")
        for i, (a, b) in enumerate(zip(actual, expected)):
            exact_or_float(a, b, f"{label}[{i}]")
    elif isinstance(expected, float):
        require(isinstance(actual, (float, int)) and not isinstance(actual, bool)
                and math.isfinite(actual) and math.isclose(actual, expected, rel_tol=1e-11, abs_tol=1e-10),
                f"{label}: got {actual!r}, independently expected {expected!r}")
    else:
        require(type(actual) is type(expected) and actual == expected,
                f"{label}: got {actual!r}, independently expected {expected!r}")


def source_check(upstream, manifest, snapshot_path):
    snapshot = json_read(snapshot_path)
    require(snapshot["commit"] == "e9967bf0d7a42c9051bdb1759bebeeac42d30681", "unexpected pinned upstream commit")
    for relative, expected in snapshot["sha256"].items():
        path = upstream / relative
        require(path.is_file() and file_hash(path) == expected, f"upstream source changed/missing: {relative}")
    required = {relative: digest for relative, digest in snapshot["sha256"].items()
                if relative.split("/")[0] in ("src", "scripts", "input", "instances")}
    recorded = manifest["source_sha256"]
    require(set(required) <= set(recorded) <= set(snapshot["sha256"])
            and all(snapshot["sha256"][p] == digest for p, digest in recorded.items()),
            "run source hash manifest differs from pinned snapshot")
    require(manifest["reference_upstream_commit"] == snapshot["commit"], "run source commit differs")
    return len(snapshot["sha256"])


def expected_configurations(upstream, manifest, scenario):
    configs = {name: json_read(upstream / "input" / f"{name}_config.json")
               for name in ("offline", "online", "simulation")}
    instance_name = manifest["instance"] + "_0"
    for config in configs.values():
        config["instance"]["sensor_fname"] = instance_name
        config["print_result"] = True
    require(manifest["profile"] in ("main-text-aligned", "author-default"), "unsupported profile")
    overrides = {"num_iters_acs": 250, "max_no_impr_acs": 25, "tol": 0.0001} if manifest["profile"] == "main-text-aligned" else {}
    require(manifest["offline_ACS_overrides"] == overrides, "unexpected ACS override declaration")
    configs["offline"]["ACS"].update(overrides)
    configs["online"]["online"]["strategy"]["name"] = "Bayesian"
    power_options = json_read(upstream / "input/real_power_config.json")
    matches = [row for row in power_options.values()
               if [row["mean_offset"], row["std_offset"]] == list(scenario)]
    require(len(matches) == 1, "scenario not found in source power config")
    configs["simulation"]["simulation"].update(log_power=True, use_avg_power=True, normal=matches[0])
    return configs


def command_kind(event):
    argv = event.get("argv", [])
    require(isinstance(argv, list) and argv, "invalid process argv")
    name = Path(argv[0]).name
    if name in ("simulation", "offline-planning", "online-planning"):
        return name
    if len(argv) > 1 and Path(argv[1]).name in ("offline_path_delete_one_visit.py", "window_sliding_power.py"):
        return Path(argv[1]).name
    raise AuditError(f"unexpected process command: {argv}")


def audit_processes(directory, strategy=None):
    events = json_read(directory / "processes.json")
    require(events, f"{directory}: no processes")
    for i, event in enumerate(events, 1):
        require(event["sequence"] == i, f"{directory}: process sequence gap")
        require(not event["timed_out"] and not event.get("error"), f"{directory}: timeout/process error")
        require(finite(event["wall_seconds"], "process wall time") >= 0, "negative process duration")
        streams = []
        for field in ("stdout_file", "stderr_file"):
            relative = Path(event[field])
            require(not relative.is_absolute() and ".." not in relative.parts, "unsafe process stream path")
            path = directory / relative
            require(path.is_file(), f"missing process stream: {path}")
            streams.append(path.read_text(encoding="utf-8"))
        require("[ERROR]" not in "".join(streams), f"{directory}: upstream error stream")
        if command_kind(event) != "simulation" or event["returncode"] not in (253, 254, 255):
            require("[WARN]" not in "".join(streams), f"{directory}: unexpected upstream warning")
    if strategy is None:
        require([command_kind(e) for e in events] == ["offline-planning", "simulation"], "initial process schedule differs")
        require(events[0]["argv"][1:] == ["offline_config.json"]
                and events[1]["argv"][1:] == ["simulation_config.json", "1"], "initial process arguments differ")
        require(all(e["returncode"] == 0 for e in events), "initialization process failed")
        return []
    codes = []
    pos = 0
    while pos < len(events):
        event = events[pos]
        require(command_kind(event) == "simulation" and event["argv"][1:] == ["simulation_config.json", "0"],
                f"{directory}: expected simulator transition at event {pos + 1}")
        code = event["returncode"]
        require(type(code) is int and code in (0, 1, 253, 254, 255), "unexpected simulator code")
        codes.append(code)
        pos += 1
        if code != 0:
            require(pos == len(events), "commands continued after terminal simulator status")
            break
        expected = (["offline_path_delete_one_visit.py"] if strategy == "Offline" else
                    (["window_sliding_power.py", "online-planning"] if strategy == "Bayesian" else ["online-planning"]))
        for name in expected:
            require(pos < len(events), "missing post-service planner/process")
            event = events[pos]
            require(command_kind(event) == name and event["returncode"] == 0, f"wrong/failed post-service command {name}")
            tail = event["argv"][2:] if name.endswith(".py") else event["argv"][1:]
            args = (["--sol_fname", "input/exp_chrg_list.csv"] if name.startswith("offline_path") else
                    ["--config", "input/simulation_config.json", "--duration", "900"] if name.startswith("window_sliding") else
                    ["online_config.json"])
            require(tail == args, f"wrong command arguments for {name}")
            pos += 1
    require(codes and codes[-1] != 0, "missing completed terminal simulator process")
    return codes


def audit_trial_initial(directory, upstream, manifest, scenario):
    expected = expected_configurations(upstream, manifest, scenario)
    for name, config in expected.items():
        for base in ("initial-config", "input"):
            require(json_read(directory / base / f"{name}_config.json") == config,
                    f"{directory}: unexpected initial {name} config")
    audit_processes(directory)
    inp = directory / "input"
    instance = manifest["instance"]
    shared = json_read(directory / "shared-inputs.json")
    required_files = {"exp_chrg_list.csv", "offline_edge_costs.csv", "real_edge_costs.csv",
                      "mission_log.csv", f"instance/{instance}_0.csv", "avg_power_log.csv"}
    require(set(shared) == required_files, "shared-input declaration has missing/extra files")
    require(all(file_hash(inp / name) == digest for name, digest in shared.items()), "initial shared-input hash mismatch")
    require(file_hash(inp / f"instance/{instance}_0.csv") == file_hash(upstream / f"instances/{instance}_0.csv"),
            "trial sensor instance differs from author instance")
    sensors = sensor_rows(inp / f"instance/{instance}_0.csv")
    offline_edges = number_rows(inp / "offline_edge_costs.csv")
    require(len(offline_edges) == len(sensors) and all(len(row) == len(sensors) for row in offline_edges),
            "invalid initial offline matrix")
    require(all(x >= 0 for row in offline_edges for x in row), "negative offline matrix cost")
    edges = audit_edges(inp / "real_edge_costs.csv", sensors, averaged=True)
    plans = number_rows(inp / "exp_chrg_list.csv")
    require(len(plans) == 1, "initial plan is not a single row")
    uav = json_read(upstream / "input/uav0_status.json")["drone"]
    initial_rows = number_rows(inp / "mission_log.csv", header=True, columns=MISSION_COLUMNS)
    require(initial_rows == [[uav["x"], uav["y"], uav["z"], 0, 0, uav["t"], uav["E"], 0]], "incorrect initial UAV mission row")
    require((inp / "avg_power_log.csv").read_bytes() == b"", "initial power log not empty")
    return expected, shared, edges, plans, initial_rows


def audit_arm(directory, initial, upstream, manifest, trial_info, expected_configs, shared, edges, initial_plans, initial_rows):
    strategy = directory.name
    arm_manifest = json_read(directory / "manifest.json")
    require(arm_manifest["shared_initial_sha256"] == shared and arm_manifest["shared_contract_verified"] is True,
            "arm does not declare identical shared inputs")
    for key, value in dict(trial_info, strategy=strategy, profile=manifest["profile"]).items():
        require(arm_manifest[key] == value, f"arm manifest {key} mismatch")
    configs = copy.deepcopy(expected_configs)
    configs["online"]["online"]["strategy"]["name"] = strategy
    configs["simulation"]["simulation"]["log_power"] = strategy == "Bayesian"
    for name in ("online", "simulation"):
        path = directory / "initial-config" / f"{name}_config.json"
        require(json_read(path) == configs[name], f"arm unexpected initial {name} config")
        require(arm_manifest["configuration_sha256"][name] == file_hash(path), "configuration hash mismatch")
    inp = directory / "input"
    instance = manifest["instance"]
    for name in ("offline_edge_costs.csv", "real_edge_costs.csv", f"instance/{instance}_0.csv"):
        require(file_hash(inp / name) == shared[name], f"arm shared file changed: {name}")
    for name in ("offline_config.json", "uav0_status.json", "real_power_config.json", "path0_config.json"):
        require(file_hash(inp / name) == file_hash(initial / "input" / name), f"unexpected arm change to {name}")
    initial_mission_bytes = (initial / "input/mission_log.csv").read_bytes()
    initial_plan_bytes = (initial / "input/exp_chrg_list.csv").read_bytes()
    require((inp / "mission_log.csv").read_bytes().startswith(initial_mission_bytes), "arm initial mission bytes differ")
    require((inp / "exp_chrg_list.csv").read_bytes().startswith(initial_plan_bytes), "arm initial plan bytes differ")
    codes = audit_processes(directory, strategy)
    mission = number_rows(inp / "mission_log.csv", header=True, columns=MISSION_COLUMNS)
    plans = number_rows(inp / "exp_chrg_list.csv")
    require(mission[:1] == initial_rows and plans[:1] == initial_plans, "arm initial state differs")
    require(len(plans) == len(codes), "plan count differs from actual simulator commands")
    snapshots = [sensor_rows(inp / "instance" / f"{instance}_{i}.csv") for i in range(len(codes) + 1)]
    require(len(list((inp / "instance").glob("*.csv"))) == len(snapshots), "unexpected extra/missing state snapshots")
    for i, plan in enumerate(plans):
        nodes = plan[4:]
        require(len(nodes) >= 2 and all(x == int(x) and 0 <= x < len(snapshots[0]) for x in nodes), "invalid plan node")
        require(nodes[-1] == 1 and 1 not in nodes[:-1] and 0 not in nodes[1:] and len(nodes) == len(set(nodes)), "invalid plan structure")
        require(plan[0] >= 0 and plan[2] >= 0 and plan[3] >= 0, "invalid plan objective/time")
        if i:
            if strategy == "Offline":
                require(plan == plans[i - 1][:4] + plans[i - 1][5:], "Offline plan was not the unchanged suffix")
            elif strategy == "Bayesian":
                require(any(abs(plan[1] - p * 100) < 1e-7 for p in configs["online"]["online"]["strategy"]["Bayesian"]["cdf_probs"]), "unexpected Bayesian belief")
            else:
                require(plan[1] == 0, "baseline belief must be zero")
    raw = audit_trajectory(mission, plans, codes, snapshots, edges, configs["simulation"])
    for name in ("simulation", "online"):
        config = copy.deepcopy(configs[name])
        iteration = len(codes) - 1 if name == "simulation" or strategy != "Offline" else 0
        config["instance"]["sensor_fname"] = f"{instance}_{iteration}"
        require(json_read(inp / f"{name}_config.json") == config, f"unexpected final {name} config")
    steps = json_read(directory / "steps.json")
    outcome_map = {0: "continue", 1: "success", 255: "service_failed", 254: "visit_failed", 253: "return_home_failed"}
    expected_steps = [{"iteration": i, "source": int(plan[4]), "target": int(plan[5]),
                       "returncode": code, "outcome": outcome_map[code]}
                      for i, (plan, code) in enumerate(zip(plans, codes))]
    require(steps == expected_steps, "steps.json differs from raw commands/plans")
    powers = number_rows(inp / "avg_power_log.csv")
    if strategy == "Bayesian":
        expected_power = [[mission[i + 1][5]] + edges[int(plan[4]), int(plan[5])][4:]
                          for i, (plan, code) in enumerate(zip(plans, codes)) if code == 0]
        require(powers == expected_power, "Bayesian observed power differs from shared realization")
    else:
        require(not powers, "non-Bayesian arm unexpectedly logged power")
    success = raw["success"]
    expected_summary = dict(trial_info, strategy=strategy, profile=manifest["profile"],
        status="success" if success else "mission_failure", outcome=outcome_map[codes[-1]],
        terminal_code=codes[-1], terminal_target=int(plans[-1][5]), return_home=success,
        route=raw["visited_path"], attempted_sensor_nodes=sum(int(p[5]) != 1 for p in plans),
        serviced_nodes=raw["serviced_nodes"], charged_energy_kJ=raw["charged_energy_kj"],
        initial_energy_kJ=mission[0][6], remaining_energy_kJ=raw["remaining_energy_kj"] if success else None,
        consumed_energy_kJ=raw["consumed_energy_kj"] if success else None,
        last_logged_energy_kJ=raw["remaining_energy_kj"], simulated_duration_s=raw["duration_s"],
        online_replans=0 if strategy == "Offline" else len(plans) - 1,
        online_algorithm_seconds=0 if strategy == "Offline" else sum(p[0] for p in plans[1:]),
        offline_algorithm_seconds=plans[0][0], shared_contract_verified=True)
    published = json_read(directory / "summary.json")
    exact_or_float(published, expected_summary, f"{directory}/summary.json")
    return expected_summary, published


def moments(values):
    return {"n": len(values), "mean": statistics.mean(values) if values else None,
            "sample_std": statistics.stdev(values) if len(values) > 1 else None,
            "min": min(values) if values else None, "max": max(values) if values else None}


def recompute_groups(rows):
    grouped = collections.defaultdict(list)
    for row in rows:
        grouped[row["scenario"], row["strategy"]].append(row)
    result = []
    for (scenario, strategy), attempts in sorted(grouped.items()):
        successful = [r for r in attempts if r["return_home"]]
        charged = [r["charged_energy_kJ"] for r in attempts]
        result.append({"scenario": scenario, "strategy": strategy, "attempted": len(attempts),
            "successful": len(successful), "mission_failures": len(attempts) - len(successful), "harness_errors": 0,
            "failure_counts": dict(collections.Counter(r["outcome"] for r in attempts if not r["return_home"])),
            "MSR_all_attempts": len(successful) / len(attempts),
            "P_star_success_conditioned_kJ": moments([r["charged_energy_kJ"] for r in successful]),
            "C_star_success_conditioned_kJ": moments([r["consumed_energy_kJ"] for r in successful]),
            "remaining_energy_success_conditioned_kJ": moments([r["remaining_energy_kJ"] for r in successful]),
            "charged_energy_all_attempted_kJ": {"attempted": len(attempts), "observed": len(attempts), "unobserved": 0,
                                               "sum_observed": sum(charged), "mean": statistics.mean(charged)},
            "online_algorithm_seconds_success_conditioned": moments([r["online_algorithm_seconds"] for r in successful])})
    return result


def audit_dataset(results, upstream, snapshot_path, expected_attempts=None, build=None):
    errors, rows, originals = [], [], []
    manifest = json_read(results / "manifest.json")
    source_count = source_check(upstream, manifest, snapshot_path)
    require(tuple(manifest["strategies"]) == ARMS, "unexpected strategy list")
    repeats = manifest["repeats"]
    require(type(repeats) is int and repeats > 0, "invalid repeat count")
    scenarios = manifest["scenarios"]
    require(len(scenarios) == len(set(map(tuple, scenarios))), "duplicate scenarios")
    planned = len(scenarios) * repeats * len(ARMS)
    require(manifest["expected_attempts"] == planned, "manifest denominator mismatch")
    if expected_attempts is not None:
        require(planned == expected_attempts, f"expected {expected_attempts} attempts, manifest planned {planned}")
    if build is not None:
        for name, digest in manifest["binary_sha256"].items():
            require(file_hash(build / name) == digest, f"binary hash mismatch: {name}")
    expected_dirs = []
    for scenario in scenarios:
        name = f"mean{scenario[0]}_std{scenario[1]}"
        trials_on_disk = sorted(p.name for p in (results / name).glob("trial-*") if p.is_dir())
        require(trials_on_disk == [f"trial-{i:04d}" for i in range(1, repeats + 1)], f"{name}: missing/extra trials")
        for trial in range(1, repeats + 1):
            trial_dir = results / name / f"trial-{trial:04d}"
            expected_dirs.extend(str((trial_dir / arm).relative_to(results)) for arm in ARMS)
            try:
                initial_data = audit_trial_initial(trial_dir / "initial", upstream, manifest, scenario)
            except (AuditError, OSError, ValueError, KeyError, TypeError) as exc:
                errors.append({"evidence": str(trial_dir.relative_to(results)), "error": str(exc), "unverified_attempts": 4})
                continue
            for arm in ARMS:
                directory = trial_dir / arm
                info = {"scenario": name, "trial": trial, "evidence_directory": str(directory.relative_to(results))}
                try:
                    row, original = audit_arm(directory, trial_dir / "initial", upstream, manifest, info, *initial_data)
                    rows.append(row)
                    originals.append(original)
                except (AuditError, OSError, ValueError, KeyError, TypeError, IndexError) as exc:
                    errors.append({"evidence": info["evidence_directory"], "error": str(exc), "unverified_attempts": 1})
    mission_rows = json_read(results / "missions.json")
    require(len(mission_rows) == planned, "missions.json omitted/added planned attempts")
    require([r["evidence_directory"] for r in mission_rows] == expected_dirs, "missions.json order/identity differs from planned attempts")
    completion = json_read(results / "completion.json")
    require(completion["attempts"] == planned and completion["all_scheduled_attempts_recorded"] is True, "incomplete planned denominator")
    if not errors:
        require(mission_rows == originals, "missions.json differs from individual summaries")
        require(completion["status"] == "complete" and completion["harness_errors"] == 0, "completion receipt has unresolved harness errors")
        groups = recompute_groups(rows)
        exact_or_float(json_read(results / "aggregate.json")["aggregates"], groups, "aggregate.json")
        for scenario in scenarios:
            name = f"mean{scenario[0]}_std{scenario[1]}"
            expected_groups = [g for g in groups if g["scenario"] == name]
            exact_or_float(json_read(results / name / "aggregate.json")["aggregates"], expected_groups, name + "/aggregate.json")
        with (results / "missions.csv").open(newline="", encoding="utf-8") as stream:
            csv_rows = list(csv.DictReader(stream))
        require(len(csv_rows) == planned, "missions.csv denominator mismatch")
        for i, (csv_row, original) in enumerate(zip(csv_rows, originals)):
            for key, value in csv_row.items():
                require(value == (str(original[key]) if original.get(key) is not None else ""), f"missions.csv row {i + 1} field {key} mismatch")
    else:
        groups = recompute_groups(rows)
    return {"status": "PASS" if not errors else "FAIL", "planned_attempts": planned,
            "independently_verified_attempts": len(rows), "unverified_attempts": planned - len(rows),
            "source_snapshot_files_verified": source_count, "binary_hashes_verified": build is not None,
            "shared_trial_environments": len(scenarios) * repeats,
            "errors": errors, "independent_aggregates": groups,
            "checks": ["pinned upstream snapshot SHA256", "exact allowed configuration changes", "planned-attempt denominator",
                       "shared realization/plan/initial-state hashes", "complete raw process schedule and return codes",
                       "every edge geometry and average-power energy identity", "every mission energy/time/charging transition",
                       "every sensor state update", "Bayesian observation provenance", "summary/CSV/group statistics recomputed"],
            "numeric_policy": "Per-field six-significant-digit C++ serialization bounds, plus rounded power-term bounds; summary comparisons only 1e-11 relative/1e-10 absolute floating-point tolerance.",
            "source_quirks_preserved": ["255 service/254 visit labels follow actual return branches",
                                        "double flight decay for other sensors", "terminal service failure stores post-service values in arrival fields",
                                        "overlapping whole-cruise average sample", "no-op upstream window script"],
            "limitations": ["Read-only consistency audit, not authentication of execution authorship",
                            "No seeded RNG or exact recovery of authors' paper experiments",
                            "When errors exist, independent aggregate rows cover verified attempts only; planned and unverified denominators remain explicit."]}


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--results", required=True, type=Path)
    parser.add_argument("--upstream", type=Path, default=Path(__file__).resolve().parents[1] / "ADAPT-upstream")
    parser.add_argument("--snapshot", type=Path, help="Pinned UPSTREAM_SNAPSHOT.json (default: upstream sibling)")
    parser.add_argument("--expected-attempts", type=int, help="Explicit external denominator, e.g. 400 for formal or 8 for preflight")
    parser.add_argument("--build-dir", type=Path, help="Optionally independently hash the executed binaries")
    args = parser.parse_args(argv)
    try:
        report = audit_dataset(args.results.resolve(), args.upstream.resolve(),
                               args.snapshot or args.upstream.parent / "UPSTREAM_SNAPSHOT.json",
                               args.expected_attempts, args.build_dir)
    except (AuditError, OSError, ValueError, KeyError, TypeError, IndexError) as exc:
        report = {"status": "FAIL", "errors": [{"error": str(exc)}]}
    print(json.dumps(report, indent=2, allow_nan=False))
    return 0 if report["status"] == "PASS" else 2


if __name__ == "__main__":
    sys.exit(main())
