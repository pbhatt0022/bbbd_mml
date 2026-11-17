# Presentation guide

For the DATA404 final project presentation. Covers all 25 slides of
`slides/slides.pdf`, who presents what, what to say on each, and what is
likely to be asked.

Written on the assumption that the reader knows nothing about the work. Every
number quoted here is in the deck or the report; nothing new is introduced.

---

## 1. The one-paragraph version

Learning from educational videos has been predicted from EEG — brain activity
recorded at the scalp. EEG is expensive and intrusive. We asked whether eye
tracking and ECG (heart activity) can do the same job, using a public dataset
of learners watching five videos and then taking a quiz. The honest answer is
that **we could not show the cheaper sensors match EEG, and combining sensors
did not help** — but EEG itself predicted only weakly, so this is a result
about our pipeline on this sample, not a verdict on cheap sensors generally.
Along the way we found and disclosed three defects in our own analysis code,
and we proved that a brain-activity difference between attentive and
distracted viewing is genuine rather than an eye-movement artefact.

**If you remember one sentence:** *we built a traceable pipeline, validated it
against published effects, and reported weak results honestly rather than
overclaiming.*

---

## 2. Who presents what

The default split below gives each person material they can defend under
questioning. Priyanka ran every analysis, so she takes the results; Tanmayee
takes the framing, method and closing, which are the parts that can be fully
owned by reading the report.

| Slides | Presenter | Why |
| --- | --- | --- |
| 1–7 | Tanmayee | Motivation, data, method, pipeline. No result is claimed yet, so questions here are about design, which is documented. |
| 8–20 | Priyanka | Every result slide. These attract the hardest probes and need the person who ran them. |
| 21–23 | Tanmayee | Limitations, what was not done, conclusion. Closing on the honest framing is stronger from the second voice. |
| 24–25 | Either | References and thanks. |

**Variant if Tanmayee wants a results slide.** Give her **slide 11**
(*Building a fair multi-sensor comparison*). It is about the quality screening
of the heart and brain data, which was her assigned area, and it contains no
model result — only inclusion criteria. Hand back to Priyanka at slide 12.

**Handover points.** Say the handover out loud; do not just stop. Suggested
wording:

- End of slide 7 → *"Priyanka will now take you through what each stage found."*
- End of slide 20 → *"Tanmayee will close with what this does and does not
  establish."*

**Do not** present a slide you cannot answer one follow-up question on. If
time is short, cut slides rather than split them further — see §5.

---

## 3. Slide-by-slide guide

Each entry gives: what is on screen, what to say, the one sentence that must
be said, and the probe most likely to follow.

### Slide 1 — Title

**On screen:** title, subtitle, both names with roll numbers, course, faculty,
institution. Deliberately no date.

**Say:** introduce both presenters and the question in one line. *"We asked
whether cheaper sensors can replace brain recording for predicting what a
student learns from a video."*

Keep this to fifteen seconds.

---

### Slide 2 — The question we set out to answer

**On screen:** two boxes. Motivation (EEG predicts learning but is expensive
and intrusive), then our question (can eye tracking and ECG substitute, and
does combining help). Three bullets below: what we predict, who for, what from.

**Say:** EEG is the established route. It needs a lab, a cap, gel, and a
technician — none of which belongs in a classroom. An eye tracker is a camera;
ECG is two electrodes. If they carry the same signal, the finding becomes
usable.

Then the three design choices, which matter more than they look:

- **What we predict:** the proportion of *memory* questions answered
  correctly, standardised within each video. Standardising matters because
  some videos are harder; without it the model could score well just by
  learning which video a row came from.
- **Who for:** learners the model has **never seen**. This is the hard
  version. Predicting a new video for a learner already in training is much
  easier, and is not what a deployed system would face.
- **What from:** that one learner's own signals. We never use how similar a
  learner is to the rest of the group watching the same video.

**Must say:** *"held-out learners, not held-out rows."*

**Likely probe — "Why memory questions only?"**
The quiz has memory items and domain items. Domain items test what the learner
already knew about the subject before watching. Including them would mix prior
knowledge into a measure of what the video taught. The preregistration lists
prior knowledge as a covariate, not as the outcome.

