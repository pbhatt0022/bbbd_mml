"""Eye tracking from raw gaze and pupil samples (Member A).

V1 default (config.yaml 'eye'):
1. Invalid samples: pupil <= 0 or NaN, or gaze off screen -> NaN.
2. Blinks: runs of invalid pupil, padded by blink_pad_ms on both sides (authors: +/-100 ms).
3. Gaps shorter than max_interp_gap_ms are linearly interpolated; longer gaps stay NaN.
4. Gaze pixels -> degrees of visual angle from screen geometry (sidecar / paper methods).
5. Saccades: velocity above saccade_velocity_deg_s (30 deg/s) for >= 2 samples.

Caveat for the report: at 128 Hz one sample is 7.8 ms, so short saccades are poorly resolved.
If the raw eye files turn out to be at the native 500 Hz, use that rate for event detection.
"""
from __future__ import annotations

import numpy as np


def runs(mask: np.ndarray) -> list[tuple[int, int]]:
    """Start/stop (exclusive) indices of consecutive True runs."""
    m = np.concatenate([[False], np.asarray(mask, bool), [False]])
    d = np.diff(m.astype(int))
    return list(zip(np.where(d == 1)[0], np.where(d == -1)[0]))


def invalid_mask(pupil: np.ndarray, gx: np.ndarray | None = None, gy: np.ndarray | None = None,
                 screen_px: tuple[int, int] | None = None) -> np.ndarray:
    bad = ~np.isfinite(pupil) | (pupil <= 0)
    if gx is not None and gy is not None:
        bad |= ~np.isfinite(gx) | ~np.isfinite(gy)
        if screen_px is not None:
            w, h = screen_px
            bad |= (gx < 0) | (gx > w) | (gy < 0) | (gy > h)
    return bad


def detect_blinks(pupil: np.ndarray, sfreq: float, pad_ms: float = 100,
                  min_ms: float = 50, max_ms: float = 500) -> tuple[list[tuple[int, int]], np.ndarray]:
    """Blinks = runs of invalid pupil lasting min_ms..max_ms. Longer runs count as track loss.

    Returns (blink intervals after padding, padded mask of all invalid samples).
    """
    bad = invalid_mask(pupil)
    pad = int(round(pad_ms / 1000 * sfreq))
    blinks, padded = [], np.zeros_like(bad)
    for s, e in runs(bad):
        dur = (e - s) / sfreq * 1000
        s2, e2 = max(0, s - pad), min(len(bad), e + pad)
        padded[s2:e2] = True
        if min_ms <= dur <= max_ms:
            blinks.append((s2, e2))
    return blinks, padded


def interpolate_short_gaps(x: np.ndarray, mask: np.ndarray, sfreq: float, max_gap_ms: float) -> np.ndarray:
    """Linear interpolation over masked gaps no longer than max_gap_ms; longer gaps -> NaN."""
    x = np.asarray(x, float).copy()
    x[mask] = np.nan
    max_n = int(round(max_gap_ms / 1000 * sfreq))
    good = np.where(np.isfinite(x))[0]
    if len(good) < 2:
        return x
    for s, e in runs(~np.isfinite(x)):
        if (e - s) <= max_n and s > 0 and e < len(x):
            x[s:e] = np.interp(np.arange(s, e), [s - 1, e], [x[s - 1], x[e]])
    return x


def px_to_deg(gx: np.ndarray, gy: np.ndarray, width_px: int, height_px: int,
              width_cm: float, distance_cm: float) -> tuple[np.ndarray, np.ndarray]:
    """Pixels -> degrees of visual angle relative to screen centre (square pixels assumed)."""
    cm_per_px = width_cm / width_px
    x_cm = (np.asarray(gx) - width_px / 2) * cm_per_px
    y_cm = (np.asarray(gy) - height_px / 2) * cm_per_px
    return (np.degrees(np.arctan2(x_cm, distance_cm)), np.degrees(np.arctan2(y_cm, distance_cm)))


def angular_velocity(x_deg: np.ndarray, y_deg: np.ndarray, sfreq: float) -> np.ndarray:
    """Point-to-point velocity (deg/s), central difference."""
    vx = np.gradient(np.asarray(x_deg, float)) * sfreq
    vy = np.gradient(np.asarray(y_deg, float)) * sfreq
    return np.hypot(vx, vy)


def detect_saccades(x_deg: np.ndarray, y_deg: np.ndarray, sfreq: float,
                    threshold_deg_s: float = 30.0, min_samples: int = 2,
                    max_deg_s: float = 1000.0) -> list[tuple[int, int]]:
    """Velocity-threshold (I-VT) saccades. Velocities above max_deg_s are treated as artefacts."""
    v = angular_velocity(x_deg, y_deg, sfreq)
    above = (v > threshold_deg_s) & (v < max_deg_s) & np.isfinite(v)
    return [(s, e) for s, e in runs(above) if e - s >= min_samples]


def fixations_from_events(n: int, saccades, invalid: np.ndarray, sfreq: float,
                          min_ms: float = 60) -> list[tuple[int, int]]:
    """Fixations = runs that are neither saccade nor invalid, at least min_ms long."""
    busy = np.asarray(invalid, bool).copy()
    for s, e in saccades:
        busy[s:e] = True
    min_n = int(round(min_ms / 1000 * sfreq))
    return [(s, e) for s, e in runs(~busy) if e - s >= min_n]


def zscore_pupil(p: np.ndarray) -> np.ndarray:
    """Per-recording z-score (Kret & Sjak-Shie 2019 recommend within-subject normalisation)."""
    p = np.asarray(p, float)
    return (p - np.nanmean(p)) / np.nanstd(p)
