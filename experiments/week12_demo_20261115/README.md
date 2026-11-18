# Replay one park day

*Data: TouringPlans.com historical posted waits and park hours.*

This example runs all five ParkPlan-S methods on July 26, 2018, the first day of the evaluation. All five start with the same ride order and use only observations available at each decision. The planner estimates waits from the preceding 385 dates. Walking and ride time are set to 10 minutes each.

## Run

Use Python 3.10 or later and run the commands from the repository root. The demo uses only the Python standard library. We tested it on Linux with Python 3.12; the PowerShell commands are provided for Windows.

The raw archive is not redistributed. Download it once. Linux / WSL:

```bash
curl --fail --location --output /tmp/parkplan-ak-933161b.tar.gz https://api.github.com/repos/TouringPlans/DisneyAnimalKingdomWaitTimes/tarball/933161b8bebb7cd50e0d54bcb3578484875487fa
sha256sum /tmp/parkplan-ak-933161b.tar.gz
python3 experiments/week12_demo_20261115/run_demo.py --archive /tmp/parkplan-ak-933161b.tar.gz
```

Native Windows PowerShell:

```powershell
Invoke-WebRequest -Uri "https://api.github.com/repos/TouringPlans/DisneyAnimalKingdomWaitTimes/tarball/933161b8bebb7cd50e0d54bcb3578484875487fa" -OutFile "$env:TEMP\parkplan-ak-933161b.tar.gz"
Get-FileHash "$env:TEMP\parkplan-ak-933161b.tar.gz" -Algorithm SHA256
py -3 experiments/week12_demo_20261115/run_demo.py --archive "$env:TEMP\parkplan-ak-933161b.tar.gz"
```

Required SHA-256:

```text
23eca800b048aecd4b3a2469e78f63f24f64637eb785c8401386e219a177f812
```

The script checks the archive and code dependencies before running. It writes a new directory under `runs/demo-*` without replacing previous results.

## Read the output

- `comparison.csv` lists the route, number of completed rides, and either the trip time or the reason the trip stopped.
- `traces.json` shows the rides and routing decisions in time order.
- `verification.json` records the data and code versions and checks the output against the saved study, apart from runtime.

On this date, four methods finish one ride and the shared-order method finishes five. All five then reach a closed attraction. Exit code 0 means the replay and its checks ran successfully, not that all six rides were open. Exit code 2 indicates an input or verification error.

## Tests and full results

```bash
python3 -m unittest discover -s experiments/week12_demo_20261115 -p test_demo.py -v
python3 -m unittest discover -s experiments/algorithm_study_20261019 -p test_engine.py -v
```

For comparisons across 165 days, see the [study results](../algorithm_study_20261019/REPORT.md). The [reproduction guide](../../RUNNING.md) explains how to rerun the full study and audit its saved results.

## Data terms

You're free to use these data however you see fit, subject to the following:

1. Any publications or redistributions credit TouringPlans.com clearly at the beginning of those publications or distributions.
2. Any redistributions include these license terms.
