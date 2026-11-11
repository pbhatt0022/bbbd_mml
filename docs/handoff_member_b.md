# Handoff to Member B — EEG, ECG, respiration, Experiments 2–5

Updated **11 Nov 2026** by Member A. Read this before writing code, and give it to your LLM
assistant as context. Most of it is things we learned the hard way, which reading the
source will not tell you.

**Submission Mon 16 Nov, presentation Wed 18 Nov — five days.** The eye track is built and
frozen; your track has not started.

---

## 1. The preregistration is now TAGGED — this changes how you work

`prereg-v1` was tagged and pushed on **9 Nov 2026** (commit `1293a1e`), after both members
confirmed that no feature had been correlated with a quiz score. **That question is
settled; you do not need to answer it.**

What it means from here:

- **Every result you produce is confirmatory**, provided you follow the frozen plan. That
  is the status R-004 lost by being run two days too early — don't waste it.
- **Any change to hypotheses, exclusions, metrics, splits or models goes in
  `docs/deviations.md`** *before* you report results that depend on it. One row: what
  changed, why, expected effect, which decision row. This is not bureaucracy — an
  undocumented change after a public, timestamped tag is the one thing that would discredit
  the whole freeze.
- **`results/folds.json` is frozen.** It currently covers Exp 1 only: 25 learners, 120
  rows. **Adding Exp 2 means rebuilding it, and that is a deviation row.** Expected and
  fine — just write it down when you do it.
- The margins are fixed: H0a ±50 ms with F1 ≥ 0.95, H1b ±0.10, H4c −0.10, and the
  exclusion thresholds in §2 of the preregistration. **Do not change one because a test
  fails.** `§1a` already states we expect H1b and H4c to come out inconclusive at this
  sample size, and commits us to reporting that as inconclusive.

**Still outstanding and genuinely yours:** 25 of 31 decision-log rows are `Proposed` with
no initials. Read `docs/decision_log.md` and initial what you agree with. Neither of us may
mark a row `Decided` alone. D-24 through D-30 are all from the last few days and none have
been reviewed by anyone but their author.

---

## 2. Where the project is

| | |
| --- | --- |
| Notebooks | `00_inventory`, `05_targets`, `06_folds`, `10_eye_preproc`, `50_features_individual`, `60_classical_models` |
| Runs | R-001 … R-011 in `docs/run_registry.csv` |
| Decision rows | 31 (D-00 … D-30), **25 still Proposed** |
| Inference rows | 2 |
| Tag | **`prereg-v1`, on origin** |
| CI | GitHub Actions: `pytest` + a notebook-parse check on every push to `main` and every PR |

**Done:** Exp 1 eye pipeline, RQ0/H0b, quiz targets, exclusions, folds, individual eye
features. `60_classical_models` is written and gated on the tag but **has not been run**,
so there are no RQ1/RQ2 numbers yet.

**Not started:** EEG, ECG, respiration, and Exps 2–5 — not downloaded.

### 2.1 What was done, 6–11 Nov

