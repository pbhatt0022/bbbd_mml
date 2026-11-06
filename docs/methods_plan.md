# Final Methods Plan

As of 6 Nov 2026. Master copy; the Project Hub tab "Final Methods Plan" mirrors it. Submission Mon 16 Nov 2026 EOD, presentation Wed 18 Nov 2026. Professor feedback (15 Oct): do all preprocessing ourselves; include some deep learning.

## 1. Repo and logging

Code and logs live in this repo; data stays on Drive and never enters git (D-19). See `README.md` for the layout and working rules. Three logs, three purposes:

- `decision_log.md`: choices made **before** running.
- `inference_log.md`: conclusions **after** running, each with a run ID.
- `deviations.md`: changes after the `prereg-v1` tag.

`run_registry.csv` ties every run ID to its git hash, config hash and seed. `references.bib` holds every citation.

## 2. Research questions and hypotheses

| ID | Question | Hypothesis | Course link |
| --- | --- | --- | --- |
| RQ0 (replication) | Do our pipelines from raw reproduce the paper's effects and the authors' derivatives? | Distraction lowers saccade/blink rate and raises EEG alpha; gaze ISC correlates with score (Madsen 2021); our R-peaks, blinks, saccades agree with the authors' | P5–P8 |
| RQ1 | How well does each modality and fusion strategy predict quiz score for unseen learners? | Eye within ±0.10 ρ of EEG; fusion gain small or non-significant | P3, P4, P12 |
| RQ2 (main novelty) | How much survives with features from one learner alone? | Above chance, below ISC | New |
| RQ3 (cut down) | Is the ranking stable with ICA (V3) instead of EOG regression (V1)? | Ranking stable | P10 mindset |
| RQ4 (DL) | Do deep encoders, pretrained on attention decoding and contrastive EEG↔eye alignment, give better features than hand-crafted ones? | Comparable or slightly better; fusion helps most for attention | P8, P9, P12, P13 |
| Aux | Attend vs distract decoding on held-out learners | Large effect; validates features | — |
| S1 (optional) | PID: unique vs shared information about score in EEG and eye | Mostly shared | P11 |

S2 (question-level prediction) is dropped to future work. Formal hypotheses H0–H4: `preregistration.md`.

## 3. Data and scope

| Exp | Signals | Conditions | Used for |
| --- | --- | --- | --- |
| 1 (~27) | Gaze, pupil | Attend + distract | RQ0 eye, Aux, eye-only RQ1/RQ2 |
| 2 (~31) | EEG, ECG, EOG, eye, head | Attend + distract, incidental learning | All RQs; DL pretraining |
| 3 (~29) | As Exp 2 | Attend + distract, 3 video styles | All RQs; DL pretraining |
| 4 (~43) | All incl. respiration | Attend only, last 3 videos quizzed | RQ1–RQ4 |
| 5 (~48) | All | 3 videos twice, incentive between | First session in main analysis; second separately |

Participant counts are from the paper; verify against `participants.tsv` in notebook 00. Unit: learner × quizzed video, attend only for quiz prediction, folds grouped by learner. Target: proportion correct z-scored within video and experiment (D-10). Pooling across experiments is a sensitivity check, not the main result (Exp 2 is incidental learning).

## 4. Preprocessing from raw

Step 0 for every modality: confirm sampling rate and units from the files and sidecars (the paper says released signals may be at 128 Hz).

| Modality | Our steps (V1) | Authors' approach | Validation (RQ0) |
| --- | --- | --- | --- |
| Eye: gaze | Pixels → degrees; track loss masked; I-VT saccades > 30°/s; fixations = remaining runs ≥ 60 ms | EyeLink online events | Saccade/blink rate vs authors' events (r, bias) |
| Eye: pupil, blinks | Blinks from pupil dropout ±100 ms; gaps < 250 ms interpolated; > 50% invalid excluded; per-recording z-score | ±100 ms interpolation | % interpolated vs paper's 22% gaze / 32% pupil |
| ECG | NeuroKit2 clean + R-peaks; RR 300–2000 ms; mean HR, HR SD, RMSSD | findpeaks + manual correction | Beat-matching F1 (±50 ms), HR correlation |
| EEG | HP 0.5 Hz; notch 60 Hz (+16 Hz if detected); robust-z bad channels → interpolation; average reference; EOG regression; 4×IQR bad segments | HP 0.05, notch 60, robust PCA, EOG regression, 4×IQR, LP 64 | Alpha attend vs distract effect; % channels interpolated |
| EEG V3 | As V1 with ICA EOG removal | — | Same; RQ3 ranking |
| Respiration | NeuroKit2 `rsp_process`; rate, rate SD | Polarity corrected | Rate 8–25 breaths/min |

Exclusions: eye > 50% invalid; EEG > 20% bad channels or > 10% bad time; ECG < 80% beats. Each listed in `results/exclusions.csv`. Per-recording QC reports go in the report appendix.

## 5. Features

