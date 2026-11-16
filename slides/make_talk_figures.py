"""Presentation versions of the two result figures, in plain language.

The report's figures label axes and panels with the project's own vocabulary
and run identifiers, which is right beside explanatory prose. A listener
reading a slide has none of that, so these versions name what is plotted.

Both redraw values already stored in the registered run summaries. Neither
introduces a new estimate, test or interval.

    python slides/make_talk_figures.py        (from the repo root)
"""
import json
import pathlib

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt

BLUE, ORANGE, GREY = "#0000dc", "#f08c00", "#555555"
OUT = pathlib.Path("slides/figures")


def load(path):
    return json.loads(pathlib.Path(path).read_text())


# --------------------------------------------------- validation (Experiment 1)
def validation_figure():
    d = load("results/R-004_eye_rq0_exp1/rq0_eye_exp1.json")
    h = d["h0b_attend_vs_distract"]
    fig, axes = plt.subplots(1, 2, figsize=(9.0, 3.0))
    panels = [
        ("Eye movements per minute", "saccade_rate_per_min",
         "Fewer eye movements when distracted"),
        ("Blinks per minute", "blink_rate_per_min",
         "More blinks when distracted"),
    ]
    for ax, (title, key, caption) in zip(axes, panels):
        a, b = h[key]["mean_01"], h[key]["mean_02"]
        bars = ax.bar(["Attentive\nviewing", "Distracted\nviewing"], [a, b],
                      color=[BLUE, ORANGE], width=0.55)
        for bar, value in zip(bars, (a, b)):
            ax.text(bar.get_x() + bar.get_width() / 2, value,
                    f"{value:.2f}" if value < 10 else f"{value:.1f}",
                    ha="center", va="bottom", fontsize=9)
        ax.set_title(title, fontsize=10)
        ax.set_ylabel("per minute", fontsize=8)
        ax.set_ylim(0, max(a, b) * 1.25)
        ax.spines[["top", "right"]].set_visible(False)
        ax.tick_params(labelsize=8)
        ax.text(0.5, -0.30, caption, transform=ax.transAxes, ha="center",
                fontsize=8.5, color=GREY)
    fig.text(0.005, 0.015,
             "27 learners, 263 recordings. Each learner contributes to both "
             "bars, so the comparison is within-person.",
             fontsize=6.5, color=GREY)
    fig.tight_layout(rect=(0, 0.12, 1, 1))
    fig.savefig(OUT / "r004_rates_talk.png", dpi=200, facecolor="white")
    print("wrote", OUT / "r004_rates_talk.png")


# ------------------------------------------------ sensor comparison (Exp 2)
def comparison_figure():
    d = load("results/R-017_exp2_matched_ridge/exp2_matched_ridge.json")
    bars = [("Brain (EEG)", "eeg"), ("Eye tracking", "eye"), ("Heart (ECG)", "ecg"),
            ("Eye + heart", "eye_ecg"), ("All three", "all_sensors"),
            ("Best single sensor", "selected_single")]
    contrasts = [("Brain minus eye", "eeg_minus_eye"),
                 ("Brain minus eye+heart", "eeg_minus_eye_ecg"),
                 ("All three minus best single", "all_sensors_minus_selected_single")]

    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(11.0, 3.4))

    rho = [d["metrics"][k]["spearman"] for _, k in bars]
    ax1.barh([lbl for lbl, _ in bars], rho,
             color=[BLUE if v >= 0 else ORANGE for v in rho])
    ax1.axvline(0, color="black", lw=0.8)
    ax1.set_xlabel("How well it ordered learners by quiz score\n"
                   "(0 = chance, right is better)", fontsize=8.5)
    ax1.set_title("Each sensor on its own, and combined", fontsize=10)
    ax1.invert_yaxis()
    for y, v in enumerate(rho):
        ax1.text(v + (0.012 if v >= 0 else -0.012), y, f"{v:+.3f}",
                 va="center", ha="left" if v >= 0 else "right", fontsize=8)
    ax1.set_xlim(-0.46, 0.22)
    ax1.tick_params(labelsize=8.5)

    ax2.axvspan(-0.10, 0.10, color="#e1e1e1")
    for y, (lbl, key) in enumerate(contrasts):
        c = d["comparisons"][key]
        ax2.plot([c["ci_low"], c["ci_high"]], [y, y], color=BLUE, lw=2.4)
        ax2.plot(c["estimate"], y, "o", color=BLUE, ms=6)
        ax2.text(c["ci_high"] + 0.02, y,
                 f"{c['estimate']:+.3f}  [{c['ci_low']:+.3f}, {c['ci_high']:+.3f}]",
                 va="center", fontsize=8)
    ax2.axvline(0, color="black", lw=0.8)
    ax2.set_yticks(range(len(contrasts)))
    ax2.set_yticklabels([lbl for lbl, _ in contrasts], fontsize=8.5)
    ax2.set_ylim(len(contrasts) - 0.35, -0.6)
    ax2.text(0.0, len(contrasts) - 0.6, "grey band = \"close enough to call equal\"",
             ha="center", fontsize=7.5, color=GREY)
    ax2.set_xlabel("Difference between sensors, with 90–95% confidence interval\n"
                   "(a difference counts only if the whole bar clears 0)", fontsize=8.5)
    ax2.set_title("Differences between sensors", fontsize=10)
    ax2.set_xlim(-0.30, 0.95)
    ax2.tick_params(labelsize=8.5)

    fig.text(0.005, 0.015,
             f"{d['n_rows']} learner–video rows from {d['n_learners']} learners. "
             "Every sensor judged on the same rows, learners and data splits.",
             fontsize=6.5, color=GREY)
    fig.tight_layout(rect=(0, 0.05, 1, 1))
    fig.savefig(OUT / "r017_matched_talk.png", dpi=200, facecolor="white")
    print("wrote", OUT / "r017_matched_talk.png")


if __name__ == "__main__":
    OUT.mkdir(parents=True, exist_ok=True)
    validation_figure()
    comparison_figure()
