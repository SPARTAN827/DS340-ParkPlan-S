**Data credit: TouringPlans.com — historical Animal Kingdom waits and published park-hour listings.**

# Run ParkPlan-S

Run these commands from the repository root. The planner uses Python 3.10 or later and requires no third-party packages. We ran the full study on Linux with Python 3.12.

## 1. Check the engine without raw data

```bash
python3 -m unittest discover -s experiments/algorithm_study_20261019 -p test_engine.py -v
```

On Windows, replace `python3` with `py -3` if you use the Python launcher.

## 2. Download and verify the pinned public source

On Linux / WSL:

```bash
curl --fail --location --output /tmp/parkplan-ak-933161b.tar.gz \
  https://api.github.com/repos/TouringPlans/DisneyAnimalKingdomWaitTimes/tarball/933161b8bebb7cd50e0d54bcb3578484875487fa
sha256sum /tmp/parkplan-ak-933161b.tar.gz
```

Required SHA-256:

```text
23eca800b048aecd4b3a2469e78f63f24f64637eb785c8401386e219a177f812
```

Do not substitute a different source when this check fails. The repository does not include the raw wait-time files.

## 3. Audit the included frozen results

```bash
python3 scripts/verify_public_results.py \
  --archive /tmp/parkplan-ak-933161b.tar.gz --require-complete
```

The public verifier independently checks raw-source observations, chronology, reported arithmetic, shared-success denominators, frozen study hashes and validation selection. It writes separate `experiments/algorithm_study_20261019/QA-public.md` and `verification-public.json`.

It checks the 20 archived files included in this repository. The original audit also checked 11 local meeting and archive files; those are not inputs to the planner.

Expected result: on the 118 dates when both plans finished, rollout took 6.36 minutes longer on average than basic replanning. The 95% interval for time saved by rollout was −13.73 to +0.36 minutes.

### Native Windows audit command

The verifier accepts an explicit archive path. These PowerShell commands are provided but were not separately executed on native Windows:

```powershell
Invoke-WebRequest -Uri "https://api.github.com/repos/TouringPlans/DisneyAnimalKingdomWaitTimes/tarball/933161b8bebb7cd50e0d54bcb3578484875487fa" -OutFile "$env:TEMP\parkplan-ak-933161b.tar.gz"
Get-FileHash "$env:TEMP\parkplan-ak-933161b.tar.gz" -Algorithm SHA256
py -3 scripts/verify_public_results.py --archive "$env:TEMP\parkplan-ak-933161b.tar.gz" --require-complete
```

## 4. Rerun policy calculations in a separate copy

Use a second checkout on Linux or WSL: rerunning the study replaces the generated results there. With the data archive at the path shown above, run:

```bash
python3 experiments/algorithm_study_20261019/prepare.py
python3 scripts/run_public_study.py reference --workers 1
```

The public runner calls the frozen scientific runner. Its only adaptation is the explicitly scoped preservation bookkeeping; it does not change route selection, forecasts, data splits or measured policy costs.

The full development sequence is:

```bash
python3 scripts/run_public_study.py validate --workers 2
python3 experiments/algorithm_study_20261019/analyze.py experiments/algorithm_study_20261019/validation
python3 scripts/run_public_study.py select
python3 scripts/run_public_study.py evaluate --workers 2
python3 scripts/run_public_study.py sensitivity --workers 2
```

These commands overwrite generated results in the reproduction copy. Runtime measurements, timestamps and resulting hashes legitimately change. A fresh `select` creates a different selection record, so the delivered original `evaluation_lock.json` no longer certifies that new run. Record new hashes separately if you audit a fresh run. Compare scientific fields separately from timing/hash metadata.

Do not run the frozen `run.py` directly in this reduced public distribution: its workspace-preservation check expects the 11 local files. Use `scripts/run_public_study.py`.

## 5. Figures

Viewing the included PNG/SVG/PDF figures needs no plotting installation. To regenerate, install `experiments/algorithm_study_20261019/requirements-plot.txt` in a separate environment.

## Data-use terms

You're free to use these data however you see fit, subject to the following:

1. Any publications or redistributions credit TouringPlans.com clearly at the beginning of those publications or distributions.
2. Any redistributions include these license terms.
