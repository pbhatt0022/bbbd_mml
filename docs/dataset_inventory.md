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

## Experiment 1, file layout (verified 8 Nov 2026 on Colab, run R-001 + diagnostics)

| Item | Value | Source |
| --- | --- | --- |
| Raw eyetrack files | 526 outside `derivatives/`: **263 gaze + 263 pupil**, one pair per recording, paired on `sub`/`ses`/`task` | R-001 |
| Gaze file | `sub-XX_ses-0Y_task-stimNN_gaze_visualangle_eyetrack.tsv.gz`, columns `x, y, vdx, vdy` | R-001 |
| **Pupil file** | `..._pupil_eyetrack.tsv.gz`, column **`pupil_size`** — this answers the open question below | R-001 diagnostics |
| Derivative files | 526, under `derivatives/`, **no JSON sidecar** (so `read_physio_tsv` cannot read them) | R-001 |
| Filename entities | `ses-01`/`ses-02` = the two **conditions**; `task-stim01..05` = the five **videos**. Which session is attend is still UNVERIFIED | R-001 |
| `x`, `y` units | **Screen pixels, not degrees**, despite `visualangle` in the name: x −376.9..1259.2, y −1010.0..1923.8 (one recording) | R-001 diagnostics |
| `vdx`, `vdy` units | deg/s, but **smoothed**: median speed 5.81, p90 10.04, p99 16.23, p99.9 26.39, only 0.02% above 30 deg/s | R-001 diagnostics |
| Pixels per degree | ≈ **24.9**, estimated from pixel speed ÷ sidecar deg/s (D-24). Real screen geometry still UNVERIFIED | R-001 diagnostics |
| Gaze sampling rate | 128 Hz (sidecar), confirmed | R-001 |
| Invalid gaze samples | **0.00 in all 263 gaze files** — contradicts the 3.03% median recorded on 14 Oct. The released gaze may already be interpolated; UNVERIFIED and worth resolving before any exclusion threshold is applied | R-001 |

Open for Exp 1: the real screen dimensions (to replace the estimated px/deg, D-24); which
session is attend vs distract; why invalid samples are 0.00 here but 3.03% on 14 Oct.

## Experiments 2–5

Not downloaded yet. Run `notebooks/00_inventory.ipynb` and fill in: participants, sessions, sampling rate of BDF and TSV files, EEG/EOG/ECG channel names, quiz file layout.