**Repo and infrastructure.** `git init` on the skeleton, pushed to `main`. Local `pytest`
became unusable mid-project (Windows Smart App Control blocks pandas' binaries), so the
suite runs in **GitHub Actions** instead, along with a notebook-parse check. That has
already caught a broken notebook before it reached Colab.

**Eye pipeline — four runs, because the first two were wrong.**

| Run | What happened |
| --- | --- |
| R-001 | Ran clean and produced **nonsense**: 2.7 saccades/min, 82-second fixations. It thresholded the sidecar's `vdx`/`vdy`, which are smoothed below the saccade threshold. Half the files errored — `_pupil_` files have no `x` column. |
| R-002 | Gaze converted to degrees and differentiated; pupil files paired. Sensible for the first time. |
| R-003 | Superseded by a rerun; kept for the audit trail. |
| **R-004** | Current. px/deg from sourced screen geometry rather than a data estimate. |

**The RQ0 result (R-004)** — Exp 1, 27 learners, 263 recordings:

| Metric | ses-01 | ses-02 | t(26) | p | d_z |
| --- | --- | --- | --- | --- | --- |
| Saccades/min | 138.0 | 93.2 | 6.18 | 1.6e-06 | 1.19 |
| Blinks/min | 1.25 | 2.90 | −3.04 | .0054 | −0.58 |
| Fixations/min | 131.8 | 84.1 | 7.02 | 1.9e-07 | 1.35 |
| Median fixation | 245 ms | 332 ms | −4.82 | 5.4e-05 | −0.93 |

Two reasons to trust it. **The blink numbers reproduce the 14 Oct quick check exactly**
(1.25 → 2.90, t = 3.04) — and blinks come from pupil, so they are independent of the px/deg
calibration, the one free parameter. And the saccade rates sit close to the **authors' own
derivative counts** (136 → 89) rather than our October detector (174 → 131). H0b holds on
all four metrics. **Marked Exploratory**, because the tag did not exist when it ran.

**Calibration.** `x`/`y` are pixels, so saccade detection needs px/deg. Estimating it from
the data gave a median of 34.31 but scattered 7.6–117.6 across recordings — unusable. The
preprint gives a 27″ monitor at ~60 cm; with an *inferred* 1920×1080 that yields **33.64
px/deg**, 2% from the data estimate. Agreement from two unrelated routes is the evidence;
the resolution itself is still unsourced (D-26).

**Targets (R-006).** Memory items only (D-27). Per-video means **0.640 / 0.557 / 0.600 /
0.597 / 0.785**, reproducing the 14 Oct figures exactly; video 5 near ceiling at 38.7% of
learners ≥ 90%. `is_correct` verified to equal `answer == correct_answer` on **all 3,286
items**, so the target is reproducible from raw responses.

**Exclusions (R-010).** The preregistered >50%-invalid rule had never been implemented.
Measured on **pupil** (D-30) — gaze reads 0.00 invalid everywhere because the released data
is already interpolated — it removes **15 of 135 recordings**, including one at 99.9%
invalid with zero saccades. sub-22 and sub-31 lose every video. `results/exclusions.csv`
now exists, as preregistration §2 requires.

**Folds (R-011).** `results/folds.json`: **120 rows, 25 learners**, 5-fold grouped by
learner × 10 repeat seeds, plus leave-one-video-out. Verified independently: no group spans
two folds in its own scheme.

### 2.2 Decision rows awaiting your initials

| Row | Subject |
| --- | --- |
| D-22 | Python 3.12 and the resolved package versions |
| D-23 | The repo is public, not private as D-19 says |
| D-24 | Estimating px/deg from data (superseded by D-26, kept as a cross-check) |
| D-25 | Blinks from pupil dropout |
| D-26 | px/deg from screen geometry; resolution inferred |
| D-27 | Target is memory items only |
| D-28 | LOVO holds out a video, not a learner — its numbers are not comparable |
| D-29 | `ses-01` is the attend session (inferred, not sourced) |
| D-30 | The eye exclusion rule is measured on pupil |

---

## 3. Working rules

1. **Raw data is never edited.**
2. **Any choice that could change a result goes in `docs/decision_log.md` _before_ it is
   used**, as a new `D-xx` row, status `Proposed`. Never mark a row `Decided` yourself,
   never overwrite one — add a new row and mark the old `Revisited`.
3. **Every result goes through `bbbd.runlog`**, which stamps it with a run ID, git hash,
   config hash and seed. A number may appear in the report only if it has a run ID.
4. **Conclusions go in `docs/inference_log.md`** with the run ID. Observation = numbers
   only. Conclusion = one sentence a reviewer could disagree with. Name at least one
   alternative explanation.
5. **After the tag, changes go in `docs/deviations.md`.** See §1.
6. Citations go in `docs/references.bib` on first use. **Never invent a reference or a
   dataset fact.** Verified facts go in `docs/dataset_inventory.md`; anything else is
   marked UNVERIFIED.
7. Branches `b/<topic>`, pull request to `main`. (A merged directly while working alone;
   now that you are back, PRs again — and CI must be green before merging.)
8. Commit messages name the row or run: `D-31: ECG inversion check`, `R-012: ECG Exp 2`.
9. ISC references and CorrCA weights use **training-fold learners only**. Deep encoders
   retrained per outer fold.

Settings live in `config.yaml`; nothing hard-coded in notebooks. Data never enters git.

---

## 4. Hard-won facts about this dataset

Every one cost us at least one wasted run. **Assume Exps 2–5 hold equivalent surprises and
run `00_inventory` before writing any preprocessing code.**

### Things that were not what the filename or docs said

- **Gaze `x`/`y` are screen pixels, not degrees** — despite files named
  `..._gaze_visualangle_eyetrack.tsv.gz`. Measured x spanning −377…1259.
- **`vdx`/`vdy` are smoothed.** Genuinely deg/s, but the 99.9th percentile is 26 deg/s,
  *below* the 30 deg/s saccade threshold. Thresholding them gave 2.7 saccades/min. **If
  any EEG or ECG file ships a pre-derived channel, suspect it the same way.**
- **Two raw files per recording**, paired on `sub`/`ses`/`task`. A naive glob picks up both
  and the second has no `x` column.
- **`derivatives/` sits inside the experiment folder and has no JSON sidecars**, so
  `io.read_physio_tsv` cannot read those files. Filter `"derivatives" not in f.parts`.
- **`ses` is the condition; `task` is the video** (`task-stim01`…`stim05`). Our first
  fallback guessed `task` was the condition, which would have run the attention contrast
  across *videos* and produced plausible nonsense.
- **Join keys differ between tables.** Eye files say `task-stim01`; the quiz table says
  integer `1`. Convert, then **assert the key sets intersect** — we shipped a run where a
  dtype mismatch reported 0 learners in common.
- **Quiz columns** are `participant_id, stimulus_id, question_type, question_no, answer,
  correct_answer, is_correct`. `question_type` is `memory` or `domain`.
- **Count scored items, not rows.** `groupby().size()` counts unanswered questions too and
  silently deflates a proportion; use `.count()`.

### Verified apparatus facts (bioRxiv 10.1101/2025.04.29.651259, Procedure)

- 27″ monitor, ~60 cm viewing distance → 59.77 cm wide, ~53° of visual angle.
- **EyeLink 1000, 35 mm lens, recorded at 500 Hz. All released signals down-sampled to
  128 Hz.** Confirm 128 Hz from the sidecar for *every* modality anyway — this is the
  number most likely to differ for BDF files.
- Screen resolution is stated in **no source we could find**; 1920×1080 is inferred (D-26).
- The authors convert to degrees with the EyeLink's **per-sample resolution columns**,
  absent from the released files — so any single px/deg constant is an approximation.
- Blinks/saccades detected by "the eye tracker's algorithm used when saving to BDF files";
  **no velocity threshold stated**. Blinks and artefacts ±100 ms linearly interpolated.
  Pupil outliers at 4×IQR of a 200 ms-median-detrended signal.
- Exp 1 ran the **attentive session first**, distracted second. The `ses-01`/`ses-02` label
  mapping is *not* stated anywhere; we infer ses-01 = attend (D-29) from blink rates.

### Open puzzles

- The 14 Oct check recorded 3.03% median invalid gaze; we measure 0.00. Probably different
  channels, but unresolved.
- **Participant `99`** appears in the Exp 1 quiz (others run 02–31), likely a pilot record.
  Harmless for Exp 1 (no gaze). **Check for it in Exps 2–5** — there it may carry features.

---

## 5. Your track, step by step

### 5.0 Environment

**Best: the Ubuntu workstation** (HP Z2, i9-14900K 32 threads, 32 GB RAM, RTX 4000 Ada
20 GB, 123 GB free on `/home`). Python 3.12.3, matching D-22. The GPU means the RQ4
deep-learning track can run there too.

```bash
cd ~ && git clone https://github.com/pbhatt0022/bbbd_mml.git && cd bbbd_mml
python3 -m venv .venv && ./.venv/bin/pip install -e ".[dev]"
./.venv/bin/python -m pytest -q
```

If `venv` fails: `sudo apt install -y python3-venv python3-pip unzip`.

**Colab** works but has sharp edges — see §7. **Windows is unusable**: Smart App Control
blocks newly-downloaded unsigned binaries, so pandas, pyarrow and neurokit2 all fail to
import in any fresh environment. Turning it off is irreversible. Don't.

### 5.1 Download Experiment 2 (do this first — everything waits on it)

| File | Zipped | md5 |
| --- | --- | --- |
| experiment2.zip | 5.6 GB | `e9671316f97e1c3ec1d86a03e0a1ab28` |
| experiment3.zip | 8.0 GB | from the Zenodo API |
| experiment4.zip | 5.5 GB | " |
| experiment5.zip | 7.0 GB | " |

```bash
URL=https://zenodo.org/api/records/19241964/files/experiment2.zip/content
wget -c -O /tmp/experiment2.zip "$URL"            # -c resumes; 5.6 GB transfers do drop
md5sum /tmp/experiment2.zip                       # MUST equal the md5 above
mkdir -p ~/MML_BBBD/01_data_raw
unzip -q /tmp/experiment2.zip -d ~/MML_BBBD/01_data_raw
rm /tmp/experiment2.zip
```

**Verify the md5 before unzipping.** A truncated BDF surfaces much later as a baffling
preprocessing error, and you will spend hours on it.

Then point the code at it — **in `config.yaml`, not in a notebook**:
`load_config(data_root="/home/<you>/MML_BBBD")`, or edit `paths.data_root`.

### 5.2 `00_inventory` on Exp 2 — before any preprocessing

Your notebook, already written. **Do not skip this.** Every assumption we made about Exp 1
without checking turned out wrong. It should tell you, and you should record in
`docs/dataset_inventory.md`:

- participant count against `participants.tsv`, and whether a `99`-style pilot id exists
- sessions present, and **which session is attend** — do not assume Exp 1's mapping carries
- BDF sampling rate (`raw.info['sfreq']`) — the paper says 128 Hz, verify it
- **exact EEG, EOG, ECG and respiration channel names**, which `config.yaml`'s
  `eeg.regions` lists for BioSemi 64 and which may not match
- whether `derivatives/` exists and what it holds
- quiz file layout, and whether `question_type` has the same values

### 5.3 ECG first (`30_ecg_preproc`) — not EEG

ECG is a fraction of the work and gives you a real second modality quickly, which unblocks
the fusion hypotheses. Do it before EEG.

```python
from bbbd import ecg
peaks = ecg.detect_rpeaks(signal, sfreq)              # handles lead inversion internally
rr    = ecg.clean_rr(peaks, sfreq,
                     rr_min_ms=cfg["ecg"]["rr_min_ms"],
                     rr_max_ms=cfg["ecg"]["rr_max_ms"])
feats = ecg.hr_features(rr)                           # mean HR, HR SD, RMSSD
```

**H0a falls straight out of this** — `ecg.match_beats(ours, ref, sfreq, tol_ms=50)` against
the authors' hand-corrected peaks returns precision, recall, F1 and median timing error.
Supported if **F1 ≥ 0.95 per recording**. That is a preregistered confirmatory test you can
deliver on day one of your track.

Watch for: **lead polarity** (`detect_rpeaks` calls `nk.ecg_invert`, but log whether it
fired — a flipped lead that goes undetected gives plausible, wrong peaks), and the
preregistered exclusion **< 80% of beats detectable**.

### 5.4 EEG V1 (`20_eeg_preproc`)

```python
from bbbd import eeg
raw = eeg.load_bdf(path, eog_channels=[...], misc_channels=[...])   # names from 00_inventory
print(raw.info["sfreq"])                                            # log it
raw, qc = eeg.preprocess(raw, cfg["eeg"], seed=cfg["seeds"]["global"])
```

`preprocess` runs the whole V1 chain and returns a QC report: `bad_channels`,
`bad_channel_frac`, `bad_time_frac`, `eye_artifact`, `bad_segments_1s`. **Save that report
per recording** — the preregistered exclusions are >20% bad channels or >10% bad time, and
the report is what applies them. Exp 1 taught us an exclusion rule nobody implements is
dead text.

Things that will bite:

- **D-20: average reference goes _before_ EOG regression.** Already handled inside
  `preprocess`; don't reorder it. MNE's `EOGRegression` refuses to run without a reference.
- **`set_biosemi64` assumes BioSemi 64 names.** If `00_inventory` shows different names,
  `config.yaml`'s `eeg.regions` lists are wrong too, and `features.eeg_features` will
  silently produce fewer regions. Fix both, log a decision row.
- **16 Hz noise in Exps 4–5** (D-13). `eeg.has_peak(raw, 16)` detects it per recording;
  `filter_raw` notches it when `notch_16hz_if_detected`. **Log which recordings were
  notched** — it is a per-recording difference in processing.
- **`eog_regression` silently no-ops without EOG channels.** The QC report's
  `eye_artifact` field says `"none (no EOG channels found)"` — check it, don't assume.
- RQ3 (V3, ICA instead of regression) is `cfg["eeg"]["eye_artifact"] = "ica"`. **D-18 lists
  RQ3 as the second thing to drop if time runs short.** With five days left, treat it as
  optional.

### 5.5 Respiration (`40_resp_preproc`), Exps 4–5 only

```python
from bbbd import resp
feats = resp.resp_features(signal, sfreq)    # rate mean, rate SD, plausibility flag
```

`resp_rate_plausible` checks 8–25 breaths/min. Lowest priority of your four.

### 5.6 RQ0 validation for your modalities

- **H0a**: beat-matching F1 vs the authors' peaks (§5.3)
- **H0b, EEG half**: posterior alpha higher when distracted, paired per learner. The eye
  half is done (R-004); yours completes it.

Write the inference-log row with the run ID, and say which fold scheme any number used.

### 5.7 Feeding the models

Your features join Member A's on `experiment, subject, video, session, variant`
(`features.KEYS`). Then:

- **Never build your own folds.** `cv.load_folds("results/folds.json")`. Every model shares
  them so comparisons are paired. Rebuilding silently unpairs everything — and after the
  tag, rebuilding is a deviation row.
- **ISC and CorrCA weights: training-fold learners only** (D-11). `isc.py` takes a
  `train_mask`. Precomputing ISC over all learners leaks the test fold into the features
  and invalidates the result — this is the single easiest way to ruin the project, and it
  looks like nothing is wrong.
- The two fold schemes are **not comparable** (D-28). Always name the scheme.

---

## 6. Suggested five-day shape

Given one person has been working and five days remain, breadth is the thing to cut, not
rigour. D-18's drop order is S1 → RQ3 → leave-one-video-out.

| Day | Aim |
| --- | --- |
| Tue 11 | Download Exp 2, run `00_inventory`, record facts in the inventory |
| Wed 12 | ECG Exp 2 end to end, including H0a. One confirmatory result banked. |
| Thu 13 | EEG V1 Exp 2, QC report, exclusions applied |
| Fri 14 | EEG/ECG features, join to A's folds, RQ1 with two modalities |
| Sat 15 | Stats, figures, report |

**Exps 3–5 are almost certainly out of reach.** A thorough two-experiment study with
honest limitations will read better than five half-done. If you disagree, say so early —
that is a scope decision for both of you, and it belongs in the decision log.

---

## 7. Workflow gotchas

- **Colab serves stale notebooks from GitHub.** It bit us three times — you push a fix,
  reopen, and get the old version. If a fix "didn't work", check you are running it.
  `https://raw.githubusercontent.com/pbhatt0022/bbbd_mml/main/notebooks/<name>.ipynb`
  always serves current `main` and is immune. Download and **File → Upload notebook**.
- **A PEP 660 editable install is invisible to a running kernel** (its `.pth` is read only
  at interpreter start), so the setup cells add `src/` to `sys.path` directly.
- **Pushing from Colab** needs a fine-grained token in Colab Secrets named `GH_TOKEN`
  (Contents: read and write, this repo only), toggled on per notebook. The push cells fetch
  and rebase first, because `main` moves while a notebook runs.
- **Run IDs are per execution, not per kept result.** Rerunning burns an ID, so the
  sequence has gaps. That is correct; do not "clean it up".
- **CI is your safety net.** Watch it — it has already caught a notebook whose cells were
  syntactically broken.
- Small results are versioned in `results/`; large outputs go to Drive `04_results` via
  `runlog.start_run(..., large_outputs=True)`.
- **A failed push does not lose a run** — outputs are mirrored before pushing.

---

## 8. For your LLM assistant, specifically

- **Do not invent dataset facts, citations, or column names.** Every guess we made about
  this dataset was wrong — the filenames, the units, the entity meanings, the join keys.
  Print the real columns, assert the mapping, fail loudly. `05_targets` cell 2 and
  `10_eye_preproc` cell 1b are the pattern to copy.
- **Assert, don't assume.** Every assumption that cost us a run would have been caught by
  one assert. Sampling rate, channel names, key overlap, value ranges.
- **Sanity-check magnitudes against physiology.** R-001 "worked" for a whole run while
  reporting 82-second fixations. Heart rate should be 50–100 bpm; breathing 8–25/min;
  fixations 200–400 ms. If a number is physically absurd, stop.
- **Put logic in `src/bbbd/`, not in notebook cells** (notebooks README rule 5), and leave a
  test behind. Notebooks call functions and show results.
- **Do not mark decision rows `Decided`.** Propose; the humans agree.
- **The preregistration is tagged.** Changing an exclusion, metric, split or model now
  requires a row in `docs/deviations.md` first. Do not quietly adjust a threshold because a
  test fails.
- **Never precompute ISC or CorrCA outside the training fold.**
- When something looks wrong, **say so rather than working around it**.

---

## 9. Questions for the two of us

- Initial the 25 Proposed decision rows, D-24 … D-30 especially — none have been reviewed
  by anyone but their author.
- Is two experiments the right scope? If so, record it as a decision row now rather than
  discovering it on Saturday.
- `60_classical_models` is written and gated but **unrun** — A should run it today so we
  know whether eye features predict anything before building fusion on top.
- Does the professor know we were briefly down to one person?
