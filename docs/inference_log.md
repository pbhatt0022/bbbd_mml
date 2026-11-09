# Inference Log

What we **concluded** from each result, kept separate from the Decision Log (what we chose before running). One row per conclusion. Every row needs a run ID from `docs/run_registry.csv`; a conclusion without a run ID is not reported.

**Confidence:** High = replicated or large effect with tight CI; Medium = clear but one run or wide CI; Low = suggestive or exploratory only.
**Type:** Confirmatory (a preregistered hypothesis H0–H4 with ridge) or Exploratory (everything else).

| Date | Run ID | RQ / H | Type | Observation (numbers) | What we conclude | Confidence | Caveats / alternative explanations | Logged by |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| 14 Oct 2026 | (pre-repo) | RQ0 / H0b | Exploratory | Exp 1, N = 27, own I-VT detector (> 30°/s) on 128 Hz gaze: saccades 174 → 131 per min attend → distract, t(26) = −4.77, d_z = −0.92, p < .001. Blinks 1.25 → 2.90 per min, t = 3.04, p = .005. Authors' saccade events: 136 → 89 per min, t(26) = −7.28 (matches paper). Per-recording agreement of our vs authors' saccade counts ρ = 0.53 | Our pipeline reproduces the direction of the distraction effects; our statistics code reproduces the paper's t exactly | Medium | Per-recording agreement only moderate (128 Hz is coarse for saccades); our blink detector undercounts. Run with `src/bbbd_quickcheck.py` on Drive, before the repo existed, so no run ID: **rerun through `bbbd.runlog` and replace this row** | A |

## How to write a row

- Observation = numbers only (estimate, CI, p, n). Conclusion = one sentence a reviewer could disagree with.
- Name at least one alternative explanation (e.g. video difficulty, artefact, small N).
- If a later run changes a conclusion, add a new row that names the old one; do not edit the old row.

## Pending: row for the RQ0 eye rerun (`10_eye_preproc.ipynb`)

**Not a result.** This is a fill-in template, deliberately kept out of the table above so a
placeholder can never be read as a number. Move it into the table only once the notebook has
actually run and every `<…>` is replaced. If the run does not happen, delete this section.

Every `<…>` below is printed by the notebook or written to
`results/<run_id>_eye_rq0_exp1/rq0_eye_exp1.json`.

```
| <date> | <R-0xx> | RQ0 / H0b | Confirmatory | Exp 1, N = <n_subjects> learners,
<n_recordings> recordings (<n_excluded> excluded at > 50% invalid). Own I-VT detector
(> 30°/s) on <sfreq> Hz gaze, saccades from sidecar vdx/vdy: saccades <mean_A> → <mean_B>
per min attend → distract, t(<df>) = <t>, d_z = <d_z>, p = <p>. Blinks <mean_A> → <mean_B>
per min, t = <t>, p = <p>. Agreement with authors' saccade counts: <ρ or "not computed,
derivative layout unknown"> | <conclusion: one sentence a reviewer could disagree with —
does our from-raw pipeline reproduce the direction of the distraction effects?> |
<High / Medium / Low> | Blinks detected from gaze track-loss, not pupil (Exp 1 has no pupil
column), so blink counts undercount; 128 Hz is coarse for saccade timing; attend/distract is
a condition contrast, not learning. <Add any alternative explanation the numbers suggest> | A |
```

Then, in the same commit:

1. Append to the **14 Oct 2026** row's caveat cell: `Replaced by <R-0xx>.` Do not edit its
   numbers or delete it — the log's own rule is that old rows are never overwritten.
2. Set **Type** above to `Confirmatory` only if `prereg-v1` was tagged before the run.
   If the run happened first, it is `Exploratory`, and say so rather than backdating.
3. If the H0b direction does **not** match the authors, that is a finding, not a bug to hide:
   log it, then check the condition-entity mapping from cell 1b before concluding anything.
