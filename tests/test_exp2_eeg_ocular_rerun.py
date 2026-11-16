"""Unit tests for the D-40 ocular-control rerun, on synthetic data only."""
import numpy as np
import pandas as pd
import pytest

from bbbd.exp2_eeg_ocular_rerun import (RAW, analyse, bootstrap_ci, describe,
                                        holm, learner_diffs)

REGIONS = ["frontal", "central", "parietal", "occipital"]


def table(n_learners=28, n_videos=5, uncorrected_shift=0.08,
          corrected_shift=0.08, seed=0):
    """Both variants, both sessions; session 2 shifted by the given amounts."""
    rng = np.random.default_rng(seed)
    rows = []
    for sub in range(1, n_learners + 1):
        for ses in ("ses-01", "ses-02"):
            for video in range(1, n_videos + 1):
                # Both variants come from the same recording, so they share the
                # noise draw; only the condition shift differs between them.
                base = {region: rng.normal(0.25, 0.05) for region in REGIONS}
                for variant in ("corrected", "uncorrected"):
                    shift = corrected_shift if variant == "corrected" else uncorrected_shift
                    bump = shift if ses == "ses-02" else 0.0
                    row = {"subject": f"sub-{sub:02d}", "session": ses,
                           "video": video, "variant": variant}
                    for region in REGIONS:
                        row[f"eeg_{region}_delta_rel"] = base[region] + bump
                    rows.append(row)
    return pd.DataFrame(rows)


def test_raw_pattern_matches_only_bids_raw_eeg():
    good = "sub-07/ses-02/eeg/sub-07_ses-02_task-stim03_eeg.bdf"
    assert RAW.match(good)
    # The authors' derivative copy must not be picked up (D-01).
    assert RAW.match("derivatives/sub-07/ses-02/eeg/sub-07_ses-02_task-stim03_desc-eeg.bdf") is None
    # Subject and session must agree between folder and filename.
    assert RAW.match("sub-07/ses-02/eeg/sub-08_ses-02_task-stim03_eeg.bdf") is None
    assert RAW.match("sub-07/ses-01/eeg/sub-07_ses-02_task-stim03_eeg.bdf") is None


def test_holm_is_monotone_and_capped():
    adjusted = holm([0.01, 0.9, 0.03])
    assert all(0 <= a <= 1 for a in adjusted)
    assert adjusted[0] == pytest.approx(0.03)


def test_learner_diffs_pairs_within_learner():
    df = table(n_learners=3, n_videos=2, seed=1)
    diff = learner_diffs(df[df.variant == "corrected"], "eeg_frontal_delta_rel")
    assert len(diff) == 3


def test_effect_that_survives_correction_is_reported_as_surviving():
    out = analyse(table(n_learners=40, uncorrected_shift=0.08,
                        corrected_shift=0.08, seed=2), REGIONS)
    assert all(out["survives_correction"].values())
    assert all(abs(v) < 0.5 for v in out["dz_change"].values())


def test_effect_removed_by_correction_is_reported_as_not_surviving():
    out = analyse(table(n_learners=40, uncorrected_shift=0.08,
                        corrected_shift=0.0, seed=3), REGIONS)
    assert not any(out["survives_correction"].values())
    # Correction shrank the effect, so the change in d_z is strongly negative.
    assert all(v < -0.5 for v in out["dz_change"].values())


def test_dz_change_is_corrected_minus_uncorrected():
    df = table(n_learners=30, uncorrected_shift=0.0, corrected_shift=0.08, seed=4)
    out = analyse(df, REGIONS)
    for region in REGIONS:
        expected = (out["corrected"]["delta_by_region"][region]["cohens_dz"]
                    - out["uncorrected"]["delta_by_region"][region]["cohens_dz"])
        assert out["dz_change"][region] == pytest.approx(expected, abs=1e-4)
    assert all(v > 0 for v in out["dz_change"].values())


def test_both_variants_are_analysed_separately():
    out = analyse(table(n_learners=20, seed=5), REGIONS)
    assert set(out["corrected"]["delta_by_region"]) == set(REGIONS)
    assert set(out["uncorrected"]["delta_by_region"]) == set(REGIONS)
    assert "gradient" in out["corrected"] and "gradient" in out["uncorrected"]


def test_bootstrap_interval_is_deterministic_and_brackets_the_mean():
    diff = np.array([0.02, -0.01, 0.03, 0.0, 0.015, -0.005])
    lo, hi = bootstrap_ci(diff)
    assert lo < diff.mean() < hi
    assert (lo, hi) == bootstrap_ci(diff)


def test_describe_reports_n_and_sign():
    row = describe(np.array([0.1, 0.2, -0.1, 0.4]), "x")
    assert row["n_learners"] == 4
    assert row["mean_diff"] > 0
