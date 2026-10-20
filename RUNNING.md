**Data credit: TouringPlans.com — historical Animal Kingdom waits and published park-hour listings.**

# Run and inspect the public ParkPlan-S snapshot

Commands are from the repository root. Core code requires Python 3.10+ and no third-party packages. Original study execution and this distribution check use Linux/Python 3.12. Full native-Windows policy execution is not claimed tested.

## 1. Check the engine without raw data

```bash
python3 -m unittest discover -s experiments/algorithm_study_20261019 -p test_engine.py -v
```

These are constructed correctness checks, not proof of park-time savings. On Windows with the Python launcher, the analogous command starts with `py -3`.

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

Do not substitute a different source when this check fails. Raw data are not included in this public update.

## 3. Audit the included frozen results

```bash
python3 scripts/verify_public_results.py \
  --archive /tmp/parkplan-ak-933161b.tar.gz --require-complete
```

The public verifier independently checks raw-source observations, chronology, reported arithmetic, shared-success denominators, frozen study hashes and validation selection. It writes separate `experiments/algorithm_study_20261019/QA-public.md` and `verification-public.json`.

Its historical-preservation scope is **20 included old artifacts**, not the original workspace's31. Exactly11 meeting-note/archive files are explicitly omitted; no raw observations, policy results or required included hash failures are silently skipped. The original `QA.md` and `verification.json` remain historical records.

Expected primary scientific result: D0 minus R is about **−6.356 modeled minutes** on118 jointly completed dates, with95% seven-date block interval **[−13.730, +0.357]**. The new method is not established as superior.

### Native Windows audit command

The verifier accepts an explicit archive path. These PowerShell commands are provided but were not separately executed on native Windows:

```powershell
Invoke-WebRequest -Uri "https://api.github.com/repos/TouringPlans/DisneyAnimalKingdomWaitTimes/tarball/933161b8bebb7cd50e0d54bcb3578484875487fa" -OutFile "$env:TEMP\parkplan-ak-933161b.tar.gz"
Get-FileHash "$env:TEMP\parkplan-ak-933161b.tar.gz" -Algorithm SHA256
py -3 scripts/verify_public_results.py --archive "$env:TEMP\parkplan-ak-933161b.tar.gz" --require-complete
```

## 4. Rerun policy calculations in a separate copy

Keep the delivered evidence unchanged. In a separate Linux/WSL copy, with the archive at the path above:

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

These commands overwrite generated results in the reproduction copy. Runtime measurements, timestamps and resulting hashes legitimately change. A fresh `select` creates a different selection record, so the delivered original `evaluation_lock.json` no longer certifies that new run. **A full new audit requires its own pre-evaluation provenance record; never silently rewrite the old lock or claim a fresh run is the old frozen evidence.** Compare scientific fields separately from timing/hash metadata.

Do not run the frozen `run.py` directly in this reduced public distribution: its workspace-preservation check expects the11 deliberately omitted files. Use `scripts/run_public_study.py`.

## 5. Optional figures and historical documents

Viewing the included PNG/SVG/PDF figures needs no plotting installation. To regenerate, install `experiments/algorithm_study_20261019/requirements-plot.txt` in a separate environment.

Historical reports may cite workspace research/meeting notes that were intentionally not made public. The current entry points, dataset provenance, protocol, code, results and public-scope checks are included. `reproduction/` remains the earlier ADAPT project, with separate prerequisites.

## Data-use terms

You're free to use these data however you see fit, subject to the following:

1. Any publications or redistributions credit TouringPlans.com clearly at the beginning of those publications or distributions.
2. Any redistributions include these license terms.
