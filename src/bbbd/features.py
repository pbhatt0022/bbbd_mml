"""Individual-only feature rows (RQ2): computed from one learner's own recording.

One row per learner x video. Required key columns: experiment, subject, video, session, variant.
ISC features are NOT built here: they depend on the training fold (see isc.py, cv.feature_fn).
"""
from __future__ import annotations

import numpy as np

from . import eeg as eeg_mod
from . import eye as eye_mod

KEYS = ["experiment", "subject", "video", "session", "variant"]


def eye_features(x_deg, y_deg, pupil, sfreq: float, cfg_eye: dict) -> dict:
    """Saccade/blink/fixation rates, fixation duration, pupil level/variability, gaze dispersion."""
    pupil = np.asarray(pupil, float)
    n = len(pupil)
    # Use recording duration so rates can be compared across videos of different lengths.
    minutes = n / sfreq / 60
    blinks, invalid = eye_mod.detect_blinks(pupil, sfreq, cfg_eye["blink_pad_ms"])
    # Apply pupil dropout to both gaze coordinates. Long gaps stay missing.
    xd = eye_mod.interpolate_short_gaps(x_deg, invalid, sfreq, cfg_eye["max_interp_gap_ms"])
    yd = eye_mod.interpolate_short_gaps(y_deg, invalid, sfreq, cfg_eye["max_interp_gap_ms"])
    pz = eye_mod.zscore_pupil(eye_mod.interpolate_short_gaps(pupil, invalid, sfreq, cfg_eye["max_interp_gap_ms"]))
    sacc = eye_mod.detect_saccades(xd, yd, sfreq, cfg_eye["saccade_velocity_deg_s"])
    fix = eye_mod.fixations_from_events(n, sacc, ~np.isfinite(xd), sfreq)
    fix_dur = [(e - s) / sfreq * 1000 for s, e in fix]
    raw_pupil = np.where(invalid, np.nan, pupil)
    return {
        "eye_invalid_frac": float(invalid.mean()),
        "saccade_rate_min": len(sacc) / minutes,
        "blink_rate_min": len(blinks) / minutes,
        "fixation_rate_min": len(fix) / minutes,
        "fixation_dur_ms_mean": float(np.mean(fix_dur)) if fix_dur else np.nan,
        "pupil_mean_raw": float(np.nanmean(raw_pupil)),   # absolute level; z-scored series used for SD
        "pupil_diff_sd_z": float(np.nanstd(np.diff(pz))),  # moment-to-moment pupil variability
        "gaze_dispersion_deg": float(np.sqrt(np.nanvar(xd) + np.nanvar(yd))),
    }


def eeg_features(data: np.ndarray, ch_names: list[str], sfreq: float, cfg_eeg: dict,
                 good_mask: np.ndarray | None = None) -> dict:
    """Relative band power by region, alpha/theta ratio, aperiodic slope (region means).

    data: (n_channels, n_times) cleaned EEG for one video. good_mask: bool per sample
    (False inside bad segments) - those samples are dropped before spectra.
    """
    if good_mask is not None:
        data = data[:, np.asarray(good_mask, bool)]
    bp = eeg_mod.band_power(data, sfreq, cfg_eeg["bands_hz"])
    slope = eeg_mod.aperiodic_slope(data, sfreq)
    idx = {c: i for i, c in enumerate(ch_names)}
    out = {}
    for region, chans in cfg_eeg["regions"].items():
        ii = [idx[c] for c in chans if c in idx]
        if not ii:
            continue
        for band, vals in bp.items():
            out[f"eeg_{region}_{band}_rel"] = float(np.mean(vals[ii]))
        out[f"eeg_{region}_alpha_theta"] = float(np.mean(bp["alpha"][ii]) / np.mean(bp["theta"][ii]))
        out[f"eeg_{region}_slope"] = float(np.mean(slope[ii]))
    return out


def zscore_target(df, value_col: str = "quiz_prop_correct", by=("experiment", "video")):
    """D-10: z-score the quiz score within each video (and experiment)."""
    g = df.groupby(list(by))[value_col]
    return (df[value_col] - g.transform("mean")) / g.transform("std")