---

### Slide 3 — How to read these slides

**On screen:** two columns. Left: terms (EEG, ECG, saccade, fixation,
attentive/distracted). Right: statistics (Spearman's ρ, Cohen's d_z,
confidence interval, p-value). A grey note at the bottom about run tags.

**Say:** walk it at a steady pace — do not rush this, it buys you the rest of
the talk. The two that matter most:

- **Spearman's ρ** — are we putting learners in the right *order*? +1 is
  perfect ordering, 0 is chance, negative means backwards.
- **Confidence interval** — if it contains zero, we have not established the
  effect.

Then the run tags: *"every result was produced by a numbered, logged run, so
any figure traces back to the exact code, settings and random seed. The tags
are for traceability; nothing on a slide depends on them."*

**Must say:** *"if an interval contains zero, we do not claim the effect."*

**Likely probe — "Why Spearman and not R² or accuracy?"**
Because the realistic use is ranking learners — who needs help — rather than
predicting an exact score. We report R² as well, and it is negative
throughout, which we state plainly: no model predicts the magnitude of a score
better than guessing the average.

---

### Slide 4 — The dataset

**On screen:** left, the BBBD dataset, Experiment 1 and Experiment 2 sample
sizes, and the memory/domain distinction. Right, a box titled *Two things the
dataset does not state, which we had to infer*.

**Say:** public dataset, Creative Commons, raw recordings not in our
repository. Learners watched five educational videos with EEG, ECG and eye
tracking recorded, then took a quiz. Each video was watched twice: once
attending, once while distracted.

Then the inferred assumptions, and do not hide them:

- **Which session was the attentive one.** The documentation does not say. We
  identified it from blink rates, which rise under distraction and which do
  not depend on any screen measurement.
- **Screen resolution.** Needed to convert gaze from pixels into degrees of
  visual angle. The published description gives screen size and viewing
  distance but not resolution. Saccade and fixation rates scale with this
  number; blink rates do not.

**Must say:** *"these two assumptions are stated wherever they affect a
result."*

**Likely probe — "What if the attentive/distracted mapping is backwards?"**
Then every Experiment 1 eye number has its sign reversed. We tested this as
hard as we could without documentation: blink rates identify the mapping and
are independent of the calibration, and the published paper states the
attentive session ran first. For Experiment 2 the question does not arise —
the data files state the condition outright, which run R-019 confirmed.

---

### Slide 5 — What we measured, and how we tested it

**On screen:** left, the eight eye measurements and the quality exclusion
rule. Right, the evaluation procedure.

**Say:** the eight measurements are deliberately simple — rates of eye
movements, pauses and blinks, pupil size and variability, how widely gaze
spread, and how much data was unusable. All come from one learner's recording.

The evaluation is where the care is:

- **Ridge regression** — a linear model that penalises large coefficients, so
  it does not overfit a small sample.
- **Grouped cross-validation** — the data is split five ways *by learner*, so
  a learner is never in both training and test. Repeated ten times with
  different splits, and averaged.
- The model's strength setting is chosen using **only training data**, inside
  a further split.
- **Permutation test**, 1,000 times: shuffle the scores, refit everything, see
  how often chance does this well.
- **Bootstrap**, 2,000 times: resample learners to measure precision.

**Must say:** *"a learner never appears in both training and test."*

**Likely probe — "Why repeat the split ten times?"**
Because with 25 learners a single split is a coin toss. Our per-split
correlations ranged from −0.077 to +0.279. One unlucky split would have shown
nothing; one lucky split would have looked like a finding. Repeating was
preregistered precisely so neither could happen.

---

### Slide 6 — The analysis pipeline

**On screen:** the architecture diagram. Three bands: completed Experiment 1
eye analysis, Experiment 2 multi-sensor comparison, and dashed boxes for what
was never run.

**Say:** trace the top band left to right in one breath — raw recordings,
event detection, eight measurements, joined to quiz scores, split by learner,
model fitted, evaluated on unseen learners. Then the middle band: three
sensors screened for quality, intersected into one shared sample, and only
*then* compared.

