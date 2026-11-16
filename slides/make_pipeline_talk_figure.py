"""Pipeline diagram for the presentation, in plain language.

The report's version (make_pipeline_figure.py) labels each box with the run
identifier that registered it, which is right for a document with an audit
trail beside it. A listener reading a slide has no such context, so this
version names what each stage does instead.

Same structure, same claims, no estimates.

    python slides/make_pipeline_talk_figure.py        (from the repo root)
"""
import pathlib

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.patches import FancyArrowPatch, FancyBboxPatch

OUT = pathlib.Path("slides/figures/pipeline_talk.png")

DONE_FILL, DONE_EDGE = "#e8f4f4", "#2c6e6e"
EXPL_FILL, EXPL_EDGE = "#fdf0e0", "#b06c10"
NONE_FILL, NONE_EDGE = "#f2f2f2", "#9a9a9a"
TEXT = "#1a1a1a"

fig, ax = plt.subplots(figsize=(7.6, 4.2))
ax.set_xlim(0, 100)
ax.set_ylim(0, 100)
ax.axis("off")


def box(x, y, w, h, label, fill, edge, dashed=False, fs=7.0):
    ax.add_patch(FancyBboxPatch(
        (x, y), w, h, boxstyle="round,pad=0,rounding_size=1.6",
        linewidth=1.0, facecolor=fill, edgecolor=edge,
        linestyle="--" if dashed else "-"))
    ax.text(x + w / 2, y + h / 2, label, ha="center", va="center",
            fontsize=fs, color=TEXT)
    return dict(l=(x, y + h / 2), r=(x + w, y + h / 2),
                t=(x + w / 2, y + h), b=(x + w / 2, y), cx=x + w / 2)


def arrow(a, b, color):
    ax.add_patch(FancyArrowPatch(a, b, arrowstyle="-|>", mutation_scale=9,
                                 linewidth=1.0, color=color, shrinkA=1, shrinkB=1))


def band(y, text, color):
    ax.text(0, y, text, ha="left", va="center", fontsize=8.0,
            color=color, fontweight="bold")


# --- Experiment 1: the completed eye analysis -----------------------------
band(96, "Experiment 1: predicting quiz score from eye movements", DONE_EDGE)

a1 = box(0, 80, 28, 9, "Raw eye-tracking\nrecordings", DONE_FILL, DONE_EDGE)
a2 = box(34, 80, 30, 9, "Detect blinks, eye jumps\nand pauses", DONE_FILL, DONE_EDGE)
a3 = box(70, 80, 30, 9, "Eight measurements\nper recording", DONE_FILL, DONE_EDGE)
a4 = box(0, 66, 28, 9, "Quiz answers\nto a score", DONE_FILL, DONE_EDGE)
a5 = box(34, 66, 30, 9, "Match by learner\nand video", DONE_FILL, DONE_EDGE)
a6 = box(70, 66, 30, 9, "Split by learner,\nfit the model", DONE_FILL, DONE_EDGE)
a7 = box(70, 53, 30, 9, "Evaluate on learners\nthe model never saw", DONE_FILL, DONE_EDGE)

for s, e in ((a1["r"], a2["l"]), (a2["r"], a3["l"]), (a4["r"], a5["l"]),
             (a5["r"], a6["l"]), (a6["b"], a7["t"])):
    arrow(s, e, DONE_EDGE)
ax.plot([a3["cx"], a3["cx"], a5["cx"]], [80, 77.5, 77.5], color=DONE_EDGE, lw=1.0)
arrow((a5["cx"], 77.5), a5["t"], DONE_EDGE)

# --- Experiment 2: the multi-sensor comparison ----------------------------
band(46, "Experiment 2: comparing eye, heart and brain recordings", EXPL_EDGE)

b1 = box(0, 36, 30, 7.5, "Eye movements\nfrom raw recordings", EXPL_FILL, EXPL_EDGE, fs=6.6)
b2 = box(0, 27, 30, 7.5, "Heart signals:\nquality screening", EXPL_FILL, EXPL_EDGE, fs=6.6)
b3 = box(0, 18, 30, 7.5, "Brain signals:\nquality screening", EXPL_FILL, EXPL_EDGE, fs=6.6)
b4 = box(38, 24, 26, 13, "Shared sample: rows with\nall three sensors present",
         EXPL_FILL, EXPL_EDGE, fs=6.6)
b5 = box(70, 24, 30, 13, "Compare each sensor,\nand sensors combined",
         EXPL_FILL, EXPL_EDGE, fs=6.6)

BUS = b4["l"][0] - 4.0
for b in (b1, b2, b3):
    ax.plot([b["r"][0], BUS], [b["r"][1], b["r"][1]], color=EXPL_EDGE, lw=1.0)
ax.plot([BUS, BUS], [b3["r"][1], b1["r"][1]], color=EXPL_EDGE, lw=1.0)
arrow((BUS, b4["l"][1]), b4["l"], EXPL_EDGE)
arrow(b4["r"], b5["l"], EXPL_EDGE)

ax.text(50, 14.5,
        "Heart and brain inputs come from previously computed tables; "
        "the brain results were later re-derived from raw.",
        ha="center", va="center", fontsize=6.2, color=EXPL_EDGE, style="italic")

# --- What was never run ---------------------------------------------------
band(9, "Planned but not carried out", NONE_EDGE)

box(0, 0, 30, 6.5, "Combined multi-sensor\nneural network",
    NONE_FILL, NONE_EDGE, dashed=True, fs=6.6)
box(38, 0, 26, 6.5, "Shared brain-and-eye\nrepresentation", NONE_FILL, NONE_EDGE,
    dashed=True, fs=6.6)
box(70, 0, 30, 6.5, "Fresh heartbeat detection\nfrom raw", NONE_FILL, NONE_EDGE,
    dashed=True, fs=6.6)

OUT.parent.mkdir(parents=True, exist_ok=True)
fig.tight_layout(pad=0.3)
fig.savefig(OUT, dpi=200, facecolor="white")
print("wrote", OUT)
