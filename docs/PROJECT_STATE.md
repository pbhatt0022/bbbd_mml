# Project state — 15 November 2026

**Submission: Tuesday, 17 November 2026 (latest date supplied by Priyanka). Presentation: Wednesday, 18 November per the existing course notes.** The original faculty brief and D-08 record Monday, 16 November EOD. Keep that historical record and confirm the current portal deadline if there is any doubt.

DATA404 Multimodal Machine Learning, Vidyashilp University, Dr. Minati Rath. Priyanka Bhatt and Tanmayee K M. Priyanka reported running the experiments so far. The project asks whether eye tracking and ECG can match EEG for held-out learners' quiz performance, and whether fusion improves prediction.

## Evidence available locally

The registry contains R-001 through R-017. Read the run summaries and inference log before quoting results.

| Run | Evidence and interpretation |
| --- | --- |
| R-004 | Exploratory Experiment 1 eye validation. Inferred attend → distract saccade rates 138.0 → 93.2/min and blinks 1.25 → 2.90/min. The run predates the freeze. |
| R-012 | Historical eye-only result. DV-02 records mismatched permutation repeats, inner tuning and R² baseline description. Use R-013 for the corrected analysis. |
| R-013 | Eye-only, corrected nested ridge. ρ +0.108, 95% learner-bootstrap CI [−0.126, +0.354], raw permutation p = .032, conventional R² −.031, training-mean skill +.027. Exploratory post-result correction. Across-modality Holm pending. |
| R-014 | Experiment 2 attentive eye extraction. 155 rows, 5 pupil-quality exclusions. Uses the D-26 screen scale as an assumption. |
| R-015 | Retrospective ECG recovery audit. 140 eligible, 15 unevaluable processing errors, zero below 80% recall. All evaluable meet the F1 criterion. The detector was not rerun. |
| R-016 | Recovered EEG audit and common Experiment 2 cohort. 139 attentive EEG rows pass QC. The common cohort has 125 learner–video rows, 26 learners, five videos. Ten repeats of five learner-grouped outer folds saved in its run directory. |
| R-017 | Exploratory matched nested ridge on R-016. Eye −.216, ECG −.292, EEG +.053, eye+ECG −.327, all sensors −.111 and training-selected single modality −.066 in Spearman ρ. |

R-017 paired differences: EEG minus eye +.269 (90% CI [.088, .462]); EEG minus eye+ECG +.380 (90% CI [.212, .550]); all sensors minus training-selected single modality −.044 (95% CI [−.177, +.073]). Neither equivalence interval fits wholly inside ±.10. The eye interval overlaps the margin, so this does not establish a difference larger than the margin. EEG's absolute correlation is weak. Fusion benefit remains uncertain. Intervals resample learners with fixed predictions, and there was no permutation test in R-017.

## Data, provenance and guardrails

- Drive `04_results` was exported and compared against this repository on 15 Nov 2026. All 51 overlapping run files for R-001 to R-014 are identical, so the committed outputs are the same artifacts produced on Drive. The export contains **no notebooks**, so the empty-output problem is unchanged. **R-015, R-016 and R-017 are absent from Drive** and exist only on this machine and in Git.
- R-013 now has a real execution record in `results/R-013_eye_reconciliation/provenance/`: `console.log` (all 1,000 permutations, final line reporting rho and p that match the registered JSON), `CODE_COMMIT.txt` (8d8e97968fc84586f4ca42010b7b1721695a2428, matching `run_meta.json`) and the run `config.yaml`. This is stronger provenance than the recovered physiology tables have.
- Drive holds an **unregistered** from-raw Experiment 2 EEG alpha analysis (`2026-10-15_eeg_alpha_exp2` and `..._v2_main`, 291/291 raw BDF files, 30 learners). It reproduces the paper's alpha-higher-when-distracted effect and relates no signal to quiz scores. It predates the freeze, has no run ID, and no notebook in this repository regenerates it, so by the Drive README's own rule it cannot be reported. Treat as a candidate for a registered RQ0 EEG validation only if both members decide to and log it first.
- Experiment 2 raw ZIP and both recovery tarballs are listed in `dataset_inventory.md`. Copies were supplied in Priyanka's Downloads and shown in Drive under `MyDrive/MML_BBBD/`. Verify availability in a new environment. Keep raw files outside Git.
- Experiment 2 sidecars identify session 01 as attentive and 02 as distracted. Phenotype matches the ZIP byte for byte, and memory item totals reproduce its scores. Use the paper for quiz timing because the release README conflicts with itself.
- The recovered physiology tables lack original registered execution records. R-015/R-016 audit the saved tables. The EEG source matches de3b603 apart from line endings. This is not a raw rerun or proof of exact execution provenance. R-014–R-017 include local source snapshots where applicable because the base Git hash is not sufficient to reproduce dirty runs.
- Preserve the `prereg-v1` tag and `results/folds.json` (Experiment 1). Load Experiment 2 folds from `results/R-016_exp2_common_cohort/folds_exp2.json` with `cv.load_folds`. Keep identical rows and splits for paired comparisons.
- Log choices before use as Proposed and disclose deviations before dependent reporting. Keep numerical thresholds fixed. Register all scientific outputs via runlog. Preserve historical rows and use a new run ID for a new result. Keep learner groups intact in every evaluation and train-time reference.
- GitHub Actions is the project runtime test gate. Colab is available. Some local packages were sufficient for R-015–R-017, but this does not restore the full Windows test environment.

## Deliverables and next decision

- Draft report: `docs/report_draft.md` is the source; `docs/report_draft.docx` is built from it by `python docs/build_report_docx.py` (styles come from `docs/report_template.docx`, `--check` diffs without writing). Edit the Markdown and rebuild — never hand-edit the `.docx`, it will be overwritten. R-013 and R-017 are included. Verify the final Word layout and result tables before submission.
- Slides: draft deck at `slides/slides.tex`, LaTeX Beamer on the MU theme with a local `workplace=vsu` patch that drops the Masaryk University artwork. 18 slides built from R-004 validation, R-013 baseline and R-017 matched results; every figure and number carries its run ID. Build with `latexmk -pdf slides.tex` from `slides/`. Not yet reviewed by either member and not rehearsed. Still outstanding: demonstrate saved outputs and include executed notebooks with submission code.
- Deep learning: no registered BBBD result. Proposed next scope is a small eye-only attention CNN on Experiment 2, with whole learners held out, recording-level balanced accuracy and a simple baseline on the same recordings. This is a possible partial response to the faculty requirement, not the original RQ4 fusion or quiz task. No scope decision, runner, or launch cell exists yet. Specify split, window/QC choices and reporting in a new Proposed decision and deviation before fitting. Prioritize the submission package if runtime or validation is uncertain.
- GitHub: PR #3 was verified merged into main (README, credits, comments). PRs #1 and #2 were still active at last check. R-013–R-017, the report and newer code are present locally; do not assume they have been published. Check current refs before any Git operation. Avoid indiscriminate staging, especially the auxiliary .submission-work folder and data.
