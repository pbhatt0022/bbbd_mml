# Dataset Inventory

What we have **verified on the real files**, per experiment. Anything not in this table is unverified. Source of each fact in the last column.

## Experiment 1 (verified 14 Oct 2026, quick check on Google Drive)

| Item | Value | Source |
| --- | --- | --- |
| Location | `MML_BBBD/01_data_raw/experiment1/` on the shared Google Drive (not on the local D: copy) | quick check summary |
| Participants | 27 in `participants.tsv`, 27 subject folders, 27 with gaze | quick check summary |
| Sessions | `ses-01`, `ses-02` | quick check summary |
| Modality folders | `eyetrack` only (no BDF files) | quick check summary |
| Gaze files | 263 (of 270 expected: 27 × 5 videos × 2 conditions) | quick check summary |
| Gaze sampling rate | 128 Hz (sidecar) | quick check summary |
| Gaze sidecar columns | `x`, `y`, `vdx`, `vdy` (velocity components; median gaze velocity 5.06 deg/s, so `vdx`/`vdy` behave as degrees) | quick check summary |
| Invalid gaze samples | median 3.03% per recording | quick check summary |
| Video durations (s) | 1: 184.9, 2: 142.2, 3: 388.8, 4: 370.1, 5: 150.2 | quick check summary |
| Authors' derivatives | present | quick check summary |
| Quiz file | `phenotype/stimuli_questionnaire.tsv` (+ `.json`, `stimuli_questionnaire_scores.tsv`) | quick check summary |
| Quiz granularity | item-level answers available; question types `memory` (1,829 rows) and `domain` (1,457 rows) | quick check summary |
| Quiz participants | 31 (vs 27 with gaze): 4 have quiz data but no gaze | quick check summary |
| Items per video | 12, 11, 12, 12, 12 (memory questions) | quick check summary |
| Quiz means (prop. correct) | 0.64, 0.56, 0.60, 0.60, 0.79; video 5 near ceiling (39% of learners ≥ 90%) | quick check summary |

Open for Exp 1: where pupil size is stored (not among the gaze columns above).

## Experiments 2–5

Not downloaded yet. Run `notebooks/00_inventory.ipynb` and fill in: participants, sessions, sampling rate of BDF and TSV files, EEG/EOG/ECG channel names, quiz file layout.
