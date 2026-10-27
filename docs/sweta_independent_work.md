# Sweta — independent research tools

D2 tasks 2.3, 3.3 and 4.3; guide supplement supports 1.3. Prepared with AI assistance for technical review, not as assessed report prose. This branch adds only Sweta-owned files and updates her evidence notes. Existing ingestion, mapping, split, access and teammate deliverables remain unchanged.

## Run and repeat

Python 3.12.14; standard library only. No installation is needed.

```bash
python -m unittest discover -s tests -v
python -m resl.sweta_demo --out results/sweta-synthetic
```

The demo reads no external files. It creates six hand-designed score examples and eight invented probability/label pairs. Output stays in ignored `results/`: `report.json`, `synthetic_predictions.csv`, and `synthetic_reliability.svg`. No trained model, real validation results or adopted cutoff is produced. The existing CI discovers the new tests, including the demo CLI test.

## 2.3: proposed point score

`resl/rule_score.py` exposes `score_application(row, settings=PROPOSED_SETTINGS)`.

| Input | Points |
| --- | --- |
| credit_score | <=620: 2; >620 and <=680: 1; >680: 0 |
| dti (percentage) | >=43: 2; >=36 and <43: 1; <36: 0 |
| ltv (percentage) | >=90: 2; >=80 and <90: 1; <80: 0 |

Total = sum of equal-weight components, range 0–6. Higher values rank greater hypothesized risk. These thresholds/weights are illustrative proposals for synthetic development, without empirical or underwriting-policy justification. They require review and validation; they are not Freddie Mac rules or loan approval decisions. No probability or validated risk band is assigned, and dividing by six does not create one.

Bounds are development checks: credit 300–850, DTI 0–65, LTV 1–998. These are not a completed release-specific mapping; cohort-specific bounds/units still require review. `None`, blanks, unavailable sentinels (9999 credit, 999 ratios), invalid numbers, infinities and out-of-range values cause a null score with explicit reasons. Partial component details are retained but never summed into a usable score when any input is invalid. No imputation is fitted. Ratios are percentage points, not fractions; the caller must establish units.

Only credit, DTI and LTV are read. Other fields, including IDs/outcomes/repayment records, have no effect. Settings validation rejects predictor additions outside that allowlist. Equal totals remain tied; do not break ties with loan IDs or later outcomes. The canonical settings hash and version accompany every result. Any change to rules requires a new version, review and repeated comparisons. A modified settings dictionary is supported only with the explicit proposed-synthetic status.

Before actual use: Hazim reviews input timing and permission, Mannan supplies reviewed normalized/prepared inputs, and Tommy provides agreed splits. Adapt the development-only settings and source-specific missing-value handling through a reviewed change. Save actual settings and loan-level validation scores locally outside Git. Compare all baselines on the same eligible loan group.

## 3.3: validation diagnostics

`resl/validation_review.py` exposes `review_validation(rows, max_reviews=..., bins=5)` for one model at a time. Each row requires a canonical unique `loan_id`, `split="validation"`, binary `target` (null/blank for censored), and a finite `probability` in [0,1]. Censored loans are counted and excluded from labelled diagnostics, never relabelled negative. Invalid schema, duplicates and train/test rows are rejected. A split label cannot prove provenance: the caller must audit chronology, IDs, preprocessing, sampling and prediction generation.

Returns Brier score, event prevalence, equal-width reliability bins with counts and descriptive Wilson 95% intervals, and every distinct probability cutoff with TP/FP/TN/FN, precision, recall, false-positive rate, false-alert share and review workload. Undefined ratios and empty bins use null. Bins include their lower boundary and exclude the upper, except the last includes 1. Brier measures overall probability error, not calibration alone. Inspect bins and sample sizes together; the Wilson intervals assume independent observations and do not establish temporal/generalization uncertainty.

