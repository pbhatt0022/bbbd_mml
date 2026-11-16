"""Unit tests for the D-39 scalp-distribution probe, on synthetic data only."""
import numpy as np
import pandas as pd
import pytest

from bbbd.exp2_eeg_topography import (BANDS, REGIONS, analyse, bootstrap_ci,
                                      describe, holm, learner_diffs)


def frame(n_learners=28, n_videos=5, frontal_shift=0.0, occipital_shift=0.0, seed=0):
    """Both sessions per learner; session 2 is shifted by region."""
    rng = np.random.default_rng(seed)
    rows = []
    for sub in range(1, n_learners + 1):
        for ses in ("ses-01", "ses-02"):
            for video in range(1, n_videos + 1):
                row = {"subject": f"sub-{sub:02d}", "session": ses, "video": video}
                for region in REGIONS:
                    bump = 0.0
                    if ses == "ses-02":
                        bump = frontal_shift if region == "frontal" else (
                            occipital_shift if region == "occipital" else 0.0)
                    for band in BANDS:
                        row[f"eeg_{region}_{band}_rel"] = rng.normal(0.25, 0.05) + (
                            bump if band == "delta" else 0.0)
                    row[f"eeg_{region}_slope"] = rng.normal(-1.2, 0.3)
                rows.append(row)
    return pd.DataFrame(rows)


def test_holm_is_monotone_and_capped():
    adjusted = holm([0.01, 0.04, 0.03, 0.9])
    assert all(0 <= a <= 1 for a in adjusted)
    assert adjusted[0] == pytest.approx(0.04)


def test_learner_diffs_average_videos_then_subtract():
    df = frame(n_learners=3, n_videos=4, seed=1)
    diff, subs = learner_diffs(df, "eeg_frontal_delta_rel")
    assert len(diff) == len(subs) == 3
    one = df[df["subject"] == "sub-01"]
    expected = (one[one.session == "ses-02"]["eeg_frontal_delta_rel"].mean()
                - one[one.session == "ses-01"]["eeg_frontal_delta_rel"].mean())
    assert diff[0] == pytest.approx(expected)


def test_learner_missing_a_session_is_dropped():
    df = frame(n_learners=5, seed=2)
    df = df[~((df.subject == "sub-05") & (df.session == "ses-02"))]
    diff, _ = learner_diffs(df, "eeg_frontal_delta_rel")
    assert len(diff) == 4


def test_frontal_only_shift_is_detected_as_frontal_dominant():
    primary, _, _ = analyse(frame(n_learners=40, frontal_shift=0.08, seed=3))
    assert primary["mean_diff"] > 0
    assert primary["frontal_dominant"] is True
    assert primary["ci_low"] > 0


def test_equal_shift_everywhere_is_not_frontal_dominant():
    primary, _, _ = analyse(frame(n_learners=40, frontal_shift=0.08,
                                  occipital_shift=0.08, seed=4))
    assert primary["frontal_dominant"] is False
    assert primary["ci_low"] < 0 < primary["ci_high"]


def test_occipital_shift_gives_a_negative_gradient():
    primary, _, _ = analyse(frame(n_learners=40, occipital_shift=0.08, seed=5))
    assert primary["mean_diff"] < 0
    assert primary["frontal_dominant"] is False


def test_regional_rows_cover_every_region_and_are_holm_corrected():
    _, regional, descriptive = analyse(frame(n_learners=20, seed=6))
    assert [r["name"] for r in regional] == REGIONS
    assert all(r["p_holm_region_family"] >= r["p"] - 1e-12 for r in regional)
    # Four bands plus a slope row for each region.
    assert len(descriptive) == len(REGIONS) * (len(BANDS) + 1)


def test_bootstrap_interval_brackets_the_mean_and_is_deterministic():
    diff = np.array([0.1, -0.2, 0.3, 0.05, 0.0, 0.25, -0.1, 0.15])
    lo, hi = bootstrap_ci(diff)
    assert lo < diff.mean() < hi
    assert (lo, hi) == bootstrap_ci(diff)


def test_describe_reports_the_sign_and_share_above_zero():
    row = describe(np.array([1.0, 2.0, 3.0, -1.0]), "x")
    assert row["mean_diff"] == pytest.approx(1.25)
    assert row["pct_positive"] == pytest.approx(75.0)
