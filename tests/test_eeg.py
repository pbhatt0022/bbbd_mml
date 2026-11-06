"""EEG pipeline runs end to end on a synthetic BioSemi-64 recording."""
import numpy as np
import pytest

mne = pytest.importorskip("mne")
from bbbd import eeg  # noqa: E402
from bbbd.config import load_config  # noqa: E402


def _synthetic_raw(sf=128.0, secs=60, alpha_amp=5e-6, seed=0):
    rng = np.random.default_rng(seed)
    names = mne.channels.make_standard_montage("biosemi64").ch_names
    t = np.arange(int(sf * secs)) / sf
    X = rng.normal(scale=10e-6, size=(64, t.size)) + alpha_amp * np.sin(2 * np.pi * 10 * t)
    X[5] *= 40                                    # one very noisy channel
    eog = np.stack([rng.normal(scale=50e-6, size=t.size) for _ in range(2)])
    X += 0.2 * eog[0]                             # eye artefact leaking into EEG
    info = mne.create_info(names + ["EXG1", "EXG2"], sf, ["eeg"] * 64 + ["eog"] * 2)
    return mne.io.RawArray(np.vstack([X, eog]), info, verbose="error"), names[5]


def test_preprocess_flags_bad_channel_and_reports():
    cfg = load_config()
    raw, noisy = _synthetic_raw()
    raw, rep = eeg.preprocess(raw, cfg["eeg"])
    assert noisy in rep["bad_channels"]
    assert rep["eye_artifact"] == "eog_regression"
    assert 0 <= rep["bad_time_frac"] <= 1


def test_band_power_sees_alpha():
    cfg = load_config()
    strong, _ = _synthetic_raw(alpha_amp=20e-6)
    weak, _ = _synthetic_raw(alpha_amp=0.0)
    a_s = eeg.band_power(strong.get_data(picks="eeg"), 128, cfg["eeg"]["bands_hz"])["alpha"].mean()
    a_w = eeg.band_power(weak.get_data(picks="eeg"), 128, cfg["eeg"]["bands_hz"])["alpha"].mean()
    assert a_s > a_w
