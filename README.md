# BBBD learning prediction

**Can eye tracking and ECG predict quiz performance as well as EEG, and does combining sensors improve prediction?**

DATA404 Multimodal Machine Learning final project at Vidyashilp University. The project uses the public Brain, Body, and Behavior Dataset (BBBD). Its target is performance on memory questions after an educational video. The primary evaluation holds out entire learners.

- **Team:** Priyanka Bhatt and Tanmayee K M
- **Dataset:** [BBBD paper](https://doi.org/10.1038/s41597-026-07215-1) and [Zenodo release](https://zenodo.org/records/19241964)
- **Preregistration:** [frozen protocol](https://github.com/pbhatt0022/bbbd_mml/blob/prereg-v1/docs/preregistration.md)

## Evidence and current scope

| Work | Where to look | Status |
| --- | --- | --- |
| Experiment 1 eye pipeline and condition contrast | [R-004](results/R-004_eye_rq0_exp1) | Registered exploratory validation |
| Eye-only quiz prediction | [R-012](results/R-012_classical_eye_exp1) | Original output. Read the implementation review in PR #2 before interpreting inference. |
| Repeated nested ridge analysis | [PR #2](https://github.com/pbhatt0022/bbbd_mml/pull/2) | Separate post-result correction. Check the run registry for completed outputs. |
| Experiment 2 ECG and EEG | [PR #1](https://github.com/pbhatt0022/bbbd_mml/pull/1) | Batch processing code. Registered results are pending. |
| Sensor equivalence, fusion and deep learning | [Methods plan](docs/methods_plan.md) | Planned evaluations. The library includes deep-learning components and synthetic tests. |

Read the [run registry](docs/run_registry.csv) for provenance and the [inference log](docs/inference_log.md) for interpretations. The planned sensor comparison requires matching modalities on the same learners and videos. The Experiment 1 eye analysis establishes a baseline for the broader project.

## Reproduce or inspect

- **Inspect saved outputs:** Open the registered CSV and JSON files in the table above. This route requires no raw data or Python installation.
- **Run in Colab:** Download the notebook from its raw GitHub URL and use **File → Upload notebook**. Use the relevant branch or commit in the URL. For the correction, follow the launcher linked from PR #2. It uses tracked tables and saves checkpoints to Drive.
- **Reprocess Experiment 1:** Point `config.yaml` at your BBBD copy. Inspect files with notebook 00, then use notebook 10 for eye validation, 05 for targets, and 50 for individual features. Notebook 60 documents the original prediction workflow. Use the existing frozen folds. Notebook 06 records their construction.
- **Check code:** GitHub Actions is the project test gate and runs pytest and notebook syntax checks. The project Windows setup has blocked scientific dependencies. Use Colab or a supported Linux environment for execution.
- **Package for submission:** Include the supporting files and executed notebooks with their outputs. The versioned result files provide a separate record of the registered runs.

## Code map for the viva

| Question | Where to open the code |
| --- | --- |
| How do we check file metadata and find the recordings? | [io.py](src/bbbd/io.py), [dataset inventory](docs/dataset_inventory.md) |
| How does one recording become a feature row? | [eye.py](src/bbbd/eye.py), [features.py](src/bbbd/features.py) |
| How do we detect beats and clean EEG? | [ecg.py](src/bbbd/ecg.py), [eeg.py](src/bbbd/eeg.py) |
| How do we keep learners out of their own test predictions? | [cv.py](src/bbbd/cv.py), [frozen fold assignments](results/folds.json) |
| Why do we shuffle within videos and resample learners? | [stats.py](src/bbbd/stats.py) |
| How would a peer reference or learned fusion work? | [isc.py](src/bbbd/isc.py), [models_dl.py](src/bbbd/models_dl.py) |
| How do we trace a number to an execution? | [runlog.py](src/bbbd/runlog.py), [run registry](docs/run_registry.csv) |

## Branches and pull requests

`main` is the shared baseline. A topic branch holds a proposed change. Its pull request shows the diff and CI checks so the other member can review it before merging. Keep the physiology and reconciliation branches available while their pull requests and run handoffs are active.

## Working rules

1. Raw data is never edited.
2. Any choice that could change a result goes in [`docs/decision_log.md`](docs/decision_log.md) **before** it is used.
3. Every result is written through `bbbd.runlog`, which gives it a run ID. A number goes in the report or slides only if it has a run ID.
4. What we conclude from a run goes in [`docs/inference_log.md`](docs/inference_log.md), with the run ID.
5. After the preregistration tag `prereg-v1`, any change to hypotheses, exclusions, metrics or splits is logged in [`docs/deviations.md`](docs/deviations.md).
6. Every citation goes in [`docs/references.bib`](docs/references.bib) when it is first used.
7. Branches: `a/<topic>` and `b/<topic>`; merge to `main` by pull request read by the other member.
8. Commit messages name the decision or run: `D-17: EEG high-pass 0.5 Hz`, `R-031: ridge eye-only`.
9. ISC references and CorrCA weights use training-fold learners only. Deep encoders are retrained per outer fold.

## Dataset credit and licensing

Cite both the data release and the paper when reporting work based on BBBD:

- **Dataset:** Madsen, J., Kuppa, N., & Parra, L. (2025). *The Brain, Body, and Behavior Dataset (BBBD): Multimodal Recordings during Educational Videos* [Data set]. Zenodo. [10.5281/zenodo.19241964](https://doi.org/10.5281/zenodo.19241964).
- **Paper:** Madsen, J., Kuppa, N., & Parra, L. C. (2026). The Brain, Body, and Behavior Dataset (BBBD): Multimodal Recordings during Educational Videos. *Scientific Data, 13*, 920. [10.1038/s41597-026-07215-1](https://doi.org/10.1038/s41597-026-07215-1).

The [Zenodo release](https://zenodo.org/records/19241964) is licensed under [CC BY 4.0](https://creativecommons.org/licenses/by/4.0/). This repository contains derived outputs from our own signal preprocessing, feature extraction, quiz scoring and modelling. When redistributing dataset material or adaptations, credit the creators, link to the release and license, retain applicable notices, and indicate changes.

The dataset license applies to the source data. The team has deferred choosing a license for its own project code until after grading.
