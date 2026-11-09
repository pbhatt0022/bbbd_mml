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
| Target, verified | **R-006 reproduces the means exactly**: 0.640, 0.557, 0.600, 0.597, 0.785; video 5 ceiling 38.7% ≥ 90%. Memory items only (D-27) | R-006 |
| Quiz column layout | `phenotype/stimuli_questionnaire.tsv`: `participant_id, stimulus_id, question_type, question_no, answer, correct_answer, is_correct` | R-006 |
| Learner overlap | 31 with quiz, 27 with gaze, **27 with both**, 0 with gaze only. Quiz-only: 24, 28, 29, 99 | R-006 |
| Scoring, verified | `is_correct` equals `answer == correct_answer` on **1.0000 of 3,286 items** — plain exact match, no partial credit or normalisation. 0 unscored items; 1,829 memory + 1,457 domain; 1,935 correct overall (58.9%). The target is therefore reproducible from the raw responses, not dependent on the authors' column | R-006 |
| Modellable rows, Exp 1 | **135** (27 learners × 5 videos), against 155 learner×video rows in the quiz alone | R-006 |
| Participant 99 | Outside the 02-31 run; likely a pilot or test record. Has no gaze, so it already contributes no model rows — but check before Exps 2-5 | R-006 |

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
| Display | **27″ monitor, ~60 cm viewing distance** (VERIFIED, preprint Procedure) → 59.77 cm wide, ~53° of visual angle | bioRxiv 10.1101/2025.04.29.651259 |
| Eye tracker | **EyeLink 1000, 35 mm lens, recorded at 500 Hz**; all released signals down-sampled to 128 Hz | bioRxiv, same |
| Screen resolution | **UNVERIFIED — stated in no source we could read.** 1920×1080 inferred (D-26) | — |
| Pixels per degree | **33.64** from the geometry above (D-26); independent data estimate 34.31, 2% apart. Authors convert with the EyeLink's per-sample resolution columns, absent from the released files | R-002; preprint |
| Authors' event detection | Blinks and saccades from "the eye tracker's algorithm that is used when saving to BDF files"; no velocity threshold stated. Blinks/artefacts ±100 ms linearly interpolated; pupil outliers at 4×IQR of a 200 ms-median-detrended signal | bioRxiv, Methods |
| Exp 1 condition order | Attentive session **first**, distracted second ("After they watched all the videos, they watched them again in a distracted condition"). The ses-01/ses-02 *label* mapping is still not stated in any source | bioRxiv, Procedure |
| Gaze sampling rate | 128 Hz (sidecar), confirmed | R-001 |
| Invalid gaze samples | **0.00 in all 263 gaze files** — contradicts the 3.03% median recorded on 14 Oct. The released gaze may already be interpolated; UNVERIFIED and worth resolving before any exclusion threshold is applied | R-001 |

Open for Exp 1: the real screen dimensions (to replace the estimated px/deg, D-24); which
session is attend vs distract; why invalid samples are 0.00 here but 3.03% on 14 Oct.

## Experiments 2–5

Not downloaded yet. Run `notebooks/00_inventory.ipynb` and fill in: participants, sessions, sampling rate of BDF and TSV files, EEG/EOG/ECG channel names, quiz file layout.
