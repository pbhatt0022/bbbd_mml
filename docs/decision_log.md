# Decision Log

Every choice that could change a result is logged here **before** it is used. Status moves Open → Proposed → Decided. If a decision changes later, mark the old row **Revisited** and add a new row explaining why; never overwrite. "Proposed" rows are recommendations and are not decided until both members agree (initial both in the Agreed column).

Commit each change with a message naming the row, e.g. `D-17: decided`.

Migrated from the Project Hub (Claude Docs) on 6 Nov 2026. From now on this file is the master copy.

| ID | Status | Decide by | Question | Options considered | Current answer and why | Source | Agreed |
| --- | --- | --- | --- | --- | --- | --- | --- |
| D-00 | Decided | | Which dataset? | BBBD; other education datasets | BBBD: 5 experiments, synchronised EEG/ECG/eye/respiration + quizzes, CC BY 4.0 | Project proposal; [Madsen 2026](https://www.nature.com/articles/s41597-026-07215-1) | A, B |
| D-01 | Decided | | Where does preprocessing start? | Authors' derivatives; raw files | Raw BDF (EEG/ECG/EOG/resp) and raw TSV (eye). Authors' derivatives used only as a validation reference. **Confirmed by the professor on 15 Oct** ("do all preprocessing on our own") | Team, 12 Oct; professor 15 Oct | A, B |
| D-02 | Decided | | Compute and storage | Local; Colab Pro | Colab Pro; data on shared Google Drive; code in GitHub (D-19) | Team, 12 Oct | A, B |
| D-03 | Proposed | 6 Nov | Which experiments are in scope? | All 5; EEG ones only (2–5); a subset | Eye on Exps 1–5, EEG/ECG on 2–5, respiration on 4–5; Exp 5 second (incentive) session analysed separately | Methods plan §3 | |
| D-04 | Proposed | 6 Nov | Prediction targets | Quiz score; attention condition; engagement; prior knowledge | Quiz score primary; attend vs distract auxiliary; engagement exploratory only | Literature Review §3 | |
| D-05 | Decided (scope) / Proposed (design) | 6 Nov | Must the project use deep learning? | Classical only; classical + DL component; DL only | **Professor 15 Oct: include some deep learning.** Design: one substantial DL track (RQ4, D-17) alongside classical confirmatory models, because N ≈ 600 learner × video rows is small for end-to-end DL | Professor 15 Oct; [Bodonhelyi 2026](https://arxiv.org/abs/2604.09569) | |
| D-06 | Decided | | Download the YouTube videos (S2)? | Yes; no | No: S2 dropped (D-18) | Methods plan §2 | |
| D-07 | Proposed | 6 Nov | Where is the preregistration timestamped? | PDF on Drive; OSF; git | `docs/preregistration.md` frozen with git tag `prereg-v1` pushed to GitHub (timestamped by GitHub); PDF copy on Drive | Preregistration | |
| D-08 | Decided | | Final dates | — | Submission Mon 16 Nov 2026 EOD (PPT, code with outputs, report); presentation Wed 18 Nov 2026 | Final Project Instructions | A, B |
| D-09 | Proposed | 6 Nov | Unit of analysis and grouping | Learner × video rows grouped by learner; learner averages | Learner × video rows; folds grouped by learner, so no learner is in both train and test | [Bodonhelyi 2026](https://arxiv.org/abs/2604.09569) on user-dependent inflation | |
| D-10 | Proposed | 6 Nov | Video difficulty in the target | Raw proportion; z-score within video; video covariate | z-score within video and experiment, so models explain differences between learners | Methods plan §3 | |
| D-11 | Proposed | 6 Nov | ISC reference group | All other learners; training-fold only | Training-fold learners only, recomputed per fold; training learners use leave-one-out within the training fold (`bbbd.isc`) | Methods plan §5 | |
| D-12 | Proposed | 6 Nov | EEG eye-artifact removal (default) | EOG regression; ICA; none | EOG regression (authors' approach) as V1; ICA as the RQ3 variant V3 | [Madsen 2026](https://www.nature.com/articles/s41597-026-07215-1); [Delorme 2023](https://pmc.ncbi.nlm.nih.gov/articles/PMC9911389) | |
| D-13 | Proposed | 6 Nov | 16 Hz noise in Exps 4–5 | Notch 16 Hz + harmonics; drop channels; exclude | Detect per recording from the spectrum (`eeg.has_peak`, ratio > 3 vs flanks); notch if present; log which recordings | Madsen 2026 known issues | |
| D-14 | Proposed | 6 Nov | Tooling | MNE + NeuroKit2 + scikit-learn; MATLAB | Python only: MNE, NeuroKit2, pandas/NumPy, scikit-learn, PyTorch | [NeuroKit2](https://github.com/neuropsychology/NeuroKit) | |
| D-15 | Proposed | 6 Nov | Primary metric | Pearson; Spearman; R²; MAE | Spearman ρ primary; R² vs mean baseline and MAE secondary | Preregistration | |
| D-16 | Proposed | 6 Nov | Split of work | By modality; by stage | A = eye + targets + models + DL fusion; B = EEG + ECG + resp + DL encoders/contrastive | Methods plan §8 | |
| D-17 | Proposed | 6 Nov | Deep learning design | End-to-end on quiz score; pretrain on window tasks then reuse; none | Encoders (EEGNet-style for EEG, 1D-CNN for eye/cardiac) trained on 4-s windows for (A) contrastive EEG↔eye alignment and (B) attend vs distract with early / late / cross-attention fusion and modality dropout; (C) pooled embeddings → ridge for quiz score. Encoders retrained in each outer fold | Methods plan §6b; [Lawhern 2018](https://doi.org/10.1088/1741-2552/aace8c) | |
| D-18 | Proposed | 6 Nov | Scope cuts for 10 days | Keep all; cut | RQ3 reduced to V1 vs V3 (ICA); V2 dropped. S1 (PID) optional on Thu 12 Nov. S2 (question-level) dropped to future work. Drop order if late: S1 → RQ3 → leave-one-video-out | Methods plan §8 | |
| D-19 | Proposed | 6 Nov | Version control and source of truth | Drive only; GitHub + Drive | Private GitHub repo `pbhatt0022/bbbd_mml` for code and docs; data on Drive only. Repo Markdown is the master; the Hub is a reading view | Methods plan §1 | |
| D-20 | Proposed | 6 Nov | Order of average reference and EOG regression | Reference before; reference after | Reference **before** EOG regression: MNE's `EOGRegression` refuses to run without a reference, and MNE's tutorial sets it first. Found while testing `bbbd.eeg` on 6 Nov | MNE-Python `EOGRegression` | |
| D-21 | Proposed | 6 Nov | DL window length | 2 s; 4 s; 8 s | 4 s, 50% overlap: long enough for alpha power and several saccades, short enough for thousands of windows per experiment. 8 s for the cardiac encoder if 4 s holds too few beats | Methods plan §6b | |
| D-22 | Proposed | 7 Nov | Python and core package versions | System default 3.14; 3.12; 3.11 | **Python 3.12** in `.venv`: torch has no 3.14 wheels, and 3.14 is the machine's `py` default, so the version must be pinned or each member gets a different one. Resolved on 6 Nov: numpy 2.5.4, scipy 1.18.1, pandas 3.1.1, scikit-learn 1.9.1, torch 2.15.0, mne 1.13.2, neurokit2 0.3.0, pyarrow 26.0.1. `pyproject.toml` sets only lower bounds, so these are what resolved today, not a guarantee; Colab may differ, which matters for RQ0 beat matching and any seeded split | Repo setup 6 Nov; `pyproject.toml` | |
| D-23 | Proposed | 7 Nov | Repository visibility | Private; public | **Public.** Chosen by A on 6 Nov 2026 after the repo was found to be public (`"private": false`), which contradicts the wording of D-19. No dataset files are in the repo, so nothing under the Zenodo CC BY 4.0 terms is exposed; `docs/` (preregistration, decision log, methods plan) is world-readable, which also makes the D-07 `prereg-v1` timestamp publicly checkable. **D-19's "Private GitHub repo" wording is superseded by this row**; mark D-19 Revisited once both members agree | Repo check 6 Nov; supersedes D-19 | |
| D-24 | Proposed | 9 Nov | How to get gaze into degrees for saccade detection | Sidecar `vdx`/`vdy` as-is; screen geometry + `px_to_deg`; estimate px/deg from the data | **Estimate px/deg** (`eye.estimate_px_per_deg`), ~24.9 on Exp 1, until the real screen dimensions are found. Exp 1 `x`/`y` are screen pixels (measured in R-001: x -377..1259, y -1010..1924) despite `visualangle` in the filename, and `vdx`/`vdy` are smoothed (p99.9 = 26 deg/s, under the 30 deg/s threshold), so thresholding them gave 2.7 saccades/min and 82-s fixations in R-001. `config.yaml eye.screen.px_per_deg` overrides the estimate once geometry is known | R-001 diagnostics, 8 Nov | |
| D-25 | Proposed | 9 Nov | Blink source for Exp 1 | Gaze track-loss; pupil dropout | **Pupil dropout**, per methods plan §4. Exp 1 does ship a `pupil_size` file per recording (263 `*_pupil_eyetrack.tsv.gz`, paired on sub/ses/task), which the Dataset Inventory had listed as an open question. R-001 used track-loss and found 0 blinks, because `invalid_frac` is 0.00 in every gaze file | R-001 diagnostics, 8 Nov | |

## Professor feedback (15 Oct 2026)

| Feedback point | Decision affected | Action |
| --- | --- | --- |
| The progress presentation was received well; keep most of the plan | All | Final plan builds on the 15 Oct deck |
| Do all preprocessing on our own | D-01 | Confirmed; raw files only, authors' derivatives for validation only |
| Use some deep learning | D-05, D-17 | Added RQ4 deep learning track |
| Replicating results from the original paper is fine | RQ0 | RQ0 kept as the replication part |
