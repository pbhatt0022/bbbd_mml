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