Point at the dashed boxes: *"these were planned and never run. They produce no
results and we claim none."*

**Must say:** *"the comparison happens only after a common sample is fixed."*

**Likely probe — "Why does the shared sample matter so much?"**
Because otherwise you compare a sensor on an easy sample against a sensor on a
hard one and call the difference a modality effect. Every sensor in our
comparison is judged on the same 125 rows, the same learners and the same
splits.

---

### Slide 7 — What we ran, in order

**On screen:** a two-column table — stage, and what it established.

**Say:** this is the roadmap; keep it to forty seconds. Seven stages:
validate the eye pipeline, predict from eye data, audit our own code, build a
matched multi-sensor sample, compare sensors, check the brain result is not an
eye artefact, and two deep-learning experiments.

**Must say:** *"where a result was superseded, we kept the original rather
than editing it."*

**Likely probe — "What does 'logged run' actually mean?"**
Each run writes a directory containing the git commit of the code, a hash of
the configuration, the random seed, and the output tables. The report cites
those identifiers. We can reproduce any number in the deck from them.

**→ Hand over to Priyanka.**

---

### Slide 8 — Validation: our pipeline reproduces the published effects

**On screen:** two bar panels — eye movements per minute, blinks per minute —
each attentive versus distracted. Statistics below.

**Say:** before predicting anything, we had to show our processing works. If
our code cannot recover an effect the dataset's authors already reported, no
prediction result from it means anything.

When distracted, learners made **fewer eye movements** (138.0 → 93.2 per
minute) and **blinked more** (1.25 → 2.90 per minute). Both match the
published direction and size. 27 learners, 263 recordings, and every learner
contributes to both bars, so this is a within-person comparison.

The effect sizes are large: d_z = 1.19 for saccades, 0.58 for blinks.

**Must say:** *"the blink result is the stronger evidence, because blinks come
from pupil data and do not depend on the screen measurement we had to infer."*

**Likely probe — "Why do the two panels have different axes?"**
Because the measures differ in size by two orders of magnitude — around 100
eye movements a minute against one to three blinks. On a shared axis the blink
panel would be invisible. Compare the panels for direction, not height.

**Likely probe — "Is reproducing an effect the same as reproducing the paper?"**
No. We reproduce the *condition contrast*. We did not compare our detected
events against the authors' event-by-event, which would be a stronger claim.
That comparison was not completed.

---

### Slide 9 — We audited our own analysis code

**On screen:** a two-column table of four defects found and how each was
fixed, plus a box titled *What this costs us*.

**Say:** this slide is a strength, not an apology. Present it that way.

After producing our first prediction result, we read our own code and found
four implementation problems: the model's strength setting was chosen with a
shortcut that ignored learner grouping; the significance test used one data
split while the headline used all ten; prediction error was measured against
the wrong baseline; and the multiple-comparison correction covered one sensor
instead of all planned ones.

We logged all four **before** rerunning, so the correction could not be shaped
by the new result.

**Must say:** *"because the correction was designed after seeing the first
result, it cannot count as a clean confirmatory test, and we do not claim it
as one."*

**Likely probe — "Why not just fix it and report the new number?"**
Because that hides a decision that could have gone the other way. A reader
cannot tell whether a correction was principled or chosen because it improved
the answer, unless you record it beforehand. We kept the original run intact
and labelled the corrected one as a post-result correction.

**Likely probe — "How do you know there are not more defects?"**
We do not. We have unit tests on synthetic data, the full suite passes, and
the pipeline is logged end to end — but an audit finds what it looks for. That
is why the corrected result is labelled exploratory rather than confirmatory.

---

### Slide 10 — Predicting quiz score from eye movements alone

**On screen:** a six-row results table, and a box titled *Two statistics that
disagree — and both are right*.

**Say:** the headline is Spearman ρ = **+0.108** with a 95% interval of
**[−0.126, +0.354]** and a permutation p of **.032**.

