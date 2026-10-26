# Sweta task evidence — October 26, 2026

Prepared with AI assistance for Sweta's review. This is an evidence snapshot, not a submitted progress report or team approval.

| Issue | Work available now | Still required |
| --- | --- | --- |
| #3 / D2 1.3 | Normalized-policy review and ten additional synthetic tests; see sweta_label_review.md | Selected guide, source mapping, authorized examples, aggregate cohort checks and independent review |
| #7 / D2 2.3 | Implementation prerequisites identified | Approved eligible inputs and documented rule thresholds/weights; implement after review, save validation predictions/settings locally, obtain independent review |
| #11 / D2 3.3 | Evaluation prerequisites identified | Actual fitted model and validation predictions, reviewed labels/splits, agreed review capacity; calibration and cutoff analysis followed by independent review |
| #15 / D2 4.3 | Local environment and reproducibility check; PR #17 review history inspected | Publish task PR and link its commit/CI results; obtain teammate review; collect actual meeting details and report/signature inputs |

## Verified in this session

- Public repository was readable on October 26. Older documents describing private visibility are historical snapshots.
- PR #17 is merged. GitHub records approval reviews from shwetachd1 on October 17; this does not establish a technical review of every source-data assumption.
- Python 3.12.14; standard-library pipeline, no modelling dependencies installed for this work.
- `python -m unittest discover -s tests -v`: 26 tests passed locally.
- `python -m resl.check_data --origination data/synthetic/origination.csv --performance data/synthetic/performance.csv --synthetic --train-before 2018-01-01 --test-from 2019-01-01 --out results/synthetic-check.json`: six synthetic loans; two positives, one negative, three censored.
- Current access record still has `permitted_access_confirmed=false`, no release and no selected years. This reports the committed record, not a claim about activities outside the repository.

## Next deliverables for remaining tasks

For #7, agree an interpretable research ranking using only reviewed origination inputs. Document units, sentinel/missing-value handling, threshold inclusivity, weights and ties. Test boundaries, missing values, input leakage and deterministic rankings. Save versioned settings and validation predictions outside Git. Do not invent a probability interpretation or select rules using test outcomes.

For #11, use validation data to compare reliability bins (counts and observed rates), Brier score, false alerts, precision/recall and workload at candidate cutoffs. Specify review capacity and tie handling before choosing a cutoff; never use test data for tuning. If fitting a calibration transform, separate fitting and evaluation through a validation subdivision or suitable out-of-fold procedure. Report sample sizes/uncertainty and use broad bands when probability claims are unsupported. Evaluate the frozen choice on held-out test data only after selection. No metrics or cutoff can be claimed from the current six fixture loans.

For #15, collect actual meeting date/time, attendees, decisions, owner actions and blockers. Link real commits, PRs and successful CI runs. Date overdue work honestly. Fresh participation signatures must come from the participants; do not reuse older signatures. Coordinate the report with the team; no submission has been made in this session.

## Alignment with supplied D1, D2, PR1 and especially PR2

The supplied PR2 records October 13–20 with a factual cutoff of October 17. Its Q1 records 16 tests and six synthetic loans/92 monthly rows; those historical counts must not be replaced with the 26 local tests run October 26. Q3 establishes Python 3.12.14 and standard-library checks as actual, while third-party modelling/UI packages remain planned. Q4 has no recorded meeting details and describes PR #17 as draft at that cutoff; the live merged state and approval belong to later evidence. Q5 assigns Sweta label/edge-case review, environment verification and Git/meeting evidence, consistent with issues #3 and #15.

D2 confirms Sweta owns 1.3, 2.3, 3.3 and 4.3. Week 6–7 prioritizes labels, payoff/gaps and tracking; baseline scoring begins Week 8 and calibration follows fitted-model/validation work. Later milestones remain part of Sweta's scope. No actual mortgage training or calibration was reported in PR2.

The PR2 template explicitly prohibits AI-generated text in submitted deliverables. These AI-assisted working notes and tests are offered for repository review, not as a submitted academic report; they are review aids. Student report wording must follow the course policy, and the team should establish what code assistance is permitted before incorporating generated code into an assessed deliverable. Do not present these notes as student-authored report text.

PR2 follow-up checks: confirm actual submission versus draft status; verify meeting details and fresh signatures with participants; reconcile changed repository visibility with the original private-repo plan; check references and document rendering before any future submission. No signatures or meeting details have been copied from the uploaded PDFs.

## Independent follow-up — October 26 (after PR #18)

PR #18 was approved by HazimAli07 and merged to main (merge commit `6f3b62bf689e95fde2f0a00357d461c35fbfa86c`). Its pull-request workflow run `40405726773` passed. The unchecked historical review box and pending wording above describe the pre-review snapshot, not the current PR #18 state. Release-specific review remains separate.

On `sweta/rule-score-validation`, Sweta's AI-assisted working components now include a public guide review supplement, a proposed point-score module, validation-only diagnostic/cutoff tooling, a fully synthetic CLI/chart and 23 additional tests. All 49 tests passed locally on Python 3.12.14; the synthetic demo ran successfully. No source mapping, actual model or real-data evaluation was added. See `sweta_independent_work.md` for exact interfaces, assumptions and remaining dependencies. These new results are October 26 work, not PR2-period activity. Current-branch CI and teammate acceptance must be recorded after publication; no meeting details or signatures have been invented.
