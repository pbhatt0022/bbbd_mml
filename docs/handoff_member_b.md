# Handoff to Member B — EEG, ECG, respiration, Experiments 2–5

Written 9 Nov 2026 by Member A. Read this before writing any code, and give it to your
LLM assistant as context — most of it is things we learned the hard way, which no amount
of reading the source will tell you.

**Submission Mon 16 Nov, presentation Wed 18 Nov.** The eye track is done for Exp 1; your
track has not started.

---

## 1. The one thing that needs you first

`docs/preregistration.md` §0 says, and nobody has yet confirmed:

> **Team to confirm before tagging:** no feature has yet been correlated with quiz scores.

**Have you, at any point, computed a relationship between any feature and a quiz score?**
In `bbbd_quickcheck.py` on Drive, a Colab cell, a scratch notebook, anything — even once,
even as a sanity check. Reading the paper's published results does *not* count; only our
own numbers do.

Member A has not. If you have not either, say so in §0 and in `DV-01`, tag `prereg-v1`,
and push the tag. **Until that tag exists, every result we produce is exploratory, not
confirmatory** — we have already lost that status for one clean p < 10⁻⁶ finding (R-004)
because the tag slipped from 6 Nov. Please settle this today.

Also waiting on you: sign-off on four preregistered margins, which are the numbers that
decide whether hypotheses pass.

| Where | Value | Why it matters |
| --- | --- | --- |
| H0a | beat match ±50 ms, F1 ≥ 0.95 | your ECG validation passes or fails on this |
| H1b | equivalence margin Δρ ±0.10 | decides whether "eye ≈ EEG" is declared |
| H4c | non-inferiority bound −0.10 | decides whether deep ≈ hand-crafted |
| Prereg §2 | eye >50% invalid, EEG >20% bad channels / >10% bad time, ECG <80% beats | who is excluded |

And **24 of 30 decision-log rows are still `Proposed`** with no initials. Work through
`docs/decision_log.md` and initial what you agree with. Nobody may mark a row `Decided`
alone.

---

## 2. Where the project actually is

| | |
| --- | --- |
| Notebooks | `00_inventory`, `05_targets`, `06_folds`, `10_eye_preproc`, `50_features_individual` |
| Runs | R-001 … R-007, all in `docs/run_registry.csv` |
| Decision rows | 30 (D-00 … D-29), 24 still Proposed |
| Inference rows | 2 — the 14 Oct pre-repo row (marked replaced) and R-004 |
| Tag | **none** |
| CI | GitHub Actions runs `pytest` + a notebook-parse check on every push to `main` and every PR |

Not started: **everything of yours** — EEG, ECG, respiration, and Exps 2–5, which are not
even downloaded.

`60_classical_models` is the next notebook and it **needs the tag**, because it is the
first thing that relates a feature to quiz score.

### 2.1 What was done, 6–9 Nov

**Repo (6 Nov).** `git init` on the skeleton, first commit on `main`, pushed. The remote
was empty, so there was no README to reconcile. Data, `.venv` and archives stay out via
`.gitignore` — verified, not assumed. `prereg-v1` was **not** tagged, per the plan that
you and A would do it together.

