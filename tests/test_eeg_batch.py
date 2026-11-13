"""Tests for Experiment 2 EEG/EOG batch processing."""

import json

import mne
import numpy as np
import pandas as pd
import pytest

from bbbd import eeg_batch
from bbbd.config import load_config


@pytest.fixture
def recording(tmp_path, monkeypatch):
    """Create a synthetic EEG/EOG recording with trailing EEG samples."""

    sfreq = 128
    n_eog_samples = 512
    n_eeg_samples = 576

    base = "sub-01_ses-01_task-stim01"
    session_dir = tmp_path / "sub-01" / "ses-01"

    eeg_dir = session_dir / "eeg"
    beh_dir = session_dir / "beh"

    eeg_dir.mkdir(parents=True)
    beh_dir.mkdir(parents=True)

    eeg_path = eeg_dir / f"{base}_eeg.bdf"
    eeg_path.touch()

    # Event-defined duration: 512 / 128 = 4 seconds.
    pd.DataFrame({
        "onset": [0.0, 4.0],
        "duration": [1 / sfreq, 1 / sfreq],
        "event": ["start", "end"],
    }).to_csv(
        eeg_dir / f"{base}_events.tsv",
        sep="\t",
        index=False,
    )

    names = mne.channels.make_standard_montage(
        "biosemi64"
    ).ch_names

    # Reproduce the observed capitalization discrepancy.
    names = [
        "Afz" if name.lower() == "afz" else name
        for name in names
    ]

    rng = np.random.default_rng(2026)

    data = rng.normal(
        0,
        1e-6,
        size=(64, n_eeg_samples),
    )

    info = mne.create_info(
        names,
        sfreq,
        ch_types=["eeg"] * 64,
    )

    def load_synthetic_bdf(path):
        assert str(path) == str(eeg_path)
        return mne.io.RawArray(
            data.copy(),
            info.copy(),
            verbose="ERROR",
        )

    monkeypatch.setattr(
        eeg_batch.eeg,
        "load_bdf",
        load_synthetic_bdf,
    )

    eog_names = [
        "ch1", "ch2", "ch3",
        "ch4", "ch5", "ch6",
    ]

    # Constant 2 microvolts, used to verify scaling.
    eog = np.full(
        (n_eog_samples, 6),
        2.0,
    )

    eog_path = (
        beh_dir /
        f"{base}_recording-eog_physio.tsv.gz"
    )

    pd.DataFrame(eog).to_csv(
        eog_path,
        sep="\t",
        header=False,
        index=False,
        compression="gzip",
    )

    metadata = {
        "SamplingFrequency": sfreq,
        "Columns": eog_names,
    }

    for name in eog_names:
        metadata[name] = {"Units": "uV"}

    with open(
        beh_dir / f"{base}_recording-eog_physio.json",
        "w",
    ) as f:
        json.dump(metadata, f)

    return eeg_path, eog_path


def test_batch_alignment_channels_and_features(
    recording, monkeypatch
):
    """Verify alignment, units, channels, masking, and features."""

    eeg_path, _ = recording

    cfg = load_config()
    observed = {}

    def fake_preprocess(raw, cfg_eeg, seed=0):

        observed["n_times"] = raw.n_times
        observed["types"] = raw.get_channel_types()
        observed["names"] = raw.ch_names

        observed["eog_values"] = raw.get_data(
            picks="eog"
        )

        return raw, {
            "n_eeg": 64,
            "bad_channels": [],
            "bad_channel_frac": 0.0,
            "bad_time_frac": 0.02,
            "bad_segments_1s": [1],
            "eye_artifact": "eog_regression",
        }

    monkeypatch.setattr(
        eeg_batch.eeg,
        "preprocess",
        fake_preprocess,
    )

    qc, feature_row = eeg_batch.process_recording(
        eeg_path, cfg
    )

    assert observed["n_times"] == 512
    assert observed["types"].count("eeg") == 64
    assert observed["types"].count("eog") == 6
    assert "AFz" in observed["names"]

    np.testing.assert_allclose(
        observed["eog_values"],
        2e-6,
    )

    assert qc["original_eeg_samples"] == 576
    assert qc["aligned_samples"] == 512
    assert qc["trimmed_samples"] == 64

    assert qc["exclude"] is False

    assert feature_row is not None

    # One flagged second out of four.
    assert feature_row["eeg_good_sample_frac"] == pytest.approx(
        0.75
    )

    feature_columns = [
        key for key in feature_row
        if key.startswith("eeg_")
        and key != "eeg_good_sample_frac"
    ]

    assert len(feature_columns) == 24

    assert np.isfinite([
        feature_row[key] for key in feature_columns
    ]).all()


def test_bad_channel_exclusion(recording, monkeypatch):
    """More than 20% bad channels must exclude a recording."""

    eeg_path, _ = recording
    cfg = load_config()

    def fake_preprocess(raw, cfg_eeg, seed=0):
        return raw, {
            "n_eeg": 64,
            "bad_channels": raw.ch_names[:18],
            "bad_channel_frac": 18 / 64,
            "bad_time_frac": 0.02,
            "bad_segments_1s": [],
            "eye_artifact": "eog_regression",
        }

    monkeypatch.setattr(
        eeg_batch.eeg,
        "preprocess",
        fake_preprocess,
    )

    qc, feature_row = eeg_batch.process_recording(
        eeg_path, cfg
    )

    assert qc["exclude_bad_channels"] is True
    assert qc["exclude_bad_time"] is False
    assert qc["exclude"] is True

    # Excluded recordings must not produce feature rows.
    assert feature_row is None


def test_missing_eog_is_explicit(recording):
    """Missing EOG must not be silently ignored."""

    eeg_path, eog_path = recording
    cfg = load_config()

    eog_path.unlink()

    with pytest.raises(FileNotFoundError, match="Missing EOG"):
        eeg_batch.process_recording(eeg_path, cfg)


def test_eog_length_mismatch_is_rejected(recording):
    """Mismatched EOG/event lengths must not be silently trimmed."""

    eeg_path, eog_path = recording
    cfg = load_config()

    eog = pd.read_csv(eog_path, sep="\t", header=None)

    eog.iloc[:-1].to_csv(
        eog_path,
        sep="\t",
        header=False,
        index=False,
        compression="gzip",
    )

    with pytest.raises(
        ValueError,
        match="EOG length differs from event endpoint",
    ):
        eeg_batch.process_recording(eeg_path, cfg)
