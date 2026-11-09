# Week 11 ADAPT running-result protocol

Recorded before the formal benchmark on November 8, 2026 (America/New_York).
This is a bounded reproduction of selected author-code experiments, not a replication of every result in the paper or a ParkPlan-S performance test.

## Target and references

Qian, Wang and Boyle, *Adaptive Probabilistic Planning for the Uncertain and Dynamic Orienteering Problem*, IEEE Internet of Things Journal (2025), DOI: https://doi.org/10.1109/JIOT.2025.3525985.

The accessible author manuscript is https://arxiv.org/abs/2409.05545v2. Its PDF SHA256 is `74b5dfab4287ec212e162842931727ce409ba157de7da0186560e2c7fddc6d4b`. Section V-A (pp. 5-6) defines the main experiment; Section V-C / Figure 5 (p. 7) defines mission success; Table VII (p. 15) provides the full successful-mission prize and cost values. Table III (p. 7) repeats selected rounded values. Reference numbers are separately transcribed in `paper_reference.csv`; they are the authors' results, not ours.

Use the distributed original source snapshot at commit `e9967bf0d7a42c9051bdb1759bebeeac42d30681`, verified against `../UPSTREAM_SNAPSHOT.json`. Do not change any author C++ source, instance, or original configuration file. All run-specific configurations belong in new output directories.

## Fixed scope

- Instance: `california20_0.csv`, 20 sensors and two depot rows.
- Initial UAV energy: 359.64 kJ; author coordinates, charging settings and sensor state.
- Two settings, chosen before new benchmark results: `mean90_std110` and `mean110_std110`.
- These code values mean power mean/SD multipliers of 0.90/1.10 and 1.10/1.10. They correspond to the paper's changes of (-10%, +10%) and (+10%, +10%); `110` does not mean an increase of 110%.
- Four strategies: Offline; DoNothing (paper: ROMP); WeightedAvg (paper: WeightedErr); Bayesian (paper: ADAPT).
- 50 independently generated trials per setting; each trial runs all four strategies. Total: 100 trial environments and 400 attempted missions.
- No MCGreedy: its min/max observation layout differs from the Bayesian average-power layout. The source's sample-count default also differs from the paper. It is outside this bounded comparison.
- At most one two-setting engineering preflight may be used to validate the harness. It is stored separately, excluded from the formal 50 trials, and cannot be used to choose a winning configuration. Bugs may be fixed before the formal run; retain a record of preflight failures.

## Configuration profile

The formal profile is `main-text-aligned`. Section V-A specifies 40 ants, 250 solver iterations, 25 no-improvement iterations, beta=2, alpha=rho=0.1, and tolerance 0.0001. These already match the online defaults. The new runner changes only the offline run copy's `num_iters_acs` (500 to 250), `max_no_impr_acs` (250 to 25), and `tol` (0.01 to 0.0001).

This profile is not claimed to recover the authors' exact table-generating configuration. Appendix C (p. 12) uses tolerance 0.01 for a separate offline comparison, and the published repository's offline defaults differ from the main text. The ambiguity remains disclosed. Keep an `author-default` profile for explicit alternative use, but do not mix its results into this benchmark.

Keep all other source defaults, including offline/online 2-opt limits 150/100, q0=0.9, Bayesian alpha0=2 and kappa0=1, equal belief/prize weights, the original 11 belief candidates from 75% to 99.9%, and WeightedAvg weights 0.5/0.5. Parameters not explicitly recoverable from the paper are identified as source defaults. Simulation uses 1-second steps, 20-second power sampling, eta_ipt=0.4 and eta_chrg=0.9.

## Shared trial environments

For each trial, run the original offline planner once and generate the real-edge matrix once with `use_avg_power=true`. Then copy the same initial input state into four separate strategy directories. Verify identical initial plan, sensor instance, offline-cost matrix, real-edge matrix and initial mission row hashes.

Bayesian logs average power. The other three strategies do not read that log and use `log_power=false`. All strategies share the same physical edge time/energy realization. Never regenerate the physical environment separately for an arm. Each strategy then updates its own state independently.

The author's C++ uses `random_device`; no algorithm seed is available. This is a shared-environment comparison, not paired algorithm RNG or bitwise repeatability. New runs may differ. Preserve generated inputs so the observed runs can be audited.

## Outcomes and denominators

Primary outcome: mission success rate (MSR), successful returns divided by all 50 attempts for each setting and strategy. A success requires the author simulator's return-home code 1, the depot as destination, and positive terminal arrival energy. Report counts alongside percentages and 95% Wilson intervals. Fifty successful trials do not establish universal 100% reliability.

Successful-mission metrics, matching the paper's conditioning:

- P*: sum of the mission log's delivered sensor energy, in kJ.
- C*: initial energy minus energy on arrival at the final depot, in kJ.
- Also report serviced sensors and simulated elapsed time as diagnostics.

Report all failed attempts by type, not just the successful subset. Summarize delivered energy across all attempts separately and label it clearly; it is not the paper's conditional P*. Different strategies can have different successful subsets, so their conditional prize means alone do not establish a fair overall winner. Any paired successful-mission comparison must state its own common-success count.

The actual simulator returns 255 for failed service, 254 for failed flight to a sensor, and 253 for failed return home on Linux, despite swapped upstream visit/service labels. These are mission outcomes, not harness crashes. A timeout, malformed output, unexpected process error or violated data contract is a separate harness error, retained in the planned-attempt denominator and reported separately. Do not retry unsuccessful missions until they pass. Do not turn failures into zeros in successful-mission means.

## Comparability and limitations

Preserve and disclose the author sliding-window script's no-op behavior: observations accumulate; a functioning 900-second window is not claimed. Preserve the original average-power sample construction and sensor-state updates, including any implementation quirks found in source inspection. Do not silently fix scientific behavior or tune parameters to match a preferred number.

Compare observed MSR with Figure 5 and observed conditional P*/C* with Table VII by reporting the actual differences. No post-hoc equivalence tolerance or guaranteed reproduction claim is permitted. The goal is to determine which selected patterns and values are recovered and where they differ, not to force agreement. The paper's values are finite experimental estimates, not exact ground truth. Results cannot establish a theme-park benefit or an improvement to ADAPT.

## Evidence and acceptance

Retain raw mission/plan/state files, commands, return codes, stdout/stderr (including timeout output), initial/final configurations, source and binary hashes, trial sharing checks, all per-mission outcomes, and aggregate tables. An independent verifier must recompute outcomes and metrics from raw evidence without importing the runner. Unit tests cover failure-code interpretation, timeout preservation, malformed data, overwrite refusal and denominators.

The batch is reviewable only when all 400 planned missions are accounted for, harness errors are absent or explicitly unresolved, all source/share checks pass, and the independent audit agrees with the summaries. A correctly recorded failed mission is valid evidence; it is not an experiment-integrity failure.

After the audit, publish the reviewed code and evidence to the existing team repository. Prepare a real-run demonstration command and a short two-person speaking guide. The students must make the actual recording; generated scripts or computer execution by the assistant are not evidence that either student recorded or presented. Canvas submission remains separate.
