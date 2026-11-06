"""Shape and sanity tests for the deep learning module (CPU, tiny inputs)."""
import numpy as np
import pytest

torch = pytest.importorskip("torch")
from bbbd import models_dl as m  # noqa: E402


def test_encoders_shapes():
    eeg = m.EEGEncoder(n_channels=64, embed_dim=128)
    eye = m.SignalEncoder(in_channels=5, embed_dim=128)
    assert eeg(torch.randn(4, 64, 512)).shape == (4, 128)
    assert eye(torch.randn(4, 5, 512)).shape == (4, 128)


def test_info_nce_and_recall():
    z = torch.randn(32, 16)
    assert m.info_nce(z, z).item() < m.info_nce(z, torch.randn(32, 16)).item()
    r = m.recall_at_k(z, z, ks=(1,))
    assert r["R@1"] == 1.0


@pytest.mark.parametrize("fusion", ["early", "late", "xattn"])
def test_fusion_heads_handle_missing_modality(fusion):
    enc = {"eeg": m.EEGEncoder(8, 32), "eye": m.SignalEncoder(5, 32), "hr": m.SignalEncoder(1, 32)}
    model = m.MultimodalClassifier(enc, fusion=fusion, dim=32, n_out=1)
    batch = {"eeg": torch.randn(6, 8, 512), "eye": torch.randn(6, 5, 512), "hr": None}
    model.train()
    assert model(batch).shape == (6, 1)
    model.eval()
    assert model(batch).shape == (6, 1)


def test_fit_runs_and_learns():
    torch.manual_seed(0)
    X = torch.randn(200, 2, 128)
    y = (X[:, 0].mean(1) > 0).float()
    ds = torch.utils.data.TensorDataset(X, y)
    tr = torch.utils.data.DataLoader(torch.utils.data.Subset(ds, range(160)), batch_size=32, shuffle=True)
    va = torch.utils.data.DataLoader(torch.utils.data.Subset(ds, range(160, 200)), batch_size=40)
    model = m.MultimodalClassifier({"eye": m.SignalEncoder(2, 16, width=8)}, fusion="early", dim=16,
                                   modality_dropout=0.0)

    def loss_fn(mod, b):
        x, t = b
        return torch.nn.functional.binary_cross_entropy_with_logits(mod({"eye": x}).squeeze(1), t)
    out = m.fit(model, tr, va, loss_fn, epochs=15, patience=15, device="cpu", log=lambda *_: None)
    assert out["history"][-1]["train_loss"] < out["history"][0]["train_loss"]


def test_pool_embeddings():
    keys, out = m.pool_embeddings(np.array([[1.0], [3.0], [10.0]]), [("s1", "v1"), ("s1", "v1"), ("s2", "v1")])
    assert keys == [("s1", "v1"), ("s2", "v1")] and out[:, 0].tolist() == [2.0, 10.0]
