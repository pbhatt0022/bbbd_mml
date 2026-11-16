"""Unit tests for the D-41 RQ3 cleaning comparison, on synthetic data only."""
import numpy as np
import pandas as pd
import pytest

from bbbd.exp2_matched_ridge import EYE
from bbbd.exp2_rq3_cleaning import VARIANTS, run_ridge


class FakeRaw:
    """Minimal stand-in exposing what regional_features needs."""

    def __init__(self, n_channels, names, sfreq=128.0, n_times=2560, seed=0):
        self._data = np.random.default_rng(seed).normal(0, 1e-5, (n_channels, n_times))
        self.ch_names = names
        self.info = {"sfreq": sfreq}

    def copy(self):
        return self

    def pick(self, _):
        return self

    def get_data(self):
        return self._data


def cohort(n_learners=20, n_videos=5, eeg_columns=4, seed=0):
    rng = np.random.default_rng(seed)
    rows = []
    for sub in range(1, n_learners + 1):
        for video in range(1, n_videos + 1):
            row = {"subject": sub, "video": video, "quiz_z": rng.normal()}
            for col in EYE:
                row[col] = rng.normal()
            for col in ("hr_mean", "hr_sd", "rmssd"):
                row[col] = rng.normal()
            for i in range(eeg_columns):
                row[f"eeg_x{i}"] = rng.normal()
            rows.append(row)
    return pd.DataFrame(rows)


def folds(table, n_splits=5, n_schemes=2):
    subs = sorted(table.subject.unique())
    assign = {s: i % n_splits for i, s in enumerate(subs)}
    return {f"scheme{j}": np.array([assign[s] for s in table.subject])
            for j in range(n_schemes)}


@pytest.fixture
def cfg():
    return {
        "cv": {"n_splits": 5, "inner_splits": 3},
        "reconciliation": {"ridge_alpha_log10_min": -1, "ridge_alpha_log10_max": 2,
                           "ridge_alpha_count": 4, "inner_scoring": "neg_mean_squared_error"},
        "stats": {"n_bootstrap": 50},
        "seeds": {"global": 2026},
    }


def test_variants_are_the_two_cleaning_methods():
    assert VARIANTS == ("eog_regression", "ica")


def test_run_ridge_returns_a_ranking_over_the_three_single_modalities(cfg):
    table = cohort(seed=1)
    out = run_ridge(table, table[["subject", "video"]], folds(table), cfg,
                    [c for c in table if c.startswith("eeg_")])
    assert sorted(out["ranking"]) == ["ecg", "eeg", "eye"]
    assert set(out["metrics"]) == {"eye", "ecg", "eeg", "eye_ecg",
                                   "all_sensors", "selected_single"}


def test_ranking_is_ordered_by_descending_spearman(cfg):
    table = cohort(seed=2)
    out = run_ridge(table, table[["subject", "video"]], folds(table), cfg,
                    [c for c in table if c.startswith("eeg_")])
    rhos = [out["metrics"][m]["spearman"] for m in out["ranking"]]
    assert rhos == sorted(rhos, reverse=True)


def test_all_three_paired_contrasts_are_reported(cfg):
    table = cohort(seed=3)
    out = run_ridge(table, table[["subject", "video"]], folds(table), cfg,
                    [c for c in table if c.startswith("eeg_")])
    assert set(out["comparisons"]) == {"eeg_minus_eye", "eeg_minus_eye_ecg",
                                       "all_sensors_minus_selected_single"}
    for result in out["comparisons"].values():
        assert result["ci_low"] <= result["estimate"] <= result["ci_high"]


def test_identical_features_give_an_identical_ranking(cfg):
    """The comparison must be driven by the EEG columns, nothing else."""
    table = cohort(seed=4)
    eeg_columns = [c for c in table if c.startswith("eeg_")]
    first = run_ridge(table, table[["subject", "video"]], folds(table), cfg, eeg_columns)
    second = run_ridge(table, table[["subject", "video"]], folds(table), cfg, eeg_columns)
    assert first["ranking"] == second["ranking"]
    assert first["metrics"]["eeg"]["spearman"] == pytest.approx(
        second["metrics"]["eeg"]["spearman"])


def test_changing_only_eeg_can_change_the_eeg_score_but_not_the_eye_score(cfg):
    table = cohort(seed=5)
    eeg_columns = [c for c in table if c.startswith("eeg_")]
    base = run_ridge(table, table[["subject", "video"]], folds(table), cfg, eeg_columns)
    swapped = table.copy()
    rng = np.random.default_rng(99)
    for col in eeg_columns:
        swapped[col] = rng.normal(size=len(swapped))
    other = run_ridge(swapped, table[["subject", "video"]], folds(table), cfg, eeg_columns)
    assert base["metrics"]["eye"]["spearman"] == pytest.approx(
        other["metrics"]["eye"]["spearman"])
    assert base["metrics"]["eeg"]["spearman"] != pytest.approx(
        other["metrics"]["eeg"]["spearman"])


def test_regional_features_emit_the_24_column_schema():
    from bbbd.exp2_rq3_cleaning import regional_features
    regions = {"frontal": ["A", "B"], "central": ["C"],
               "parietal": ["D"], "occipital": ["E"]}
    names = ["A", "B", "C", "D", "E"]
    raw = FakeRaw(len(names), names)
    cfg_eeg = {"bands_hz": {"delta": [1, 4], "theta": [4, 8],
                            "alpha": [8, 13], "beta": [13, 30]},
               "regions": regions}
    row = regional_features(raw, cfg_eeg)
    assert len(row) == 24
    for region in regions:
        assert f"eeg_{region}_alpha_theta" in row
        assert f"eeg_{region}_slope" in row
        assert row[f"eeg_{region}_alpha_theta"] == pytest.approx(
            row[f"eeg_{region}_alpha_rel"] / row[f"eeg_{region}_theta_rel"])


def test_missing_region_channels_raise_rather_than_silently_dropping():
    from bbbd.exp2_rq3_cleaning import regional_features
    raw = FakeRaw(1, ["A"])
    cfg_eeg = {"bands_hz": {"delta": [1, 4], "theta": [4, 8],
                            "alpha": [8, 13], "beta": [13, 30]},
               "regions": {"frontal": ["A"], "central": ["ZZ"]}}
    with pytest.raises(ValueError, match="No channels present"):
        regional_features(raw, cfg_eeg)
