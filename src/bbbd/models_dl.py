"""Deep learning track (RQ4): per-modality encoders, contrastive alignment and fusion heads.

Design (docs/methods_plan.md section 6b):
- Inputs are synchronized windows (default 4 s at 128 Hz = 512 samples) from cleaned signals.
- EEGEncoder: EEGNet-style compact CNN (Lawhern et al. 2018).
- SignalEncoder: 1D-CNN for eye (gaze x/y, velocity, pupil, blink mask) or cardiac/resp series.
- Task A, contrastive: symmetric InfoNCE between EEG and eye embeddings of the same window
  (CLIP-style, labs P9/P13); evaluated with Recall@K retrieval on held-out learners.
- Task B, attention decoding: encoders + a fusion head (early / late / cross-attention) with
  modality dropout (labs P3/P4/P12).
- Task C: pooled window embeddings per learner x video -> ridge in bbbd.cv (quiz score).
Encoders are retrained inside every outer CV fold (no test learner in pretraining).
"""
from __future__ import annotations

import copy

import numpy as np
import torch
import torch.nn as nn
import torch.nn.functional as F


# ---------------------------------------------------------------- encoders
class EEGEncoder(nn.Module):
    """EEGNet-style: temporal conv -> depthwise spatial conv -> separable conv -> embedding.

    Input (batch, n_channels, n_times). Defaults follow EEGNet-8,2 scaled for 128 Hz.
    """

    def __init__(self, n_channels: int = 64, embed_dim: int = 128, F1: int = 8, D: int = 2,
                 kern: int = 64, dropout: float = 0.25):
        super().__init__()
        F2 = F1 * D
        self.block1 = nn.Sequential(
            nn.Conv2d(1, F1, (1, kern), padding=(0, kern // 2), bias=False),
            nn.BatchNorm2d(F1),
            nn.Conv2d(F1, F2, (n_channels, 1), groups=F1, bias=False),
            nn.BatchNorm2d(F2), nn.ELU(), nn.AvgPool2d((1, 4)), nn.Dropout(dropout),
        )
        self.block2 = nn.Sequential(
            nn.Conv2d(F2, F2, (1, 16), padding=(0, 8), groups=F2, bias=False),
            nn.Conv2d(F2, F2, 1, bias=False),
            nn.BatchNorm2d(F2), nn.ELU(), nn.AvgPool2d((1, 8)), nn.Dropout(dropout),
        )
        self.proj = nn.LazyLinear(embed_dim)

    def forward(self, x):
        z = self.block2(self.block1(x.unsqueeze(1)))
        return self.proj(z.flatten(1))


class SignalEncoder(nn.Module):
    """1D-CNN for low-channel signals (eye: ~5 channels; cardiac/resp: 1-2). Input (batch, ch, times)."""

    def __init__(self, in_channels: int, embed_dim: int = 128, width: int = 32, dropout: float = 0.2):
        super().__init__()
        layers, c = [], in_channels
        for w, k in [(width, 7), (width * 2, 5), (width * 4, 3)]:
            layers += [nn.Conv1d(c, w, k, padding=k // 2), nn.BatchNorm1d(w), nn.GELU(),
                       nn.MaxPool1d(2), nn.Dropout(dropout)]
            c = w
        self.net = nn.Sequential(*layers)
        self.proj = nn.Linear(c * 2, embed_dim)   # mean + max pooling over time

    def forward(self, x):
        h = self.net(torch.nan_to_num(x))
        return self.proj(torch.cat([h.mean(-1), h.amax(-1)], dim=1))


class ProjectionHead(nn.Module):
    """Maps an embedding into the shared contrastive space (as in CLIP / SimCLR)."""

    def __init__(self, dim: int = 128, out: int = 64):
        super().__init__()
        self.net = nn.Sequential(nn.Linear(dim, dim), nn.GELU(), nn.Linear(dim, out))

    def forward(self, z):
        return F.normalize(self.net(z), dim=-1)


# ---------------------------------------------------------------- Task A: contrastive
def info_nce(za: torch.Tensor, zb: torch.Tensor, temperature: float = 0.07) -> torch.Tensor:
    """Symmetric InfoNCE: row i of za and row i of zb come from the same window (positive pair)."""
    za, zb = F.normalize(za, dim=-1), F.normalize(zb, dim=-1)
    logits = za @ zb.T / temperature
    target = torch.arange(len(za), device=za.device)
    return 0.5 * (F.cross_entropy(logits, target) + F.cross_entropy(logits.T, target))


@torch.no_grad()
def recall_at_k(za: torch.Tensor, zb: torch.Tensor, ks=(1, 5, 10)) -> dict:
    """Retrieval a->b: fraction of queries whose true partner ranks in the top k. Chance = k/N."""
    za, zb = F.normalize(za, dim=-1), F.normalize(zb, dim=-1)
    sim = za @ zb.T
    rank = (sim > sim.diag().unsqueeze(1)).sum(1)    # 0 = best
    n = len(za)
    return {f"R@{k}": float((rank < k).float().mean()) for k in ks} | {f"chance@{k}": k / n for k in ks}


class ContrastiveModel(nn.Module):
    def __init__(self, eeg_enc: nn.Module, eye_enc: nn.Module, dim: int = 128, out: int = 64):
        super().__init__()
        self.eeg_enc, self.eye_enc = eeg_enc, eye_enc
        self.eeg_head, self.eye_head = ProjectionHead(dim, out), ProjectionHead(dim, out)

    def forward(self, eeg, eye):
        return self.eeg_head(self.eeg_enc(eeg)), self.eye_head(self.eye_enc(eye))


# ---------------------------------------------------------------- Task B: fusion
class EarlyFusionHead(nn.Module):
    """Concatenate modality embeddings -> MLP (lab P3/P4 early fusion)."""

    def __init__(self, n_mod: int, dim: int = 128, n_out: int = 1, hidden: int = 128):
        super().__init__()
        self.net = nn.Sequential(nn.Linear(n_mod * dim, hidden), nn.GELU(), nn.Dropout(0.3), nn.Linear(hidden, n_out))

    def forward(self, tokens, mask):            # tokens (B, M, D); mask (B, M) True = present
        return self.net((tokens * mask.unsqueeze(-1)).flatten(1))


class LateFusionHead(nn.Module):
    """One classifier per modality; average the logits of the modalities present."""

    def __init__(self, n_mod: int, dim: int = 128, n_out: int = 1):
        super().__init__()
        self.heads = nn.ModuleList([nn.Linear(dim, n_out) for _ in range(n_mod)])

    def forward(self, tokens, mask):
        logits = torch.stack([h(tokens[:, i]) for i, h in enumerate(self.heads)], 1)   # (B, M, out)
        w = mask.float().unsqueeze(-1)
        return (logits * w).sum(1) / w.sum(1).clamp_min(1)


class CrossAttentionFusionHead(nn.Module):
    """Transformer over modality tokens + a [CLS] token; absent modalities are masked out.

    Each modality attends to the others (cross-modal attention, Module 3), and the CLS output
    is the fused representation.
    """

    def __init__(self, n_mod: int, dim: int = 128, n_out: int = 1, heads: int = 4, layers: int = 2):
        super().__init__()
        self.cls = nn.Parameter(torch.zeros(1, 1, dim))
        self.mod_emb = nn.Parameter(torch.randn(1, n_mod, dim) * 0.02)
        layer = nn.TransformerEncoderLayer(dim, heads, dim * 2, dropout=0.1, batch_first=True, norm_first=True)
        self.enc = nn.TransformerEncoder(layer, layers, enable_nested_tensor=False)
        self.out = nn.Linear(dim, n_out)

    def forward(self, tokens, mask):
        B = tokens.shape[0]
        x = torch.cat([self.cls.expand(B, -1, -1), tokens + self.mod_emb], 1)
        pad = torch.cat([torch.zeros(B, 1, dtype=torch.bool, device=mask.device), ~mask], 1)
        return self.out(self.enc(x, src_key_padding_mask=pad)[:, 0])


FUSION_HEADS = {"early": EarlyFusionHead, "late": LateFusionHead, "xattn": CrossAttentionFusionHead}


class MultimodalClassifier(nn.Module):
    """Encoders (dict name -> module) + fusion head, with modality dropout during training.

    Modality dropout: each present modality is dropped with probability p (at least one kept),
    which trains the model to cope with missing sensors and gives a direct ablation.
    """

    def __init__(self, encoders: dict[str, nn.Module], fusion: str = "xattn", dim: int = 128,
                 n_out: int = 1, modality_dropout: float = 0.3):
        super().__init__()
        self.names = list(encoders)
        self.encoders = nn.ModuleDict(encoders)
        self.head = FUSION_HEADS[fusion](len(self.names), dim, n_out)
        self.p = modality_dropout

    def embed(self, batch: dict[str, torch.Tensor]):
        B = next(iter(batch.values())).shape[0]
        dev = next(self.parameters()).device
        tokens, mask = [], []
        for n in self.names:
            if n in batch and batch[n] is not None:
                tokens.append(self.encoders[n](batch[n]))
                mask.append(torch.ones(B, dtype=torch.bool, device=dev))
            else:
                tokens.append(torch.zeros(B, self.head_dim, device=dev))
                mask.append(torch.zeros(B, dtype=torch.bool, device=dev))
        return torch.stack(tokens, 1), torch.stack(mask, 1)

    @property
    def head_dim(self):
        return self.encoders[self.names[0]].proj.out_features

    def forward(self, batch, return_tokens: bool = False):
        tokens, mask = self.embed(batch)
        if self.training and self.p > 0:
            drop = (torch.rand_like(mask, dtype=torch.float) < self.p) & mask
            all_gone = (mask & ~drop).sum(1) == 0
            drop[all_gone] = False                 # always keep at least one modality
            mask = mask & ~drop
        out = self.head(tokens, mask)
        return (out, tokens, mask) if return_tokens else out


# ---------------------------------------------------------------- training utilities
def fit(model: nn.Module, train_loader, val_loader, loss_fn, epochs: int = 50, lr: float = 1e-3,
        weight_decay: float = 1e-2, patience: int = 5, device: str | None = None, log=print) -> dict:
    """Generic loop with early stopping on validation loss. loss_fn(model, batch) -> scalar.

    Returns history and restores the best weights. Validation learners must come from the
    training fold of the outer CV.
    """
    device = device or ("cuda" if torch.cuda.is_available() else "cpu")
    model.to(device)
    with torch.no_grad():                      # initialise lazy layers before building the optimiser
        loss_fn(model, _to(next(iter(train_loader)), device))
    opt = torch.optim.AdamW(model.parameters(), lr=lr, weight_decay=weight_decay)
    best, best_state, wait, hist = np.inf, None, 0, []
    for ep in range(epochs):
        model.train()
        tr = []
        for batch in train_loader:
            batch = _to(batch, device)
            loss = loss_fn(model, batch)
            opt.zero_grad()
            loss.backward()
            opt.step()
            tr.append(loss.item())
        model.eval()
        with torch.no_grad():
            va = [loss_fn(model, _to(b, device)).item() for b in val_loader]
        hist.append({"epoch": ep, "train_loss": float(np.mean(tr)), "val_loss": float(np.mean(va))})
        log(f"epoch {ep:3d}  train {hist[-1]['train_loss']:.4f}  val {hist[-1]['val_loss']:.4f}")
        if hist[-1]["val_loss"] < best - 1e-4:
            best, best_state, wait = hist[-1]["val_loss"], copy.deepcopy(model.state_dict()), 0
        else:
            wait += 1
            if wait >= patience:
                break
    if best_state is not None:
        model.load_state_dict(best_state)
    return {"history": hist, "best_val_loss": float(best)}


def _to(batch, device):
    if isinstance(batch, dict):
        return {k: (v.to(device) if torch.is_tensor(v) else v) for k, v in batch.items()}
    if isinstance(batch, (list, tuple)):
        return type(batch)(_to(b, device) for b in batch)
    return batch.to(device) if torch.is_tensor(batch) else batch


def pool_embeddings(emb: np.ndarray, keys: list[tuple]) -> tuple[list[tuple], np.ndarray]:
    """Task C: mean of window embeddings per (subject, video) key -> one row per learner x video."""
    order = list(dict.fromkeys(keys))
    idx = {k: i for i, k in enumerate(order)}
    out = np.zeros((len(order), emb.shape[1]))
    cnt = np.zeros(len(order))
    for e, k in zip(emb, keys):
        out[idx[k]] += e
        cnt[idx[k]] += 1
    return order, out / cnt[:, None]
