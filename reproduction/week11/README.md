# Week 11: ADAPT running results

This directory contains a bounded rerun of the ADAPT author's original code for two California20 power settings. The benchmark uses 50 trials per setting and four methods: Offline, ROMP (`DoNothing`), WeightedErr (`WeightedAvg`), and ADAPT (`Bayesian`). All four methods share each trial's initial plan and simulated physical environment.

Parent paper: Qian, Wang and Boyle, *Adaptive Probabilistic Planning for the Uncertain and Dynamic Orienteering Problem*, IEEE Internet of Things Journal, 2025. [Published paper](https://doi.org/10.1109/JIOT.2025.3525985) · [Accessible manuscript](https://arxiv.org/abs/2409.05545v2) · [Original code](https://github.com/sysal-bruce-publication/Uncertain-Dynamic-OP).

## Read the result

- [Three-page running-results summary (PDF)](results/Week11-Running-Results-Summary.pdf)
- [Measured results and paper comparison](results/REPORT.md)
- [Comparison CSV](results/comparison.csv), including conditional success counts, sample SDs and MSR intervals
- [Success-rate figure](results/mission-success.png)
- [Successful-mission prize and cost figure](results/success-conditioned-quality.png)
- [Independent verification](results/independent-verification.json)
- [Complete raw-evidence archives and checksums](evidence/README.md)
- [Protocol fixed before the new runs](PROTOCOL.md), [freeze receipt](protocol-freeze.json) and [paper reference values](paper_reference.csv)

P* is actual energy delivered to sensors. C* is UAV energy consumed. The paper's P*/C* means include successful missions only; MSR includes every attempt. A failed simulated mission is a recorded algorithm outcome, not automatically a broken program. Full limitations are in the protocol and result report.

## Build on Ubuntu / Windows WSL2

The benchmark and independent verifier use Python's standard library. The original C++ needs a C++20 compiler, CMake, and Boost headers. On Ubuntu, install missing prerequisites with:

```bash
sudo apt update
sudo apt install -y build-essential cmake libboost-dev python3 git
```

From this repository's root:

```bash
cmake -S reproduction -B reproduction/build -DCMAKE_BUILD_TYPE=Release
cmake --build reproduction/build -j 2
```

This builds the vendored original source, whose 69-file snapshot is checked against `reproduction/UPSTREAM_SNAPSHOT.json`. Existing local Boost headers can also be selected with CMake's `BOOST_HEADERS` argument. No paid solver, GPU, cloud account, or Python scientific package is required to run the experiment.

## Make a fresh live demonstration

Run one trial of the higher-mean setting, keeping all four outcomes:

```bash
python3 reproduction/week11/run_benchmark.py \
  --repeats 1 --scenarios 110:110 \
  --output reproduction/runs/week11-demo-01

python3 reproduction/week11/verify_results.py \
  --results reproduction/runs/week11-demo-01 \
  --upstream reproduction/ADAPT-upstream \
  --expected-attempts 4 --build-dir reproduction/build
```

If that output directory already exists, choose a new name such as `week11-demo-02`; do not delete or overwrite earlier evidence. The source uses uncontrolled `random_device`, so live outputs may differ. Show the real output, including failures. This four-mission demonstration is separate from the saved 400-mission benchmark and must not be described as having rerun all 400 missions.

## Rerun the complete fixed benchmark

```bash
python3 reproduction/week11/run_benchmark.py \
  --profile main-text-aligned --repeats 50 \
  --scenarios 90:110 110:110 \
  --output reproduction/runs/week11-new-full-run

python3 reproduction/week11/verify_results.py \
  --results reproduction/runs/week11-new-full-run \
  --upstream reproduction/ADAPT-upstream \
  --expected-attempts 400 --build-dir reproduction/build
```

The runner rejects an occupied output directory. It records every scheduled outcome and returns nonzero if a harness error occurs. Mission failures remain in the results without triggering reruns or dropping rows.

## Check the saved evidence without rerunning the algorithms

The archive contains every initial environment and strategy's original input, mission log, plan history, sensor snapshots, process logs, configurations and summary. It also contains the original batch manifest and aggregate files. It does not contain compiled binaries, external credentials, or private project files.

```bash
python3 reproduction/week11/verify_archive.py
```

That helper checks the ZIP's size, SHA256 and CRC, extracts to a fresh temporary directory, then runs the independent verifier using the vendored source. It does not run a new mission. The archive audit does not verify a local compiled binary: it preserves the original binary-hash records. The original full audit also checked the three actual execution binaries; local rebuilds may differ by toolchain.

## Optional table and figure regeneration

After extracting and auditing the evidence, use `make_report.py --results <extracted-batch> --output <new-report-dir>`. The tables can be generated without third-party packages using `--no-plots`. Plot generation requires matplotlib; keep it in an isolated environment if installing it. Do not overwrite the frozen distributed report when exploring a different run.

## Tests and provenance

```bash
python3 -m unittest discover -s reproduction/week11 -p 'test_*.py' -v
```

The tests exercise execution failures, timeout evidence, paired inputs, outcome accounting, malformed output and independent-audit corruption detection. [Build receipt](build-receipt.json) records the compiler and binary hashes. The source snapshot is unchanged. The new code is experiment orchestration, checking and reporting, not a new ADAPT algorithm.

The main-text-aligned profile changes three offline run-copy parameters to the main paper text; source defaults and Appendix C differ. The known upstream sliding-window no-op and other original state-update behavior are preserved. MCGreedy and other instances/settings are outside scope. These UAV results are separate from ParkPlan-S's theme-park replay.
