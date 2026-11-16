"""Unit tests for the D-42 Aux-task decoder, on synthetic data only."""
import numpy as np
import pandas as pd
import pytest

from bbbd.exp2_attention_cnn import (EYE_FEATURES, N_SPLITS, OVERLAP, SEEDS, SFREQ,
                                     WINDOW_S, baseline, recording_scores,
                                     standardize, windows)


def test_window_geometry_matches_the_d21_decision():
    assert (WINDOW_S, OVERLAP) == (4.0, 0.5)
    size = int(WINDOW_S * SFREQ)
    n_samples = size * 5
    out = windows(*[np.random.default_rng(0).normal(size=n_samples) for _ in range(3)])
    assert out.shape[1:] == (3, size)
    # 50% overlap: stride is half a window.
    expected = (n_samples - size) // (size // 2) + 1
    assert out.shape[0] == expected


def test_short_recording_yields_no_windows_rather_than_crashing():
    short = [np.zeros(10) for _ in range(3)]
    assert windows(*short).shape[0] == 0


def test_standardize_is_zero_mean_unit_sd():
    x = np.array([1.0, 2.0, 3.0, 4.0])
    z = standardize(x)
    assert z.mean() == pytest.approx(0.0)
    assert z.std() == pytest.approx(1.0)


def test_standardize_survives_a_constant_channel():
    assert np.all(standardize(np.full(50, 7.0)) == 0.0)


def test_standardizing_removes_a_per_recording_offset():
    base = np.random.default_rng(1).normal(size=512)
    assert standardize(base) == pytest.approx(standardize(base + 100.0))


def test_recording_scores_average_windows_within_a_recording():
    p = np.array([0.1, 0.3, 0.9, 0.7])
    rec = np.array([0, 0, 1, 1])
    y = np.array([0, 0, 1, 1])
    probs, labels = recording_scores(p, rec, y)
    assert probs == pytest.approx([0.2, 0.8])
    assert list(labels) == [0, 1]


def test_recording_label_is_constant_within_a_recording():
    probs, labels = recording_scores(np.array([0.4, 0.6]), np.array([3, 3]),
                                     np.array([1, 1]))
    assert len(probs) == len(labels) == 1


def test_baseline_is_perfect_on_a_separable_feature():
    n = 40
    rng = np.random.default_rng(2)
    y = np.array([0, 1] * (n // 2))
    frame = pd.DataFrame({f: rng.normal(size=n) for f in EYE_FEATURES})
    frame["saccade_rate_min"] = np.where(y == 0, 150.0, 100.0) + rng.normal(0, 1, n)
    folds = np.arange(n) % N_SPLITS
    assert baseline(frame, folds, y) > 0.95


def test_baseline_is_near_chance_on_noise():
    n = 60
    rng = np.random.default_rng(3)
    y = np.array([0, 1] * (n // 2))
    frame = pd.DataFrame({f: rng.normal(size=n) for f in EYE_FEATURES})
    assert 0.2 < baseline(frame, np.arange(n) % N_SPLITS, y) < 0.8


def test_three_seeds_are_used_per_the_methods_plan():
    assert len(SEEDS) == 3
