"""Register the D-36 audit of the 15 Oct Experiment 2 EEG alpha tables.

The 15 October analysis ran from raw BDF outside this repository, before
`prereg-v1`, with no run ID. This recomputes its paired statistics from the
saved per-recording table so the result has a run ID and a reproducible path.

It is an audit of a saved table, not a raw EEG rerun, and it does not certify
how the 15 October run executed. Quiz scores are not involved: this is an RQ0
condition check only.

    python -m bbbd.exp2_eeg_alpha_audit <eeg_alpha_per_recording.csv>
"""
import argparse
import hashlib
from pathlib import Path

import numpy as np
import pandas as pd
from scipy import stats

from . import runlog
from .config import load_config

# The six alpha metrics the 15 Oct v2 run corrected together, and the control
# bands it reported descriptively beside them.
ALPHA_FAMILY = [
    "log_alpha_all", "log_alpha_posterior",
    "rel_alpha_all", "rel_alpha_posterior",
    "alpha_flank_all", "alpha_flank_posterior",
]
CONTROL_BANDS = [
    f"log_{band}_{scope}"
    for band in ("delta", "theta", "beta", "gamma_lo")
    for scope in ("all", "posterior")
]
ATTENTIVE_SES, DISTRACTED_SES = 1, 2

# Headline values printed by the 15 Oct v2 summary, to be compared against the
# recomputation. Discrepancies are reported, not reconciled away (DV-07).
REPORTED = {
    "log_alpha_all": dict(mean_diff=0.058, cohens_dz=0.65, t=3.59),
    "log_alpha_posterior": dict(mean_diff=0.074, cohens_dz=0.80, t=4.37),
    "rel_alpha_all": dict(mean_diff=0.021, cohens_dz=0.11, t=0.58),
    "rel_alpha_posterior": dict(mean_diff=-0.001, cohens_dz=-0.00, t=-0.02),
    "alpha_flank_all": dict(mean_diff=0.001, cohens_dz=0.00, t=0.02),
    "alpha_flank_posterior": dict(mean_diff=0.041, cohens_dz=0.41, t=2.25),
}


def holm(pvalues):
    """Holm-Bonferroni adjusted p-values, in the order given."""
    order = np.argsort(pvalues)
    n = len(pvalues)
    adjusted = np.empty(n, dtype=float)
    running = 0.0
    for rank, idx in enumerate(order):
        running = max(running, (n - rank) * pvalues[idx])
        adjusted[idx] = min(running, 1.0)
    return adjusted


def paired_by_learner(df, metric):
    """Session means per learner, then the pair for learners present in both."""
    means = df.groupby(["sub", "ses"])[metric].mean().unstack("ses")
    if ATTENTIVE_SES not in means or DISTRACTED_SES not in means:
        raise ValueError(f"Both sessions required for {metric}")
    pair = means[[ATTENTIVE_SES, DISTRACTED_SES]].dropna()
    return pair[ATTENTIVE_SES].to_numpy(), pair[DISTRACTED_SES].to_numpy()


def compare(df, metric):
    attentive, distracted = paired_by_learner(df, metric)
    diff = distracted - attentive
    n = len(diff)
    sd = diff.std(ddof=1)
    t, p = stats.ttest_rel(distracted, attentive)
    # Wilcoxon is undefined when every difference is zero.
    w_p = float(stats.wilcoxon(distracted, attentive).pvalue) if np.any(diff) else float("nan")
    return dict(
        metric=metric, n_learners=n,
        mean_attentive=float(attentive.mean()), mean_distracted=float(distracted.mean()),
        mean_diff=float(diff.mean()),
        pct_higher_when_distracted=float(100.0 * np.mean(diff > 0)),
        cohens_dz=float(diff.mean() / sd) if sd > 0 else float("nan"),
        t=float(t), p=float(p), p_wilcoxon=w_p,
    )


