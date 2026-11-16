# Report completion checklist

Draft: `report_draft.md` and editable Word export. This checklist is separate from the report.

- [x] Cover: Priyanka Bhatt (2023UG000127), Tanmayee K M (2023UG000134), Dr. Minati Rath, Vidyashilp University. Faculty/institution verified at https://vidyashilp.edu.in/minati_rath/ on 13 Nov 2026.
- [x] All twelve sections follow the professor's structure.
- [x] Literature comparison uses verified sources; bibliography entries updated before use.
- [x] R-004 and R-012 values trace to registered summaries; original outputs preserved.
- [x] No unregistered ECG diagnostic values or fabricated fusion/DL results included.
- [x] Incorporate R-013 with its CI, raw p-value and baseline definitions. Package versions are in the registered summary.
- [ ] Agree on the multiplicity family and final inference; do not label raw eye p as a completed across-modality test.
- [ ] Both humans review consequential Proposed decisions; no assistant initials or automatic status promotion.
- [ ] Record the actual scope decision and resolve the professor's deep-learning requirement.
- [x] Register the recovered ECG audit (R-015). A fresh detector run remains pending.
- [x] Verify common cohort and folds (R-016), then run exploratory paired comparison (R-017).
- [ ] Save executed notebooks with outputs; historical committed notebooks are currently empty of outputs.
- [x] Incorporate R-013 and R-017 into the draft.
- [x] Register the 15 Oct Experiment 2 EEG alpha analysis as R-018 (D-36 / DV-07) and report it in §8.5 as a session difference in absolute power that is **not** shown to be alpha-specific. A fresh raw EEG run remains pending, as does RQ3.
- [x] Settle the ocular question directly with R-021 (D-40 / DV-10): reprocessed from raw, the condition effect survives EOG regression with d_z moving by at most 0.08. Reported in §8.8. This also showed the recovered tables were already EOG-regressed, which corrects a statement in §8.7. RQ3 is still not executed.
- [x] Probe the ocular explanation a second way with R-020 (D-39 / DV-09): the low-frequency increase is distributed across the scalp, not frontal-dominant, which argues against it. Reported in §8.7. RQ3 remains the only thing that could settle it.
- [x] Test the ocular explanation for R-018 by pairing the Experiment 2 eye conditions from raw (R-019, D-37 / DV-08). The test could not be run: blink rate is identically zero in all 302 recordings. §8.6 reports that, the saccade and fixation effects that did reproduce, and the indirect saccade argument. The ocular explanation for R-018 stays open and only RQ3 can close it.
- [ ] Check final Word layout, figures, and submission copy.
- [ ] Review report wording and remove pending-work statements only when evidence actually exists.
- [ ] Complete PPT and rehearse a demonstration of saved outputs and the actual pipeline.
      Draft deck built in LaTeX Beamer at `slides/slides.tex` (18 slides, compiles to
      `slides/slides.pdf`). Content review and rehearsal still outstanding.
- [ ] Submit report, PPT and executable source with outputs by 17 Nov 2026 per latest team update.

## Figure provenance

The two empirical graphics redraw values already stored in R-004 and R-012 JSON summaries.
They introduce no new fit, test, aggregation, interval or significance claim. Their source
run IDs appear in each image and caption. R-012's figure is explicitly historical. Section 8.4 reports the completed correction. The architecture diagram contains no empirical estimates.

`report_assets/pipeline.png` was redrawn on 15 Nov 2026 by `slides/make_pipeline_figure.py`,
replacing the unscripted 13 Nov version, which still labelled the Experiment 2 matched
comparison as awaiting evaluation and had overlapping box text. The diagram contains no
empirical estimates: it shows which route produced which run ID and which routes were never
executed. Figure 1's caption in the report was updated to match. `report_draft.docx` was
patched in place for that one figure: the embedded image, its alt text and the caption were
replaced and nothing else in the file was touched (verified: only `word/document.xml` and
`word/media/image1.png` differ from the previous copy).

The Word export is now built by `docs/build_report_docx.py` from `report_draft.md`, so the two
can no longer drift. Styles, page setup and the page-number footer come from
`docs/report_template.docx`, which is the 13 November document with its body removed; change
formatting there, in Word, not in the script. Rebuild with `python docs/build_report_docx.py`,
or `--check` to see what would change without writing. The rebuilt file reproduces the previous
one block for block apart from two added blank spacer paragraphs and the §8.4 Experiment 2 text,
which the old export had collapsed into a single paragraph containing raw newlines and which now
renders as the three paragraphs the Markdown actually has.

The deck adds one further graphic, `slides/figures/r017_matched.png`, generated by
`slides/make_r017_figure.py`. It redraws the per-modality Spearman values and the three
paired bootstrap intervals already stored in the R-017 JSON summary. It introduces no new
fit, test, aggregation, interval or significance claim, and carries its run ID on the figure.

## Literature verification

| Report reference | Checked source and boundary |
| --- | --- |
| [1] BBBD paper | Publisher-indexed article and PubMed 42014748; dataset description, not proof of our implementation |
| [2] Cohen et al. | Published paper at https://par.nsf.gov/servlets/purl/10096199; EEG ISC and recall |
| [3] Madsen et al. | https://pmc.ncbi.nlm.nih.gov/articles/PMC7865179/ and PubMed 33509928; do not transplant its scoring scheme into the BBBD release |
| [4] Madsen and Parra | https://pmc.ncbi.nlm.nih.gov/articles/PMC9802497/; multimodal synchrony, not our fusion performance |
| [5] EEGNet | Author manuscript https://arxiv.org/abs/1611.08024v4 and linked DOI; architectural inspiration only |
| [6] Varoquaux | https://arxiv.org/abs/1706.07581 and PubMed 28655633; uncertainty motivation |
| [7] NeuroKit2 | https://neuropsychology.github.io/NeuroKit/introduction.html; official citation |
| [8] MNE | Publisher article https://www.frontiersin.org/journals/neuroscience/articles/10.3389/fnins.2013.00267/full |
| [9] Dataset release | https://zenodo.org/records/19241964; retains release identity despite advertised newer version |
| [10] scikit-learn | JMLR article page and paper; software citation |

All checked 13 Nov 2026. Other existing BibTeX entries have not all been verified and are
not used in this draft. No numerical cross-paper leaderboard is claimed.
