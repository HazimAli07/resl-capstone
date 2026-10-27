# Sweta — model integration handoff

October 26, 2026 (Toronto). AI-assisted technical review aid for tasks #7,
#11 and #15; not submitted academic-report prose. Existing teammate files
and implementations remain unchanged.

## Reuse and run

`resl/sweta_model_review.py` calls Hazim's `synthetic_cohort` and
`train_candidates` unchanged, which reuse Mannan's train-only preprocessing.
It passes each model's predictions into Sweta's existing `review_validation`
and scores the identical validation applications with `score_application`.

Python 3.12; use the existing requirements-model.txt dependencies:

    python -m resl.sweta_model_review --synthetic --max-reviews 7
    python -m unittest discover -s tests

Capacity seven is a declared software demonstration parameter, not an accepted
business budget. The CLI permits synthetic mode only; outputs must remain in
ignored repository results/ storage. No training, validation or test data from
Freddie Mac is loaded. No final-test cohort is created or read.

Outputs in results/sweta-model-review/: diagnostics.json, rule_scores.csv,
reliability.svg and manifest.json. The manifest preserves Hazim's training
report (versions, grid, counts and cohort digests), review/settings, prediction
fingerprint and output checksums. Scores remain points; no point-to-probability
conversion is performed. Rule exports retain censored cases and eligibility.

The adapter requires unique canonical validation IDs and identical IDs/targets
for every model. Existing prediction validation rejects invalid probabilities,
duplicate model-loan rows and non-validation splits. Censored labels are
excluded from metrics and counted. Rule ties are retained whole; the first
unaffordable score group stops the ranked review list. Model threshold proposals
use the existing validation optimization; these are not final policy choices.

## Executed synthetic evidence

120 training applications (113 observed), 40 validation applications
(37 observed, 3 censored). All 37 observed validation rows are scoreable.

| Component | Brier | Reviewed at budget 7 | TP | FP | Recall |
| --- | --- | --- | --- | --- | --- |
| rf-depth-4 | 0.157969 | 5 | 4 | 1 | 0.40 |
| rf-depth-8 | 0.161195 | 5 | 4 | 1 | 0.40 |
| Proposed rule ranking | Not applicable | 6 | 4 | 2 | 0.40 |

This checks software on invented records, not mortgage-model performance.
These model cutoffs were optimized on the same validation outcomes and are
optimistic; the rule threshold is fixed by ranking/capacity. Neither is accepted.
Capacity refers only to the observed-label evaluation cohort; censored loans
are not incorporated into operational workload estimates. Report score coverage
before comparing on other cohorts. No calibrator was fitted, no model was
selected by this adapter and no risk bands were adopted.

The reliability SVG uses blue/orange and distinct circle/square markers,
counts and descriptive Wilson intervals. Small bins and synthetic outcomes
cannot establish probability reliability for real applications.

## Tests and next owner

Five new integration tests cover cohort/label agreement, duplicate/missing
predictions, censored exclusions, test-split refusal, budget/tie boundaries and
escaped chart labels. Full local suite: 122 discovered, 116 passed, six optional
Streamlit tests skipped. Existing CI must independently confirm its environment.

Sweta: inspect diagnostics and guide-release label decisions; obtain teammate
review. Hazim: genuine permitted access, source/release and timing acceptance.
Mannan: reviewed normalized data and preprocessing mapping. Tommy: reviewed
chronological splits, logistic baseline and untouched final-test protocol.
Actual calibration requires an agreed held-out/out-of-fold fitting/evaluation
plan; do not fit and evaluate a calibrator on these same selected predictions.
Freeze model, calibration, review capacity and cutoff before final-test use.

#3 remains open for selected-release and authorized-data label acceptance.
#7 and #11 remain open for actual-data evidence and accepted decisions.
#15 continues; genuine meeting information/signatures are not supplied here.
