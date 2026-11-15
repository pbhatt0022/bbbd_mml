"""Redraw the system-architecture diagram for the report and the deck.

Replaces the hand-made 13 Nov PNG, which still labelled the Experiment 2
matched comparison as "awaiting evaluation" -- R-017 has since run it.

The diagram carries no estimates: it shows which route produced which
registered run ID, and which routes were never executed. Nothing here is
computed from data.

Usage:  python slides/make_pipeline_figure.py            (from the repo root)
Writes: docs/report_assets/pipeline.png  and  slides/figures/pipeline.png
"""
import pathlib
import shutil

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.patches import FancyArrowPatch, FancyBboxPatch

OUT = pathlib.Path("docs/report_assets/pipeline.png")
COPY = pathlib.Path("slides/figures/pipeline.png")

DONE_FILL, DONE_EDGE = "#e8f4f4", "#2c6e6e"
EXPL_FILL, EXPL_EDGE = "#fdf0e0", "#b06c10"
NONE_FILL, NONE_EDGE = "#f2f2f2", "#9a9a9a"
TEXT = "#1a1a1a"

fig, ax = plt.subplots(figsize=(7.6, 4.4))
ax.set_xlim(0, 100)
ax.set_ylim(0, 100)
ax.axis("off")


def box(x, y, w, h, label, fill, edge, dashed=False, fs=7.0):
    """Draw one node and return its (left, right, top, bottom, cx, cy) anchors."""
    ax.add_patch(FancyBboxPatch(
        (x, y), w, h,
        boxstyle="round,pad=0,rounding_size=1.6",
        linewidth=1.0, facecolor=fill, edgecolor=edge,
        linestyle="--" if dashed else "-"))
    ax.text(x + w / 2, y + h / 2, label, ha="center", va="center",
            fontsize=fs, color=TEXT, wrap=True)
    return dict(l=(x, y + h / 2), r=(x + w, y + h / 2),
                t=(x + w / 2, y + h), b=(x + w / 2, y),
                cx=x + w / 2, cy=y + h / 2)


def arrow(a, b, color, dashed=False, rad=0.0):
    ax.add_patch(FancyArrowPatch(
        a, b, arrowstyle="-|>", mutation_scale=9, linewidth=1.0,
        color=color, linestyle="--" if dashed else "-",
        shrinkA=1, shrinkB=1,
        connectionstyle=f"arc3,rad={rad}"))


def band(y, text, color):
    ax.text(0, y, text, ha="left", va="center", fontsize=8.0,
            color=color, fontweight="bold")


# ---------------------------------------------------------------- band 1
band(96, "Completed Experiment 1 eye analysis", DONE_EDGE)

a1 = box(0, 80, 28, 9, "Released gaze and pupil", DONE_FILL, DONE_EDGE)
a2 = box(34, 80, 30, 9, "Eye events and quality checks", DONE_FILL, DONE_EDGE)
a3 = box(70, 80, 30, 9, "Individual feature table", DONE_FILL, DONE_EDGE)
a4 = box(0, 66, 28, 9, "Quiz items to score targets", DONE_FILL, DONE_EDGE)
a5 = box(34, 66, 30, 9, "Join by learner and video", DONE_FILL, DONE_EDGE)
a6 = box(70, 66, 30, 9, "Frozen folds and nested ridge", DONE_FILL, DONE_EDGE)
a7 = box(70, 53, 30, 9, "Registered evaluation\nR-013 (corrects R-012)",
         DONE_FILL, DONE_EDGE, fs=6.6)

arrow(a1["r"], a2["l"], DONE_EDGE)
arrow(a2["r"], a3["l"], DONE_EDGE)
arrow(a4["r"], a5["l"], DONE_EDGE)
arrow(a5["r"], a6["l"], DONE_EDGE)
arrow(a6["b"], a7["t"], DONE_EDGE)
# feature table drops into the join
ax.plot([a3["cx"], a3["cx"], a5["cx"]], [80, 77.5, 77.5], color=DONE_EDGE, lw=1.0)
arrow((a5["cx"], 77.5), a5["t"], DONE_EDGE)

# ---------------------------------------------------------------- band 2
band(46, "Experiment 2 matched comparison — exploratory, on recovered "
         "physiology tables", EXPL_EDGE)

b1 = box(0, 36, 30, 7.5, "Attentive gaze and pupil → eye features\nR-014",
         EXPL_FILL, EXPL_EDGE, fs=6.6)
b2 = box(0, 27, 30, 7.5, "Recovered ECG tables → eligibility audit\nR-015",
         EXPL_FILL, EXPL_EDGE, fs=6.6)
b3 = box(0, 18, 30, 7.5, "Recovered EEG tables → QC audit\nR-016",
         EXPL_FILL, EXPL_EDGE, fs=6.6)
b4 = box(38, 24, 26, 13,
         "Common attentive cohort\nand separate outer folds\nR-016",
         EXPL_FILL, EXPL_EDGE, fs=6.6)
b5 = box(70, 24, 30, 13,
         "Matched ridge, per modality\nand early fusion\nR-017",
         EXPL_FILL, EXPL_EDGE, fs=6.6)

BUS = b4["l"][0] - 4.0
for b in (b1, b2, b3):
    ax.plot([b["r"][0], BUS], [b["r"][1], b["r"][1]], color=EXPL_EDGE, lw=1.0)
ax.plot([BUS, BUS], [b3["r"][1], b1["r"][1]], color=EXPL_EDGE, lw=1.0)
arrow((BUS, b4["l"][1]), b4["l"], EXPL_EDGE)
arrow(b4["r"], b5["l"], EXPL_EDGE)

ax.text(50, 14.5,
        "Audits of saved tables, not fresh detector or MNE runs. "
        "Experiment 1 folds are untouched.",
        ha="center", va="center", fontsize=6.2, color=EXPL_EDGE, style="italic")

# ---------------------------------------------------------------- band 3
band(9, "Not executed", NONE_EDGE)

c1 = box(0, 0, 30, 6.5, "ICA variant of EEG cleaning  (RQ3)",
         NONE_FILL, NONE_EDGE, dashed=True, fs=6.6)
c2 = box(38, 0, 26, 6.5, "Deep encoders  (RQ4)",
         NONE_FILL, NONE_EDGE, dashed=True, fs=6.6)
c3 = box(70, 0, 30, 6.5, "Fresh Exp 2 ECG detector run",
         NONE_FILL, NONE_EDGE, dashed=True, fs=6.6)

OUT.parent.mkdir(parents=True, exist_ok=True)
fig.tight_layout(pad=0.3)
fig.savefig(OUT, dpi=200, facecolor="white")
COPY.parent.mkdir(parents=True, exist_ok=True)
shutil.copyfile(OUT, COPY)
print("wrote", OUT, "and", COPY)
