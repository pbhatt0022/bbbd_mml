# bbbd_mml

**Can eye-tracking and heart signals predict learning from educational videos as well as EEG?**

DATA404 Multimodal Machine Learning, final project. We preprocess the Brain, Body and Behavior Dataset (BBBD) from raw, build hand-crafted and deep multimodal models, and evaluate them on learners the models have never seen.

- Dataset: Madsen, Kuppa & Parra (2026), *Scientific Data* 13:920, [doi:10.1038/s41597-026-07215-1](https://www.nature.com/articles/s41597-026-07215-1). Data on [Zenodo](https://zenodo.org/records/19241964) (CC BY 4.0). The data is **not** in this repo.
- Team: Member A (eye tracking, targets, models), Member B (EEG, ECG, respiration).
- Submission: 16 Nov 2026. Presentation: 18 Nov 2026.

## Research questions

| ID | Question |
| --- | --- |
| RQ0 | Do our pipelines from raw reproduce the paper's effects and the authors' derivatives? |
| RQ1 | How well does each modality and each fusion strategy predict quiz score for unseen learners? |
| RQ2 | How much survives with features from one learner alone (no peer group)? |
| RQ3 | Is the modality ranking stable if EEG is cleaned with ICA instead of EOG regression? |
| RQ4 | Do deep encoders (contrastive EEG-eye alignment, attention decoding) give better features than hand-crafted ones? |

Full plan: [`docs/methods_plan.md`](docs/methods_plan.md). Hypotheses and tests: [`docs/preregistration.md`](docs/preregistration.md).

## Repository layout

```
config.yaml        every path, seed and tunable setting (notebooks read this, nothing hard-coded)
src/bbbd/          shared library code
  config.py        load config.yaml, resolve paths
  runlog.py        stamp every result with git hash + config hash + seed; append to run registry
  io.py            find BBBD files (BIDS) and read sidecars
  eye.py           gaze/pupil cleaning, blink + saccade detection
  ecg.py           R-peaks (NeuroKit2), HR/HRV, beat matching vs authors' peaks
  eeg.py           MNE pipeline: filters, bad channels, EOG regression, ICA variant, band power
  resp.py          respiration rate
  isc.py           inter-subject correlation and CorrCA, fold-safe (training learners only)
  features.py      individual-only feature tables
  cv.py            grouped folds, saved once, shared by every model
  stats.py         permutation tests, learner bootstrap, equivalence (TOST), Holm
  models_dl.py     EEGNet, 1D-CNN encoders, InfoNCE contrastive loss, fusion heads
notebooks/         numbered notebooks; run top to bottom with outputs saved
scripts/           command-line wrappers for long Colab runs
tests/             unit tests on synthetic data (run: pytest)
docs/              decision log, inference log, deviations, preregistration, references
results/           small result files (JSON, CSV, figures) that are versioned
```

Data lives on the shared Google Drive under `MML_BBBD/` (`01_data_raw` read-only, `02_data_interim`, `03_features`, `04_results`). Paths are set in `config.yaml`.

## Running it

**Colab (main route).** Open any notebook; its first cell does this:

```python
from google.colab import drive; drive.mount('/content/drive')
!git clone https://github.com/pbhatt0022/bbbd_mml.git /content/bbbd_mml || git -C /content/bbbd_mml pull
%cd /content/bbbd_mml
!pip install -q -e .
```

Then set `data_root` in `config.yaml` to your Drive path (default `/content/drive/MyDrive/MML_BBBD`).

**Local.**

```bash
python -m venv .venv && source .venv/bin/activate   # Windows: .venv\Scripts\activate
pip install -e ".[dev]"
pytest                                             # all tests should pass
```

**Order.** Run notebooks in number order. `00`-`09` inventory and targets, `10`-`49` preprocessing per modality, `50`-`59` features, `60`-`69` classical models, `70`-`79` deep learning, `80`-`89` robustness and statistics, `90`-`99` figures.

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

## Citation

If you use this code, cite the dataset paper above. Code licence: to be decided after grading.