`max_reviews` is an integer operational budget supplied before analysis. Thresholds include p >= cutoff. Tied probabilities stay together; unused capacity is possible. The proposed selection rule maximizes validation positives captured within the budget, then minimizes false alerts and review volume. A separate `review_none` candidate handles zero capacity and no feasible tied group. With only one observed class, no cutoff is proposed. The illustrative optimization is not an agreed business cost function. Team members must agree capacity, false-alert tradeoffs and the final selection objective.

These tools do not train, recalibrate or choose the final model. Do not pass rule points or normalized rule points as model probabilities. Do not assess a fitted calibrator on the same data used to fit it. If calibration is needed, use an appropriate held-out or out-of-fold design; select settings/cutoffs on validation data, freeze decisions, then evaluate once on untouched test data. Validation selection metrics can be optimistic. Use natural prevalence, report censoring and vintage distributions, and investigate small-sample or temporal uncertainty before displaying probabilities.

Background references checked October 26 (no scikit-learn dependency was added):
- Probability calibration: https://scikit-learn.org/stable/modules/calibration.html
- Decision-threshold tuning: https://scikit-learn.org/stable/modules/classification_threshold.html

## What is complete and what is blocked

Independent components implemented: proposed score, validation diagnostic/selection tooling, synthetic integration example/chart, tests and guide-review supplement. Actual baseline performance, calibrated mortgage probabilities, final review cutoff and source-cohort label validation remain pending team inputs. The six score cases and eight probability cases are separate invented demonstrations, not a validation cohort or evidence of performance. Do not close #3, #7 or #11 on this evidence alone. #15 continues across the project; meeting facts and signatures must come from participants.

## Handoff for the next teammate

### Files and ownership

| File | Purpose and next action |
| --- | --- |
| `resl/rule_score.py` | Sweta 2.3: proposed point-score engine/settings, input warnings and settings fingerprint. Review thresholds/units before connecting prepared data. |
| `resl/validation_review.py` | Sweta 3.3: per-model validation diagnostics and capacity-constrained cutoff proposal. Supply genuine validation predictions only after provenance review. |
| `resl/sweta_demo.py` | Sweta 2.3/3.3: repeatable synthetic examples and chart. Run to learn interfaces; it does not load real data. |
| `tests/test_sweta_tools.py` | Sweta tests: 23 additional methods, including hand-calculated metrics and integration checks. Existing tests remain unchanged. |
| `docs/sweta_guide_review.md` | Sweta 1.3: public guide findings and unresolved release/date conventions. Append selected-release evidence later. |
| `docs/sweta_work_status.md` | Sweta 4.3: append-only activity snapshots, PR #18 acceptance and the new independent work. |
| `docs/sweta_independent_work.md` | Sweta handoff: this file, decisions, APIs, run instructions, limits and blockers. |

No existing files outside Sweta's work-status note were edited. New modules are additive and are not wired into another owner's ingestion, preprocessing, training or split pipeline. No task assignments, access flags, original fixtures, reports or historical test counts were changed.

### API examples

```python
from resl.rule_score import score_application
from resl.validation_review import review_validation

# Made-up input: this returns a research point total and component breakdown.
score = score_application({"credit_score": 680, "dti": 36, "ltv": 80})
assert score["score"] == 3

# Invented values to demonstrate the schema, not results from a trained model.
rows = [
    {"loan_id": "SYNTHETIC_A", "split": "validation", "target": 0, "probability": .1},
    {"loan_id": "SYNTHETIC_B", "split": "validation", "target": 1, "probability": .8},
]
diagnostics = review_validation(rows, max_reviews=1)
assert round(diagnostics["brier_score"], 3) == .025
```

### Check before connecting actual data

