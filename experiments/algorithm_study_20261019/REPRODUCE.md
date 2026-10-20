**Data credit: TouringPlans.com — historical Animal Kingdom waits and public park-hour listings.**

> **Public-distribution update — October20:** use the repository-level [RUNNING.md](../../RUNNING.md), `scripts/run_public_study.py`, and `scripts/verify_public_results.py`. This reduced public distribution excludes11 meeting-note/archive artifacts and strictly verifies20 included legacy hashes. The instructions below describe the earlier complete local evidence archive; their workspace-only ZIP/package command and original31-file preservation check do **not** apply to this reduced public copy. Original scientific code/locks remain unchanged. The public verifier writes separate `QA-public.md` / `verification-public.json`.

# Reproduce and inspect the algorithm-study evidence

This package is research evidence, **not a PPT**. The main finding is negative for the proposed rollout improvement; reproducibility does not imply superiority.

Start with the Chinese research report in `writing/research/ParkPlan-S-Algorithm-Study-2026-10-19-zh.md`, the study's English `REPORT.md`, `PROTOCOL.md`, `QA.md`, and `figures/README.md`. Paths below are relative to the extracted package root, which mirrors the workspace layout. Do not flatten or move the `experiments/` and `data/` folders.

## 1. Environment and dependency boundary

- Core simulation, analysis, verification, input retrieval and engine tests: Python 3.10+ syntax; this run was executed on Linux/Python 3.12. No third-party core packages are required.
- Figure regeneration only: install the optional `requirements-plot.txt`. The observed plotting environment used Matplotlib 3.10.7; exact transitive versions are recorded there. Package installation needs network access; viewing included PNG/SVG/PDF figures does not.
- Raw data are **not included**. The archive must be downloaded from the pinned public source and its exact checksum verified.
- Original evidence is hash-locked. Keep an untouched extracted copy. Policy reruns write output CSVs/traces/metadata; do them in a separate copy, not the evidence copy.

**Distribution check actually performed:** the preliminary evidence ZIP was extracted into a fresh Linux temporary directory. Its independent verifier passed all 6,200 policy-days across all eight phase/configuration folders. A separate import/input check using only the extracted package recovered 550 dates, reproduced the existing 385-day training curves exactly, and read all 280 sourced validation/evaluation hours. No policy simulations were rerun for that packaging check. These checks do not constitute a Windows execution test.

## 2. Download the pinned source on Linux / WSL

From the package root:

```bash
curl --fail --location \
  --output /tmp/parkplan-ak-933161b.tar.gz \
  https://api.github.com/repos/TouringPlans/DisneyAnimalKingdomWaitTimes/tarball/933161b8bebb7cd50e0d54bcb3578484875487fa
sha256sum /tmp/parkplan-ak-933161b.tar.gz
```

Required SHA-256:

```text
23eca800b048aecd4b3a2469e78f63f24f64637eb785c8401386e219a177f812
```

The frozen `prepare.py`/`run.py` pipeline defaults to this `/tmp` archive and a `/tmp` parsed cache. The verifier also accepts an explicit archive path. Do not replace a checksum failure with an arbitrary newer source version.

## 3. Check the delivered evidence without rerunning policies

```bash
python3 experiments/algorithm_study_20261019/package_evidence.py --verify ../ParkPlan-S-Algorithm-Study-2026-10-19.zip
python3 experiments/algorithm_study_20261019/verify_results.py \
  --archive /tmp/parkplan-ak-933161b.tar.gz --require-complete
python3 -m unittest discover \
  -s experiments/algorithm_study_20261019 -p test_engine.py -v
```

Adjust the ZIP location to where you saved it. ZIP verification checks CRCs, the complete file list and every payload SHA-256 against the embedded `PACKAGE-MANIFEST.json`. Result verification independently reparses the pinned raw archive, checks all 6,200 policy-days and recomputes reported means/counts and primary bootstrap intervals. It writes only refreshed `QA.md` and `verification.json`; it does not rerun or alter policy results. The engine tests include constructed examples, not evidence that rollout wins on park data.

Expected scientific result: on 118 common-success evaluation dates, D0 minus rollout is approximately −6.356 minutes, with independently reproduced 7-day block 95% interval [−13.730, +0.357]. Completion counts are D0 126/165 and rollout 128/165. **QA PASS is not an algorithm-win flag.**

## 4. Full frozen policy pipeline on Linux / WSL

Use a separate reproduction copy. Included validation/evaluation hour CSVs are sufficient; do not refetch pages merely to reproduce this frozen input snapshot. Refetching may produce changed source hashes or revised schedules.

