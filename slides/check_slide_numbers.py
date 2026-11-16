"""Check that every numeric claim on a slide matches its registered JSON."""
import csv
import json
import pathlib
import sys

root = pathlib.Path(sys.argv[1])
tex = (root / "slides/slides.tex").read_text(encoding="utf-8")
flat = tex.replace("$", "").replace("\\", "")


def R(p):
    return json.loads((root / p).read_text())


r4 = R("results/R-004_eye_rq0_exp1/rq0_eye_exp1.json")
r13 = R("results/R-013_eye_reconciliation/eye_reconciliation.json")
r17 = R("results/R-017_exp2_matched_ridge/exp2_matched_ridge.json")
r15 = R("results/R-015_exp2_ecg_recovery_audit/ecg_recovery_audit.json")
r16 = R("results/R-016_exp2_common_cohort/exp2_cohort_audit.json")
r18 = R("results/R-018_exp2_eeg_alpha_audit/eeg_alpha_audit.json")
r19 = R("results/R-019_exp2_eye_condition/exp2_eye_condition.json")
r20 = R("results/R-020_exp2_eeg_topography/exp2_eeg_topography.json")
r21 = R("results/R-021_exp2_eeg_ocular_rerun/exp2_eeg_ocular_rerun.json")
r22 = R("results/R-022_exp2_rq3_cleaning/exp2_rq3_cleaning.json")
h0 = r4["h0b_attend_vs_distract"]

# R-018 per-metric rows, keyed by metric name.
with (root / "results/R-018_exp2_eeg_alpha_audit/eeg_alpha_condition_tests.csv").open() as f:
    eeg = {row["metric"]: row for row in csv.DictReader(f)}


def s3(x):
    return f"{x:+.3f}".replace("0.", ".")


checks = [
    ("138.0", f"{h0['saccade_rate_per_min']['mean_01']:.1f}"),
    ("93.2", f"{h0['saccade_rate_per_min']['mean_02']:.1f}"),
    ("1.25", f"{h0['blink_rate_per_min']['mean_01']:.2f}"),
    ("2.90", f"{h0['blink_rate_per_min']['mean_02']:.2f}"),
    ("6.18", f"{h0['saccade_rate_per_min']['t']:.2f}"),
    ("1.19", f"{h0['saccade_rate_per_min']['d_z']:.2f}"),
    ("-3.04", f"{h0['blink_rate_per_min']['t']:.2f}"),
    ("-0.58", f"{h0['blink_rate_per_min']['d_z']:.2f}"),
    ("+0.108", f"{r13['metrics']['spearman']:+.3f}"),
    ("-0.126", f"{r13['ci_low']:+.3f}"),
    ("+0.354", f"{r13['ci_high']:+.3f}"),
    ("-0.031", f"{r13['metrics']['r2']:+.3f}"),
    ("+0.027", f"{r13['training_mean_skill']:+.3f}"),
    ("0.759", f"{r13['metrics']['mae']:.3f}"),
    (".032", f"{r13['p_permutation_raw']:.3f}".lstrip("0")),
    ("+.053", s3(r17["metrics"]["eeg"]["spearman"])),
    ("-.216", s3(r17["metrics"]["eye"]["spearman"])),
    ("-.292", s3(r17["metrics"]["ecg"]["spearman"])),
    ("-.327", s3(r17["metrics"]["eye_ecg"]["spearman"])),
    ("+.269", s3(r17["comparisons"]["eeg_minus_eye"]["estimate"])),
    ("+.380", s3(r17["comparisons"]["eeg_minus_eye_ecg"]["estimate"])),
    ("-.044", s3(r17["comparisons"]["all_sensors_minus_selected_single"]["estimate"])),
    ("-.177", s3(r17["comparisons"]["all_sensors_minus_selected_single"]["ci_low"])),
    ("+.073", s3(r17["comparisons"]["all_sensors_minus_selected_single"]["ci_high"])),
    ("125 rows", f"{r17['n_rows']} rows"),
    ("26 learners", f"{r17['n_learners']} learners"),
    ("140 eligible", f"{r15['eligibility']['eligible']} eligible"),
    ("15 unevaluable", f"{r15['eligibility']['unevaluable']} unevaluable"),
    ("139 attentive rows", f"{r16['attentive_eeg_qc_rows']} attentive rows"),
    ("5 videos", f"{r16['n_videos']} videos"),
    # R-018: the headline, and the two numbers the "not alpha-specific" argument rests on.
    ("+0.80", f"{float(eeg['log_alpha_posterior']['cohens_dz']):+.2f}"),
    ("+0.65", f"{float(eeg['log_alpha_all']['cohens_dz']):+.2f}"),
    ("+0.11", f"{float(eeg['rel_alpha_all']['cohens_dz']):+.2f}"),
    ("+0.71", f"{float(eeg['log_delta_posterior']['cohens_dz']):+.2f}"),
    ("+0.60", f"{float(eeg['log_delta_all']['cohens_dz']):+.2f}"),
    ("+0.41", f"{float(eeg['alpha_flank_posterior']['cohens_dz']):+.2f}"),
    (".0009", f"{float(eeg['log_alpha_posterior']['p_holm_alpha_family']):.4f}".lstrip("0")),
    (".0061", f"{float(eeg['log_alpha_all']['p_holm_alpha_family']):.4f}".lstrip("0")),
    ("+.143", s3(float(eeg["log_delta_all"]["mean_diff"]))),
    ("+.058", s3(float(eeg["log_alpha_all"]["mean_diff"]))),
    ("291 recordings", f"{r18['n_recordings']} recordings"),
    ("30 learners", f"{r18['n_learners']} learners"),
    # R-019: the empty blink channel and the two rates that did move.
    ("148.1", f"{r19['contrasts']['saccade_rate_min']['mean_attentive']:.1f}"),
    ("106.4", f"{r19['contrasts']['saccade_rate_min']['mean_distracted']:.1f}"),
    ("128.9", f"{r19['contrasts']['fixation_rate_min']['mean_attentive']:.1f}"),
    ("84.1", f"{r19['contrasts']['fixation_rate_min']['mean_distracted']:.1f}"),
    ("-1.17", f"{r19['contrasts']['saccade_rate_min']['cohens_dz']:+.2f}".replace("-0", "-")),
    ("-1.77", f"{r19['contrasts']['fixation_rate_min']['cohens_dz']:+.2f}".replace("-0", "-")),
    ("31 learners", f"{r19['n_learners']} learners"),
    ("302 recordings", f"{r19['n_recordings']} recordings"),
    # R-020: the four regional delta effects and the primary gradient.
    ("+1.19", f"{r20['delta_by_region']['occipital']['cohens_dz']:+.2f}"),
    ("+1.08", f"{r20['delta_by_region']['frontal']['cohens_dz']:+.2f}"),
    ("+1.01", f"{r20['delta_by_region']['parietal']['cohens_dz']:+.2f}"),
    ("+0.70", f"{r20['delta_by_region']['central']['cohens_dz']:+.2f}"),
    ("-0.19", f"{r20['primary']['cohens_dz']:+.2f}".replace("-0.", "-0.")),
    ("-0.0069", f"{r20['primary']['mean_diff']:+.4f}".replace("+", "")),
    ("263 recordings", f"{r20['n_recordings']} recordings"),
    ("28 learners", f"{r20['n_learners_paired']} learners"),
    # R-021: corrected and uncorrected effect sizes, and the sample.
    ("+1.26", f"{r21['corrected']['delta_by_region']['occipital']['cohens_dz']:+.2f}"),
    ("+1.06", f"{r21['corrected']['delta_by_region']['frontal']['cohens_dz']:+.2f}"),
    ("+1.03", f"{r21['corrected']['delta_by_region']['parietal']['cohens_dz']:+.2f}"),
    ("+0.59", f"{r21['corrected']['delta_by_region']['central']['cohens_dz']:+.2f}"),
    ("+1.24", f"{r21['uncorrected']['delta_by_region']['occipital']['cohens_dz']:+.2f}"),
    ("+1.14", f"{r21['uncorrected']['delta_by_region']['frontal']['cohens_dz']:+.2f}"),
    ("+0.99", f"{r21['uncorrected']['delta_by_region']['parietal']['cohens_dz']:+.2f}"),
    ("+0.63", f"{r21['uncorrected']['delta_by_region']['central']['cohens_dz']:+.2f}"),
    ("264 of 291", f"{r21['n_recordings']} of {r21['n_recordings_attempted']}"),
    # R-022: the two cleaning variants.
    ("+.080", s3(r22["variants"]["eog_regression"]["metrics"]["eeg"]["spearman"])),
    ("+.123", s3(r22["variants"]["ica"]["metrics"]["eeg"]["spearman"])),
    ("-.049", s3(r22["variants"]["eog_regression"]["metrics"]["all_sensors"]["spearman"])),
    ("-.098", s3(r22["variants"]["ica"]["metrics"]["all_sensors"]["spearman"])),
    ("+.025", s3(r22["variants"]["eog_regression"]["metrics"]["selected_single"]["spearman"])),
    ("+.051", s3(r22["variants"]["ica"]["metrics"]["selected_single"]["spearman"])),
    ("-.149", s3(r22["variants"]["ica"]["comparisons"]["all_sensors_minus_selected_single"]["estimate"])),
    ("125 rows", f"{r22['n_rows']} rows"),
]

