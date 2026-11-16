Data credit: TouringPlans.com — historical Animal Kingdom waits and published park-hour listings.

# Week 12: modified implementation

Jesse Zhang and Yongqi Sheng | DS 340W

Our revised paper explains the C, R and S modifications and compares them with fixed planning and the existing dynamic baseline. The experiments did not establish an improvement over D0. The Evaluation section discusses the comparison, failed trips, ablation and input sensitivities.

## Files

- [Paper PDF](ParkPlan-S-Week12-Revised-Paper.pdf) — eight pages including references
- [Overleaf source](ParkPlan-S-Week12-Overleaf.zip)
- [Code demonstration](../../experiments/week12_demo_20261115/README.md)
- [Recording outline and screen cues](recording-script.md)
- [Jesse's speaking notes](Jesse-speaker.pdf) and [Yongqi's speaking notes](Yongqi-speaker.pdf)
- [Demo and submission checklist](DEMO-AND-SUBMISSION.md)
- [Paper build notes](PAPER-QA.md) and [comparison checks](EVIDENCE-AND-RUBRIC-AUDIT.md)

The methods and full results come from the October study. This update adds the one-date demo and extends the paper's Contribution and Evaluation sections. The ADAPT UAV experiment in `reproduction/week11/` is a separate parent-paper reproduction.

## Rebuild the documents

Upload the source ZIP to Overleaf with `main.tex` as the main file. The local build used Tectonic; a fresh extracted source build matched the PDF's text and rendered pages. The Overleaf web interface was not tested.

The core demo needs Python 3.10+ with no extra packages. Regenerating the speaker PDFs needs ReportLab:

```bash
python3 coursework/week12/build_recording.py
```

TouringPlans data terms: clearly credit TouringPlans.com at the beginning of publications or redistributions, and include these terms in redistributions. Raw source data are not included.