def audit(df):
    alpha = [compare(df, m) for m in ALPHA_FAMILY]
    for row, p_adj in zip(alpha, holm([r["p"] for r in alpha])):
        row["family"] = "alpha"
        row["p_holm_alpha_family"] = float(p_adj)
    control = [compare(df, m) for m in CONTROL_BANDS]
    for row in control:
        row["family"] = "control band"
        row["p_holm_alpha_family"] = None
    return alpha + control


def discrepancies(rows, tol=0.011):
    """Where the recomputation disagrees with the 15 Oct printed summary."""
    found = {}
    by_metric = {r["metric"]: r for r in rows}
    for metric, reported in REPORTED.items():
        row = by_metric[metric]
        off = {k: dict(reported=v, recomputed=round(row[k], 4))
               for k, v in reported.items() if abs(row[k] - v) > tol}
        if off:
            found[metric] = off
    return found


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("table", type=Path, help="eeg_alpha_per_recording.csv from the v2 run")
    args = parser.parse_args()

    digest = hashlib.sha256(args.table.read_bytes()).hexdigest()
    df = pd.read_csv(args.table)
    missing = [c for c in ["sub", "ses", "stim", *ALPHA_FAMILY, *CONTROL_BANDS]
               if c not in df.columns]
    if missing:
        raise ValueError(f"Saved table is missing columns: {missing}")
    if not set(df["ses"].unique()) <= {ATTENTIVE_SES, DISTRACTED_SES}:
        raise ValueError(f"Unexpected session labels: {sorted(df['ses'].unique())}")

    rows = audit(df)
    off = discrepancies(rows)

    cfg = load_config()
    run = runlog.start_run(cfg, "exp2_eeg_alpha_audit", "exp2_eeg_alpha_audit", member="A")
    runlog.save_table(run, pd.DataFrame(rows), "eeg_alpha_condition_tests.csv")
    # Keep the audited input beside the run: without it nothing here is checkable.
    runlog.save_table(run, df, "eeg_alpha_per_recording_source.csv")

    headline = next(r for r in rows if r["metric"] == "log_alpha_posterior")
    summary = dict(
        experiment=2, source="Saved 15 Oct 2026 v2 per-recording EEG alpha table",
        source_sha256=digest, decision="D-36 Proposed", deviation="DV-07",
        raw_eeg_reprocessed=False, confirmatory=False,
        predates_prereg_tag=True, quiz_scores_used=False,
        condition_mapping_assumed={"ses-1": "attentive", "ses-2": "distracted"},
        eog_regression_or_ica_applied=False,
        n_recordings=int(len(df)), n_learners=int(df["sub"].nunique()),
        n_learners_paired=headline["n_learners"],
        alpha_family_size=len(ALPHA_FAMILY),
        headline_metric="log_alpha_posterior", headline=headline,
        alpha_significant_after_holm=[r["metric"] for r in rows
                                      if r["family"] == "alpha"
                                      and r["p_holm_alpha_family"] is not None
                                      and r["p_holm_alpha_family"] < 0.05],
        control_bands_with_p_below_05=[r["metric"] for r in rows
                                       if r["family"] == "control band" and r["p"] < 0.05],
        discrepancies_vs_15_oct_summary=off or "none beyond rounding",
    )
    runlog.save_json(run, summary, "eeg_alpha_audit.json")
    runlog.finish_run(run, note="D-36/DV-07 retrospective audit of saved Exp 2 EEG alpha "
                                "tables; RQ0 condition check, no raw EEG rerun.")
    for key in ("n_recordings", "n_learners", "n_learners_paired",
                "alpha_significant_after_holm", "control_bands_with_p_below_05",
                "discrepancies_vs_15_oct_summary"):
        print(f"  {key}: {summary[key]}")
    print(f"  headline {headline['metric']}: d_z={headline['cohens_dz']:+.2f} "
          f"t={headline['t']:+.2f} p_holm={headline['p_holm_alpha_family']:.5f}")


if __name__ == "__main__":
    main()
