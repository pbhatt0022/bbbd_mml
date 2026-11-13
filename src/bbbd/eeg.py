"""EEG preprocessing with MNE-Python (Member B). Written for a team new to EEG.

V1 default pipeline (config.yaml 'eeg', Decision Log D-12, D-13), in this order:
  1. load        BDF -> mne.io.Raw; keep the 64 EEG channels, mark EOG channels as 'eog'
  2. montage     standard BioSemi 64 positions (needed to interpolate bad channels)
  3. high-pass   0.5 Hz: removes slow drift (sweat, movement)
  4. notch       60 Hz line noise (US recordings), and 16 Hz + harmonics only if the spectrum shows it
  5. bad chans   channels whose variance or correlation with the others is extreme (robust z > 3)
                 -> interpolated from neighbours (spherical splines)
  6. reference   average reference (set before EOG regression, as MNE requires)
  7. eye artefact EOG regression (subtract the part of each EEG channel explained by EOG);
                 V3 replaces this with ICA (remove components that correlate with EOG)
  8. bad time    1-s segments whose amplitude range is beyond 4x IQR are marked bad

Why so minimal: Delorme (2023) found most automated cleaning beyond high-pass filtering and
bad-channel handling did not improve results. Keep each step's settings in config.yaml.
"""
from __future__ import annotations

import numpy as np


def load_bdf(path, eog_channels: list[str] | None = None, misc_channels: list[str] | None = None):
    """Read a BDF; set channel types. Check raw.info['sfreq'] and log it (UNVERIFIED rate)."""
    import mne
    raw = mne.io.read_raw_bdf(path, preload=True, verbose="error")
    types = {}
    for ch in eog_channels or []:
        if ch in raw.ch_names:
            types[ch] = "eog"
    for ch in misc_channels or []:
        if ch in raw.ch_names:
            types[ch] = "misc"
    if types:
        raw.set_channel_types(types, verbose="error")
    return raw


def set_biosemi64(raw):
    import mne
    raw.set_montage(mne.channels.make_standard_montage("biosemi64"), on_missing="warn", verbose="error")
    return raw


def has_peak(raw, freq: float, ratio: float = 3.0, half_width: float = 0.5) -> bool:
    """True if median EEG power at `freq` exceeds `ratio` x the power in the flanking bands.

    Used for the 16 Hz noise known in some Exp 4-5 recordings (D-13).
    """
    psd = raw.compute_psd(picks="eeg", fmin=max(0.5, freq - 4), fmax=freq + 4, verbose="error")
    f, p = psd.freqs, np.median(psd.get_data(), axis=0)
    peak = p[np.abs(f - freq) <= half_width].mean()
    flank = p[(np.abs(f - freq) > 1.5) & (np.abs(f - freq) <= 4)].mean()
    return bool(peak > ratio * flank)


def filter_raw(raw, highpass: float = 0.5, line_freq: float = 60, notch_16: bool = True) -> dict:
    """High-pass + notch filters in place. Returns a report of what was applied."""
    # Line-noise harmonics must lie below Nyquist to be valid notch frequencies.
    nyq = raw.info["sfreq"] / 2
    raw.filter(l_freq=highpass, h_freq=None, picks=["eeg", "eog"], verbose="error")
    notches = [f for f in np.arange(line_freq, nyq, line_freq)]
    found16 = notch_16 and has_peak(raw, 16.0)
    if found16:
        notches += [f for f in np.arange(16, nyq, 16) if f not in notches]
    if notches:
        raw.notch_filter(freqs=sorted(notches), picks=["eeg", "eog"], verbose="error")
    return {"highpass_hz": highpass, "notch_hz": sorted(float(f) for f in notches), "found_16hz": bool(found16)}


def _robust_z(x: np.ndarray) -> np.ndarray:
    med = np.median(x)
    mad = np.median(np.abs(x - med)) * 1.4826
    return (x - med) / mad if mad > 0 else np.zeros_like(x)


def find_bad_channels(raw, z_thresh: float = 3.0) -> list[str]:
    """Flag channels that are flat, very noisy, or poorly correlated with the rest."""
    picks = raw.copy().pick("eeg")
    X = picks.get_data()
    names = np.array(picks.ch_names)
    logvar = np.log(np.var(X, axis=1) + 1e-30)
    C = np.corrcoef(X)
    np.fill_diagonal(C, np.nan)
    medcorr = np.nanmedian(np.abs(C), axis=1)
    bad = (np.abs(_robust_z(logvar)) > z_thresh) | (_robust_z(medcorr) < -z_thresh) | (np.var(X, axis=1) < 1e-20)
    return names[bad].tolist()


def interpolate_bads(raw, bads: list[str]) -> None:
    raw.info["bads"] = list(bads)
    if bads:
        raw.interpolate_bads(reset_bads=True, verbose="error")


