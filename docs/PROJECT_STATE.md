# Project state — read this first

**Canonical status of `bbbd_mml`. Updated 13 Nov 2026.** If you are an assistant picking
this project up cold, read this file, then `README.md`, then `docs/decision_log.md`.
Everything here is checkable against the repo; nothing is from memory.

**Submission Mon 16 Nov 2026. Presentation Wed 18 Nov.**

---

## 1. One-paragraph summary

A DATA404 course project predicting learning from educational videos using the public BBBD
multimodal dataset (EEG, ECG, eye tracking, respiration + quizzes). The eye-tracking track
for Experiment 1 is complete, validated and frozen under a tagged preregistration, and has
produced its headline result (R-012, below). The EEG/ECG/respiration track for Experiments
2–5 has working code but **no registered results yet**. The deep-learning track (RQ4) has
not been started. Report, slides and figures have not been started.

---

## 2. Hard facts, verifiable from the repo

| | |
| --- | --- |
| Preregistration | **Tagged `prereg-v1`**, on origin, commit `1293a1e`, 9 Nov 2026 |
| Registered runs | **R-001 … R-012** in `docs/run_registry.csv` |
| Decision rows | **31** (D-00 … D-30), **25 still `Proposed`** with no initials |
| Inference rows | **3** (pre-repo 14 Oct, R-004, R-012) |
| Deviations | 1 (DV-01, resolved) |
| Notebooks | **6 of 18 planned**: `00`, `05`, `06`, `10`, `50`, `60` |
| Open PRs | **#1**, `b/exp2-physiology` → `main` |
| CI | GitHub Actions: `pytest` + a notebook-parse check, on push to `main` and every PR |

Verify any of this with:

```bash
git tag -l; tail -3 docs/run_registry.csv
grep -c '^| D-' docs/decision_log.md
grep -c '^| D-[0-9]* | Proposed' docs/decision_log.md
ls notebooks/
```

---

## 3. Results so far

### R-004 — RQ0 / H0b, Exp 1 eye (Exploratory)

Attend vs distract, 27 learners, 263 recordings. Saccades 138.0 → 93.2 /min, t(26) = 6.18,
p = 1.6e-06; blinks 1.25 → 2.90, t = −3.04, p = .0054; median fixation 245 → 332 ms.

**Why it is trustworthy:** the blink figures reproduce a 14 Oct pre-repo check *exactly*,
and blinks come from pupil, so they are independent of the px/deg calibration — the one
free parameter. Saccade rates also sit close to the authors' own derivative counts
(136 → 89).

**Marked Exploratory** because it ran two days before the tag existed. That status cannot
be recovered.

### R-012 — RQ1 / H1a and RQ2 / H2 (individual half), Exp 1 eye (**Confirmatory**)

25 learners, 120 rows, 8 individual-only features, target `quiz_z`.

| Model | ρ | 95% CI | R² | p (perm) | Status |
| --- | --- | --- | --- | --- | --- |
| **ridge** (primary) | **+0.149** | **[−0.104, +0.411]** | **−0.073** | **.026** | confirmatory |
| rf | +0.231 | [+0.023, +0.415] | +0.005 | — | exploratory |
| mlp | +0.037 | [−0.252, +0.361] | −0.590 | — | exploratory |

**H1a is supported on the preregistered criterion** (permutation p < .05, Holm-corrected).
**But read it carefully:**

- **The permutation test and the bootstrap CI disagree, and both are right.** The
  permutation asks whether ρ beats a shuffled-target null — it does. The bootstrap asks how
  precisely ρ is known from 25 learners — barely. **Never report the p-value without the
  CI.**
- **R² is negative**: the model predicts score magnitude *worse* than the training mean.
  The signal is ordinal only.
- **Per-repeat ρ ranged +0.006 to +0.305.** A single 5-fold split could have shown nothing.
  This is why 10 repeats were preregistered.
- **RF scored higher than ridge but is exploratory and unpermuted.** Per preregistration
  §4.5 this is *not* a model comparison and must not be presented as one.
- Leave-one-video-out ridge gave ρ = +0.374, but it holds out a *video* and keeps the same
  learners in train and test (D-28). **Not comparable. Always name the scheme.**

Full detail and caveats: `docs/inference_log.md`.

---

## 4. What is done, and what is not

**Done and frozen**
- Exp 1 eye: preprocessing, RQ0 validation, targets, exclusions, folds, features
- Preregistration tagged; margins fixed; §0 disclosure recorded
- Infrastructure: `runlog` provenance, CI, 12 registered runs

**Code written, never run**
- `src/bbbd/ecg_batch.py`, `src/bbbd/eeg_batch.py` (+ `batch_runlog.py`) on PR #1. Tests
  pass. **No Exp 2 results exist** — the data lives on Member B's machine, not in the repo.

**Not started**
- RQ3 (ICA variant) — optional per D-18
- RQ4 (deep learning) — notebooks `70`–`73`. **The professor explicitly required a deep
  learning component (D-05).**
- `45_rq0_validation`, `80`, `85_statistics`, `88`, `90_figures`
- Report, slides, figures
- Experiments 3, 4, 5 (not downloaded; 8.0 / 5.5 / 7.0 GB)