```bash
python3 experiments/algorithm_study_20261019/prepare.py
python3 experiments/algorithm_study_20261019/run.py validate --workers 2
python3 experiments/algorithm_study_20261019/analyze.py experiments/algorithm_study_20261019/validation
python3 experiments/algorithm_study_20261019/run.py select
python3 experiments/algorithm_study_20261019/run.py reference --workers 2
python3 experiments/algorithm_study_20261019/run.py evaluate --workers 2
python3 experiments/algorithm_study_20261019/run.py sensitivity --workers 2
python3 experiments/algorithm_study_20261019/analyze.py \
  experiments/algorithm_study_20261019/evaluation \
  experiments/algorithm_study_20261019/sensitivity/uniform5 \
  experiments/algorithm_study_20261019/sensitivity/uniform15 \
  experiments/algorithm_study_20261019/sensitivity/illustrative \
  experiments/algorithm_study_20261019/sensitivity/illustrative_fast \
  experiments/algorithm_study_20261019/sensitivity/illustrative_slow
```

`--workers 1` gives serial execution. The scenario bank uses deterministic training-day selection; stochastic uncertainty analysis uses fixed seeds (IID base 20261019, block stream 20261026) and 5,000 resamples. No parameter is selected on the 165 evaluation days.

### Why a rerun will not be byte-identical

Wall-clock `planning_seconds`, total runtime, selection creation time and generated file hashes legitimately change. After a fresh `select`, the delivered `evaluation_lock.json` still refers to the **original** `selection.json`; therefore its integrity check should fail on a modified reproduction copy. Do not report that as a failure of the original evidence or quietly relabel the old lock as a fresh one.

For a formal new reproduction, create a **new** run-provenance record before its evaluation, preserving the delivered original lock separately. Compare scientific fields—success/failure, completed order, elapsed/walk/wait/service minutes, choices and selected decay—not measured wall-clock timings or selection timestamps. The package's unchanged-code/source hashes and original independent verification are the reference. The commands above regenerate the scientific calculations; they are not a promise of byte-identical rerun files or prewritten approval of a newly generated lock.

## 5. Windows instructions and exact support claim

**Native Windows execution of the complete frozen pipeline was not tested.** We do not claim otherwise. The frozen loader's `/tmp` archive/cache paths are Linux-oriented. Merely passing `--archive` to `prepare.py` does not change the bound default archive used by later `run.py` calls.

Two concrete options:

1. **Full rerun:** use an existing WSL2 Ubuntu environment, open a WSL terminal in the extracted folder, and follow the Linux commands above. Inside WSL, `/tmp` is the Linux temporary directory. WSL installation/availability is a user-system prerequisite, not something this package silently changes. WSL itself was not separately exercised during this run; the tested environment was Linux.
2. **Native Windows evidence audit:** the standard-library verifier accepts an explicit Windows archive path and does not import the Linux-oriented loader. The following PowerShell commands are provided for that path-portable operation, but were not executed on Windows here:

```powershell
Invoke-WebRequest -Uri "https://api.github.com/repos/TouringPlans/DisneyAnimalKingdomWaitTimes/tarball/933161b8bebb7cd50e0d54bcb3578484875487fa" -OutFile "$env:TEMP\parkplan-ak-933161b.tar.gz"
Get-FileHash "$env:TEMP\parkplan-ak-933161b.tar.gz" -Algorithm SHA256
py -3 experiments/algorithm_study_20261019/verify_results.py --archive "$env:TEMP\parkplan-ak-933161b.tar.gz" --require-complete
```

Do not edit frozen `engine.py`, `run.py`, `prepare.py` or the legacy loader just to make a path fit and still claim their original hashes. A native-Windows full-pipeline port would be a separately documented environment change, not part of the current tested claim.

## 6. Optional figure regeneration

On Linux/WSL, from a reproduction copy:

```bash
python3 -m venv .plot-venv
.plot-venv/bin/python -m pip install -r experiments/algorithm_study_20261019/requirements-plot.txt
MPLCONFIGDIR="$PWD/.matplotlib-cache" .plot-venv/bin/python experiments/algorithm_study_20261019/make_figures.py
```

`MPLCONFIGDIR` overrides the plotting script's Linux `/tmp` cache default. A native-Windows virtual environment uses `.plot-venv\Scripts\python.exe` and an explicitly set writable `MPLCONFIGDIR`; that path has not been tested here. Font/backend or dependency differences can change rendered binary files without changing underlying numerical summaries. Included figures were rendered on the observed Linux environment and contain their source-summary hashes.

## 7. Additional diagnostics and limitations

```bash
python3 experiments/algorithm_study_20261019/diagnostics/audit_baseline.py --archive /tmp/parkplan-ak-933161b.tar.gz
python3 experiments/algorithm_study_20261019/diagnostics/audit_rollout_errors.py
```

The second diagnostic reconstructs frozen rollout decisions and uses retrospective historical outcomes to explain them; it is not a new online candidate, a tuning pass, or an independent deployment result. It uses the same Linux default loader path. These diagnostics overwrite only their derived outputs in the reproduction copy.

The evaluation dates had previously been examined. Time comparisons condition on shared success; closures, posted-wait error, source conflicts and synthetic geometry limit interpretation. Preserve the source terms and these limits when reusing results. See `SOURCES-AND-LICENSE.md`.
