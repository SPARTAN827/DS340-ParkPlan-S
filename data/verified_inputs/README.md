**TouringPlans.com** is credited for the historical park-hours facts extracted from its publicly readable, date-specific pages. Other sources are linked in the files below. These files do not copy or redistribute the source wait-time CSVs or complete source webpages.

# Source-backed input candidates — checked 2026-10-14

The directory name `verified_inputs` means **verified source extraction/provenance**, not that every historical fact is independently proved or that every value is a ready-to-use model parameter.

- `historical_park_hours.csv`: all 165 replay test dates, 2018-07-26–2019-01-06. Each row has the TouringPlans URL, retrieval date, original HTML SHA-256, exact date/weekday heading, and normal park hours in America/New_York. **No Extra Magic Hours are included.** All sources are retrospective secondary listings, not original Disney operation logs. Their status is source-extracted/date-header-checked, not independently confirmed actual operation.
- `fetch_historical_hours.py`: reproducible extraction and per-row date/weekday verification; requires network access.
- `hours_fetch_status.json`: requested/retrieved count and failures.
- `hours_independent_spot_checks.csv`: ten date-specific comparisons against WDWinfo monthly archives, including earliest/latest and seasonal/holiday changes. Seven agree, three disagree. **Do not silently resolve conflicts or claim all 165 days were independently cross-checked.** Exact alternatives are usable for a source-disagreement sensitivity run.
- `duration_candidates.csv`: six currently published TouringPlans duration labels, with pre-show separately recorded where the publisher separates it. These are **not historical service-time measurements**. Loading/unloading, queue corridors, pre-show overlap with posted waits, and variable ride cycles remain unresolved. A dated official April2018 guide lists Safaris at22min, versus current Disney18min and TouringPlans20min: source/date/scope matter.
- `historical_walking_evidence.json`: two contemporaneous 2018 planDisney walking estimates only. They are panelist estimates on a Disney-hosted site, not Disney-certified measurements and not a complete pairwise matrix. Do not infer other edges, reverse times, or a constant pace from them.

Public-distribution note (2026-10-20): the older workspace research dossier is not bundled. Direct source URLs and checks remain in the files above. For the current study's actual assumptions, see the [frozen protocol](../../experiments/algorithm_study_20261019/PROTOCOL.md). The dated notes below describe the October14 input-audit stage.

## Appropriate next use

An explicitly labeled **TouringPlans-listed historical park-window sensitivity** can replace the old artificial17:00 deadline with each listed close while keeping the same10:00 start and all other assumptions unchanged. It is not a fully corrected park simulator: individual rides can close earlier, and actual queue entry before closing can finish after park close. Keep failures/closures visible and report alternative-source results separately.
