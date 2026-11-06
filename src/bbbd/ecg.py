"""ECG: R-peaks, heart rate and HRV with NeuroKit2 (Makowski et al. 2021). Member B.

Validation (H0a): our R-peaks vs the authors' manually corrected peaks, matched within
+/- 50 ms; supported if F1 >= 0.95 per recording (both PROPOSED in the preregistration).
"""
from __future__ import annotations

import numpy as np


def detect_rpeaks(ecg: np.ndarray, sfreq: float, method: str = "neurokit") -> np.ndarray:
    """Clean the ECG and return R-peak sample indices.

    If peaks come out inverted (lead polarity), NeuroKit's ecg_invert handles it; we check
    polarity first and log it.
    """
    import neurokit2 as nk
    sig = np.asarray(ecg, float)
    sig, inverted = nk.ecg_invert(sig, sampling_rate=int(sfreq))
    clean = nk.ecg_clean(sig, sampling_rate=int(sfreq), method=method)
    _, info = nk.ecg_peaks(clean, sampling_rate=int(sfreq), method=method)
    return np.asarray(info["ECG_R_Peaks"], dtype=int)


def clean_rr(peaks: np.ndarray, sfreq: float, rr_min_ms: float = 300,
             rr_max_ms: float = 2000) -> tuple[np.ndarray, np.ndarray]:
    """RR intervals (ms) with implausible ones set to NaN. Returns (rr_ms, peak times of each RR end)."""
    peaks = np.asarray(peaks)
    rr = np.diff(peaks) / sfreq * 1000.0
    rr = np.where((rr >= rr_min_ms) & (rr <= rr_max_ms), rr, np.nan)
    return rr, peaks[1:] / sfreq


def hr_features(rr_ms: np.ndarray) -> dict:
    """Individual-only cardiac features (RQ2)."""
    rr = rr_ms[np.isfinite(rr_ms)]
    if len(rr) < 3:
        return {"hr_mean": np.nan, "hr_sd": np.nan, "rmssd": np.nan}
    hr = 60000.0 / rr
    d = np.diff(rr_ms)
    d = d[np.isfinite(d)]
    return {"hr_mean": float(hr.mean()), "hr_sd": float(hr.std(ddof=1)),
            "rmssd": float(np.sqrt(np.mean(d ** 2))) if len(d) else np.nan}


def instantaneous_hr(peaks: np.ndarray, sfreq: float, n_samples: int, out_sfreq: float,
                     rr_min_ms: float = 300, rr_max_ms: float = 2000) -> np.ndarray:
    """HR (bpm) interpolated onto a regular grid, for ISC and the deep cardiac encoder."""
    rr, t = clean_rr(peaks, sfreq, rr_min_ms, rr_max_ms)
    ok = np.isfinite(rr)
    grid = np.arange(int(n_samples / sfreq * out_sfreq)) / out_sfreq
    if ok.sum() < 2:
        return np.full(len(grid), np.nan)
    return np.interp(grid, t[ok], 60000.0 / rr[ok], left=np.nan, right=np.nan)


def match_beats(ours: np.ndarray, ref: np.ndarray, sfreq: float, tol_ms: float = 50) -> dict:
    """Greedy one-to-one matching of detected vs reference peaks within tol_ms.

    Returns precision, recall, F1 and the median timing error of matched beats (ms).
    """
    ours, ref = np.sort(np.asarray(ours)), np.sort(np.asarray(ref))
    tol = tol_ms / 1000 * sfreq
    used = np.zeros(len(ref), bool)
    errors = []
    j0 = 0
    for p in ours:
        while j0 < len(ref) and ref[j0] < p - tol:
            j0 += 1
        best, best_d = -1, tol + 1
        j = j0
        while j < len(ref) and ref[j] <= p + tol:
            if not used[j] and abs(ref[j] - p) < best_d:
                best, best_d = j, abs(ref[j] - p)
            j += 1
        if best >= 0:
            used[best] = True
            errors.append((p - ref[best]) / sfreq * 1000)
    tp = int(used.sum())
    prec = tp / len(ours) if len(ours) else np.nan
    rec = tp / len(ref) if len(ref) else np.nan
    f1 = 2 * prec * rec / (prec + rec) if tp else 0.0
    return {"tp": tp, "n_ours": len(ours), "n_ref": len(ref), "precision": prec,
            "recall": rec, "f1": f1, "median_error_ms": float(np.median(errors)) if errors else np.nan}
