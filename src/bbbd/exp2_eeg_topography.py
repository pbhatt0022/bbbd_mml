"""Scalp distribution of the Experiment 2 condition effect (D-39 / DV-09).

Ocular artefact projects maximally to frontal electrodes. If R-018's
low-frequency increase in the distracted session is ocular, it should be
frontal-dominant. This tests that in the recovered regional band tables,
without reprocessing raw EEG.

Primary statistic, fixed before fitting: the within-learner
frontal-minus-occipital difference of the delta condition contrast, against
zero. Positive means frontal-dominant, which is what an ocular source
predicts. Secondary: per-region delta contrasts, Holm-corrected across the
four regions. Everything else is descriptive.

Not a raw rerun, and not a re-test of R-018's numbers: these are regional
relative powers from a different pipeline than the 15 Oct whole-scalp
absolute log powers.

    python -m bbbd.exp2_eeg_topography <BBBD_Exp2_recovery_*.tar.gz>
"""
import argparse
import csv
import hashlib
import io
import tarfile
from pathlib import Path

import numpy as np
import pandas as pd
from scipy import stats

from . import runlog
from .config import load_config
from .exp2_ecg_recovery_audit import ARCHIVE_SHA256

TABLE = "MML_BBBD/04_results/eeg_full_features/eeg_features.csv"
REGIONS = ["frontal", "central", "parietal", "occipital"]
BANDS = ["delta", "theta", "alpha", "beta"]
PRIMARY_BAND = "delta"
FRONT, BACK = "frontal", "occipital"
ATTENTIVE, DISTRACTED = "ses-01", "ses-02"
N_BOOTSTRAP = 2000
SEED = 2026


def holm(pvalues):
    order = np.argsort(pvalues)
    n, adjusted, running = len(pvalues), np.empty(len(pvalues)), 0.0
    for rank, idx in enumerate(order):
        running = max(running, (n - rank) * pvalues[idx])
        adjusted[idx] = min(running, 1.0)
    return adjusted


def read_table(archive):
    digest = hashlib.sha256(Path(archive).read_bytes()).hexdigest()
    if digest != ARCHIVE_SHA256:
        raise ValueError("Recovery archive SHA-256 mismatch")
    with tarfile.open(archive, "r:gz") as bundle:
        member = bundle.getmember(TABLE)
        if not member.isfile():
            raise ValueError(f"Expected regular file: {TABLE}")
        rows = list(csv.DictReader(
            io.TextIOWrapper(bundle.extractfile(member), encoding="utf-8-sig")))
    df = pd.DataFrame(rows)
    if df.empty or not set(df["session"]) <= {ATTENTIVE, DISTRACTED}:
        raise ValueError("Unexpected sessions in the recovered EEG table")
    for region in REGIONS:
        for band in BANDS:
            df[f"eeg_{region}_{band}_rel"] = df[f"eeg_{region}_{band}_rel"].astype(float)
        df[f"eeg_{region}_slope"] = df[f"eeg_{region}_slope"].astype(float)
    return df, digest


def learner_diffs(df, column):
    """Per-learner (distracted - attentive) of `column`, learners with both sessions."""
    means = df.groupby(["subject", "session"])[column].mean().unstack("session")
    pair = means[[ATTENTIVE, DISTRACTED]].dropna()
    return (pair[DISTRACTED] - pair[ATTENTIVE]).to_numpy(), pair.index.to_numpy()


def describe(diff, name):
    sd = diff.std(ddof=1)
    t, p = stats.ttest_1samp(diff, 0.0)
    return dict(name=name, n_learners=int(len(diff)), mean_diff=float(diff.mean()),
                cohens_dz=float(diff.mean() / sd) if sd > 0 else float("nan"),
                t=float(t), p=float(p),
                pct_positive=float(100.0 * np.mean(diff > 0)))