1. Resolve the selected-release guide/version discrepancy with Hazim; retain the applicable reference and terms record.
2. Have eligible input definitions and source mapping reviewed by their owners. Confirm ratio units and unavailable codes. Sweta's score uses three proposed inputs only; it does not approve them for use.
3. Have Tommy's chronology and loan-disjoint split rules available. Use the same eligible cohort for baseline comparisons. Keep identifiers solely for joining/audit.
4. Review Sweta's thresholds and weights. Record why they were chosen and any validation-only changes; never infer probability from points. Export loan-level scores only to local excluded storage.
5. For calibration, require one row per validation loan per model, frozen prediction provenance and natural class prevalence. Exclude censored labels with counts. Agree capacity and false-alert tradeoffs before choosing a cutoff. Training data cannot double as calibration evaluation data.
6. Freeze approved choices and hand the specification to the owner of final test comparisons; this module intentionally refuses test-split inputs for cutoff tuning.
7. Record an actual teammate review and current CI run for this PR. Do not close source-data acceptance issues or claim actual model performance from synthetic checks.

### Verification and activity record

October 26: started this branch from merged PR #18 (`6f3b62b`); inspected the committed contract/access record; checked the public guide; implemented additive research tools; ran 49 unit/integration tests successfully and both synthetic commands. Generated outputs remain under ignored `results/`. Python runtime is 3.12.14; all committed executable code uses the standard library. The SVG is blue (#0072B2) with a grey dashed reference line, visible labels and interval marks; meaning does not depend on colour alone.

Publication/CI/review links will be supplied on the new pull request. Meeting details, signatures, selected release, actual input data, fitted models and actual probability/cutoff results remain unavailable in this work. No claim is made about work outside the repository.

## Follow-up: connected to the existing RESL pipeline

The independent score is now composed with the repository's existing code through `resl/sweta_pipeline.py`. This is an additive Sweta 2.3 integration; existing project functions and data are not edited.

```bash
python -m resl.sweta_pipeline --synthetic --train-before 2018-01-01 --test-from 2019-01-01
```

The demonstration dates are the existing README's fixture dates, not adopted cohort splits.

| Existing project component | Reused by Sweta's runner |
| --- | --- |
| `data_checks.summarize` | Runs `check_records` and the existing `outcome` policy; retains its quality counts and label/censoring reasons. |
| `data_checks.chronological_split` | Assigns loan-level membership using caller-supplied chronological boundaries. |
| `data_checks.feature_record` | Keeps IDs, dates and later performance data out of score inputs. |
| `data/synthetic/origination.csv` and `performance.csv` | Used as-is for the integration check. |
| Sweta's `score_application` | Adds points and per-feature explanations to the already checked loan records. |

Outputs are restricted to ignored `results/` storage. `rule_scores.csv` preserves each loan's score, target, censoring reason, split, input warnings, component explanation and settings fingerprint. `validation_rule_scores.csv` contains validation rows only, retaining censored/ineligible rows explicitly. `manifest.json` saves settings, Python version, input/code/output hashes, quality counts and split/eligibility counts. Points are not renamed probabilities or passed into calibration.

Observed integration result on the unmodified six-loan fixtures: two train, two validation and two test loans. Eligible labelled/scored counts are two, zero and one respectively. Both validation fixtures are censored. Therefore there is no eligible validation cohort for a baseline-performance estimate in this fixture set. This is a documented limitation, not a reason to change another owner's data or split choices. The overall label counts remain two positives, one negative and three censored loans.

`tests/test_sweta_pipeline.py` adds eight integration tests: agreement with existing labels/counts, chronological membership, no outcome leakage into scores, explicit censoring, missing-input abstention, propagation of upstream join/duplicate failures, validation export/manifest hashes, and synthetic/input/output guards. All 57 project tests passed after this addition.

The CLI currently refuses real-data mode because the score settings are proposed. The in-memory composition exposes the intended handoff interface; real integration requires the previously listed permission/mapping/input/split approvals. Calibration still requires actual fitted-model validation probabilities, which the existing repository does not currently supply. Sweta's calibration diagnostic API is ready to consume that future output, but no probabilities are fabricated from the rule-score pipeline.
