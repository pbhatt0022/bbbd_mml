"""Unit tests for the D-36 EEG alpha audit, on synthetic data only."""
import numpy as np
import pandas as pd
import pytest

from bbbd.exp2_eeg_alpha_audit import (ALPHA_FAMILY, CONTROL_BANDS, audit, compare,
                                       holm, paired_by_learner)


def frame(n_learners=12, n_videos=5, shift=0.5, seed=0):
    """Two sessions per learner; session 2 is `shift` higher on every metric."""
    rng = np.random.default_rng(seed)
    rows = []
    for sub in range(1, n_learners + 1):
        for ses in (1, 2):
            for stim in range(1, n_videos + 1):
                row = {"sub": sub, "ses": ses, "stim": stim}
                for metric in [*ALPHA_FAMILY, *CONTROL_BANDS]:
                    row[metric] = rng.normal(0, 1) + (shift if ses == 2 else 0)
                rows.append(row)
    return pd.DataFrame(rows)


def test_holm_matches_worked_example():
    # Step-down: sorted p are scaled by the remaining count (3, 2, 1), then made
    # monotone. 0.01*3=0.03; 0.03*2=0.06; 0.04*1=0.04 but cannot drop below 0.06.
    adjusted = holm([0.01, 0.04, 0.03])
    assert adjusted == pytest.approx([0.03, 0.06, 0.06])


def test_holm_is_monotone_and_capped():
    adjusted = holm([0.2, 0.5, 0.9, 0.99])
    assert all(a <= 1.0 for a in adjusted)
    assert sorted(adjusted) == pytest.approx(sorted(adjusted))


def test_holm_leaves_a_single_p_alone():
    assert holm([0.042]) == pytest.approx([0.042])


def test_pairs_average_recordings_within_a_learner_session():
    df = frame(n_learners=3, n_videos=4, shift=0.0, seed=1)
    attentive, distracted = paired_by_learner(df, "log_alpha_all")
    assert len(attentive) == len(distracted) == 3
    expected = df[(df["sub"] == 1) & (df["ses"] == 1)]["log_alpha_all"].mean()
    assert attentive[0] == pytest.approx(expected)


def test_learner_missing_a_session_is_dropped_not_imputed():
    df = frame(n_learners=4, seed=2)
    df = df[~((df["sub"] == 4) & (df["ses"] == 2))]
    attentive, _ = paired_by_learner(df, "log_alpha_all")
    assert len(attentive) == 3


def test_recovers_a_known_shift():
    df = frame(n_learners=40, shift=0.8, seed=3)
    row = compare(df, "log_alpha_posterior")
    assert row["mean_diff"] == pytest.approx(0.8, abs=0.25)
    assert row["cohens_dz"] > 0
    assert row["p"] < 0.01
    assert row["pct_higher_when_distracted"] > 60


def test_no_shift_gives_no_effect():
    row = compare(frame(n_learners=40, shift=0.0, seed=4), "log_alpha_all")
    assert row["p"] > 0.05
    assert abs(row["cohens_dz"]) < 0.5


def test_sign_convention_is_distracted_minus_attentive():
    df = frame(n_learners=30, shift=-0.9, seed=5)
    row = compare(df, "log_alpha_all")
    assert row["mean_diff"] < 0 and row["cohens_dz"] < 0


def test_audit_labels_families_and_corrects_only_alpha():
    rows = audit(frame(n_learners=20, shift=0.6, seed=6))
    assert len(rows) == len(ALPHA_FAMILY) + len(CONTROL_BANDS)
    alpha = [r for r in rows if r["family"] == "alpha"]
    control = [r for r in rows if r["family"] == "control band"]
    assert len(alpha) == len(ALPHA_FAMILY)
    assert all(r["p_holm_alpha_family"] is not None for r in alpha)
    assert all(r["p_holm_alpha_family"] is None for r in control)
    # Holm can only make a p-value larger, never smaller.
    assert all(r["p_holm_alpha_family"] >= r["p"] - 1e-12 for r in alpha)


def test_missing_session_raises_rather_than_guessing():
    df = frame(n_learners=5, seed=7)
    with pytest.raises(ValueError, match="Both sessions"):
        paired_by_learner(df[df["ses"] == 1], "log_alpha_all")