Those two disagree, and the slide explains why. The permutation test asks
*could chance order learners this well?* — and says probably not. The
confidence interval asks *how precisely do we know this number from 25
learners?* — and says barely at all.

**Must say:** *"the eye measurements carry a weak signal about who scored
better, but not enough to state its size with confidence."*

Then the negative R²: the model orders learners slightly better than chance
while predicting *how much* they scored worse than guessing the average. The
signal is ordinal at best.

**Likely probe — "So is the result significant or not?"**
The uncorrected permutation p is below .05. But the correction across sensors
was never completed, so that p is not a corrected claim, and the confidence
interval spans zero. We report it as a weak ordering, not as an established
effect. Both numbers are in the report; neither is hidden.

**Likely probe — "Negative R² — doesn't that mean the model is useless?"**
For predicting the score itself, essentially yes — it does worse than always
guessing the average. What it does slightly better than chance is *rank*
learners. We say so explicitly rather than quoting only the correlation.

---

### Slide 11 — Building a fair multi-sensor comparison

**On screen:** left, the inclusion criteria for each sensor and the resulting
shared sample. Right, a box stating a provenance limitation up front.

**Say:** to compare sensors you must judge them on identical data. Eye
recordings were processed from raw, with 5 dropped for poor pupil quality. For
heart data we required the heartbeat detector to have found at least 80% of
the reference heartbeats: **140 eligible, 15 unevaluable** because processing
had failed. For brain data, **139 attentive recordings** passed quality
control.

Keeping only rows where all three sensors *and* a quiz score exist gives
**125 learner–video rows from 26 learners across 5 videos**.

Then the limitation, before the results rather than after: the heart and brain
measurements came from **previously computed tables** recovered from earlier
processing, not from a fresh run. We verified the code that produced them
matches our repository, but we cannot certify the exact execution.

**Must say:** *"everything built on those tables is labelled exploratory."*

**Likely probe — "Why not just rerun them?"**
We did, for the brain data — that is slide 17, and it is the only brain result
computed from raw recordings. The heart detector was not rerun; we say so in
the report's list of what was not done.

---

### Slide 12 — Comparing the sensors

**On screen:** two panels. Left, how well each sensor ordered learners. Right,
differences between sensors with confidence intervals and a grey equivalence
band.

**Say:** read the left panel first. Zero is chance. **Brain recording is the
only one above zero at +0.053.** Eye is −0.216, heart −0.292, eye and heart
combined −0.327, all three −0.111.

Negative means ordering learners backwards — which, with 26 learners, is what
weak signal plus noise looks like.

Right panel: brain beat eye by **+0.269** and beat eye-plus-heart by
**+0.380**, both intervals clear of zero. The grey band is the margin inside
which we would have called two sensors equivalent.

**Must say:** *"every sensor here is judged on the same rows, the same
learners and the same splits — only the sensor changes."*

**Likely probe — "Why are most correlations negative?"**
With 26 learners and a weak signal, a cross-validated correlation can easily
land below zero; that is sampling noise, not a model that has learned to
invert. The honest reading is that none of these sensors predicts usefully on
this sample, which is what we conclude.

---

### Slide 13 — What the sensor comparison does and does not show

**On screen:** left, four bullets of what can be said. Right, four reasons to
hold it loosely.

**Say:** this is the most important slide in the talk. Four claims:

1. Brain recording ordered learners better than the cheaper sensors, both
   intervals clear of zero.
2. Neither interval fits inside the equivalence margin, so **we did not show
   the cheaper sensors match EEG**.
3. The eye interval overlaps that margin, so **neither did we show they are
   meaningfully worse**.
4. Combining all sensors scored −0.044 against the best single sensor, 95%
   interval [−0.177, +0.073] — **no benefit from combining**.

Then why to hold it loosely: brain recording itself only reached +0.053;
intervals resample learners without refitting models; no permutation test was
run for this comparison; and the inputs came from recovered tables.

**Must say:** *"failing to show equivalence is not the same as showing a
difference."*

