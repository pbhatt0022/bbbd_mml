"""Respiration (Exps 4-5): breathing rate and its variability with NeuroKit2. Member B."""
from __future__ import annotations

import numpy as np


def resp_features(resp: np.ndarray, sfreq: float) -> dict:
    """Individual-only respiration features. Polarity does not affect rate."""
    import neurokit2 as nk
    signals, _ = nk.rsp_process(np.asarray(resp, float), sampling_rate=int(sfreq))
    rate = signals["RSP_Rate"].to_numpy()
    rate = rate[np.isfinite(rate)]
    if len(rate) == 0:
        return {"resp_rate_mean": np.nan, "resp_rate_sd": np.nan, "resp_rate_plausible": False}
    m = float(rate.mean())
    return {"resp_rate_mean": m, "resp_rate_sd": float(rate.std(ddof=1)),
            "resp_rate_plausible": bool(8 <= m <= 25)}


def resp_rate_series(resp: np.ndarray, sfreq: float) -> np.ndarray:
    """Breathing rate time course (breaths/min) at the input rate, for ISC and the DL encoder."""
    import neurokit2 as nk
    signals, _ = nk.rsp_process(np.asarray(resp, float), sampling_rate=int(sfreq))
    return signals["RSP_Rate"].to_numpy()
