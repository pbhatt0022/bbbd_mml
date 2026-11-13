I'm continuing work on a university course project. The repo is at `D:\bbbd_mml` (also on
GitHub at https://github.com/pbhatt0022/bbbd_mml, public). I'm "Member A"; my teammate is
"Member B".

**Before doing anything else, read these four files in this order:**

1. `docs/PROJECT_STATE.md` — canonical status: what's done, the actual numbers, the
   dataset traps, the rules. Everything in it is checkable against the repo.
2. `README.md` — the project and its nine working rules.
3. `docs/decision_log.md` — 31 recorded decisions. 25 are still `Proposed`.
4. `docs/inference_log.md` — the three results we have concluded anything from.

**Context in one paragraph.** DATA404 Multimodal Machine Learning final project, predicting
learning from educational videos using the public BBBD dataset (EEG, ECG, eye tracking,
respiration, plus quizzes). Submission **Mon 16 Nov 2026**, presentation Wed 18 Nov. The
eye-tracking track for Experiment 1 is complete, validated and frozen under a tagged
preregistration, and has produced one confirmatory result. The EEG/ECG/respiration track
(Experiments 2–5) has working code on PR #1 but **no registered results**. The
deep-learning track (RQ4) has not been started. Report, slides and figures: not started.

**The rules that bind you here, which are unusual and non-negotiable:**

- The preregistration is **tagged** (`prereg-v1`, on origin). Any change to hypotheses,
  exclusions, metrics, splits or models needs a row in `docs/deviations.md` **before**
  reporting results that depend on it. **Never adjust a threshold because a test failed.**
- Every choice that could change a result goes in `docs/decision_log.md` as a new `D-xx`
  row, status `Proposed`, **before** it is used. **Never mark a row `Decided`** — the two
  humans agree those.
- Every result goes through `bbbd.runlog`, which stamps a run ID. **A number may appear in
  the report only if it has a run ID.**
- **Never invent a dataset fact, a column name or a citation.** Print the real columns,
  assert the mapping, fail loudly. Every assumption we made about this dataset without
  checking turned out to be wrong — filenames, units, entity meanings, join keys.
- Logic lives in `src/bbbd/` with a test; notebooks call functions and show results.
- `results/folds.json` is frozen (120 rows, 25 learners). Load it with `cv.load_folds`;
  never build your own folds.

**The headline result so far (R-012, confirmatory):** eye features predict quiz score on
unseen learners at ρ = +0.149, permutation p = .026 — but the 95% CI is [−0.104, +0.411]
and R² is −0.073. H1a is supported on the preregistered criterion, yet the effect is weak
and imprecise. Do not quote the p-value without the CI. `docs/inference_log.md` explains
why the permutation and the bootstrap disagree.

**Environment warning:** local Windows cannot run this code — Smart App Control blocks
newly-downloaded unsigned binaries, so pandas, pyarrow and neurokit2 fail to import in any
fresh environment, and local `pytest` does not work. **GitHub Actions CI is the only
working test gate.** Do not suggest disabling Smart App Control; it cannot be re-enabled
without reinstalling Windows. Notebooks run on Colab — and Colab serves stale notebooks
from GitHub, so always fetch via
`https://raw.githubusercontent.com/pbhatt0022/bbbd_mml/main/notebooks/<name>.ipynb` and use
File → Upload notebook.

**What I need help with next**, in priority order:

1. **The report and figures.** Three days left, nothing written. `85_statistics` and
   `90_figures` don't exist. We have R-004 and R-012 to write up.
2. **Getting Experiment 2 ECG results registered.** The code is on PR #1 and
   `ecg.match_beats` yields H0a — a preregistered confirmatory result — from one run.
3. **Deciding and recording the scope cut.** RQ3 and RQ4 are probably unreachable. That
   needs a decision row, and the professor should be told, since D-05 asked for deep
   learning.

Start by reading those four files and telling me what you think the state is, so I can
check your understanding matches mine before you change anything.