**Likely probe — "So did the cheap sensors fail?"**
We cannot say that. We failed to establish equivalence *and* failed to
establish a difference larger than our margin. With 26 learners both outcomes
are what an underpowered test looks like. The honest statement is that this
sample cannot settle the question.

**Likely probe — "Why would fusion not help?"**
On 125 rows, adding sensors adds parameters faster than it adds information.
Our fusion was early fusion — concatenating features. Late fusion and learned
fusion were planned and not run.

---

### Slide 14 — A brain-activity difference between the two conditions

**On screen:** an eight-row table of frequency-band contrasts, and a box
titled *Why we do not claim a replication*.

**Say:** published work reports that **alpha** activity rises specifically
when attention drops. We found power does rise in the distracted session —
posterior alpha has the largest effect of any band, d_z = +0.80.

But it is **not confined to alpha**. Delta rises too (+0.71 posteriorly), and
delta's raw shift is larger than alpha's: +0.143 against +0.058. Theta and
beta move as well. The pattern falls away with frequency, which is what a
broad low-frequency increase looks like, not an alpha-specific one.

The test designed to isolate alpha — comparing it against neighbouring
frequencies — gives d_z = +0.41 but does not survive correction (p = .13).

**Must say:** *"we found a condition difference in brain activity, but we
cannot attribute it specifically to alpha, so we do not claim the
replication."*

**Likely probe — "Why not just report the alpha result? It's significant."**
Because the specificity check is the point. Any broad increase in power will
raise absolute alpha. Reporting that as an alpha effect, when delta moved
more, would be selective.

---

### Slides 15–17 — The three-part artefact investigation

Present these as **one argument in three steps**, not three separate results.
Signpost at the start of slide 15: *"the obvious objection is that this is
just the eyes, not the brain. We tested that three ways."*

#### Slide 15 — Test 1: count the blinks

**On screen:** a three-row table (blinks, saccades, fixations), and a box
explaining why the test failed.

**Say:** blinking creates large electrical artefacts that look like brain
activity, and blinking increases under distraction. So we reprocessed both
conditions from raw to count blinks.

**The blink rate is exactly zero in all 302 recordings.**

This is not a bug. We scanned every pupil file: 9.5 million samples, and only
six files contain any gap at all — five of those are empty from start to
finish. **The published data has already been smoothed**, erasing the gaps
that mark a blink.

**Must say:** *"this is not evidence that learners did not blink — it is
evidence that the released data cannot tell us."*

One clue does survive: saccades are *fewer* when distracted, so eye-movement
artefact would be *lower* in the condition with *more* brain power — the wrong
direction to explain the finding.

**Likely probe — "Could you not detect blinks a different way?"**
Yes, by detecting dips in pupil size rather than gaps. We chose not to.
Picking a new detection rule *after* seeing that the first test failed is a
rule selected to rescue a result. We logged the question as open and deferred
it.

#### Slide 16 — Test 2: where on the scalp?

**On screen:** a five-row table of regional effects, with the front-minus-rear
gradient highlighted as the primary test.

**Say:** eye artefacts project most strongly to electrodes at the **front** of
the head. So if this is eye-driven, it should be much larger at the front.

It is not. The front-minus-rear difference is **−0.19, p = .33** — the point
estimate actually leans towards the *back*. Delta rises in all four regions,
most strongly at the rear.

**Must say:** *"the decisive comparison was fixed before we ran it."*

**Likely probe — "Isn't that just an argument from pattern?"**
Yes, and we say so. It weakens the eye explanation without ruling it out.
Slide 17 removes the eye contribution directly.

#### Slide 17 — Test 3: remove the eye contribution

**On screen:** a four-row before/after table, and a box titled *The effect
survives. It is not an eye artefact.*

**Say:** the dataset includes dedicated eye electrodes. We reprocessed every
raw brain recording twice from the same starting point — once with the
eye-measured contribution mathematically subtracted, once without. The only
difference between the two columns is that subtraction.

Every region stays significant. The effect sizes barely move: the largest
change is at the front, −0.08, and the rear regions move slightly *up*.

**Must say:** *"a small reduction at the front and none elsewhere is what a
little eye contamination sitting on top of a genuine effect looks like — a
purely eye-driven effect would have collapsed."*

