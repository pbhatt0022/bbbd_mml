"""Unit tests for the D-43 Task C comparison, on synthetic data only."""
import numpy as np
import pandas as pd
import pytest

from bbbd.exp2_attention_cnn import make_model
from bbbd.exp2_rq4_taskc import EMBED_DIM, embed, ridge_cv


@pytest.fixture
def cfg():
    return {"cv": {"inner_splits": 3},
            "reconciliation": {"ridge_alpha_log10_min": -1, "ridge_alpha_log10_max": 2,
                               "ridge_alpha_count": 4,
                               "inner_scoring": "neg_mean_squared_error"}}


def test_embedding_drops_the_classifier_head():
    torch = pytest.importorskip("torch")
    model = make_model(torch)
    x = np.random.default_rng(0).normal(size=(7, 3, 512)).astype(np.float32)
    out = embed(torch, model, x)
    assert out.shape == (7, EMBED_DIM)
    # The full model emits a single logit; the trunk must not.
    with torch.no_grad():
        assert model(torch.from_numpy(x)).shape == (7, 1)


def test_embedding_is_deterministic_for_a_frozen_encoder():
    torch = pytest.importorskip("torch")
    torch.manual_seed(0)
    model = make_model(torch)
    x = np.random.default_rng(1).normal(size=(5, 3, 512)).astype(np.float32)
    assert embed(torch, model, x) == pytest.approx(embed(torch, model, x))


def test_embedding_batches_do_not_change_the_result():
    torch = pytest.importorskip("torch")
    torch.manual_seed(0)
    model = make_model(torch)
    x = np.random.default_rng(2).normal(size=(9, 3, 512)).astype(np.float32)
    assert embed(torch, model, x, batch=2) == pytest.approx(
        embed(torch, model, x, batch=512), abs=1e-5)


def test_ridge_cv_predicts_every_row_exactly_once(cfg):
    rng = np.random.default_rng(3)
    n = 40
    x = rng.normal(size=(n, 5))
    y = rng.normal(size=n)
    groups = np.repeat(np.arange(8), 5)
    labels = np.repeat(np.arange(4), 10)
    out = ridge_cv(x, y, groups, labels, cfg)
    assert np.isfinite(out).all() and len(out) == n


def test_ridge_cv_recovers_a_linear_signal(cfg):
    rng = np.random.default_rng(4)
    n = 60
    x = rng.normal(size=(n, 3))
    y = 2.0 * x[:, 0] + 0.1 * rng.normal(size=n)
    groups = np.repeat(np.arange(12), 5)
    labels = np.repeat(np.arange(4), 15)
    predicted = ridge_cv(x, y, groups, labels, cfg)
    assert np.corrcoef(predicted, y)[0, 1] > 0.9


def test_ridge_cv_is_near_zero_on_noise(cfg):
    rng = np.random.default_rng(5)
    n = 60
    x = rng.normal(size=(n, 10))
    y = rng.normal(size=n)
    groups = np.repeat(np.arange(12), 5)
    labels = np.repeat(np.arange(4), 15)
    predicted = ridge_cv(x, y, groups, labels, cfg)
    assert abs(np.corrcoef(predicted, y)[0, 1]) < 0.6


def test_a_test_learner_never_appears_in_its_own_training_split(cfg):
    """The guarantee the whole comparison rests on."""
    groups = np.repeat(np.arange(10), 4)
    labels = np.repeat(np.arange(5), 8)
    for fold in sorted(set(labels)):
        test_learners = set(groups[labels == fold])
        train_learners = set(groups[labels != fold])
        assert not (test_learners & train_learners)