def bootstrap_ci(diff, level=0.95, seed=SEED, n=N_BOOTSTRAP):
    rng = np.random.default_rng(seed)
    idx = rng.integers(0, len(diff), size=(n, len(diff)))
    means = diff[idx].mean(axis=1)
    lo, hi = (1 - level) / 2 * 100, (1 + level) / 2 * 100
    return float(np.percentile(means, lo)), float(np.percentile(means, hi))


def analyse(df):
    # Primary: frontal minus occipital, delta.
    front, subs_f = learner_diffs(df, f"eeg_{FRONT}_{PRIMARY_BAND}_rel")
    back, subs_b = learner_diffs(df, f"eeg_{BACK}_{PRIMARY_BAND}_rel")
    if not np.array_equal(subs_f, subs_b):
        raise ValueError("Frontal and occipital learner sets differ")
    gradient = front - back
    primary = describe(gradient, f"{PRIMARY_BAND}: {FRONT} minus {BACK}")
    primary["ci_low"], primary["ci_high"] = bootstrap_ci(gradient)
    primary["ci_level"] = 0.95
    primary["frontal_dominant"] = bool(primary["ci_low"] > 0)

    # Secondary: per-region delta, Holm across the four regions.
    regional = [describe(learner_diffs(df, f"eeg_{r}_{PRIMARY_BAND}_rel")[0], r)
                for r in REGIONS]
    for row, adj in zip(regional, holm([r["p"] for r in regional])):
        row["p_holm_region_family"] = float(adj)
        row["band"] = PRIMARY_BAND

    # Descriptive: every band and the slope, per region.
    descriptive = []
    for region in REGIONS:
        for band in BANDS:
            row = describe(learner_diffs(df, f"eeg_{region}_{band}_rel")[0], f"{region}_{band}")
            row.update(region=region, band=band, family="descriptive")
            descriptive.append(row)
        row = describe(learner_diffs(df, f"eeg_{region}_slope")[0], f"{region}_slope")
        row.update(region=region, band="slope", family="descriptive")
        descriptive.append(row)
    return primary, regional, descriptive


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("archive", type=Path)
    args = parser.parse_args()

    df, digest = read_table(args.archive)
    primary, regional, descriptive = analyse(df)

    cfg = load_config()
    run = runlog.start_run(cfg, "exp2_eeg_topography", "exp2_eeg_topography", member="A")
    runlog.save_table(run, pd.DataFrame(regional), "delta_by_region.csv")
    runlog.save_table(run, pd.DataFrame(descriptive), "all_bands_by_region.csv")
    summary = dict(
        experiment=2, decision="D-39 Proposed", deviation="DV-09",
        source="Recovered regional EEG feature table", source_table=TABLE,
        archive_sha256=digest, raw_eeg_reprocessed=False, confirmatory=False,
        ocular_correction_applied=False,
        relative_power_is_near_compositional=True,
        n_recordings=int(len(df)),
        n_attentive=int((df["session"] == ATTENTIVE).sum()),
        n_distracted=int((df["session"] == DISTRACTED).sum()),
        n_learners_paired=primary["n_learners"],
        primary=primary,
        delta_by_region={r["name"]: r for r in regional},
        n_bootstrap=N_BOOTSTRAP, seed=SEED,
    )
    runlog.save_json(run, summary, "exp2_eeg_topography.json")
    runlog.finish_run(run, note="D-39/DV-09 scalp distribution of the Exp 2 condition effect; "
                                "ocular probe for R-018, no raw rerun.")

    print(f"  primary {primary['name']}: {primary['mean_diff']:+.4f} "
          f"95% CI [{primary['ci_low']:+.4f}, {primary['ci_high']:+.4f}] "
          f"d_z {primary['cohens_dz']:+.2f} p {primary['p']:.4g}")
    print(f"  frontal-dominant (CI excludes zero, positive): {primary['frontal_dominant']}")
    for r in regional:
        print(f"    delta {r['name']:10s} d_z {r['cohens_dz']:+.2f}  "
              f"p {r['p']:.4g}  Holm {r['p_holm_region_family']:.4g}")


if __name__ == "__main__":
    main()