264 of 291 recordings were usable; the other 27 have no eye-electrode file.
This is our only brain result computed from raw recordings rather than saved
tables.

**Likely probe — "Why not use ICA instead?"**
We did, on slide 18, for a different question. For this test we used the
regression method because it has no threshold to choose. ICA requires deciding
how many components to remove, and that decision would have been made after
seeing this result.

---

### Slide 18 — Does the ranking depend on how we clean the brain data?

**On screen:** a six-row table comparing two cleaning methods, and a box
stating the ranking is stable.

**Say:** this is a robustness check. We cleaned the brain data two different
ways — subtracting the eye-electrode contribution, versus separating the
recording into independent sources and removing the eye-related ones — and
reran the whole comparison on identical rows and splits.

**The ranking is the same: brain, then eye, then heart.**

Point at the eye and heart rows: identical to four decimal places. That is the
check that nothing but the brain data changed.

**Must say:** *"a stable ordering among three weak predictors is a modest
claim — brain recording itself only reaches +0.08 to +0.12."*

Combining sensors still never beats the best single sensor; under the second
method it is measurably worse.

**Likely probe — "Did the second method work properly?"**
Partly. It failed to converge on 19 of the 125 recordings, so we label that
column indicative rather than definitive. We say so on the slide rather than
reporting it as equivalent evidence.

---

### Slide 19 — Deep learning, part 1: telling the conditions apart

**On screen:** a four-row accuracy table, and a box titled *It works, but it
adds nothing*.

**Say:** we trained a convolutional neural network on raw gaze and pupil
signals, in four-second windows, to classify whether a learner was attending
or distracted — tested on learners it had never seen.

It reaches **0.797** balanced accuracy, where 0.5 is chance.

But the comparison is the point: **logistic regression on our eight
hand-designed measurements reaches 0.764**. The gap is +0.034, which is barely
larger than the **0.021 variation between the network's own training runs**.

**Must say:** *"we fixed the comparison baseline before training the network,
so it could not be chosen to flatter the result — and we do not claim the
network is better."*

**Likely probe — "Why is the accuracy so high if your other results are weak?"**
Because this is a much easier question. Eye-movement rate alone nearly
separates the two conditions — we showed d_z = −1.17 on slide 15. Identifying
*which condition* someone was in is not the same as predicting *what they
learned*.

**Likely probe — "Is this your deep-learning component for the course?"**
It is a trained, evaluated deep model on this dataset. Whether it satisfies
the requirement is a question for you — we have deliberately not assumed it
does, and slide 22 says exactly what was not attempted.

---

### Slide 20 — Deep learning, part 2: predicting what was learned

**On screen:** a five-row table comparing learned features against
hand-designed ones, and a box titled *Learned features give no advantage*.

**Say:** this is the question the project plan actually asked: do features
learned by a network beat hand-designed ones for **quiz prediction**?

Learned features: **−0.077**. Hand-designed: **−0.050**. Difference −0.026,
with an interval from −0.206 to +0.158 — straddling zero.

**Must say:** *"the network was retrained from scratch inside every data
split, using only training learners — otherwise it would have shaped its
features around the learners we then tested on."*

**Likely probe — "Both numbers are negative. Does the comparison mean
anything?"**
Only as a comparison. Neither approach orders learners better than chance, so
the honest conclusion is that learned features add nothing *here*, not that
they are worse in general. This run also used one data split rather than ten,
so the individual levels are unstable — read the difference, not the levels.

**Likely probe — "64 features on 100 rows — isn't that doomed?"**
Largely, yes, and we say so. The network is handicapped by dimensionality as
much as by representation quality. A fair test needs far more learners or a
much smaller embedding.

**→ Hand back to Tanmayee.**

---

### Slide 21 — Limitations

**On screen:** six bullets.

**Say:** do not rush this and do not apologise through it. Read each one as a
statement of fact.

