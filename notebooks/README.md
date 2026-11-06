# Notebooks

Numbered so the order is the run order. Every notebook:

1. starts with the setup cell from `00_inventory.ipynb` (mount Drive, pull repo, `pip install -e .`, load `config.yaml`);
2. reads paths and settings only from `config.yaml`;
3. writes every result through `bbbd.runlog` (run ID, git hash, config hash);
4. runs top to bottom without errors and is committed **with outputs**;
5. keeps logic in `src/bbbd/`; notebooks call functions and show results.

| No. | Notebook | Owner | Produces |
| --- | --- | --- | --- |
| 00 | `00_inventory.ipynb` | B | Files, sampling rates, channels, quiz format per experiment → Dataset Inventory |
| 05 | `05_targets.ipynb` | A | Quiz proportion correct, z-scored within video (D-10) |
| 06 | `06_folds.ipynb` | A | `results/folds.json` (all schemes; used by every model) |
| 10 | `10_eye_preproc.ipynb` | A | Cleaned gaze/pupil, blink/saccade events, QC per recording |
| 20 | `20_eeg_preproc.ipynb` | B | Cleaned EEG V1 (and V3), QC per recording |
| 30 | `30_ecg_preproc.ipynb` | B | R-peaks, HR series, QC |
| 40 | `40_resp_preproc.ipynb` | B | Breathing rate series |
| 45 | `45_rq0_validation.ipynb` | A + B | RQ0 table: our vs authors' derivatives; attention effects |
| 50 | `50_features_individual.ipynb` | A + B | `03_features/*.parquet` |
| 60 | `60_classical_models.ipynb` | A | RQ1 / RQ2 results (ISC computed in-fold) |
| 70 | `70_dl_windows.ipynb` | A | Window datasets for DL |
| 71 | `71_dl_contrastive.ipynb` | B | Task A: alignment, Recall@K |
| 72 | `72_dl_attention_fusion.ipynb` | A | Task B: early / late / cross-attention |
| 73 | `73_dl_embeddings_to_quiz.ipynb` | A | Task C: RQ4 vs hand-crafted |
| 80 | `80_robustness_v3.ipynb` | B | RQ3 |
| 85 | `85_statistics.ipynb` | A | Permutations, bootstraps, TOST, Holm; final tables |
| 88 | `88_pid_optional.ipynb` | A | S1 (only if on time) |
| 90 | `90_figures.ipynb` | A + B | Every figure in the report and slides |
