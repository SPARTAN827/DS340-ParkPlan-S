**Data credit: TouringPlans.com: historical Animal Kingdom posted waits and published park-hour listings.**

# Week 12: five-policy execution demo

This wrapper executes the existing modified implementation. It does not introduce a new algorithm or tune a new parameter. It runs F (fixed), D0 (existing dynamic), C (30-minute calibration), R (scenario rollout), and S (shared-order scenario ablation) on **2018-07-26**, the chronologically first frozen evaluation date. That rule is fixed without consulting policy outcomes. A single-date demo demonstrates execution, not average performance.

All methods receive the same initial order and first ride. The wrapper imports the unchanged frozen `run.py`, verifies its ten locked dependencies, parses the checksum-verified raw archive without a parsed-cache dependency, trains on the preceding 385 dates, and executes the five policies. It retains failures and writes fresh CSV/JSON records to a unique new `runs/demo-*` directory. It never overwrites the 2018 and 2019 study results. Saved evaluation rows are consulted **only after execution**, for parity checks excluding runtime.

The source is historical posted waits, with uniform 10-minute walking and service inputs. These are modeled trips, not measured visitor savings. The core predictor is a time-bin median plus a decaying residual; it is not a neural network. KOWCPI's conditional-coverage method and ADAPT's drone optimizer are not integrated into this park planner.

## 1. Prerequisites and pinned source

Use Python 3.10 or newer and a complete checkout of the team repository. No third-party package is required. Run commands from the repository root. Do not extract this folder alone and discard `experiments/algorithm_study_20261019`, `experiments/tie_preserving_pilot`, or `data/verified_inputs`.

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

The wrapper automatically verifies that checksum; it stops with a clear message if data or dependencies are missing or modified. It does not download silently or accept an arbitrary newer snapshot. Native Windows commands are provided for the path-portable wrapper; actual native Windows execution is not verified. The recorded execution environment is Linux / Python 3.12.

Exit code 0 means execution and evidence checks completed, even when a modeled trip fails. Exit code 2 means an input or verification error. Trip failures remain explicit in the output and are never converted to zero-minute successful trips. On the default date, F/D0/C/R each complete one ride and S completes five; all then encounter a closure. This date is retained to show genuine failure handling. Use the saved full-study table for completed-trip timing comparisons.

## 2. What to show during a real recording

1. Show the repository and `run_demo.py`, including the first-date rule.
2. Explain the five method labels and which components changed.
3. Execute the command above; let it parse the raw archive and print all five outcomes.
4. Open the newly printed output directory. `comparison.csv` has completion, trip time, failure reason and route; `traces.json` has timestamped visits/decisions. `verification.json` records source/code hashes, the input split and checks.
5. Explain the full-study comparison from `experiments/algorithm_study_20261019/REPORT.md`, including its successful-trip denominator, all attempted dates and failures. Do not present a single demonstration date as the 165-date experiment.

Both team members must actually participate and explain their parts. These files are recording preparation, not evidence that a student recording or upload has happened. The assignment does not specify a video duration.

## 3. Check the new wrapper and existing engine

```bash
python3 -m unittest discover -s experiments/week12_demo_20261115 -p test_demo.py -v
python3 -m unittest discover -s experiments/algorithm_study_20261019 -p test_engine.py -v
```

The wrapper checks source/hash integrity, chronological training, all five policy records, the shared initial plan, success arithmetic, all-six-ride completion, retained failure reasons, raw-source as-of arrival observations, and nonfuture/fresh online snapshots. It then checks scientific fields against the frozen result for this one date. This is a demo integrity check, not independent re-verification of all 6,200 historical study records.

## 4. Audit the complete published evidence

In a complete public repository copy:

```bash
python3 scripts/verify_public_results.py --archive /tmp/parkplan-ak-933161b.tar.gz --require-complete
```

On Windows, use `py -3` and the explicit `$env:TEMP` archive path. This audits the existing frozen evidence and writes separate `QA-public.md` / `verification-public.json`; it does not execute the policies again. It verifies the public distribution's **20 included legacy files**, not the original workspace's 31. See the repository's `RUNNING.md` for scope.

## 5. Rerun the complete frozen study

Use a **separate copy** on Linux / WSL, because the published phase runners replace generated results in that copy. Keep the delivered evidence intact. Use the archive at `/tmp/parkplan-ak-933161b.tar.gz`:

```bash
python3 experiments/algorithm_study_20261019/prepare.py
python3 scripts/run_public_study.py validate --workers 2
python3 experiments/algorithm_study_20261019/analyze.py experiments/algorithm_study_20261019/validation
python3 scripts/run_public_study.py select
python3 scripts/run_public_study.py reference --workers 2
python3 scripts/run_public_study.py evaluate --workers 2
python3 scripts/run_public_study.py sensitivity --workers 2
python3 experiments/algorithm_study_20261019/analyze.py experiments/algorithm_study_20261019/evaluation experiments/algorithm_study_20261019/sensitivity/uniform5 experiments/algorithm_study_20261019/sensitivity/uniform15 experiments/algorithm_study_20261019/sensitivity/illustrative experiments/algorithm_study_20261019/sensitivity/illustrative_fast experiments/algorithm_study_20261019/sensitivity/illustrative_slow
```

New timings/timestamps will differ. A new `select` changes the selection-record hash, so the delivered `evaluation_lock.json` no longer certifies that new run. Preserve the original lock and create a separately named new provenance record before a formal new evaluation; do not silently rewrite it. The Week 12 demo deliberately rejects altered dependencies. Compare scientific outcomes separately from runtimes and timestamps. Full-study reruns are not needed merely to record this demonstration.

## Scientific conclusion to preserve

On 118 dates where D0 and R both completed, D0 minus R is **−6.356 modeled minutes**: R is slower on that conditional mean. The 95% seven-date block interval is [−13.730, +0.357], so an improvement is not established. D0 and R complete 126/165 and 128/165 attempted dates, respectively; their successful dates differ. C and S also fail to establish an advantage over D0. The original F versus D0 conditional advantage is a separate comparator result, not evidence that R improves D0. The same-wait-data input sensitivities are not new-dataset replications.

## Data terms

You're free to use these data however you see fit, subject to the following:

1. Any publications or redistributions credit TouringPlans.com clearly at the beginning of those publications or distributions.
2. Any redistributions include these license terms.
