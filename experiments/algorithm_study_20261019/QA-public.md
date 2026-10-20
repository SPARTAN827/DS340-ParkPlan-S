# Public-distribution independent result QA

**Status: PASS**

Independent raw-source, chronology, arithmetic, denominators, split/hash and validation-selection audit. No engine, runner, preparation or analysis imports. No policy runs or tuning.

## Completed phase checks

| Phase | Policy-days | Raw visits | Decision snapshots | Scenario-ID checks |
|---|---:|---:|---:|---:|
| validation | 920 | 5145 | 3731 | 1058 |
| reference_check | 330 | 1870 | 800 | 0 |
| evaluation | 825 | 4781 | 3216 | 1607 |
| sensitivity/uniform5 | 825 | 4809 | 3246 | 1624 |
| sensitivity/uniform15 | 825 | 4558 | 2996 | 1490 |
| sensitivity/illustrative | 825 | 4702 | 3144 | 1574 |
| sensitivity/illustrative_fast | 825 | 4758 | 3204 | 1598 |
| sensitivity/illustrative_slow | 825 | 4459 | 2931 | 1465 |
| **Total** | **6200** | **35082** | **23268** | **10416** |

## Algorithm finding: QA pass is not a performance win

On 118 jointly successful evaluation dates, D0 minus rollout is **-6.356 minutes**: rollout is slower on average in this conditional subset.
The independently reproduced 7-day block-bootstrap 95% interval is **[-13.730, 0.357] minutes**. It does not support a positive rollout time advantage.
Completion counts are D0 **126/165**, rollout **128/165**. Different failed dates and success-selection prevent treating the conditional time mean as an all-attempt causal effect.

The result is a reproducible negative primary-hypothesis finding, not an algorithm-superiority certificate.

## Integrity and accounting checks

- Independently parsed pinned raw CSV data; every executed arrival and real decision snapshot agrees with the declared latest-as-of/15-minute freshness rule.
- Reconstructed route chronology, same-six completion, failures/deadlines, elapsed decomposition, and walking including the failed arrival leg.
- Checked one common initial order per date/configuration, full attempted-day denominators, training-only scenario IDs, and scenario action choice against logged costs.
- Recomputed all reported policy completion/failure counts, paired means/medians/signs/discordances, common-success groups and planning-overhead adjustments without importing the experiment summarizer.
- Recomputed primary IID and block7 bootstrap intervals for all seven analyzed phase/configuration folders with independent frequency-weight resampling.
- Reproduced validation-only decay selection and recommendation; confirmed330 legacy reference outcomes,20 included legacy-artifact hashes and10 pre-evaluation locked-file hashes.
- Eleven historical meeting/archive artifacts are intentionally omitted, not verified. Original metadata values of31 are historical records, not a claim by this public audit.
- Verified the documented original-runner exception is exactly a one-line relocation of `flush=True` from `json.dumps` to `print`; no policy/data logic changed.

## Limits

- Recorded real visit streams and decision snapshots are fully checked; this verifier does not rerun scenario rollouts or independently prove all simulated continuation decisions nonanticipative.
- Scenario IDs are checked against chronological training pools; engine interface tests and code review separately cover simulated-policy information boundaries.
- Planning overhead is measured replanning wall-clock time under parallel execution, excludes the shared initial-order search, and is not pure CPU time or measured phone/network latency.
- Primary bootstrap intervals are independently reproduced: IID seed20261019; block7 derived seed20261026;5000full-date resamples. Secondary-pair bootstrap intervals are not independently recalculated.
- The retrospective evaluation dates were previously examined; integrity checks do not make them an untouched confirmatory test.
- Park-hour sources, synthetic geometry and posted-wait proxy limitations remain; no true visitor benefit or commercial superiority is validated.

Reproduce: `python3 scripts/verify_public_results.py --require-complete`.

The public verifier writes only `QA-public.md` and `verification-public.json`; original QA is unchanged. Unexpected missing outputs are never treated as passed.
