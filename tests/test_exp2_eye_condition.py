"""Unit tests for the D-37 paired Experiment 2 eye condition contrast."""
import numpy as np
import pandas as pd
import pytest

from bbbd.exp2_eye_condition import CONDITION, GAZE, PRIMARY, contrast


def table(n_learners=12, n_videos=5, shift=1.0, seed=0, metric="blink_rate_min"):
    rng = np.random.default_rng(seed)
    rows = []
    for sub in range(1, n_learners + 1):
        for session, condition in (("ses-01", "attentive"), ("ses-02", "distracted")):
            for video in range(1, n_videos + 1):
                rows.append({
                    "subject": f"sub-{sub:02d}", "session": session,
                    "condition": condition, "video": video,
                    metric: rng.normal(0, 1) + (shift if condition == "distracted" else 0),
                })
    return pd.DataFrame(rows)


def test_gaze_pattern_accepts_both_sessions_only():
    base = "sub-07/ses-{}/eyetrack/sub-07_ses-{}_task-stim3_gaze_visualangle_eyetrack.tsv.gz"
    assert GAZE.fullmatch(base.format("01", "01"))
    assert GAZE.fullmatch(base.format("02", "02"))
    assert GAZE.fullmatch(base.format("03", "03")) is None


def test_gaze_pattern_requires_matching_subject_and_session():
    mismatch = ("sub-07/ses-01/eyetrack/"
                "sub-08_ses-01_task-stim3_gaze_visualangle_eyetrack.tsv.gz")
    assert GAZE.fullmatch(mismatch) is None
    crossed = ("sub-07/ses-01/eyetrack/"
               "sub-07_ses-02_task-stim3_gaze_visualangle_eyetrack.tsv.gz")
    assert GAZE.fullmatch(crossed) is None


def test_condition_labels_are_the_sidecar_strings():
    assert CONDITION == {"01": "Attentive Condition", "02": "Distracted Condition"}


def test_recovers_a_known_increase_when_distracted():
    row = contrast(table(n_learners=40, shift=0.9, seed=1), PRIMARY)
    assert row["mean_diff"] == pytest.approx(0.9, abs=0.3)
    assert row["cohens_dz"] > 0 and row["p"] < 0.01
    assert row["pct_higher_when_distracted"] > 60


def test_no_difference_is_not_reported_as_one():
    row = contrast(table(n_learners=40, shift=0.0, seed=2), PRIMARY)
    assert row["p"] > 0.05


def test_sign_is_distracted_minus_attentive():
    row = contrast(table(n_learners=30, shift=-0.8, seed=3), PRIMARY)
    assert row["mean_diff"] < 0 and row["cohens_dz"] < 0


def test_learner_means_average_videos_before_pairing():
    df = table(n_learners=3, n_videos=4, shift=0.0, seed=4)
    row = contrast(df, PRIMARY)
    assert row["n_learners"] == 3
    expected = df[(df["subject"] == "sub-01") & (df["condition"] == "attentive")][PRIMARY].mean()
    means = df.groupby(["subject", "condition"])[PRIMARY].mean().unstack("condition")
    assert means.loc["sub-01", "attentive"] == pytest.approx(expected)


def test_learner_missing_the_distracted_session_is_dropped():
    df = table(n_learners=5, seed=5)
    df = df[~((df["subject"] == "sub-05") & (df["condition"] == "distracted"))]
    assert contrast(df, PRIMARY)["n_learners"] == 4


def test_blink_rate_is_flagged_scale_independent():
    assert contrast(table(seed=6), "blink_rate_min")["scale_dependent"] is False
    df = table(seed=6, metric="saccade_rate_min")
    assert contrast(df, "saccade_rate_min")["scale_dependent"] is True
