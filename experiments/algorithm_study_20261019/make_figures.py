#!/usr/bin/env python3
"""Render reproducible research figures, never a slide deck or inferred winner.

Usage (isolated pre-existing plotting environment):
  /tmp/parkplan-plot-venv/bin/python experiments/algorithm_study_20261019/make_figures.py
  .../python .../make_figures.py --conceptual-only

Every paired estimate is read from its own summary comparison, with its own n.
The all-attempt denominator is displayed separately.  Sensitivity cells have
neutral coloring, including when conditional time savings coexist with failures.
Source hashes are saved alongside figures.  No new analyses or tuning occur here.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
from pathlib import Path

os.environ.setdefault("MPLCONFIGDIR", "/tmp/parkplan-matplotlib-cache")
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.patches import FancyArrowPatch, FancyBboxPatch, Rectangle


HERE = Path(__file__).resolve().parent
OUT = HERE / "figures"
NAVY = "#16324F"
BLUE = "#3078A8"
AMBER = "#B56D22"
INK = "#172B3B"
GRAY = "#5B6874"
LIGHT = "#EDF2F5"
GRID = "#D7E0E7"
WHITE = "#FFFFFF"

plt.rcParams.update({
    "font.family": "DejaVu Sans", "font.size": 12,
    "text.color": INK, "axes.labelcolor": INK,
    "axes.edgecolor": GRID, "xtick.color": GRAY, "ytick.color": INK,
    "figure.facecolor": WHITE, "savefig.facecolor": WHITE,
    "svg.fonttype": "none", "pdf.fonttype": 42,
})

CAPTION = ("Source: TouringPlans.com. Exploratory posted-wait simulation, not measured visitor savings. "
           "Synthetic travel geometry and service assumptions.")
FILES: dict[str, str] = {}


def read_json(path):
    FILES[str(path.relative_to(HERE))] = hashlib.sha256(path.read_bytes()).hexdigest()
    return json.loads(path.read_text())


def save(fig, name):
    for suffix in ("svg", "png", "pdf"):
        fig.savefig(OUT / f"{name}.{suffix}", dpi=180, bbox_inches=None)
    plt.close(fig)


def heading(fig, kicker, title, subtitle):
    fig.text(.05, .946, kicker.upper(), fontsize=11, color=BLUE, weight="bold")
    fig.text(.05, .888, title, fontsize=25, color=NAVY, weight="bold")
    fig.text(.05, .846, subtitle, fontsize=11.2, color=GRAY)


def footer(fig, note=CAPTION):
    fig.text(.05, .035, note, fontsize=8.7, color=GRAY)


def paired(summary, policy):
    return summary["paired"]["dynamic_minus_" + policy]


def primary(summary, selection):
    total = summary["attempted_days"]
    tau = selection["selected_decay"]
    policies = ["calibrated", "rollout", "scenario_open_loop"]
    colors = [BLUE, NAVY, AMBER]
    names = [f"Calibrated D0\n(decay = {tau} min)",
             "Adaptive rollout\n(primary hypothesis)",
             "Shared-order SAA\n(ablation)"]
    fig = plt.figure(figsize=(16, 9))
    intervals = [paired(summary, p)["block7_date_bootstrap"]["percentile_95"] for p in policies]
    no_clear_gain = all(lo is not None and lo <= 0 <= hi for lo, hi in intervals)
    heading(fig, "ParkPlan-S / algorithm comparison",
            "No clear time gain in this replay evaluation" if no_clear_gain else
            "Does a richer replanner actually save time?",
            f"{total} evaluation dates ({summary['date_range'][0]} to {summary['date_range'][1]})  |  "
            "Six rides  |  Same initial route  |  Uniform 10-min walk / 10-min service")
    fig.text(.05, .775, "A   Paired time difference vs. existing D0", fontsize=14, weight="bold")
    fig.text(.65, .775, "B   Finished all six rides", fontsize=14, weight="bold")
    fig.text(.65, .74, f"All {total} attempts; uncompleted attempts stay visible", fontsize=10, color=GRAY)

    ax = fig.add_axes([.245, .29, .345, .42])
    values = [paired(summary, p) for p in policies]
    cis = [v["block7_date_bootstrap"]["percentile_95"] for v in values]
    extent = [0.0] + [float(x) for interval in cis for x in interval if x is not None]
    span = max(max(extent) - min(extent), 5)
    ax.set_xlim(min(extent) - span * .16, max(extent) + span * .16)
    ax.axvline(0, color=GRAY, lw=1.1, ls="--", zorder=1)
    yticks = []
    for i, (entry, interval, color) in enumerate(zip(values, cis, colors)):
        y = 2 - i
        mu = entry["mean_saved_minutes"]
        low, high = interval
        yticks.append(f"{names[i]}\npaired n = {entry['paired_success_days']}")
        if mu is not None and low is not None and high is not None:
            ax.errorbar(mu, y + .09, xerr=[[mu - low], [high - mu]],
                        fmt="o", markersize=8, color=color,
                        ecolor=color, elinewidth=2.3, capsize=5, zorder=3)
            ax.text(.5, y - .20, f"{mu:+.2f} min   [ {low:+.2f}, {high:+.2f} ]",
                    transform=ax.get_yaxis_transform(), ha="center", va="center",
                    fontsize=11, color=color, weight="bold")
        else:
            ax.text(.5, y, "No paired estimate", transform=ax.get_yaxis_transform(), ha="center")
    ax.set_yticks([2, 1, 0], yticks, fontsize=10.5)
    ax.tick_params(axis="y", length=0, pad=15)
    ax.set_ylim(-.5, 2.55)
    ax.grid(axis="x", color=GRID, alpha=.7, lw=.7)
    for spine in ax.spines.values():
        spine.set_visible(False)
    ax.set_xlabel("D0 time − candidate time (model minutes)", labelpad=13, fontsize=11)
    fig.text(.245, .201, "Negative: candidate slower     |     Positive: candidate faster", fontsize=9.8, color=GRAY)
    fig.text(.245, .169, "Dots: paired means. Bars: 95% seven-date block-bootstrap intervals.", fontsize=9.8, color=GRAY)

    bx = fig.add_axes([.725, .29, .225, .42])
    complete_policies = ["fixed", "dynamic", "calibrated", "rollout", "scenario_open_loop"]
    complete_labels = ["Fixed", "Existing D0", f"Calibrated ({tau})", "Rollout", "SAA"]
    for i, policy in enumerate(complete_policies):
        y = len(complete_policies) - 1 - i
        completed = summary["by_policy"][policy]["success_days"]
        failed = total - completed
        bx.barh(y, completed, height=.55, color=NAVY, zorder=2)
        bx.barh(y, failed, left=completed, height=.55, color=LIGHT,
                edgecolor=GRID, hatch="///", linewidth=.6, zorder=2)
        bx.text(completed / 2, y, f"{completed}/{total}", ha="center", va="center",
                color=WHITE, fontsize=10, weight="bold")
        bx.text(completed + failed / 2, y, str(failed), ha="center", va="center",
                color=GRAY, fontsize=9)
    bx.set_xlim(0, total)
    bx.set_ylim(-.6, 4.65)
    bx.set_yticks(list(reversed(range(5))), complete_labels, fontsize=10.5)
    bx.tick_params(axis="y", length=0, pad=8)
    bx.set_xlabel("Number of evaluation dates", labelpad=13, fontsize=11)
    bx.grid(axis="x", color=GRID, alpha=.7, lw=.7)
    for spine in bx.spines.values():
        spine.set_visible(False)
    fig.text(.725, .201, "Solid: completed     Hatched: did not complete", fontsize=9.7, color=GRAY)
    fig.text(.05, .112,
             "Read together: time estimates use each pair's joint-success dates, not all attempts. "
             "The interval excludes model / input uncertainty.",
             fontsize=11, color=NAVY, weight="bold")
    fig.text(.05, .077,
             f"Decay {tau} was selected on earlier validation dates. These evaluation dates had been examined in prior work; "
             "this is not a pristine new holdout.", fontsize=9.5, color=GRAY)
    footer(fig)
    save(fig, "01_candidate_comparison")


def sensitivity(reference, sensitivity_summaries, selection):
    entries = [
        ("uniform5", "Uniform 5 / 5", "Walk / service minutes"),
        ("reference", "Uniform 10 / 10", "Primary reference inputs"),
        ("uniform15", "Uniform 15 / 15", "Walk / service minutes"),
        ("illustrative_fast", "Illustrative graph × 0.8", "Travel-scale sensitivity"),
        ("illustrative", "Illustrative graph × 1.0", "Nonuniform travel + ride-specific service"),
        ("illustrative_slow", "Illustrative graph × 1.2", "Travel-scale sensitivity"),
    ]
    all_summaries = {"reference": reference, **sensitivity_summaries}
    missing = [name for name, _, _ in entries if name not in all_summaries]
    if missing:
        raise FileNotFoundError(f"Sensitivity summaries not ready: {', '.join(missing)}")
    tau = selection["selected_decay"]
    fig = plt.figure(figsize=(16, 10))
    sensitivity_intervals = [paired(summary, p)["block7_date_bootstrap"]["percentile_95"]
                             for summary in all_summaries.values()
                             for p in ("calibrated", "rollout", "scenario_open_loop")]
    no_clear_gain = all(lo is not None and lo <= 0 <= hi for lo, hi in sensitivity_intervals)
    heading(fig, "ParkPlan-S / common-input sensitivity",
            "No clear time gain across six input settings" if no_clear_gain else
            "Input assumptions can change the conclusion",
            "Every cell compares candidate vs. D0 under identical inputs. "
            "Positive = candidate faster on joint-success dates; negative = slower.")
    ax = fig.add_axes([0, 0, 1, 1])
    ax.set_xlim(0, 1)
    ax.set_ylim(0, 1)
    ax.axis("off")
    left, label_width, col_width = .05, .27, .215
    policies = ["calibrated", "rollout", "scenario_open_loop"]
    titles = [f"Calibrated D0 (decay {tau})", "Adaptive rollout", "Shared-order SAA"]
    for j, title in enumerate(titles):
        ax.text(left + label_width + (j + .5) * col_width, .775, title,
                ha="center", va="center", fontsize=13, weight="bold", color=NAVY)
    height = .096
    top = .742
    for i, (name, label, detail) in enumerate(entries):
        summary = all_summaries[name]
        total = summary["attempted_days"]
        d0_failed = total - summary["by_policy"]["dynamic"]["success_days"]
        y = top - (i + 1) * height
        ax.text(left, y + height * .64, label, fontsize=13, weight="bold", va="center")
        ax.text(left, y + height * .34, detail, fontsize=9.5, color=GRAY, va="center")
        for j, policy in enumerate(policies):
            entry = paired(summary, policy)
            mu = entry["mean_saved_minutes"]
            low, high = entry["block7_date_bootstrap"]["percentile_95"]
            failed = total - summary["by_policy"][policy]["success_days"]
            x = left + label_width + j * col_width
            ax.add_patch(Rectangle((x + .004, y + .004), col_width - .008, height - .008,
                                   facecolor=LIGHT, edgecolor=WHITE, linewidth=1))
            center = x + col_width / 2
            ax.text(center, y + height * .76, f"{mu:+.2f} min" if mu is not None else "No estimate",
                    ha="center", va="center", fontsize=17, weight="bold", color=NAVY)
            ci_text = f"95% CI [{low:+.2f}, {high:+.2f}]" if low is not None else "CI undefined"
            ax.text(center, y + height * .52, ci_text, ha="center", va="center", fontsize=9.3, color=GRAY)
            ax.text(center, y + height * .30, f"paired n = {entry['paired_success_days']} / {total}",
                    ha="center", va="center", fontsize=9.7)
            ax.text(center, y + height * .10, f"not completed: candidate {failed} | D0 {d0_failed}",
                    ha="center", va="center", fontsize=9.2, color=GRAY)
    fig.text(.05, .122,
             "No cell is a universal win: jointly completed dates differ across cells; unsuccessful attempts are not assigned zero time.",
             fontsize=11, weight="bold", color=NAVY)
    fig.text(.05, .085,
             "Intervals: 95% seven-date block bootstrap. The illustrative graph is not a measured 2018 park map. "
             "These checks do not validate real-world travel times.", fontsize=9.7, color=GRAY)
    footer(fig)
    save(fig, "02_input_sensitivity")


def flow():
    fig = plt.figure(figsize=(16, 9))
    heading(fig, "ParkPlan-S / first principles",
            "Plan with what is known. Execute one action. Learn again.",
            "Single objective: minimize total time to finish the same six rides = walking + queueing + service.")
    ax = fig.add_axes([0, 0, 1, 1])
    ax.set_xlim(0, 1)
    ax.set_ylim(0, 1)
    ax.axis("off")
    cards = [
        (.05, "1  Current snapshot", "Location + clock\nRemaining rides + visible waits"),
        (.29, "2  Choose next ride", "Compare remaining-time costs\nCommit only the next action"),
        (.53, "3  Execute one visit", "Walk → queue → ride\nTime and location change"),
        (.77, "4  New snapshot", "Observe information now available\nNever read the real future"),
    ]
    width, bottom, height = .18, .585, .16
    for x, title, body in cards:
        ax.add_patch(FancyBboxPatch((x, bottom), width, height,
            boxstyle="round,pad=0.008,rounding_size=0.012", facecolor=LIGHT,
            edgecolor=GRID, linewidth=1))
        ax.text(x + width / 2, bottom + .115, title, ha="center", va="center",
                fontsize=13, weight="bold", color=NAVY)
        ax.text(x + width / 2, bottom + .056, body, ha="center", va="center",
                fontsize=9.5, color=GRAY, linespacing=1.5)
    for x in (.23, .47, .71):
        ax.add_patch(FancyArrowPatch((x + .012, .665), (x + .048, .665),
            arrowstyle="-|>", mutation_scale=15, color=BLUE, linewidth=1.8))
    ax.plot([.86, .86, .14], [.574, .49, .49], color=BLUE, linewidth=1.7)
    ax.add_patch(FancyArrowPatch((.14, .49), (.14, .574),
        arrowstyle="-|>", mutation_scale=15, color=BLUE, linewidth=1.7))
    ax.text(.50, .445,
            "After every completed ride: re-evaluate. Replanning does not require changing the route.",
            ha="center", va="center", fontsize=12, weight="bold", color=NAVY)

    boxes = [
        (.05, .43, "EXISTING D0: point-forecast replanning",
         "Forecast complete remaining orders using current information.\n"
         "Choose the lowest predicted total time; preserve the incumbent on ties.\n"
         "Only the next ride is executed before the next replan."),
        (.53, .42, "ROLLOUT CANDIDATE: explicitly model later decisions",
         "Try each next ride on the same training-day scenarios.\n"
         "Within each scenario, D0 sees only simulated current information.\n"
         "Compare mean completion time, including later replanning."),
    ]
    for x, width, title, body in boxes:
        ax.add_patch(FancyBboxPatch((x, .18), width, .19,
            boxstyle="round,pad=0.008,rounding_size=0.010", facecolor=WHITE,
            edgecolor=GRID, linewidth=1.2))
        ax.text(x + .015, .325, title, fontsize=11.5, weight="bold", color=NAVY)
        ax.text(x + .015, .255, body, fontsize=10.2, color=GRAY, va="center", linespacing=1.7)
    fig.text(.05, .111,
             "Research question: does modeling future feedback improve decisions enough to overcome forecast / scenario error?",
             fontsize=12, weight="bold", color=NAVY)
    fig.text(.05, .074,
             "The richer model is a testable hypothesis, not a guarantee. Calibration changes the wait predictor; "
             "the shared-order SAA ablation omits adaptive tails.", fontsize=10, color=GRAY)
    footer(fig, "Conceptual decision diagram. No numerical result is claimed here. Dataset analyses credit TouringPlans.com; "
                "the executor uses synthetic geometry.")
    save(fig, "03_feedback_first_principles")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--conceptual-only", action="store_true")
    args = parser.parse_args()
    OUT.mkdir(parents=True, exist_ok=True)
    flow()
    if not args.conceptual_only:
        selection = read_json(HERE / "selection.json")
        reference = read_json(HERE / "evaluation/summary.json")
        variants = {path.parent.name: read_json(path)
                    for path in sorted((HERE / "sensitivity").glob("*/summary.json"))}
        primary(reference, selection)
        sensitivity(reference, variants, selection)
    manifest = {
        "source_files_sha256": FILES,
        "figure_script_sha256": hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
        "figures": [p.name for p in sorted(OUT.iterdir()) if p.suffix in {".svg", ".png", ".pdf"}],
        "interpretation": "Exploratory conditional posted-wait-proxy differences, with all-attempt completion shown separately.",
        "source_credit": "TouringPlans.com",
        "geometry": "Synthetic; nonuniform graph is an illustrative sensitivity, not a measured park map",
        "uncertainty": "Existing summary 95% seven-date block-bootstrap intervals; input/model uncertainty excluded",
    }
    (OUT / "figure_manifest.json").write_text(json.dumps(manifest, indent=2) + "\n")
    print(json.dumps({"generated": manifest["figures"], "source_files": list(FILES)}, indent=2))


if __name__ == "__main__":
    main()