Two inferred assumptions underpin every eye result. Only 25–26 learners, so
intervals are necessarily wide. No model predicts quiz scores usefully. One
video is too easy — 38.7% of learners scored 90% or above, which compresses
the differences we are trying to predict. Most heart and brain measurements
came from recovered tables. And the correction for testing several sensors at
once is unresolved, so every p-value is uncorrected across sensors.

**Must say:** *"we would rather state these than have them found."*

**Likely probe — "Which limitation worries you most?"**
Sample size. With 26 learners, almost everything else follows from it — wide
intervals, unstable splits, and an underpowered equivalence test. A second
cohort would change more than any modelling choice.

---

### Slide 22 — What we did not do

**On screen:** three bullets inside a box.

**Say:** three things, stated as scope decisions rather than omissions,
because each was recorded before the work was skipped.

We did not build encoders that learn a shared representation across brain and
eye signals, and did not build a combined multi-sensor network — on 26
learners these would produce numbers we could not interpret or defend. The
robustness check was answered on the exploratory sample only. And the
heartbeat detector was never rerun from raw; we audited the saved output
instead.

**Must say:** *"each of these was logged before the work was skipped, not
explained afterwards."*

**Likely probe — "Isn't that just an excuse for not finishing?"**
The distinction is whether the decision was recorded in advance. Ours were. We
would rather present three honest gaps than three numbers we cannot stand
behind.

---

### Slide 23 — Conclusion

**On screen:** a summary box and five bullets.

**Say:** close on the honest framing, not on a hedge.

We could not show that eye tracking or heart activity matches brain recording,
and combining sensors gave no benefit. But brain recording itself predicted
only weakly, so this is evidence about our pipeline on this sample — not a
general verdict.

Then what we *did* establish: our from-raw processing reproduces published
attention effects in both eye movement and brain activity; eye measurements
carry a weak ordinal signal; the brain-activity difference is genuine, not an
eye artefact, confirmed by reprocessing raw recordings; neither neural network
beat simple measurements; and we audited our own code, found defects, and
disclosed them before reporting the correction.

**Must say:** *"the contribution is a traceable pipeline and an honest
negative result."*

---

### Slides 24–25 — References and thanks

Ten references. Do not read them. Pause, invite questions.

---

## 4. Anticipated viva questions

Grouped by theme. Each answer is short enough to say out loud.

### On the headline result

**"Your correlations are negative. Did the project fail?"**
The predictive results are weak and we report them as weak. The project's
contribution is the comparison method and the evidence chain, not a strong
predictor. A negative result on 26 learners, reported honestly with its
uncertainty, is more useful than a positive one that would not replicate.

**"If EEG only reaches +0.05, how can you rank sensors at all?"**
We can only rank them relative to each other, and we say the ranking is a
modest claim. The paired differences are clear of zero because the comparison
is within the same rows and splits, which removes a lot of noise. The absolute
levels remain weak and we do not hide that.

**"What would make this work?"**
More learners, first. Then a peer-similarity feature — our current features use
one learner's signal alone, and the published effects that motivated the
project are based on how synchronised a learner is with the group. We left
that comparison unmeasured; it is the most promising next step.

### On method

**"Why ridge and not something more powerful?"**
With 120 rows and eight features, a flexible model overfits. We did run random
forest and a small neural network as exploratory secondary models; neither was
permutation-tested, so we do not use them to rank model families. The deep
models on slides 19 and 20 are the serious attempt at something more powerful,
and neither beat the simple approach.

**"How do you know there is no leakage?"**
Three ways. Splits are grouped by learner, so a learner never appears in both
sides. Model settings are chosen inside the training data only. And where a
neural network is involved, it is retrained from scratch inside each split,
because a network pretrained on everyone would have seen the test learners'
signals. We have a unit test asserting that last property.

**"Why standardise scores within video?"**
Because videos differ in difficulty. Without it, a model could score well by
inferring which video a row came from rather than anything about the learner.

**"What is the equivalence margin and where did it come from?"**
It is ±0.10 in correlation, fixed in advance as the largest difference we would
be willing to call practically equivalent. It was not chosen after seeing
results. Our intervals do not fit inside it, which is why we say equivalence
was not established.

### On the data

