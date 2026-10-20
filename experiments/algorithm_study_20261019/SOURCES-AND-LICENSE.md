**Data credit: TouringPlans.com — historical Animal Kingdom attraction posted-wait records and published park-hour listings.**

> **Public-distribution update — October20:** source terms below remain applicable. The historical inventory/preservation sections describe the earlier full local evidence archive, not this reduced public copy. Public contents exclude all meeting-note files, the nested historical ZIP, and the `writing/` workspace notes. Exactly20 included legacy artifacts are verified, while11 preservation-only artifacts are explicitly omitted; see [public adapter provenance](../../scripts/PUBLIC-ADAPTER-PROVENANCE.md). No raw wait bulk, private memory, credentials or PPT is included. Current instructions: [RUNNING.md](../../RUNNING.md).

# Sources, redistribution terms, and package boundaries

## Wait-data source

- Repository: <https://github.com/TouringPlans/DisneyAnimalKingdomWaitTimes>
- Pinned commit: `933161b8bebb7cd50e0d54bcb3578484875487fa`
- Pinned archive URL: <https://api.github.com/repos/TouringPlans/DisneyAnimalKingdomWaitTimes/tarball/933161b8bebb7cd50e0d54bcb3578484875487fa>
- Archive SHA-256: `23eca800b048aecd4b3a2469e78f63f24f64637eb785c8401386e219a177f812`
- Source README: <https://github.com/TouringPlans/DisneyAnimalKingdomWaitTimes/blob/933161b8bebb7cd50e0d54bcb3578484875487fa/README.md>
- Source license file: <https://github.com/TouringPlans/DisneyAnimalKingdomWaitTimes/blob/933161b8bebb7cd50e0d54bcb3578484875487fa/LICENSE.md>

The source `LICENSE.md` was read from the pinned archive; its terms below are preserved verbatim in wording:

> You're free to use these data however you see fit, subject to the following:
>
> 1) Any publications or redistributions credit TouringPlans.com clearly at the beginning of those publications or distributions
>
> 2) Any redistributions include these license terms

The package contains derived results and small derived trace observations needed to explain the simulations, **not the raw bulk wait CSVs, downloaded source archive, or cached parsed source**. Download the pinned archive separately for raw-source verification or new simulations. Source observation time is treated as availability time; transmission latency is not recorded. Posted waits are not measured full visitor itineraries.

## Historical park hours and other inputs

- Existing evaluation hours: `data/verified_inputs/historical_park_hours.csv`, 165 dated listings.
- New validation hours: `experiments/algorithm_study_20261019/inputs/validation_park_hours.csv`, 115 dated listings retrieved 2026-10-19.
- Each row preserves its public TouringPlans date URL, HTML SHA-256, opening/closing values, and date-heading check. Full webpage HTML is not redistributed.
- These are secondary-source published schedules, not independently verified actual operating logs or ride-level hours. The older independent spot checks and source limitations are included; successful date-heading checks do not resolve cross-source calendar conflicts.
- Primary geometry is uniform synthetic ten-minute walking and service time. The nonuniform graph and walking-scale variants are illustrative sensitivities, not measured 2018 walking matrices. Nominal service-duration labels do not establish total boarding/unloading time.

## Research sources

The package includes the first-principles research note and relevant earlier source audits under `writing/research/`. The main Chinese and English reports cite the applicable prior work. They distinguish existing dynamic itinerary planning, policy rollout, uncertainty modeling, and this project's implementation; no claim of inventing dynamic replanning or outperforming proprietary TouringPlans software is made. Full commercial papers or book scans are not included.

## Code and software dependencies

- Core experiment, data loading, result analysis, tests, audits, and ZIP packaging use Python's standard library. The original author/dependency code files and their attribution remain in place.
- Optional figures use Matplotlib. `requirements-plot.txt` records the exact installed plotting environment observed during this run; those third-party packages are **not bundled**. Their upstream licenses remain applicable when installed separately.
- No new blanket license is imposed on third-party data, source pages, research articles, or package dependencies. This document records source terms, not a grant of rights beyond them.

## Included preservation evidence

The 31 files referenced by the old preservation manifest are included byte-for-byte so the independent verifier can check its full preservation claim. One is an older approximately 576 KB project-evidence ZIP, included only because its bytes are part of that preservation record. Its inventory and report introductions were inspected: it preserves earlier project reports, derived results and source documentation, including contributor names. This is not a claim of a comprehensive sensitive-content audit. This nested historical ZIP is **not the current conclusion**.

Only the note and original `run.py` from the initial print-error archive are retained. Duplicate failed-run result copies are excluded; the note explains that the only source repair moved `flush=True` from `json.dumps` to `print`.

Excluded: raw TouringPlans archives/caches, Python bytecode/cache directories, private agent/user memory, credentials, unrelated workspace projects, duplicate archived result sets, and PPT deliverables. This package is algorithm-research evidence, not the midterm presentation and not an external publication.

## Scientific scope

The primary rollout hypothesis did **not** establish an improvement over D0. QA PASS certifies preserved inputs and reproducible calculations, not algorithm superiority, measured visitor savings, or readiness for deployment. Keep negative findings, conditional-success denominators, all-attempt failures, and model limitations with any reused figure or result.