**Infrastructure.** Local `pytest` became unusable mid-project (Windows Smart App Control
started blocking pandas' binaries), so the suite now runs in **GitHub Actions** on every
push to `main` and every PR. It also parses every notebook. That has already caught a
broken notebook before it reached Colab, and it is the reason the environment is known to
be reproducible from `pyproject.toml` alone.

**Eye pipeline — four runs, because the first was wrong.**

| Run | What happened |
| --- | --- |
| R-001 | Ran end to end and produced **nonsense**: 2.7 saccades/min, 82-second fixations. Cause: it thresholded the sidecar's `vdx`/`vdy`, which are smoothed below the saccade threshold. Half the files also errored — the `_pupil_` files have no `x` column. |
| R-002 | Fixed: gaze converted to degrees and differentiated; pupil files paired properly. Sensible numbers for the first time. |
| R-003 | Superseded by a rerun; kept for the audit trail. |
| **R-004** | Current. px/deg from sourced screen geometry rather than a data estimate. |

**The RQ0 result (R-004), Exp 1, 27 learners, 263 recordings, 0 excluded:**

| Metric | ses-01 | ses-02 | t(26) | p | d_z |
| --- | --- | --- | --- | --- | --- |
| Saccades/min | 138.0 | 93.2 | 6.18 | 1.6e-06 | 1.19 |
| Blinks/min | 1.25 | 2.90 | −3.04 | .0054 | −0.58 |
| Fixations/min | 131.8 | 84.1 | 7.02 | 1.9e-07 | 1.35 |
| Median fixation | 245 ms | 332 ms | −4.82 | 5.4e-05 | −0.93 |

Two things make this trustworthy. **The blink numbers reproduce the 14 Oct quick check
exactly** (1.25 → 2.90, t = 3.04) — and blinks come from pupil, so they are independent of
the px/deg calibration, which is the one free parameter. And the saccade rates (138 → 93)
sit close to the **authors' own derivative counts** (136 → 89), rather than to our October
detector (174 → 131). H0b holds on all four metrics. Written up in
`docs/inference_log.md`, **marked Exploratory** because the tag did not exist when it ran.

**The calibration, and why it needed sourcing.** `x`/`y` are pixels, so saccade detection
needs px/deg. Estimating it from the data gave a median of 34.31 but scattered wildly
across recordings (7.6–117.6, relative IQR 0.69) — not usable. Reading the preprint gave a
27″ monitor at ~60 cm; with an *inferred* 1920×1080 that yields **33.64 px/deg**, 2% from
the data estimate. The agreement from two unrelated routes is the evidence; the resolution
itself is still unsourced (D-26).

**Targets (R-006).** Memory items only (D-27) — domain questions probe prior knowledge,
which the preregistration treats as a covariate, not the outcome. Per-video means came out
**0.640 / 0.557 / 0.600 / 0.597 / 0.785**, reproducing the 14 Oct figures exactly, with
video 5's ceiling at 38.7% of learners ≥ 90%. 31 learners have quiz data, 27 have gaze →
**135 modellable rows**. We also verified that `is_correct` equals
`answer == correct_answer` on **all 3,286 items**, so the target is reproducible from raw
responses rather than dependent on the authors' scoring column.

**Folds (R-007).** `results/folds.json`: 135 rows, 5-fold grouped by learner × 10 repeat
seeds, plus leave-one-video-out — 11 schemes. Verified independently of the notebook that
no group spans two folds in its own scheme. Fold sizes 30/30/25/25/25, i.e. 6,6,5,5,5
learners.

**Features.** `50_features_individual` is written but **not yet run**. It deliberately
writes **no target column** — the join to quiz score happens in `60_classical_models`,
after the tag.

### 2.2 Decision rows added since the migration

All `Proposed`, all needing your initials.

| Row | Subject |
| --- | --- |
| D-22 | Python 3.12 and the resolved package versions |
| D-23 | The repo is public, not private as D-19 says |
| D-24 | Estimating px/deg from the data (superseded by D-26, kept as a cross-check) |
| D-25 | Blinks from pupil dropout — Exp 1 does ship `pupil_size` |
| D-26 | px/deg from screen geometry; resolution inferred |
| D-27 | The target is memory items only |
| D-28 | Leave-one-video-out holds out a video, not a learner — its numbers are not comparable to the grouped ones |
| D-29 | `ses-01` is the attend session (inferred, not sourced) |

---

## 3. Working rules (README §Working rules — your LLM must follow these)

1. **Raw data is never edited.**
2. **Any choice that could change a result goes in `docs/decision_log.md` _before_ it is
   used**, as a new `D-xx` row with status `Proposed`. Never mark a row `Decided`
   yourself. Never overwrite a row; add a new one and mark the old `Revisited`.
3. **Every result is written through `bbbd.runlog`**, which stamps it with a run ID, git
   hash, config hash and seed. A number may appear in the report only if it has a run ID.
4. **Conclusions go in `docs/inference_log.md`** with the run ID. Observation = numbers
   only; conclusion = one sentence a reviewer could disagree with; name at least one
   alternative explanation.
5. After `prereg-v1`, changes to hypotheses, exclusions, metrics or splits go in
   `docs/deviations.md`.
6. Citations go in `docs/references.bib` on first use. **Never invent a reference or a
   dataset fact.** Verified facts go in `docs/dataset_inventory.md`; everything else is
   marked UNVERIFIED.
7. Branches `b/<topic>`, pull request to `main`. (Member A has been merging directly while
   you were away, since no reviewer was available — now that you are back, PRs again.)
8. Commit messages name the row or run: `D-17: EEG high-pass 0.5 Hz`, `R-031: ridge eye-only`.
9. ISC references and CorrCA weights use **training-fold learners only**. Deep encoders
   are retrained per outer fold.

Settings live in `config.yaml`; nothing is hard-coded in notebooks. Data is never
committed — it lives outside the repo.

---

## 4. Hard-won facts about this dataset

Every one of these cost us at least one wasted run. Assume Exps 2–5 hold equivalent
surprises and **run `00_inventory` before writing any preprocessing code.**

### Things that were not what the filename or the docs said

- **Gaze `x`/`y` are screen pixels, not degrees** — despite the files being named
  `..._gaze_visualangle_eyetrack.tsv.gz`. We measured x spanning −377…1259.
- **`vdx`/`vdy` are smoothed.** They are genuinely deg/s, but their 99.9th percentile is
  26 deg/s, *below* the 30 deg/s saccade threshold. Thresholding them yielded 2.7
  saccades/min and 82-second fixations (R-001, wrong). You must differentiate position
  instead. **If the EEG files ship any pre-derived channel, suspect it the same way.**
- **Two raw files per recording**, paired on `sub`/`ses`/`task`: `..._gaze_visualangle_...`
  (`x, y, vdx, vdy`) and `..._pupil_...` (`pupil_size`). A naive glob picks up both, and
  the second has no `x` column.
- **`derivatives/` sits inside the experiment folder and has no JSON sidecars**, so
  `io.read_physio_tsv` cannot read those files. Filter `"derivatives" not in f.parts`.
- **`ses` is the condition; `task` is the video** (`task-stim01`…`stim05`). Our first
  fallback guessed `task` was the condition, which would have run the attention contrast
  across *videos* and produced plausible nonsense.
- **Join keys differ between tables.** The eye files say `task-stim01`; the quiz table
  says integer `1`. Convert and then *assert* the key sets intersect.

### Verified apparatus facts (bioRxiv 10.1101/2025.04.29.651259, Procedure)

- 27″ monitor, ~60 cm viewing distance → 59.77 cm wide, ~53° of visual angle.
- **EyeLink 1000, 35 mm lens, recorded at 500 Hz. All released signals down-sampled to
  128 Hz.** Confirm 128 Hz from the sidecar for every modality anyway.
- Screen **resolution is stated in no source we could find.** 1920×1080 is *inferred*
  (D-26): it gives 33.64 px/deg, against 34.31 estimated independently from the data.
- The authors convert to degrees with the EyeLink's **per-sample resolution columns**,
  which are not in the released files — so any single px/deg constant is an approximation.
- Blinks and saccades were detected by "the eye tracker's algorithm used when saving to
  BDF files"; **no velocity threshold is stated**. Blinks and artefacts, ±100 ms, were
  linearly interpolated. Pupil outliers at 4×IQR of a 200 ms-median-detrended signal.
- Exp 1 ran the **attentive session first**, distracted second. The `ses-01`/`ses-02`
  label mapping is *not* stated anywhere; we infer ses-01 = attend (D-29) from R-004's
  blink rates reproducing the 14 Oct figures exactly.

### Open puzzles — please look at these with fresh eyes

- **`invalid_frac` is 0.00 in all 263 Exp 1 gaze files**, but the 14 Oct quick check
  recorded a 3.03% median. Either that check was wrong, or the released gaze is already
  interpolated. **This makes the >50%-invalid exclusion rule a no-op**, so it matters.
- **Participant `99`** appears in the Exp 1 quiz (others run 02–31) and is likely a pilot
  record. Harmless for Exp 1 (no gaze), but check for it in Exps 2–5.
- 31 learners have quiz data, 27 have gaze, giving **135 modellable rows** for Exp 1.

---

## 5. Your track

### Data — not downloaded

| File | Zipped |
| --- | --- |
| experiment2.zip | 5.6 GB |
| experiment3.zip | 8.0 GB |
| experiment4.zip | 5.5 GB |
| experiment5.zip | 7.0 GB |

From `https://zenodo.org/api/records/19241964/files/experimentN.zip/content`.
**Verify the md5 before unzipping** — a truncated BDF surfaces much later as a baffling
preprocessing error. Exp 2's is `e9671316f97e1c3ec1d86a03e0a1ab28`; the rest are in the
Zenodo API response.

A free Google Drive account (15 GB) will not hold these. See §6.

### Suggested order

1. **`00_inventory` on Exp 2.** Your notebook, already written. Confirms participants,
   sessions, sampling rates, EEG/EOG/ECG channel names, quiz layout. **Do this before
   anything else** — see §4 for why.
2. **ECG (`30_ecg_preproc`).** Far less work than EEG: `ecg.detect_rpeaks` →
   `clean_rr` → `hr_features`, and `match_beats` gives you H0a directly against the
   authors' hand-corrected peaks. A real second modality for fusion, quickly.
3. **EEG V1 (`20_eeg_preproc`).** `eeg.preprocess(raw, cfg["eeg"])` runs the whole V1
   chain. Note **D-20: average reference goes _before_ EOG regression** — MNE's
   `EOGRegression` refuses to run without a reference.
4. **Respiration (`40_resp_preproc`)**, Exps 4–5 only. `resp.resp_features`.
5. **RQ0 validation** for your modalities: beat-matching F1, alpha attend-vs-distract.

Modules already written for you, all with tests: `eeg.py` (load_bdf, filter_raw,
find_bad_channels, eog_regression, ica_remove_eog, bad_segments, preprocess, band_power,
aperiodic_slope, has_peak for the 16 Hz issue), `ecg.py`, `resp.py`, `isc.py` (CorrCA),
`features.eeg_features`. **They were written against the paper, not against real files** —
expect to adjust them, and log any change that affects a result.

### Rules specific to your work

- **Never build your own CV folds.** Load `results/folds.json` with `cv.load_folds`. Every
  model shares it so comparisons are paired. Rebuilding them silently unpairs everything.
- **ISC and CorrCA weights: training-fold learners only** (D-11). `isc.py` takes a
  `train_mask` for exactly this reason.
- The two fold schemes answer different questions and **their numbers are not comparable**
  (D-28): `group5_seed*` holds out whole learners; `lovo` holds out a video and keeps the
  same learners in train and test. Always say which scheme a number came from.

---

## 6. Environments

**Best: the Ubuntu workstation** (HP Z2, i9-14900K, 32 GB RAM, RTX 4000 Ada 20 GB,
123 GB free on `/home`). Python 3.12.3, which matches D-22. No storage limit worth
worrying about, and the GPU means the RQ4 deep-learning track can run there too.

```bash
cd ~ && git clone https://github.com/pbhatt0022/bbbd_mml.git && cd bbbd_mml
python3 -m venv .venv && ./.venv/bin/pip install -e ".[dev]"
./.venv/bin/python -m pytest -q          # the full suite should pass
```

(If `venv` fails: `sudo apt install -y python3-venv python3-pip unzip`.)

**Colab** works but has sharp edges we hit repeatedly:

- **Colab serves stale notebooks from GitHub.** It bit us three times — you edit, push,
  reopen, and get the old version. If a fix "didn't work", check you are running it.
  `raw.githubusercontent.com/pbhatt0022/bbbd_mml/main/notebooks/<name>.ipynb` always
  serves current `main` and is immune.
- **A PEP 660 editable install is invisible to the running kernel** (its `.pth` is read
  only at interpreter start), so the setup cell adds `src/` to `sys.path` directly instead
  of making you restart the runtime.
- **Push from Colab** needs a fine-grained GitHub token in Colab Secrets named `GH_TOKEN`
  (Contents: read and write, this repo only), toggled on per notebook. The push cell
  fetches and rebases first, because `main` often moves while a notebook runs.
- Outputs are mirrored to Drive `04_results/runs/` before pushing, so a failed push never
  loses a run.

**Windows is unusable.** Smart App Control blocks newly-downloaded unsigned binaries —
pandas, pyarrow and neurokit2 all fail to import in any fresh environment. Turning it off
is irreversible without reinstalling Windows. Don't.

---

## 7. Workflow gotchas

- **Run IDs are per execution, not per kept result.** Rerunning a notebook burns an ID, so
  the sequence has gaps. That is fine and should not be "cleaned up".
- `runlog.finish_run` rewrites the row for its run ID rather than appending — re-running
  a save cell used to produce duplicate rows (R-003 appeared three times).
- **CI is your safety net**: every push to `main` and every PR runs the test suite and a
  notebook-parse check that catches syntax errors and cells whose source lines lost their
  newlines. It has already caught a broken notebook before it reached Colab. Watch it.
- Small results are versioned in `results/`; large outputs go to Drive `04_results`
  (`runlog.start_run(..., large_outputs=True)`).

---

## 8. For your LLM assistant, specifically

- **Do not invent dataset facts, citations, or column names.** Every guess we made about
  this dataset was wrong. Print the real columns, assert the mapping, and fail loudly.
  `05_targets` cell 2 and `10_eye_preproc` cell 1b are the pattern to copy.
- **Put logic in `src/bbbd/`, not in notebook cells** (notebooks README rule 5), and leave
  a test behind. Notebooks call functions and show results.
- **Do not mark decision rows `Decided`.** Propose; the humans agree.
- **Do not correlate any feature with quiz score until `prereg-v1` is tagged.** This is the
  one irreversible mistake available in this project.
- When something looks wrong, say so rather than working around it. The saccade detector
  "worked" for a whole run while producing 82-second fixations.

---

## 9. Questions for the two of us

- Confirm the §0 disclosure, then tag `prereg-v1`. **Today.**
- Initial the 24 Proposed decision rows.
- Agree the four margins in §1.
- Given one person has been working for the last stretch: is the five-experiment scope
  still realistic by the 16th, or do we invoke the D-18 drop order (S1 → RQ3 →
  leave-one-video-out) now rather than at Thursday's gate?
- Does the professor know we were briefly down to one person?