**"You inferred the screen resolution. How much does that matter?"**
Saccade and fixation rates scale with it, so their absolute values would shift.
Blink rates do not depend on it at all. And in any within-condition comparison
one constant applies to both sessions, so the contrast survives even if the
constant is wrong. Our validation leans on blink rates for exactly this reason.

**"The published data had already been smoothed. Should you have noticed
earlier?"**
Ideally yes. We found it when a blink-counting test returned exactly zero
across 302 recordings and we went looking for why. The scan that established
it — 9.5 million samples, six files with any gap — is in the report. The
lesson is that a result of exactly zero deserves investigation rather than a
footnote.

**"Why is Experiment 2 exploratory?"**
Because most of its heart and brain features came from previously computed
tables rather than a run we executed and logged at the time. We verified the
code matches our repository but cannot certify the execution. The brain
results were later re-derived from raw, which is slide 17.

### On the self-audit

**"Does finding defects undermine your results?"**
It changes their status. The corrected analysis is labelled a post-result
correction rather than a confirmatory test, which is a weaker claim and
deliberately so. The alternative — not looking, or quietly fixing — would have
left an unverifiable result in the report.

**"What stopped you fixing the code and rerunning quietly?"**
A working rule we set at the start: any choice that could change a result is
logged before it is used, and superseded results are preserved rather than
edited. The original run is still in the repository.

### On deep learning

**"Why so little deep learning for a multimodal ML course?"**
We trained and evaluated two models and reported both honestly. The planned
multimodal encoders were not attempted because 26 learners cannot support
them — we recorded that decision in advance rather than producing a number we
could not defend. If you would like that attempted regardless, we can say
exactly what it would take.

**"Your network beat the baseline on slide 19. Why not claim it?"**
Because +0.034 is barely above the 0.021 spread across the network's own
random seeds, and we computed no interval for that gap. Claiming an advantage
of that size would be reading noise.

### Awkward but fair

**"Who did what?"**
Priyanka ran the analyses reported here. The original division assigned eye
processing, targets and modelling to Priyanka, and physiology to Tanmayee.
Both of us are responsible for understanding and presenting the whole
pipeline. — *Say this plainly; the report states it in §7.3.*

**"Your notebooks have no saved outputs."**
Correct. The registered result tables and JSON summaries are the evidence, and
every number traces to a logged run. Saved notebook outputs are a submission
requirement we have not yet met, and we are not claiming otherwise.

**"Is any of this confirmatory?"**
No. Everything in the deck is exploratory or a post-result correction. The one
analysis originally labelled confirmatory is the one whose defects we found,
and we withdrew that label.

---

## 5. Timing and what to cut

Full deck at a comfortable pace is roughly **18–20 minutes**.

| Target | Cut these | Keeps |
| --- | --- | --- |
| **15 min** | Slide 3 (fold the two statistics into slide 10), slide 7 | Full argument, slightly faster setup |
| **12 min** | Also slides 16 and 18 | Artefact argument becomes two steps instead of three |
| **10 min** | Also slides 19 and 20; mention deep learning in one line on slide 22 | Core: question, data, method, validation, audit, prediction, comparison, limitations, conclusion |

**Never cut:** slide 9 (the audit), slide 13 (what the comparison does and does
not show), slide 21 (limitations). Those three are the project's case for
itself.

---

## 6. The evening before

- Read the report's §8 once, slowly. Every slide number has a corresponding
  section with more detail than the slide.
- Say slides 10, 13 and 17 out loud. They carry the three hardest ideas:
  two statistics that disagree, failure to establish equivalence, and an
  artefact control.
- Check `slides/slides.pdf` opens on the presenting machine, and that the
  fonts render. It is a PDF, so it should be safe anywhere.
- Agree the two handover sentences and say them once each.
- Decide in advance who answers what. Suggested: method and data questions to
  Tanmayee, result and statistics questions to Priyanka, scope questions to
  whoever is standing.

**If you do not know an answer**, say so and say what you would do to find
out. The project's whole stance is that an honest gap beats a confident guess,
and answering in that style is consistent with the work.