def eog_regression(raw):
    """Remove EOG-explained activity from EEG (authors' approach; D-12). Returns the fitted model."""
    from mne.preprocessing import EOGRegression
    model = EOGRegression(picks="eeg", picks_artifact="eog").fit(raw)
    model.apply(raw, copy=False)
    return model


def ica_remove_eog(raw, n_components: float | int = 0.99, seed: int = 0, threshold: float = 3.0) -> list[int]:
    """V3 variant: ICA on a 1 Hz high-passed copy, remove EOG-correlated components."""
    from mne.preprocessing import ICA
    fit_raw = raw.copy().filter(l_freq=1.0, h_freq=None, verbose="error")
    ica = ICA(n_components=n_components, method="fastica", random_state=seed, max_iter="auto")
    ica.fit(fit_raw, picks="eeg", verbose="error")
    idx, _ = ica.find_bads_eog(fit_raw, threshold=threshold, verbose="error")
    ica.exclude = list(idx)
    ica.apply(raw, verbose="error")
    return list(idx)


def average_reference(raw) -> None:
    raw.set_eeg_reference("average", projection=False, verbose="error")


def bad_segments(raw, seg_s: float = 1.0, iqr_mult: float = 4.0) -> np.ndarray:
    """Boolean per 1-s segment: peak-to-peak (median over channels) beyond Q3 + k*IQR."""
    X = raw.get_data(picks="eeg")
    n = int(seg_s * raw.info["sfreq"])
    k = X.shape[1] // n
    ptp = np.median(np.ptp(X[:, : k * n].reshape(X.shape[0], k, n), axis=2), axis=0)
    q1, q3 = np.percentile(ptp, [25, 75])
    return ptp > q3 + iqr_mult * (q3 - q1)


def preprocess(raw, cfg_eeg: dict, seed: int = 0) -> tuple[object, dict]:
    """Run the configured pipeline (V1, or V3 if eye_artifact == 'ica'). Returns (raw, QC report)."""
    rep = {"sfreq": raw.info["sfreq"], "n_eeg": len(raw.copy().pick("eeg").ch_names)}
    set_biosemi64(raw)
    rep.update(filter_raw(raw, cfg_eeg["highpass_hz"], cfg_eeg["line_freq_hz"], cfg_eeg["notch_16hz_if_detected"]))
    bads = find_bad_channels(raw, cfg_eeg["bad_channel_z"])
    rep["bad_channels"] = bads
    rep["bad_channel_frac"] = len(bads) / max(rep["n_eeg"], 1)
    interpolate_bads(raw, bads)
    average_reference(raw)                     # MNE's EOGRegression requires the reference first
    has_eog ="eog" in raw.get_channel_types()
    if cfg_eeg["eye_artifact"] == "eog_regression" and has_eog:
        eog_regression(raw)
        rep["eye_artifact"] = "eog_regression"
    elif cfg_eeg["eye_artifact"] == "ica":
        rep["ica_excluded"] = ica_remove_eog(raw, seed=seed) if has_eog else []
        rep["eye_artifact"] = "ica"
    else:
        rep["eye_artifact"] = "none (no EOG channels found)"
    segs = bad_segments(raw, iqr_mult=cfg_eeg["artifact_iqr_mult"])
    rep["bad_time_frac"] = float(segs.mean()) if len(segs) else 0.0
    rep["bad_segments_1s"] = np.where(segs)[0].tolist()
    return raw, rep


def band_power(data: np.ndarray, sfreq: float, bands: dict[str, list[float]],
               fmin: float = 1.0, fmax: float = 40.0) -> dict[str, np.ndarray]:
    """Relative band power per channel (Welch). data: (n_channels, n_times).

    Relative = band power / total power in [fmin, fmax], so it is comparable across people.
    """
    from scipy.signal import welch
    f, p = welch(data, fs=sfreq, nperseg=int(2 * sfreq), axis=-1)
    total = p[:, (f >= fmin) & (f <= fmax)].sum(1)
    return {name: p[:, (f >= lo) & (f < hi)].sum(1) / total for name, (lo, hi) in bands.items()}


def aperiodic_slope(data: np.ndarray, sfreq: float, fmin: float = 2.0, fmax: float = 40.0,
                    exclude: tuple[float, float] = (7.0, 14.0)) -> np.ndarray:
    """1/f slope per channel: linear fit of log10 power vs log10 frequency, alpha band excluded."""
    from scipy.signal import welch
    f, p = welch(data, fs=sfreq, nperseg=int(2 * sfreq), axis=-1)
    m = (f >= fmin) & (f <= fmax) & ~((f >= exclude[0]) & (f <= exclude[1]))
    lf = np.log10(f[m])
    return np.array([np.polyfit(lf, np.log10(row[m] + 1e-30), 1)[0] for row in p])
