"""Redraw R-017 values that are already stored in its registered JSON summary.

Introduces no new fit, test, aggregation, interval or significance claim.
Source run ID is printed on the figure. ponytail: one script, one figure.
"""
import json
import pathlib

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt

SRC = pathlib.Path("results/R-017_exp2_matched_ridge/exp2_matched_ridge.json")
OUT = pathlib.Path("slides/figures/r017_matched.png")

d = json.loads(SRC.read_text())
assert d["run_id"] == "R-017" and d["exploratory"] is True

bars = [
    ("eye", "eye"),
    ("ECG", "ecg"),
    ("EEG", "eeg"),
    ("eye+ECG", "eye_ecg"),
    ("all sensors", "all_sensors"),
    ("selected single", "selected_single"),
]
contrasts = [
    ("EEG - eye", "eeg_minus_eye"),
    ("EEG - (eye+ECG)", "eeg_minus_eye_ecg"),
    ("all - selected single", "all_sensors_minus_selected_single"),
]

fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(11.0, 3.6))

rho = [d["metrics"][k]["spearman"] for _, k in bars]
labels = [lbl for lbl, _ in bars]
ax1.barh(labels, rho, color=["#0000dc" if v >= 0 else "#f08c00" for v in rho])
ax1.axvline(0, color="black", lw=0.8)
ax1.set_xlabel(r"held-out Spearman $\rho$")
ax1.set_title("Matched Experiment 2 modalities (R-017)", fontsize=10)
ax1.invert_yaxis()
for y, v in enumerate(rho):
    ax1.text(v + (0.012 if v >= 0 else -0.012), y, f"{v:+.3f}",
             va="center", ha="left" if v >= 0 else "right", fontsize=8)
ax1.set_xlim(-0.46, 0.20)

ax2.axvspan(-0.10, 0.10, color="#e1e1e1")
for y, (lbl, key) in enumerate(contrasts):
    c = d["comparisons"][key]
    ax2.plot([c["ci_low"], c["ci_high"]], [y, y], color="#0000dc", lw=2.2)
    ax2.plot(c["estimate"], y, "o", color="#0000dc", ms=6)
    ax2.text(c["ci_high"] + 0.02, y,
             f"{c['estimate']:+.3f}  [{c['ci_low']:+.3f}, {c['ci_high']:+.3f}]"
             f"  {int(c['ci_level'] * 100)}%", va="center", fontsize=8)
ax2.axvline(0, color="black", lw=0.8)
ax2.set_yticks(range(len(contrasts)))
ax2.set_yticklabels([lbl for lbl, _ in contrasts])
ax2.invert_yaxis()
ax2.set_xlabel(r"paired learner-bootstrap $\Delta\rho$ (fixed predictions)")
ax2.set_title("Paired contrasts, no permutation test (R-017)", fontsize=10)
ax2.set_xlim(-0.30, 0.95)
ax2.text(0.0, -0.62, r"equivalence margin $\pm$0.10", ha="center",
         fontsize=7, color="#555555")
ax2.set_ylim(len(contrasts) - 0.5, -0.9)

fig.text(0.005, 0.015,
         f"R-017, exploratory, n = {d['n_rows']} rows, {d['n_learners']} learners; "
         f"{d['n_bootstrap']} learner bootstrap resamples. Redrawn from the "
         "registered summary; no new estimate.", fontsize=6.5, color="#555555")
fig.tight_layout(rect=(0, 0.045, 1, 1))
OUT.parent.mkdir(parents=True, exist_ok=True)
fig.savefig(OUT, dpi=200)
print("wrote", OUT)