| Modality | Individual (RQ2) | ISC (peer group) |
| --- | --- | --- |
| Eye | Saccade, blink, fixation rate; fixation duration; pupil level and variability; gaze dispersion | Gaze, pupil, saccade-rate time courses vs training-learner mean (Madsen 2021) |
| ECG | Mean HR, HR SD, RMSSD | HR time course vs training-learner mean (Pérez 2021) |
| EEG | Relative band power by region; alpha/theta; aperiodic slope | CorrCA top 3 components, weights fitted on training learners (Cohen 2018; Parra 2019) |
| Respiration | Rate, rate SD | Rate time course vs training mean |

Leakage rule (D-11): ISC references and CorrCA weights use training-fold learners only (`bbbd.isc`).

## 6. Models

Deep networks are not trained end to end on quiz score (≈ 600 rows); they train on window-level tasks with thousands of samples, and their embeddings are reused (D-17).

**6a. Classical (RQ1–RQ3):** ridge (primary, alpha tuned internally); random forest and small MLP secondary; early fusion (concatenation), late fusion (averaged/stacked predictions), leave-one-modality-out.

**6b. Deep learning (RQ4):** 4-s windows at 128 Hz, 50% overlap (D-21).

| Component | Architecture | Trained on | Course link |
| --- | --- | --- | --- |
| EEG encoder | EEGNet-style CNN → 128-d (Lawhern 2018) | Tasks A/B | P8 |
| Eye encoder | 1D-CNN on gaze x/y, velocity, pupil, blink mask → 128-d | Tasks A/B | P5/P8 |
| Cardiac encoder | 1D-CNN on instantaneous HR (+ resp) → 128-d | Task B | P5 |
| Task A: contrastive | Symmetric InfoNCE between EEG and eye of the same window; Recall@1/5/10 on held-out learners | Exps 2–5, no labels | P9, P13 |
| Task B: attention | Encoders + early / late / cross-attention fusion, modality dropout p = 0.3 | Exps 2–3 | P3, P4, P12 |
| Task C: learning | Mean-pooled window embeddings per learner × video → ridge | Quiz score | Links RQ4 to RQ1 |

Encoders are retrained in each outer fold; early-stopping validation learners come from the training fold. AdamW, lr 1e-3, wd 1e-2, batch 256, 3 seeds.

## 7. Evaluation and statistics

| Item | Choice |
| --- | --- |
| Main split | 5-fold grouped by learner; classical ×10 repeats; DL ×1 with 3 seeds |
| Second split | Leave-one-video-out |
| Quiz metrics | Spearman ρ (primary); R² vs mean; MAE |
| Attention metrics | Balanced accuracy, ROC AUC |
| Alignment | Recall@1/5/10 vs chance |
| Significance | Permutation, 1,000 within-video shuffles, full CV refit |
| Uncertainty | Learner bootstrap 95% CI (2,000) |
| Eye vs EEG | Paired bootstrap Δρ, TOST with ±0.10 |
| Multiplicity | Holm within each RQ |

We report CIs and equivalence, not a single winner (Varoquaux 2018). Preregistration frozen with tag `prereg-v1` before any feature–score correlation.

## 8. Schedule

| Day | Member A (eye, targets, models) | Member B (EEG, ECG, resp) | Gate |
| --- | --- | --- | --- |
| Fri 6 Nov | Repo live; docs in `docs/`; freeze prereg | Download Exps 2–3; inventory (notebook 00) | Repo live, `prereg-v1` |
| Sat 7 | Eye pipeline Exps 1–5; targets | EEG V1 on Exp 2; ECG R-peaks | Exp 2 cleaned |
| Sun 8 | RQ0 eye; gaze ISC vs score | RQ0 EEG/ECG; Exps 3–5 | RQ0 table |
| Mon 9 | Eye features; classical RQ1/RQ2 | EEG/ECG/resp features; CorrCA in-fold | First RQ1/RQ2 numbers |
| Tue 10 | Window dataset; fusion heads; Task B | Encoders; Task A | DL trains on one fold |
| Wed 11 | Task B all folds; Task C | Task A all folds; V3 (RQ3) | RQ3 + RQ4 numbers |
| Thu 12 | Stats; S1 if on time | LOVO runs; QC appendix | **Results frozen** |
| Fri 13 | Final figures | Clean repo; rerun notebooks with outputs | Repo runs end to end |
| Sat 14–Sun 15 | Report §1–4, 8–10; slides | Report §5–7, 11–12; slides | Drafts |
| Mon 16 | Proofread; submit | Proofread; submit | **Submitted** |
| Tue 17 | Rehearsal | Rehearsal | — |

If behind on Thursday, drop S1, then RQ3, then leave-one-video-out. Minimum to present: RQ0, RQ1, RQ2, RQ4 Task B.

## 9. Open questions

- [ ] What exists since 15 Oct (data, notebooks)?
- [ ] Was any feature compared with quiz score already? (Needed before tagging `prereg-v1`.)
- [ ] Exact wording of the professor's DL request.
- [ ] Hours per day per member until 16 Nov.
- [ ] Submit as a GitHub link or a zip?
- [ ] Agree on every Proposed row in the Decision Log.