Rough completion: **foundations ~90%, results ~25%, write-up 0%.**

---

## 5. Rules that bind any future work

From `README.md`. An assistant working here must follow these.

1. Raw data is never edited.
2. **Any choice that could change a result goes in `docs/decision_log.md` _before_ use**, as
   a new `D-xx` row with status `Proposed`. **Never mark a row `Decided`** — the humans
   agree. Never overwrite a row; add a new one and mark the old `Revisited`.
3. **Every result goes through `bbbd.runlog`**, which stamps a run ID, git hash, config hash
   and seed. **A number may appear in the report only if it has a run ID.**
4. Conclusions go in `docs/inference_log.md` with the run ID. Observation = numbers only;
   conclusion = one sentence a reviewer could disagree with; name at least one alternative
   explanation.
5. **The preregistration is tagged.** Any change to hypotheses, exclusions, metrics, splits
   or models now requires a row in `docs/deviations.md` *before* reporting results that
   depend on it. **Do not adjust a threshold because a test failed.**
6. Citations go in `docs/references.bib` on first use. **Never invent a reference or a
   dataset fact.** Verified facts go in `docs/dataset_inventory.md`; anything else is marked
   UNVERIFIED.
7. Branches `a/<topic>` (Member A) and `b/<topic>` (Member B); pull request to `main`; CI
   green before merge.
8. Commit messages name the row or run: `D-31: ...`, `R-013: ...`.
9. **ISC references and CorrCA weights use training-fold learners only** (D-11). Deep
   encoders retrained per outer fold.

Also: settings live in `config.yaml`, never hard-coded in notebooks. Data never enters git.
Logic lives in `src/bbbd/` with a test; notebooks call functions and show results.

**`results/folds.json` is frozen** — 120 rows, 25 learners, 11 schemes. Every model loads it
with `cv.load_folds`. Rebuilding it is a deviation row.

---

## 6. Dataset traps — each cost a wasted run

Full list in `docs/dataset_inventory.md`. The ones that matter most:

- **Gaze `x`/`y` are screen pixels, not degrees**, despite filenames saying
  `gaze_visualangle`. Convert with px/deg before detecting saccades.
- **`vdx`/`vdy` are smoothed** — 99.9th percentile 26 deg/s, *below* the 30 deg/s threshold.
  Thresholding them produced 2.7 saccades/min and 82-second fixations (R-001, wrong).
  **Suspect any pre-derived channel the same way.**
- **Two raw files per recording** (`_gaze_visualangle_`, `_pupil_`); a naive glob gets both
  and the second has no `x` column.
- **`derivatives/` is inside the experiment folder and has no JSON sidecars.** Filter
  `"derivatives" not in f.parts`.
- **`ses` is the condition; `task` is the video.** Guessing the other way round runs the
  attention contrast across videos and yields plausible nonsense.
- **Join keys differ**: eye files say `task-stim01`, the quiz table says integer `1`.
  Convert, then *assert* the key sets intersect.
- **Exp 1 gaze reads 0.00 invalid** (already interpolated); pupil carries the real dropout.
  The exclusion rule is measured on **pupil** (D-30).
- Screen: 27″ at ~60 cm (sourced); **resolution 1920×1080 is inferred** (D-26) giving
  33.64 px/deg.
- `ses-01 = attend` is **inferred** from blink rates (D-29), not stated in any source.

---

## 7. Environment

- **Member B's Ubuntu workstation** (i9-14900K, 32 GB, RTX 4000 Ada, Python 3.12.3) is the
  best environment and holds the Exp 2 data.
- **Colab** works. Two traps: it **serves stale notebooks from GitHub** (use
  `https://raw.githubusercontent.com/pbhatt0022/bbbd_mml/main/notebooks/<name>.ipynb` and
  File → Upload notebook), and a PEP 660 editable install is invisible to a running kernel,
  so setup cells add `src/` to `sys.path` directly.
- **Windows is unusable**: Smart App Control blocks newly-downloaded unsigned binaries, so
  pandas, pyarrow and neurokit2 fail to import in any fresh environment. Local `pytest`
  does not run; **CI is the only working test gate.** Do not disable Smart App Control —
  it cannot be re-enabled without reinstalling Windows.
- Pushing from Colab needs a fine-grained token in Colab Secrets named `GH_TOKEN`.

---

## 8. Highest-value next actions

1. **Write the report and figures.** Three days left and nothing is written. `85_statistics`
   and `90_figures` do not exist. You cannot write results you have not generated, but you
   now have R-004 and R-012 to write about.
2. **Run `ecg_batch.py`** on Member B's machine — `ecg.match_beats` yields H0a, a
   preregistered confirmatory result, from one run.
3. **Decide and record the scope cut.** RQ3 and RQ4 are almost certainly unreachable. Record
   it as a decision row *now* rather than discovering it on Sunday, and tell the professor,
   since D-05 asked for deep learning.
4. **Initial the 25 Proposed decision rows.** D-24 … D-30 have been reviewed by nobody but
   their author.
5. Merge PR #1 once reviewed.
