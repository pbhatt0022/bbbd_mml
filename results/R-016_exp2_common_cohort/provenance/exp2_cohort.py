"""Audit recovered EEG and register the common Experiment 2 cohort and folds."""
import argparse
import hashlib
import io
import re
import subprocess
import tarfile
from pathlib import Path
from zipfile import ZipFile

import numpy as np
import pandas as pd

from . import cv, runlog
from .config import REPO_ROOT, load_config

KEYS = ["experiment", "subject", "video"]
ARTIFACTS = REPO_ROOT / "results"


def digest(path, algorithm="sha256"):
    with path.open("rb") as stream:
        return hashlib.file_digest(stream, algorithm).hexdigest()


def normalize(table):
    table = table.copy()
    table["subject"] = table.subject.map(lambda s: int(re.fullmatch(r"(?:sub-)?(\d+)", str(s))[1]))
    table["video"] = table.video.map(lambda s: int(re.fullmatch(r"(?:stim-?)?(\d+)", str(s))[1]))
    if not table.experiment.eq(2).all() or table.duplicated(KEYS).any():
        raise ValueError("Unexpected experiment or duplicate key")
    return table


def attentive(table):
    return normalize(table.loc[table.session.eq("ses-01")])


def finite(table, columns):
    return np.isfinite(table[columns].to_numpy(dtype=float)).all(axis=1)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("recovery", type=Path)
    parser.add_argument("raw", type=Path)
    args = parser.parse_args()
    recovery_hash, raw_md5 = digest(args.recovery), digest(args.raw, "md5")
    if recovery_hash != "767f2d6be2c8933309ab14f5e01e71436a0adfed9754b0e510d379a5c95cf50a" or raw_md5 != "e9671316f97e1c3ec1d86a03e0a1ab28":
        raise ValueError("Archive checksum mismatch")
    cfg = load_config()
    with tarfile.open(args.recovery, "r:gz") as archive:
        def table(name):
            return pd.read_csv(io.BytesIO(archive.extractfile("MML_BBBD/04_results/" + name).read()))
        eeg = attentive(table("eeg_full_features/eeg_features.csv"))
        qc = table("eeg_full_features/eeg_qc.csv").query("session == 'ses-01'").copy()
        errors = table("eeg_full_features/eeg_errors.csv")
        ecg = attentive(table("ecg_full_diagnostic/ecg_features.csv"))
        for path in ("src/bbbd/eeg_batch.py", "src/bbbd/eeg.py", "src/bbbd/features.py", "config.yaml"):
            archived = archive.extractfile("bbbd_mml/" + path).read()
            git = subprocess.check_output(["git", "show", f"de3b603:{path}"], cwd=REPO_ROOT)
            if archived.splitlines() != git.splitlines():
                raise ValueError(f"Recovered source differs: {path}")
    limits = cfg["exclusions"]
    qc_fields = ["bad_channel_frac", "bad_time_frac"]
    if not qc.recording.is_unique or not qc.status.eq("processed").all() or not finite(qc, qc_fields).all() or not qc[qc_fields].apply(lambda col: col.between(0, 1)).all().all():
        raise ValueError("Invalid attentive EEG QC")
    excluded = qc.bad_channel_frac.gt(limits["eeg_max_bad_channel_frac"]) | qc.bad_time_frac.gt(limits["eeg_max_bad_time_frac"])
    if not qc.exclude.eq(excluded).all() or set(eeg.recording) != set(qc.loc[~excluded, "recording"]):
        raise ValueError("EEG feature and QC coverage differ")
    eeg_columns = [c for c in eeg if c.startswith("eeg_") and c != "eeg_good_sample_frac"]
    if len(eeg_columns) != 24 or not finite(eeg, eeg_columns).all():
        raise ValueError("Invalid EEG features")
    ecg_columns = ["hr_mean", "hr_sd", "rmssd"]
    eye_path = ARTIFACTS / "R-014_eye_features_exp2/eye_features_exp2.csv"
    ecg_audit = ARTIFACTS / "R-015_exp2_ecg_recovery_audit/ecg_eligibility.csv"
    eye, eligibility = (attentive(pd.read_csv(p)) for p in (eye_path, ecg_audit))
    if not eye.run_id.eq("R-014").all() or not eligibility.run_id.eq("R-015").all():
        raise ValueError("Wrong source run")
    eye_columns = [c for c in eye if c not in {*KEYS, "run_id", "session", "variant", "excluded"}]
    if len(eye_columns) != 8 or not eye.excluded.isin([True, False]).all():
        raise ValueError("Unexpected eye schema")
    with ZipFile(args.raw) as archive:
        quiz = pd.read_csv(archive.open("phenotype/stimuli_questionnaire_scores.tsv"), sep="\t")
    quiz = normalize(quiz.rename(columns={"participant_id": "subject", "stim_no": "video"}).assign(experiment=2))
    if not quiz.total_memory_questions.gt(0).all() or not quiz.memory_score.between(0, quiz.total_memory_questions).all():
        raise ValueError("Invalid memory scores")
    quiz["quiz_prop_correct"] = quiz.memory_score / quiz.total_memory_questions
    groups = quiz.groupby("video").quiz_prop_correct
    quiz["quiz_z"] = (quiz.quiz_prop_correct - groups.transform("mean")) / groups.transform("std")
    tables = [
        eye.loc[eye.excluded.eq(False) & finite(eye, eye_columns), KEYS+eye_columns],
        ecg.loc[finite(ecg, ecg_columns), KEYS+ecg_columns],
        eligibility.loc[eligibility.eligibility.eq("eligible"), KEYS],
        eeg[KEYS+eeg_columns],
        quiz[KEYS+["quiz_prop_correct", "quiz_z"]],
    ]
    cohort = tables[0]
    for next_table in tables[1:]:
        cohort = cohort.merge(next_table, on=KEYS, validate="one_to_one")
    cohort = cohort.sort_values(["subject", "video"]).reset_index(drop=True)
    if not finite(cohort, ["quiz_prop_correct", "quiz_z"]).all() or cohort.empty:
        raise ValueError("Missing target or empty cohort")
    n_splits = cfg["cv"]["n_splits"]
    folds = {}
    for seed in cfg["seeds"]["cv_repeats"]:
        labels = cv.make_group_folds(cohort.subject.to_numpy(), n_splits=n_splits, seed=seed)
        cv.check_no_leakage(labels, cohort.subject)
        if len(set(labels)) != n_splits:
            raise ValueError("Empty outer fold")
        folds[f"group{n_splits}_seed{seed}"] = labels
    frozen = ARTIFACTS / "folds.json"
    frozen_hash = digest(frozen)
    run = runlog.start_run(cfg, "exp2_common_cohort", "exp2_cohort", member="A")
    runlog.save_table(run, qc.assign(audited_exclude=excluded), "eeg_qc_audit.csv")
    runlog.save_table(run, cohort, "exp2_common_cohort.csv")
    split_file = run.output_dir / "folds_exp2.json"
    cv.save_folds(split_file, cohort[KEYS], folds)
    saved_keys, saved_folds = cv.load_folds(split_file)
    if not saved_keys.equals(cohort[KEYS].astype(str)) or any(not np.array_equal(saved_folds[k], v) for k, v in folds.items()) or digest(frozen) != frozen_hash:
        raise ValueError("Split artifact verification failed")
    summary = dict(decision="D-34 Proposed", deviation="DV-05", eeg_source_match="de3b603",
                   eeg_raw_rerun=False, attentive_eeg_qc_rows=len(qc), eeg_excluded=int(excluded.sum()),
                   attentive_eeg_feature_rows=len(eeg), recovered_eeg_batch_errors=len(errors),
                   n_rows=len(cohort), n_learners=int(cohort.subject.nunique()), n_videos=int(cohort.video.nunique()),
                   outer_repeats=len(folds), outer_folds=n_splits, frozen_exp1_sha256=frozen_hash,
                   source_hashes={"recovery_sha256": recovery_hash, "raw_md5": raw_md5,
                                  "eye_sha256": digest(eye_path), "ecg_audit_sha256": digest(ecg_audit)})
    runlog.save_json(run, summary, "exp2_cohort_audit.json")
    runlog.finish_run(run, note="D-34/DV-05 recovered EEG audit, exploratory common cohort and separate Exp 2 outer folds.")
    print(summary)


if __name__ == "__main__":
    main()
