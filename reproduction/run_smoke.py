#!/usr/bin/env python3
"""Run the original ADAPT executables in a fresh, non-destructive workspace.

Coursework execution evidence, not a reproduction of the paper's full results.
No upstream source changes, shortened ACS settings, or selected random seed.
"""
import csv
import hashlib
import json
import math
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import time

ROOT = Path(__file__).resolve().parent
UPSTREAM = ROOT / "ADAPT-upstream"


def save_json(path, data):
    path.write_text(json.dumps(data, indent=2) + "\n")


def sha256(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def require(condition, message):
    if not condition:
        raise RuntimeError(message)


def main():
    for name in ("offline-planning", "simulation", "online-planning"):
        require((ROOT / "build" / name).is_file(), f"Build missing: {name}")
    runs = ROOT / "runs"
    runs.mkdir(exist_ok=True)
    run = Path(tempfile.mkdtemp(prefix=time.strftime("smoke-%Y%m%d-%H%M%S-"), dir=runs))
    inp = run / "input"
    (inp / "instance").mkdir(parents=True)
    (run / "output").mkdir()
    (run / "initial-config").mkdir()
    for source in (UPSTREAM / "input").glob("*.json"):
        shutil.copy2(source, inp / source.name)
    instance = UPSTREAM / "instances" / "california20_0.csv"
    shutil.copy2(instance, inp / "instance" / instance.name)
    # Match the author's initialization and first tested mean/std condition.
    configs = {}
    for name in ("offline", "online", "simulation"):
        path = inp / f"{name}_config.json"
        config = json.loads(path.read_text())
        config["instance"]["sensor_fname"] = "california20_0"
        config["print_result"] = True
        configs[name] = config
    configs["online"]["online"]["strategy"]["name"] = "Bayesian"
    configs["simulation"]["simulation"].update(log_power=True, use_avg_power=True)
    powers = json.loads((inp / "real_power_config.json").read_text())
    configs["simulation"]["simulation"]["normal"] = next(
        v for v in powers.values() if v["mean_offset"] == 90 and v["std_offset"] == 110
    )
    for name, config in configs.items():
        save_json(inp / f"{name}_config.json", config)
        save_json(run / "initial-config" / f"{name}_config.json", config)
    uav = json.loads((inp / "uav0_status.json").read_text())["drone"]
    with (inp / "mission_log.csv").open("w", newline="") as f:
        writer = csv.writer(f)
        writer.writerow("x,y,z,t_arrive,E_arrive,t_leave,E_leave,E_chrg".split(","))
        writer.writerow([uav["x"], uav["y"], uav["z"], 0, 0, uav["t"], uav["E"], 0])
    # ZIP has no .git: verify distributed files against the fixed upstream snapshot.
    snapshot = json.loads((ROOT / "UPSTREAM_SNAPSHOT.json").read_text())
    for relative, expected in snapshot["sha256"].items():
        require(sha256(UPSTREAM / relative) == expected, f"Upstream file changed: {relative}")
    commit = snapshot["commit"]
    manifest = {
        "upstream_url": "https://github.com/sysal-bruce-publication/Uncertain-Dynamic-OP",
        "upstream_commit": commit,
        "source_changes": "",
        "source_verification": "SHA256 for distributed snapshot files; not a live git status check",
        "instance_sha256": sha256(instance),
        "binary_sha256": {n: sha256(ROOT / "build" / n) for n in ("offline-planning", "online-planning", "simulation")},
        "runner_sha256": sha256(Path(__file__)),
        "strategy": "Bayesian", "mean_offset_percent": 90, "std_offset_percent": 110,
        "acs_parameters": "unchanged upstream defaults",
        "randomness": "upstream random_device; not seed-controlled or bitwise reproducible",
        "power_window": "author script unchanged; known no-op subtraction bug",
        "scope": "one complete California20 smoke mission; not full paper reproduction",
    }
    require(not manifest["source_changes"], "Upstream checkout is modified; inspect before claiming unchanged source")
    save_json(run / "manifest.json", manifest)
    events = []
    start = time.monotonic()
    with (run / "console.log").open("w") as log:
        def say(message):
            print(message, flush=True)
            log.write(message + "\n")
            log.flush()

        def execute(args, accepted=(0,)):
            say("$ " + " ".join(str(x) for x in args))
            proc = subprocess.run([str(x) for x in args], cwd=run, text=True,
                                  stdout=subprocess.PIPE, stderr=subprocess.STDOUT, timeout=180)
            say(proc.stdout.rstrip())
            events.append({"argv": [str(x) for x in args], "returncode": proc.returncode})
            save_json(run / "processes.json", events)
            say(f"[process exit={proc.returncode}]")
            require(proc.returncode in accepted, f"Unexpected return code {proc.returncode}")
            require("[ERROR]" not in proc.stdout and "[WARN]" not in proc.stdout, "Runtime warning/error; inspect log")
            return proc.returncode

        say(f"ADAPT source commit: {commit}\nEvidence directory: {run}")
        try:
            execute([ROOT / "build/offline-planning", "offline_config.json"])
            execute([ROOT / "build/simulation", "simulation_config.json", "1"])
            targets = []
            for iteration in range(22):
                with (inp / "exp_chrg_list.csv").open() as f:
                    rows = list(csv.reader(f))
                target = int(rows[-1][5])
                targets.append(target)
                configs["simulation"]["instance"]["sensor_fname"] = f"california20_{iteration}"
                save_json(inp / "simulation_config.json", configs["simulation"])
                status = execute([ROOT / "build/simulation", "simulation_config.json", "0"], (0, 1))
                if status == 1:
                    require(target == 1, "Simulation ended without targeting home")
                    break
                require(target != 1, "Home visit did not end mission")
                execute([sys.executable, UPSTREAM / "scripts/window_sliding_power.py",
                         "--config", "input/simulation_config.json", "--duration", "900"])
                configs["online"]["instance"]["sensor_fname"] = f"california20_{iteration + 1}"
                save_json(inp / "online_config.json", configs["online"])
                execute([ROOT / "build/online-planning", "online_config.json"])
            else:
                raise RuntimeError("Mission exceeded maximum possible visits")
            with (inp / "mission_log.csv").open() as f:
                mission = [{k: float(v) for k, v in row.items()} for row in csv.DictReader(f)]
            require(all(math.isfinite(v) for row in mission for v in row.values()), "Non-finite mission output")
            require(len(mission) == len(targets) + 1, "Mission rows do not match simulation steps")
            require(len(targets) >= 2 and len(targets[:-1]) == len(set(targets[:-1])), "No service or repeated sensor")
            require(all(2 <= n <= 21 for n in targets[:-1]), "Invalid serviced node")
            require(all(row["E_arrive"] > 0 and row["E_leave"] > 0 for row in mission[1:-1]), "Energy budget violated")
            end = mission[-1]
            require(end["E_arrive"] > 0 and end["E_leave"] == -1, "Invalid terminal energy/status")
            require(all(abs(end[k] - uav[k]) < 1e-6 for k in ("x", "y", "z")), "Not returned to depot")
            online_calls = sum(Path(e["argv"][0]).name == "online-planning" for e in events)
            with (inp / "exp_chrg_list.csv").open() as f:
                plans = list(csv.reader(f))
            require(online_calls == len(targets) - 1 == len(plans) - 1, "Online replan count mismatch")
            require(all(math.isfinite(float(v)) for row in plans for v in row), "Non-finite plan output")
            require(all(75 <= float(row[1]) <= 99.9 for row in plans[1:]), "Missing Bayesian belief outputs")
            summary = {
                "status": "PASS", "upstream_commit": commit,
                "route": [0] + targets, "serviced_nodes": len(targets) - 1,
                "bayesian_replans": online_calls, "initial_energy_kJ": uav["E"],
                "remaining_energy_kJ": end["E_arrive"],
                "consumed_energy_kJ": round(uav["E"] - end["E_arrive"], 6),
                "charged_energy_kJ": sum(row["E_chrg"] for row in mission),
                "simulated_duration_s": end["t_arrive"],
                "wall_seconds": round(time.monotonic() - start, 3),
                "terminal_simulator_code": 1,
                "terminal_code_meaning": "author-defined successful return home, not execution error",
                "power_window_bug_preserved": True,
                "claim": "single smoke mission only; not statistical or theme-park validation",
            }
            save_json(run / "summary.json", summary)
            say(json.dumps(summary, indent=2))
            say("PASS: original offline -> simulation -> Bayesian online loop -> successful return home")
        except Exception as error:
            save_json(run / "summary.json", {"status": "FAIL", "error": str(error)})
            say(f"FAIL: {error}")
            raise
    return run


if __name__ == "__main__":
    main()
