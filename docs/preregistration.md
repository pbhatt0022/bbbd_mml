# Preregistration (v1, draft until tagged)

**Status: DRAFT.** It becomes binding when both members agree and the commit is tagged `prereg-v1` and pushed (D-07). Planned freeze: 6 Nov 2026, before any relationship between features and quiz scores is computed. After freezing, every change goes in `docs/deviations.md`. Values marked *(proposed)* need both members' sign-off.

Changes from draft v0 (Project Hub, 12 Oct): freeze date moved (DV-01); H4 added for the deep learning track (D-05, D-17); H3 reduced to V1 vs V3 (D-18); S2 removed.

## 0. What we already know (disclosure)

- The dataset authors have published that EEG, eye and heart-rate ISC relate to attention and quiz scores. Our hypotheses are therefore not blind to the direction of ISC effects. They are blind to *our* features, our pipelines and multimodal held-out performance, which have not been reported.
- On 15 Oct we ran an attend vs distract saccade-rate analysis on Exp 1 (inference log, first row). It did not involve quiz scores.
- **Team to confirm before tagging:** no feature has yet been correlated with quiz scores.

## 1. Hypotheses

| ID | Hypothesis | Test | Supported if |
| --- | --- | --- | --- |
| H0a | Our R-peak detection matches the authors' hand-corrected peaks | Beat matching within ±50 ms *(proposed)* | F1 ≥ 0.95 per recording *(proposed)* |
| H0b | Distraction lowers saccade rate and raises posterior alpha power in our own pipeline | Paired t-test per experiment, attend vs distract | Same direction as the authors, p < .05 |
| H1a | Each modality (eye, cardiac, EEG) predicts within-video quiz score above chance on unseen learners | Permutation test (1,000 shuffles within video, full CV refit) on Spearman ρ | p < .05, Holm-corrected across modalities |
| H1b | Eye-only performance is equivalent to EEG-only | Bootstrap 90% CI of Δρ (EEG − eye), resampling learners (TOST) | CI inside ±0.10 *(proposed margin)* |
| H1c | Fusing all modalities beats the best single modality | Bootstrap 95% CI of Δρ (fused − best unimodal) | CI excludes 0 |
| H2 | Individual-only features predict above chance but below ISC features, per modality | H1a test + bootstrap Δρ (ISC − individual) | Individual p < .05 and Δρ CI > 0 |
| H3 | The modality ranking in H1 is unchanged with ICA (V3) instead of EOG regression (V1) | Rank of modalities across variants | Same top modality in V1 and V3 |
| H4a | Contrastive EEG↔eye alignment exceeds chance on held-out learners | Recall@10 vs chance (k/N), permutation of window pairing | R@10 above the 95th percentile of the null |
| H4b | Fused deep models decode attend vs distract better than the best single-modality deep model | Bootstrap CI of Δ balanced accuracy, resampling learners | CI excludes 0 |
| H4c | Pooled deep embeddings predict quiz score at least as well as hand-crafted features of the same modalities | Bootstrap 90% CI of Δρ (deep − hand-crafted) | Lower bound > −0.10 (non-inferiority, *proposed margin*) |

## 2. Data and exclusions

- **Unit:** one row per learner × quizzed video, attend session only for quiz prediction. Exp 5 session 2 excluded from pooled analyses and reported separately.
- **Exclude a video for a modality if** *(proposed thresholds)*:
    - eye: > 50% of samples invalid or interpolated;
    - EEG: > 20% of channels marked bad, or bad segments > 10% of the duration;
    - ECG: < 80% of beats detectable.
- **Exclude a learner** if quiz data is missing. Missing modalities are allowed; models are compared on the subset that has every modality in the comparison.
- All exclusions are counted and reported per experiment (`results/exclusions.csv`).

## 3. Variables

- **Outcome:** proportion correct per video, z-scored within video and experiment (D-10). Secondary: median split per video (AUC).
- **Auxiliary outcome:** attend vs distract (Exps 1–3).
- **Predictors:** feature lists in `docs/methods_plan.md` §5 and `src/bbbd/features.py`; settings fixed in `config.yaml` at the tag.
- **Covariates:** none in the primary models. Digit span and prior knowledge (Exp 2) only in exploratory models.

## 4. Analysis plan

1. **Splits:** 5-fold grouped by learner, repeated 10 times (classical) with the seeds in `config.yaml`; inner 3-fold for tuning; one shared fold file `results/folds.json`. Second scheme: leave-one-video-out. ISC references and CorrCA weights from training-fold learners only. Deep encoders retrained per outer fold, 3 training seeds.
2. **Models:** ridge regression (primary). Random forest and a small MLP secondary. Fusion: early concatenation, late averaging/stacking, leave-one-modality-out. Deep track per D-17.
3. **Metrics:** Spearman ρ (primary), R² vs training-mean baseline, MAE; AUC for the median split; balanced accuracy and AUC for attention; Recall@1/5/10 for alignment.
4. **Inference:** permutation p-values and learner-bootstrap CIs (2,000 resamples); Holm correction within each RQ.
5. **Confirmatory vs exploratory:** H0–H4 with the stated models are confirmatory. Everything else (other models, PID, engagement ratings, pooled-experiment models) is exploratory and labelled as such.

## 5. Preprocessing variants for H3

| Variant | EEG | Eye | ECG |
| --- | --- | --- | --- |
| V1 default | 0.5 Hz high-pass, notch (60 Hz; 16 Hz if detected), bad-channel interpolation, average reference, EOG regression | Blink padding 100 ms, interpolate gaps < 250 ms | NeuroKit2 default detector + RR plausibility filter (300–2000 ms) |
| V3 ICA | V1 with ICA EOG components removed instead of regression | As V1 | As V1 |

V2 (minimal) is dropped for time (D-18).
