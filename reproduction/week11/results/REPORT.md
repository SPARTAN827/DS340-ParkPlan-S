# Week 11: selected ADAPT running results

This report compares new runs of the original author code with two selected California20 settings in the paper. The formal profile is `main-text-aligned`; the known upstream sliding-window no-op is preserved. This is a bounded author-code reproduction with disclosed differences, not an exact or full-paper replication.

## Success rate: all attempts

| Power mean / SD change | Method | New successes | New MSR | 95% Wilson interval | Paper MSR | Difference (percentage points) |
|---|---|---:|---:|---:|---:|---:|
| -10% / +10% | Offline | 50/50 | 100.0% | [92.9%, 100.0%] | 100% | +0.0 |
| -10% / +10% | ROMP | 50/50 | 100.0% | [92.9%, 100.0%] | 100% | +0.0 |
| -10% / +10% | WeightedErr | 50/50 | 100.0% | [92.9%, 100.0%] | 100% | +0.0 |
| -10% / +10% | ADAPT | 50/50 | 100.0% | [92.9%, 100.0%] | 100% | +0.0 |
| +10% / +10% | Offline | 0/50 | 0.0% | [0.0%, 7.1%] | 0% | +0.0 |
| +10% / +10% | ROMP | 8/50 | 16.0% | [8.3%, 28.5%] | 12% | +4.0 |
| +10% / +10% | WeightedErr | 25/50 | 50.0% | [36.6%, 63.4%] | 48% | +2.0 |
| +10% / +10% | ADAPT | 50/50 | 100.0% | [92.9%, 100.0%] | 100% | +0.0 |

Paper MSR is from arXiv v2, p. 7, Figure 5, with 50 executions per method/setting. Paper success counts in the reference CSV are inferred from the displayed percentages and 50-trial denominator. New intervals describe finite-sample uncertainty; 50/50 is not a guarantee of universal success.

## Prize and cost: successful missions only

| Setting | Method | Successful n | Paper P* | New P* | Difference | Paper C* | New C* | Difference |
|---|---|---:|---:|---:|---:|---:|---:|---:|
| -10% / +10% | Offline | 50 | 47.073 | 47.073 | -0.000 | 322.524 | 322.498 | -0.026 |
| -10% / +10% | ROMP | 50 | 48.747 | 48.743 | -0.004 | 341.920 | 341.717 | -0.203 |
| -10% / +10% | WeightedErr | 50 | 50.993 | 50.926 | -0.067 | 348.541 | 348.890 | 0.349 |
| -10% / +10% | ADAPT | 50 | 50.422 | 50.369 | -0.053 | 351.075 | 351.575 | 0.500 |
| +10% / +10% | Offline | 0 | N/A | N/A | N/A | N/A | N/A | N/A |
| +10% / +10% | ROMP | 8 | 45.836 | 45.475 | -0.361 | 358.480 | 356.541 | -1.939 |
| +10% / +10% | WeightedErr | 25 | 43.957 | 44.207 | 0.250 | 354.046 | 354.414 | 0.368 |
| +10% / +10% | ADAPT | 50 | 44.400 | 44.338 | -0.062 | 349.981 | 349.897 | -0.084 |

All values in this table are kJ. P* is actual sensor energy delivered, summed from `mission_log.csv`; C* is 359.64 kJ minus terminal arrival energy. The paper values come from p. 15, Table VII. N/A means there were no successful missions, not zero energy. Sample SDs and exact values are in `comparison.csv`. The two means can condition on different successful cases.

## Outcome accounting

- mean90_std110 / Offline: 50 attempted, 50 successful, 0 mission failures, 0 harness errors. Failure types: {}.
- mean90_std110 / ROMP: 50 attempted, 50 successful, 0 mission failures, 0 harness errors. Failure types: {}.
- mean90_std110 / WeightedErr: 50 attempted, 50 successful, 0 mission failures, 0 harness errors. Failure types: {}.
- mean90_std110 / ADAPT: 50 attempted, 50 successful, 0 mission failures, 0 harness errors. Failure types: {}.
- mean110_std110 / Offline: 50 attempted, 0 successful, 50 mission failures, 0 harness errors. Failure types: {"return_home_failed": 50}.
- mean110_std110 / ROMP: 50 attempted, 8 successful, 42 mission failures, 0 harness errors. Failure types: {"return_home_failed": 42}.
- mean110_std110 / WeightedErr: 50 attempted, 25 successful, 25 mission failures, 0 harness errors. Failure types: {"return_home_failed": 25}.
- mean110_std110 / ADAPT: 50 attempted, 50 successful, 0 mission failures, 0 harness errors. Failure types: {}.

## Paired trial checks

| Setting | Baseline | Both succeed | Only ADAPT succeeds | Only baseline succeeds | Neither succeeds | ADAPT minus baseline P*, joint successes (kJ) |
|---|---|---:|---:|---:|---:|---:|
| mean90_std110 | Offline | 50 | 0 | 0 | 0 | 3.296 |
| mean90_std110 | ROMP | 50 | 0 | 0 | 0 | 1.626 |
| mean90_std110 | WeightedErr | 50 | 0 | 0 | 0 | -0.557 |
| mean110_std110 | Offline | 0 | 50 | 0 | 0 | N/A |
| mean110_std110 | ROMP | 8 | 42 | 0 | 0 | -0.978 |
| mean110_std110 | WeightedErr | 25 | 25 | 0 | 0 | -0.133 |

These pairs share initial states, initial offline plans and physical edge costs. The C++ optimizer randomness is not seed-controlled. Do not interpret conditional differences as all-attempt policy benefit.

## Scope and remaining differences

- Two of the paper's power settings, one instance, and four methods were rerun; California30/40, other settings, MCGreedy and other paper experiments were not reproduced.
- Only separate run configurations changed. The profile aligns three offline solver parameters to Section V-A. Appendix C and repository defaults differ; the exact original table-generating setup was not recovered.
- The upstream 900-second sliding-window script is a no-op; Bayesian observations accumulate. Other original sampling and state-update behavior is preserved.
- Fresh generated environments and uncontrolled optimizer RNG mean values need not match exactly. No post-hoc matching tolerance, tuning-to-target or guaranteed ADAPT superiority is asserted.
- The original author result archive was checked for public availability but was not downloaded and re-aggregated. Reference values were checked against the paper.
- These are UAV charging simulations. They do not establish ParkPlan-S time savings or a new improvement to ADAPT.

## Reproducible evidence

See the accompanying raw-evidence archive, protocol, source snapshot, manifest, comparison CSV and independent verification report. Live demonstration runs must use a separate fresh output directory and must not overwrite the frozen formal batch.
