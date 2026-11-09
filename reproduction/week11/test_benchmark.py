#!/usr/bin/env python3
"""Harness contract tests; synthetic fixtures are never benchmark evidence."""
import csv
import importlib.util
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

SPEC = importlib.util.spec_from_file_location("week11_benchmark", Path(__file__).with_name("run_benchmark.py"))
benchmark = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(benchmark)


class BenchmarkContracts(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.root = Path(self.temp.name)

    def tearDown(self):
        self.temp.cleanup()

    def mission_fixture(self, code=1, service=True):
        inp = self.root / "input"
        (inp / "instance").mkdir(parents=True)
        (inp / "instance/california20_0.csv").write_text(
            "lat,lon,alt,volt\n0,0,0,0\n0,0,0,0\n10,20,0,40\n")
        initial = [0, 0, 0, 0, 0, 0, 100, 0]
        intermediate = [10, 20, 0, 10, 90, 20, 70, 8]
        rows = [initial]
        steps = []
        if service:
            rows.append(intermediate)
            steps.append({"source": 0, "target": 2, "returncode": 0})
        terminal_target = 1 if code in (1, 253) else 2
        if terminal_target == 2 and service:
            raise ValueError("Use no-service fixture for failed first sensor")
        terminal_pos = [0, 0, 0] if terminal_target == 1 else [10, 20, 0]
        rows.append(terminal_pos + [30, 60 if code == 1 else -2, -1, -1, 0])
        steps.append({"source": 2 if service else 0, "target": terminal_target, "returncode": code})
        with (inp / "mission_log.csv").open("w", newline="") as handle:
            writer = csv.writer(handle)
            writer.writerow(benchmark.MISSION_FIELDS)
            writer.writerows(rows)
        initial_plan = "0.01,0,8,40,0,2,1\n" if service or terminal_target == 2 else "0.01,0,0,0,0,1\n"
        (inp / "exp_chrg_list.csv").write_text(initial_plan + ("0.005,99.9,0,10,2,1\n" if service else ""))
        return steps, {"x": 0, "y": 0, "z": 0, "t": 0, "E": 100}

    def test_failure_codes_follow_actual_source_not_printed_labels(self):
        # Execute real child processes to check Linux modulo-256 return handling.
        if sys.platform == "win32":
            self.skipTest("The benchmark targets Linux/WSL")
        expected = {-1: "service_failed", -2: "visit_failed", -3: "return_home_failed"}
        for raw, outcome in expected.items():
            child = subprocess.run([sys.executable, "-c", f"import sys; sys.exit({raw})"], check=False)
            self.assertEqual(benchmark.MISSION_CODES[child.returncode], outcome)

    def test_timeout_preserves_command_and_partial_streams(self):
        recorder = benchmark.ProcessRecorder(self.root, timeout=0.2)
        code = "import sys,time; print('before-timeout',flush=True); print('stderr-evidence',file=sys.stderr,flush=True); time.sleep(2)"
        with self.assertRaises(benchmark.HarnessError):
            recorder.run([sys.executable, "-c", code])
        events = json.loads((self.root / "processes.json").read_text())
        self.assertEqual(len(events), 1)
        self.assertTrue(events[0]["timed_out"])
        self.assertIsNone(events[0]["returncode"])
        self.assertIn("before-timeout", (self.root / events[0]["stdout_file"]).read_text())
        self.assertIn("stderr-evidence", (self.root / events[0]["stderr_file"]).read_text())
        self.assertEqual(events[0]["argv"][0], sys.executable)

    def test_unexpected_process_exit_is_not_swallowed(self):
        recorder = benchmark.ProcessRecorder(self.root)
        with self.assertRaises(benchmark.HarnessError):
            recorder.run([sys.executable, "-c", "raise SystemExit(7)"])
        self.assertEqual(json.loads((self.root / "processes.json").read_text())[0]["returncode"], 7)

    def test_mission_metrics_come_from_actual_rows_not_plan_prize(self):
        steps, uav = self.mission_fixture()
        result = benchmark.summarize_mission(self.root, "Bayesian", steps, "california20", uav)
        self.assertEqual(result["status"], "success")
        self.assertEqual(result["charged_energy_kJ"], 8)
        self.assertEqual(result["consumed_energy_kJ"], 40)
        self.assertEqual(result["remaining_energy_kJ"], 60)
        self.assertEqual(result["serviced_nodes"], 1)
        self.assertEqual(result["route"], [0, 2, 1])

    def test_zero_service_return_home_is_valid(self):
        steps, uav = self.mission_fixture(service=False)
        result = benchmark.summarize_mission(self.root, "Offline", steps, "california20", uav)
        self.assertEqual(result["status"], "success")
        self.assertEqual(result["serviced_nodes"], 0)
        self.assertEqual(result["charged_energy_kJ"], 0)

    def test_mission_failure_keeps_delivered_energy_without_false_remaining(self):
        steps, uav = self.mission_fixture(code=253)
        result = benchmark.summarize_mission(self.root, "Bayesian", steps, "california20", uav)
        self.assertEqual(result["status"], "mission_failure")
        self.assertEqual(result["outcome"], "return_home_failed")
        self.assertEqual(result["charged_energy_kJ"], 8)
        self.assertEqual(result["last_logged_energy_kJ"], -2)
        self.assertIsNone(result["remaining_energy_kJ"])
        self.assertIsNone(result["consumed_energy_kJ"])

    def test_failure_aggregates_are_not_conditioned_on_success(self):
        rows = [{"scenario": "mean110_std110", "strategy": "Bayesian", "status": "success",
                 "outcome": "success", "charged_energy_kJ": 10, "consumed_energy_kJ": 80,
                 "remaining_energy_kJ": 20, "online_algorithm_seconds": 0.1},
                {"scenario": "mean110_std110", "strategy": "Bayesian", "status": "mission_failure",
                 "outcome": "return_home_failed", "charged_energy_kJ": 4,
                 "consumed_energy_kJ": None, "remaining_energy_kJ": None}]
        aggregate = benchmark.aggregate_results(rows)["aggregates"][0]
        self.assertEqual(aggregate["MSR_all_attempts"], 0.5)
        self.assertEqual(aggregate["P_star_success_conditioned_kJ"]["mean"], 10)
        self.assertEqual(aggregate["P_star_success_conditioned_kJ"]["n"], 1)
        self.assertEqual(aggregate["C_star_success_conditioned_kJ"]["mean"], 80)
        self.assertEqual(aggregate["charged_energy_all_attempted_kJ"]["mean"], 7)
        self.assertEqual(aggregate["failure_counts"], {"return_home_failed": 1})
        rows.append({"scenario": "mean110_std110", "strategy": "Bayesian", "status": "harness_error",
                     "outcome": "initialization_error", "charged_energy_kJ": None})
        aggregate = benchmark.aggregate_results(rows)["aggregates"][0]
        self.assertEqual(aggregate["MSR_all_attempts"], 1 / 3)
        self.assertEqual(aggregate["harness_errors"], 1)
        self.assertIsNone(aggregate["charged_energy_all_attempted_kJ"]["mean"])
        self.assertEqual(aggregate["charged_energy_all_attempted_kJ"]["unobserved"], 1)

    def test_nonempty_output_refused_without_mutation(self):
        sentinel = self.root / "keep.txt"
        sentinel.write_text("original evidence")
        with self.assertRaises(benchmark.HarnessError):
            benchmark.reserve_output(self.root)
        self.assertEqual(sentinel.read_text(), "original evidence")

    def test_sharing_contract_detects_changed_edge(self):
        (self.root / "real_edge_costs.csv").write_text("0,2,1,2,3,4,5\n")
        expected = {"real_edge_costs.csv": benchmark.sha256(self.root / "real_edge_costs.csv")}
        self.assertEqual(benchmark.verify_shared_inputs(self.root, expected), expected)
        (self.root / "real_edge_costs.csv").write_text("0,2,1,9,3,4,5\n")
        with self.assertRaises(benchmark.HarnessError):
            benchmark.verify_shared_inputs(self.root, expected)

    def test_nonfinite_and_bad_route_are_rejected(self):
        steps, uav = self.mission_fixture()
        plan = self.root / "input/exp_chrg_list.csv"
        plan.write_text("0.01,0,8,40,0,2,1\n0.005,99.9,0,10,2,2,1\n")
        with self.assertRaises(benchmark.HarnessError):
            benchmark.summarize_mission(self.root, "Bayesian", steps, "california20", uav)
        plan.write_text("0.01,0,8,40,0,2,1\n0.005,99.9,0,10,2,1\n")
        mission = self.root / "input/mission_log.csv"
        mission.write_text(mission.read_text().replace("30,60", "30,nan"))
        with self.assertRaises(benchmark.HarnessError):
            benchmark.summarize_mission(self.root, "Bayesian", steps, "california20", uav)

    def test_terminal_target_and_status_must_agree(self):
        steps, uav = self.mission_fixture(code=255, service=False)
        result = benchmark.summarize_mission(self.root, "DoNothing", steps, "california20", uav)
        self.assertEqual(result["outcome"], "service_failed")
        self.assertEqual(result["serviced_nodes"], 0)
        steps[-1]["returncode"] = 253
        with self.assertRaises(benchmark.HarnessError):
            benchmark.summarize_mission(self.root, "DoNothing", steps, "california20", uav)

    def test_source_snapshot_rejects_modified_and_extra_compiled_sources(self):
        upstream = self.root / "upstream"
        (upstream / "src/simulation").mkdir(parents=True)
        source = upstream / "src/simulation/main.cpp"
        source.write_text("int main() { return 0; }\n")
        expected = {"src/simulation/main.cpp": benchmark.sha256(source)}
        snapshot = self.root / "UPSTREAM_SNAPSHOT.json"
        benchmark.save_json(snapshot, {"commit": benchmark.REFERENCE_COMMIT, "sha256": expected})
        self.assertEqual(benchmark.verify_source_snapshot(upstream, snapshot), expected)
        extra = upstream / "src/simulation/extra.cpp"
        extra.write_text("// Would be picked up by the CMake source glob.\n")
        with self.assertRaisesRegex(benchmark.HarnessError, "extra=.*extra.cpp"):
            benchmark.verify_source_snapshot(upstream, snapshot)
        extra.unlink()
        source.write_text("int main() { return 42; }\n")
        with self.assertRaisesRegex(benchmark.HarnessError, "modified=.*main.cpp"):
            benchmark.verify_source_snapshot(upstream, snapshot)

    def test_source_snapshot_requires_pinned_commit(self):
        upstream = self.root / "upstream"
        upstream.mkdir()
        snapshot = self.root / "UPSTREAM_SNAPSHOT.json"
        benchmark.save_json(snapshot, {"commit": "wrong", "sha256": {"main.cpp": "unused"}})
        with self.assertRaisesRegex(benchmark.HarnessError, "commit mismatch"):
            benchmark.verify_source_snapshot(upstream, snapshot)


if __name__ == "__main__":
    unittest.main()
