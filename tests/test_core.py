"""Unit tests on synthetic data. Run: pytest -q"""
import numpy as np
import pytest

from bbbd import cv, ecg, eye, isc, stats


# ---------------------------------------------------------------- cv
def test_group_folds_no_leakage_and_balanced():
    groups = np.repeat(np.arange(40), np.random.default_rng(0).integers(3, 7, 40))
    folds = cv.make_group_folds(groups, n_splits=5, seed=1)
    cv.check_no_leakage(folds, groups)
    sizes = np.bincount(folds)
    assert sizes.max() - sizes.min() <= 6


def test_leakage_detected():
    with pytest.raises(ValueError):
        cv.check_no_leakage(np.array([0, 1]), np.array(["s1", "s1"]))


def test_cv_recovers_signal():
    rng = np.random.default_rng(0)
    groups = np.repeat(np.arange(60), 4)
    X = rng.normal(size=(240, 5))
    y = X[:, 0] + 0.5 * rng.normal(size=240)
    pred = cv.cross_val_predict_grouped(X, y, cv.make_group_folds(groups, 5, 0))
    assert cv.score(y, pred)["spearman"] > 0.7


def test_feature_fn_sees_only_train_rows():
    y = np.arange(20, dtype=float)
    folds = np.repeat(np.arange(5), 4)
    seen = []

    def feature_fn(tr, te):
        seen.append(set(tr) & set(te))
        return np.c_[y[tr]], np.c_[y[te]]
    cv.cross_val_predict_grouped(None, y, folds, feature_fn=feature_fn)
    assert all(len(s) == 0 for s in seen)


# ---------------------------------------------------------------- stats
def test_holm():
    out = stats.holm({"a": 0.01, "b": 0.04, "c": 0.03})
    assert out["a"]["p_holm"] == pytest.approx(0.03)
    assert out["c"]["p_holm"] == pytest.approx(0.06)
    assert out["b"]["p_holm"] == pytest.approx(0.06)


def test_shuffle_within_keeps_strata():
    y = np.array([1, 2, 3, 10, 20, 30])
    s = np.array([0, 0, 0, 1, 1, 1])
    z = stats.shuffle_within(y, s, np.random.default_rng(0))
    assert sorted(z[:3]) == [1, 2, 3] and sorted(z[3:]) == [10, 20, 30]


def test_bootstrap_and_equivalence():
    rng = np.random.default_rng(0)
    subj = np.repeat(np.arange(80), 3)
    y = rng.normal(size=240)
    a = y + rng.normal(size=240)
    r = stats.bootstrap_learners(stats.spearman, subj, y, a, n_boot=300)
    assert r["ci_low"] < r["estimate"] < r["ci_high"]
    eq = stats.equivalence_tost(subj, y, a, a.copy(), margin=0.1, n_boot=200)
    assert eq["equivalent"]


def test_permutation_detects_real_effect():
    rng = np.random.default_rng(1)
    groups = np.repeat(np.arange(30), 4)
    video = np.tile(np.arange(4), 30)
    X = rng.normal(size=(120, 3))
    y = X[:, 0] + 0.5 * rng.normal(size=120)
    folds = cv.make_group_folds(groups, 5, 0)
    fn = lambda yy: cv.score(yy, cv.cross_val_predict_grouped(X, yy, folds))["spearman"]
    r = stats.permutation_test(fn, y, video, n_perm=30)
    assert r["p"] < 0.05


# ---------------------------------------------------------------- isc
def test_isc_shared_signal_and_no_self_correlation():
    rng = np.random.default_rng(0)
    common = rng.normal(size=500)
    sig = np.stack([common + rng.normal(size=500) for _ in range(10)] + [rng.normal(size=500) for _ in range(2)])
    train = np.array([True] * 8 + [False] * 4)
    r = isc.isc_1d(sig, train)
    assert np.all(r[8:10] > 0.4)          # test learners following the stimulus
    assert np.all(np.abs(r[10:]) < 0.2)   # test learners not following it
    assert np.all(r[:8] < 0.9)            # leave-one-out: never correlated with themselves


def test_corrca_finds_shared_component():
    rng = np.random.default_rng(0)
    n_sub, n_t, n_ch = 12, 2000, 8
    s = rng.normal(size=n_t)
    mix = rng.normal(size=n_ch)
    data = np.stack([np.outer(s, mix) + rng.normal(size=(n_t, n_ch)) * 2 for _ in range(n_sub)])
    train = np.arange(n_sub) < 9
    r = isc.corrca_isc(data, train, n_components=2)
    assert r[~train, 0].mean() > 0.3
    assert r[~train, 0].mean() > r[~train, 1].mean()


# ---------------------------------------------------------------- eye
def test_saccade_and_blink_detection():
    sf = 500.0
    x = np.zeros(5000); y = np.zeros(5000)
    for start in (1000, 2500, 4000):                 # three 10-deg jumps over 30 ms
        x[start:start + 15] = np.linspace(0, 10, 15) + x[start - 1]
        x[start + 15:] = x[start + 14]
    pupil = np.full(5000, 4.0)
    pupil[3000:3100] = 0                             # one 200 ms blink
    sacc = eye.detect_saccades(x, y, sf, 30)
    blinks, mask = eye.detect_blinks(pupil, sf, pad_ms=100)
    assert len(sacc) == 3
    assert len(blinks) == 1 and mask[2960] and mask[3140]


def test_px_to_deg_centre_is_zero():
    dx, dy = eye.px_to_deg(np.array([960]), np.array([540]), 1920, 1080, 53.0, 60.0)
    assert abs(dx[0]) < 1e-9 and abs(dy[0]) < 1e-9


# ---------------------------------------------------------------- ecg
def test_beat_matching():
    ref = np.arange(100, 10000, 100)
    ours = np.r_[ref[:-2] + 3, 5050]                # 2 misses, 1 false positive, small offset
    r = ecg.match_beats(ours, ref, sfreq=128, tol_ms=50)
    assert r["tp"] == len(ref) - 2
    assert 0.9 < r["f1"] < 1.0


def test_rpeaks_on_simulated_ecg():
    nk = pytest.importorskip("neurokit2")
    sf = 128
    sig = nk.ecg_simulate(duration=60, sampling_rate=sf, heart_rate=70, random_state=0)
    peaks = ecg.detect_rpeaks(sig, sf)
    rr, _ = ecg.clean_rr(peaks, sf)
    hr = ecg.hr_features(rr)["hr_mean"]
    assert 60 < hr < 80
