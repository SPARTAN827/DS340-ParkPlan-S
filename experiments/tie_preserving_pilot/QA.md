**Data credit: TouringPlans.com. Source terms are included in SOURCE-CREDIT.txt.**

# Verification record — 2026-10-14

**PASS for the scope below.** This is an implementation/raw-data check in the current work session, not an external independent reviewer or proof of real visitor benefits.

- Nine targeted unit tests passed, including the exact allowed difference from the preserved replay source.
- The 165 new CSV rows are identical to the old frequent-replan rows in **every field other than the policy label**. The 495 existing comparison rows were reused, not recomputed.
- A separate verifier, without importing the simulation or summary functions, recomputed the shared-success counts/means and checked all **965 visit events** against the pinned raw source CSVs using the latest prior posted observation and the 15-minute freshness limit.
- The verifier reconstructed all **800 decisions**, including **401 switches**, and confirmed the route order, completed rides, elapsed/wait/walk/service totals, failures and deadlines.
- There were **zero different tied-cost candidate events** on these new-policy trajectories. Equality handling is nevertheless exercised by the synthetic tests. This is not a claim that ties are impossible on other data or assumptions.
- All 31 recorded old-artifact hashes remained unchanged after the run and verification. The old v2 ZIP was not repackaged.
- Both new PDFs have one page. Embedded fonts were checked: Times New Roman in both; SimHei for Chinese. The Chinese HTML rendering was visually inspected for legibility and layout. PDF page count/font checks are not a claim that the actual PDFs were raster-inspected.

One initial runner attempt stopped in a new audit assertion when comparing a null gain (representing an infinite incumbent cost) with a float; it stopped before writing result files. The guard was corrected to handle the infeasible incumbent first, and the new-policy run then completed and passed the separate raw-data audit. No original completed experiment was rerun or changed.

Machine-readable result: `verification.json`. The original data/forecast limitations, timestamp-conflict tie convention and exploratory status still apply. No new threshold was selected and no uncertainty-aware rule was implemented.