# The deck says the ranking is stable and that eye/ECG were untouched.
if not r22["ranking_stable"]:
    checks.append(("ranking stable", "RANKING IS NO LONGER STABLE"))
if any(abs(r22["spearman_shift"][m]) > 1e-9 for m in ("eye", "ecg", "eye_ecg")):
    checks.append(("eye and ECG unchanged", "A NON-EEG MODALITY MOVED"))

# The deck claims the effect survives correction in every region.
if not all(r21["survives_correction"].values()):
    checks.append(("survives in every region", "A REGION NO LONGER SURVIVES"))
# ...and that the largest shift is at most 0.08.
if max(abs(v) for v in r21["dz_change"].values()) > 0.085:
    checks.append(("d_z moves by at most 0.08", "A LARGER SHIFT APPEARED"))

# The deck says the gradient is not frontal-dominant; that must stay true.
if r20["primary"]["frontal_dominant"]:
    checks.append(("not frontal-dominant", "GRADIENT IS NOW FRONTAL-DOMINANT"))

# The deck states blink rate is identically zero; that must stay true of the data.
with (root / "results/R-019_exp2_eye_condition/"
             "eye_features_exp2_both_sessions.csv").open() as f:
    blinks = [float(row["blink_rate_min"]) for row in csv.DictReader(f)]
if any(blinks):
    checks.append(("blink rate identically zero", "SOME NON-ZERO BLINKS"))

bad = []
for shown, expected in checks:
    if shown != expected:
        bad.append(f"  MISMATCH  slide says {shown!r}, JSON gives {expected!r}")
    elif shown.split()[0] not in flat:
        bad.append(f"  MISSING   {shown!r} is not in slides.tex")

# Claims the project rules forbid on a slide.
for forbidden in ["H1a is supported", "confirmatory eye", "RQ4 was executed"]:
    if forbidden.lower() in tex.lower():
        bad.append(f"  FORBIDDEN claim present: {forbidden!r}")

print("\n".join(bad) if bad else f"all {len(checks)} numbers match their registered JSON")
sys.exit(1 if bad else 0)
