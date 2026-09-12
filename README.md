# DS340-ParkPlan-S

Group 9 DS340 project: ParkPlan-S. ADAPT parent-paper code, data, and reproduction instructions.

Team: Jesse Zhang and Yongqi Sheng.

## First parent research paper

Qiuchen Qian, Yanran Wang, and David Boyle. **Adaptive Probabilistic Planning for the Uncertain and Dynamic Orienteering Problem**. IEEE Internet of Things Journal, 12(10), 13988–14001, 2025.

- Published paper: https://doi.org/10.1109/JIOT.2025.3525985
- Open reading version: https://arxiv.org/abs/2409.05545
- Author repository: https://github.com/sysal-bruce-publication/Uncertain-Dynamic-OP
- Author commit: `e9967bf0d7a42c9051bdb1759bebeeac42d30681`
- Original public data: https://github.com/sysal-bruce-publication/Uncertain-Dynamic-OP/tree/main/instances
- Included source and license: [reproduction/ADAPT-upstream](reproduction/ADAPT-upstream/)
- Included datasets: [instances](reproduction/ADAPT-upstream/instances/)

The public synthetic instances have 20, 30, or 40 sensor nodes for UAV charging-scheduling simulations. The California20 CSV contains 20 sensors plus two depot rows. Columns are lat, lon, alt, volt; the first three contain converted relative coordinates, not raw geographic coordinates. These are the parent paper's data, not theme-park waiting-time data.

ADAPT supplies a methodological foundation for planning and replanning under uncertain costs and a limited budget. ParkPlan-S proposes a stable route-switching decision layer for theme-park itineraries. This repository does not demonstrate theme-park performance.

## Run on Ubuntu 24.04 / Windows WSL2 Ubuntu 24.04

Native Ubuntu 24.04 was verified. User-side Windows/WSL execution is pending. Windows users should run these commands inside Ubuntu, not PowerShell.

Install prerequisites once:

```bash
sudo apt update
sudo apt install build-essential cmake python3 git libboost-dev
```

Clone into a new location and run:

```bash
git clone https://github.com/SPARTAN827/DS340-ParkPlan-S.git
cd DS340-ParkPlan-S
python3 reproduction/setup_and_run.py
```

C++20 and Boost >=1.78 are required. This lightweight repository does not bundle Boost or compiled binaries. The helper builds the original offline-planning, simulation, and online-planning modules and runs one complete California20 Bayesian mission. It uses only Python's standard library and does not require a paid solver.

Each invocation creates a fresh `reproduction/runs/smoke-*` folder. Inspect that run's `summary.json`, `console.log`, `processes.json`, and `input/mission_log.csv`. Do not execute the upstream `main.sh` or cleanup scripts for this coursework workflow.

## Provenance and limits

Original author source files are preserved unchanged and checked against `UPSTREAM_SNAPSHOT.json` before execution. Author code is MIT licensed: see [LICENSE.txt](reproduction/ADAPT-upstream/LICENSE.txt). Upstream authors retain credit; the team does not claim to have written ADAPT. The added CMake and Python build/run helpers were prepared with AI assistance.

The previously verified portable package completed one full mission on native Ubuntu 24.04, with 9 sensor services, 9 Bayesian replans, and successful return. That prior check is not a claim that a team member has already run this public checkout or recorded it. Random outcomes may differ.

The Bayesian configuration selects average-power samples before edge generation. The original sliding-window script has a no-op subtraction bug; its behavior is preserved, so this run uses accumulated observations rather than a validated 900-second window. A successful smoke run is not a reproduction of all paper experiments or proof of ParkPlan-S effectiveness.

The original simulator intentionally returns status 1 for successful return home. The helper accepts it only for a home-target step with additional checks, and finally exits 0 on success; it does not ignore arbitrary errors.

## Coursework status

This repository supports the first parent-paper assignment. A genuine code-download-and-run Kaltura recording and the final submission PDF remain separate deliverables. No recording link is fabricated here.
