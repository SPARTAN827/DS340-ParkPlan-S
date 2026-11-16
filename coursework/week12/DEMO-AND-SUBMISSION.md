Data credit: TouringPlans.com — historical Animal Kingdom posted waits and published park-hour listings.

# Week 12: what to submit and how to record

Jesse Zhang and Yongqi Sheng. Due November 15, 2026, 23:59 as shown in the assignment; the screenshot does not state a timezone. This is a group assignment: one member submits.

## Submission items

1. Team code repository: https://github.com/SPARTAN827/DS340-ParkPlan-S
2. A real Kaltura recording showing both members explaining code execution and results. Replace the pending field in `Canvas-submission.txt` after recording/uploading. The assignment does not prescribe video length.
3. `ParkPlan-S-Week12-Revised-Paper.pdf`. The paper preserves and revises Abstract, Introduction, Related Work and Method, explicitly identifies the contribution, and adds comparative Evaluation and Conclusion.

The Overleaf ZIP is editable source, not a replacement for the required PDF. Speaker PDFs and the script are preparation, not proof of an actual recording, team agreement, upload or submission. Do not reuse the Week 11 drone recording as if it demonstrated these park modifications.

## What changed

The C/R/S methods and full comparison were implemented and evaluated in the October study. They are not new November experiments. Week 12 adds a fresh-run wrapper, its tests and verification, clearer contribution documentation, and a revised paper with the saved comparisons. The original study and ADAPT author snapshot remain unchanged.

The main result is negative: rollout did not establish an advantage over D0. Report this directly. The strongest rubric tier for controlled original/modified-dataset comparisons is not established: six walking/service settings reuse the same wait records. No grade, similarity score or real-world visitor benefit is claimed.

## Set up on Windows using an existing WSL terminal

Open a new WSL terminal. Clone into a new folder (do not replace an existing project):

```bash
git clone https://github.com/SPARTAN827/DS340-ParkPlan-S.git DS340-Week12
cd DS340-Week12
curl --fail --location --output /tmp/parkplan-ak-933161b.tar.gz https://api.github.com/repos/TouringPlans/DisneyAnimalKingdomWaitTimes/tarball/933161b8bebb7cd50e0d54bcb3578484875487fa
python3 experiments/week12_demo_20261115/run_demo.py --archive /tmp/parkplan-ak-933161b.tar.gz
```

Copy only the commands, not Markdown backtick fences. If the folder already exists, use a different new folder name and `cd` into it. Python 3.10+ is required. Core code needs no pip packages. WSL is a prerequisite, not installed by these instructions. Native PowerShell instructions are in the demo README but native Windows execution has not been verified.

The wrapper checks the archive SHA-256 before execution:

`23eca800b048aecd4b3a2469e78f63f24f64637eb785c8401386e219a177f812`

## Record a genuine run

Use `recording-script.md` for screen cues; each speaker's PDF contains only spoken paragraphs and timestamp headings. Suggested total time is 5-6 minutes, not a course limit or a measured recording.

1. Show the actual repository commit and the new `experiments/week12_demo_20261115/` folder.
2. Explain what D0 already does, then C/R/S and the parent-paper adaptation boundary.
3. Run the command above while recording. New `runs/demo-*` files are written each time. The program executes the unchanged planner; it is not a prerecorded table player.
4. On the predetermined first evaluation date, the verified preparation run had **five genuine closed-at-arrival failures**: F/D0/C/R completed one ride each; S completed five. `elapsed` for an unfinished trip is not a six-ride completion time. Show the failure reasons and successful integrity check. Do not change the date to obtain a more favorable result.
5. Then show the paper's full-study tables. They cover 165 attempts per policy, not the single-date live demo. Shared-success time comparisons and all-attempt completion counts have different denominators.
6. Both members should explain their own parts. Rehearse first; do not claim discussion or contributions that did not occur.
7. Upload the real recording to Kaltura, copy its actual share URL, and verify video/audio playback and instructor/TA access under the required sharing setting. Paste that URL into the submission text and attach the PDF.

## Check or rerun the research

The demo README gives engine/wrapper tests, full published-evidence verification and the full frozen study commands. Run full experimental regeneration in a separate copy: it changes derived outputs and new selection timestamps invalidate the original hash lock. A demo integrity PASS is not evidence that rollout wins.

## Data terms

You're free to use these data however you see fit, subject to: (1) clearly credit TouringPlans.com at the beginning of publications or redistributions; (2) include these terms in redistributions. No raw wait CSVs are bundled here.
