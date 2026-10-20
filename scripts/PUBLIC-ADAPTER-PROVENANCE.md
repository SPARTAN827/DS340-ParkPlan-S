**Data credit: TouringPlans.com.** The dataset redistribution terms remain in the study's `SOURCES-AND-LICENSE.md`.

# Public distribution adapter provenance

These adapters do not implement a new route algorithm. The original frozen source, protocol, locks, selections and experimental results remain byte-for-byte unchanged. The sole reason for these adapters is to omit unrelated meeting notes and a historical meeting-evidence ZIP from the public repository while preserving runnable scientific code and honest audit scope.

## Fixed boundary

The original `experiments/tie_preserving_pilot/preserved_artifacts_sha256.json` contains 31 artifacts. Its SHA-256 is `c5634a39e1e494035e61e9ae7994e22c19af803aaf5f75ed590c30ad144be2c2`.

- **20 included experiment artifacts:** every hash is verified.
- **11 omitted meeting/archive artifacts:** their original paths/hashes are recorded in `public-omissions.json`; their bytes are not distributed and are not verified by these adapters.
- The original 31-entry manifest is unchanged, not shortened.
- Missing/modified included artifacts, unexpected omission paths, or a changed original manifest cause an error. The public copy also rejects accidentally bundled omitted artifacts.
- The old scientific metadata's `old_artifacts_unchanged: 31` describes the original full local run. It is not rewritten. Newly rerun public metadata reports 20 and adds an explicit `public_distribution` record.
- A public-scoped PASS does not reissue the original 31-artifact certificate.

## Runner: exact substitutions

`run_public_study.py` imports the actual unchanged `experiments/algorithm_study_20261019/run.py`, guarded by SHA-256 `a8ed8bd340c66f6be7106d58f6098df01d112cc2407cc986bcce4059fed94cd0`.

It substitutes only:

1. `preserved()` → the strict 20-included/11-omitted checker, returning **20**, not 31.
2. `write_rows()` → forwards the same rows and original metadata to the original writer, adding only a `public_distribution` provenance field to a copied metadata dictionary.
3. `save()` → forwards all values unchanged except the reference-only summary containing `rows_matched` and `old_artifact_hashes`; that summary receives the same public provenance field.

Policy selection, scenario construction, routing, forecasting, input retrieval, phase scheduling, statistical results, seeds, and frozen-source hashes are not replaced. The wrapper's own hash is recorded separately. `check` performs only the import, frozen-entrypoint checks and public preservation check.

Examples, from the repository root:

```bash
python3 scripts/run_public_study.py check
python3 scripts/run_public_study.py reference --workers 2
```

The other phase names are `validate`, `select`, `evaluate`, `sensitivity`. Run policy phases **only in a separate reproduction copy**, because the inherited runner writes phase outputs. A newly created selection will not match the old historical evaluation lock; preserve the original evidence and make a separately identified reproduction record. This adapter does not relabel a new run as the original frozen run.

## Verifier: exact diff and scope

`verify_public_results.py` is a public-scoped copy of the unchanged `verify_results.py`, original SHA-256 `a4543d18222785bdc9ce4a1054a4b987ea6d4ccda6ea7f5bfef9997a5eea508d`.

The complete source difference is included as `verify-public-vs-frozen.diff`. Changes are limited to:

1. Public-scope module description and repository-relative location of the unchanged scientific evidence.
2. Importing the strict public integrity helper, which pins both original entrypoint hashes.
3. Replacing the original 31-file preservation loop with the explicit 20-included/11-omitted check.
4. Distinguishing original historical metadata (31) from newly rerun, explicitly annotated public metadata (20).
5. Recording public scope and the historical-metadata explanation in the audit result.
6. Writing `experiments/algorithm_study_20261019/QA-public.md` and `verification-public.json` rather than overwriting historical `QA.md` and `verification.json`.
7. Updating generated report labels, preservation counts and the reproduction command.

Raw-data parsing, chronology reconstruction, split reconstruction, source/lock checks, independent arithmetic, bootstrap calculations, completion accounting and validation-selection calculations are unchanged.

```bash
python3 scripts/verify_public_results.py \
  --archive /tmp/parkplan-ak-933161b.tar.gz --require-complete
```

This writes only the two public audit outputs. It does not run policies. Use the pinned external archive and exact checksum documented in the repository. A passing public audit confirms its stated integrity/arithmetic scope, not rollout superiority, new independent evaluation, or real visitor savings.

## Tests

```bash
PYTHONDONTWRITEBYTECODE=1 python3 -m unittest discover \
  -s scripts -p test_public_adapters.py -v
```

The tests cover exact-20 pass; missing, modified or unexpectedly omitted included files; changed original manifest; accidentally included meeting/archive files; frozen entrypoint hashes; and metadata-only wrapping without substituting the policy object or changing rows.

The existing 12 engine tests remain separate scientific-implementation tests:

```bash
PYTHONDONTWRITEBYTECODE=1 python3 -m unittest discover \
  -s experiments/algorithm_study_20261019 -p test_engine.py -v
```

The public adapter test results and full public audit must be checked on an extracted public package before claiming a distribution verification. No claim of a full native-Windows policy run is added by these wrappers.
