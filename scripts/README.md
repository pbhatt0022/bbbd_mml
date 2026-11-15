# scripts

Command-line wrappers for long runs on Colab (e.g. preprocessing every recording, training DL models across folds), so a notebook does not need to stay open. Each script loads `config.yaml`, writes through `bbbd.runlog`, and is called from a notebook cell, e.g. `!python scripts/preprocess_eeg.py --experiment 2`.

Add scripts here as the pipelines are built (Sat 7 Nov onwards).

## D-31 / DV-02 eye reconciliation

`python -m bbbd.reconcile_eye` runs the separately registered post-result correction.
The Colab launcher is `notebooks/85_statistics.ipynb`; download its raw file from
branch `a/r012-reconciliation` and use File → Upload notebook. It needs only the
versioned tables, not raw data. The notebook backs up checkpoints to a new Drive folder.

The runner preserves R-012 and all outer folds, uses grouped three-fold inner tuning,
and refits all ten repeats for each of 1,000 permutations. It can take hours; progress
and ETA appear after each five permutations. A failed process can resume with
`python -m bbbd.reconcile_eye --resume results/R-013_eye_reconciliation` (substitute the
actual run directory). Code, configuration, source files, inputs and numerical package
versions must match. An in-progress registry row is not reportable.

Keep the completed ZIP and notebook outputs. Do not automatically push a Colab registry
over another member's new runs: check for run-ID collisions during integration. The
output reports raw eye p with its CI; across-modality Holm and human agreement on
D-31 remain outstanding. No confirmatory support claim is generated automatically.

## Experiment 2 run entry points

R-014 used notebook 51. R-015–R-017 use the following modules from an installed checkout. These commands generate new registered runs. Use a separate scratch output area if validating existing artifacts.

- `python -m bbbd.exp2_ecg_recovery_audit <recovery.tar.gz>` for the saved ECG audit.
- `python -m bbbd.exp2_cohort <recovery.tar.gz> <experiment2.zip>` for EEG QC and cohort construction.
- `python -m bbbd.exp2_matched_ridge` for the matched comparison, reading the existing R-016 cohort and split file.

See docs/PROJECT_STATE.md and run provenance snapshots for interpretation and input details.
