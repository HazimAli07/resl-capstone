# PR3 working draft and evidence - Team 2B

**Project:** RESL origination-time mortgage-risk research prototype  
**Course:** INFO53883  
**Evidence cutoff:** October 26, 2026 (Toronto)  
**Status:** AI-assisted working content draft for team verification. The official
PR3 template, reporting window and submission requirements have not been supplied.
This document does not assert that a report has been submitted.

## Progress during this checkpoint

The project now has a runnable software path from normalized candidate inputs
through training-only preprocessing, bounded tree-model development, saved-model
inference and a local synthetic demonstration. All executed training and UI
checks use invented records. No Freddie Mac loan cohort has been analysed and
no actual mortgage-model performance is claimed.

Mannan's implementation is published in PR #20. It adds explicit normalized-export
mapping, aggregate data audits, train-fitted preprocessing, matched-cohort
comparison tools and a local Streamlit/offline input preview. Its final revision
passed 57 tests and four checks.

Hazim's PR #21 builds on that branch. It adds a strict nine-field inference
contract, verified date partitions and label-availability cutoffs, two fixed
random-forest candidates, reproducible run metadata, portable JSON packaging
and an integrated synthetic-trained Streamlit preview. The full combined suite
passed 86 tests, including six Streamlit cases, without skips.

A technical integration review was posted from Hazim's account on PR #20 with
AI assistance disclosed. GitHub then recorded Mannan1398's approval of PR #21
and its merge into Mannan's branch. HazimAli07 approved PR #20; that reviewed
implementation was subsequently merged into main. Source/data/model acceptance
conditions remain separate from these code-review records.

## Hazim's task status

| D2 task | Verified software progress | Remaining acceptance |
|---|---|---|
| 1.1 / #1 access | Real-data gate retained; unaccepted run-review template added | Source permission, terms, release and years |
| 2.1 / #5 eligible inputs | Exact allowlist, timing supplement, future-field exclusions and leakage checks | Selected-release source fields, date anchor and prediction-time review |
| 3.1 / #9 tree candidate | Two bounded forests, validation-only proposal, fixed seed and metadata | Authorized-data training, baseline comparison and human selection |
| 4.1 / #13 package | Fitted preprocessing/forest JSON, checksum, inference parity and synthetic UI | Accepted actual model, calibration/bands and independent acceptance |

The four issues remain open because these acceptance conditions are unresolved.

## Verification evidence

- Full CI run 40428409304: 86 tests passed with no skips. The model and original
  demo checks include six Streamlit UI cases.
- Verified implementation revision 69dbc90f00597c462bae48c28d100c0fa78a6bdc:
  both push and pull-request Data/Hazim model checks passed.
- Synthetic training created 120 training applications (113 observed labels,
  7 censored) and 40 validation applications (37 observed, 3 censored).
- Exported inference matched sklearn on all 40 validation applications.
- Training budget: two candidates, 64 trees each, depths 4/8, minimum leaf 5,
  seed 42 and one worker. Maximum input budget is 100000 rows per partition.
- Candidate proposal uses validation Brier score with a fixed name tie-break.
  It is not an accepted final selection. Final-test data is not read.
- Optional dependency checks used scikit-learn 1.7.2 and Streamlit 1.50.0.
  Exact resolved versions, inputs/review digests and settings are recorded in
  the ignored local run manifest.
- Local standard-library run: 86 discovered, 73 passed and 13 dependency-based
  skips. Complete model/UI execution was verified in GitHub CI.

These counts validate software behavior on invented data. They are not
estimates of real mortgage accuracy, calibration, fairness or business value.

## Team and integration status

Sweta's label-boundary tests are in main through merged PR #18. Her proposed
rule-score/validation work was merged into main through PR #19. Actual baseline results, calibration and cutoffs still need reviewed data
and model predictions. Tommy is the assigned owner of split review (1.4), logistic regression (2.4),
explanation/fairness review (3.4) and final report/demo assembly (4.4).
His work is pending and planned for the next work period; no completed
implementation or verification is claimed.

The original Mannan preview remains unscored. Hazim's separate model preview
displays explicitly synthetic-trained output and refuses actual-data model
packages. Neither preview makes loan approval, rejection or pricing decisions.
Personal feature contributions and accepted risk bands have not been invented.

## Next work and blockers

1. Hazim records genuinely permitted access, applicable terms, release and years.
   The committed approval flag stays false until those facts are established.
2. The team accepts release-specific mappings, code dictionaries, a date anchor,
   label/censoring rules, eligible input timing and split/label-observation dates.
3. Run authorized-data audits and train the agreed baselines/tree candidates.
   Compare identical validation cohorts and freeze the accepted selection,
   calibration, capacity and cutoff before final-test evaluation.
4. Obtain genuine teammate review and visual acceptance. Integrate accepted
   actual model/bands into the local app and update the report with real evidence.

No real meeting dates, attendees, decisions or participation signatures have
been supplied for PR3. Add genuine records; do not reuse PR1/PR2 signatures or
invent attendance. Apply the official PR3 questions, reporting dates, formatting
and course-permitted assistance rules before submission.

## Direct evidence links

- Hazim implementation: https://github.com/HazimAli07/resl-capstone/pull/21
- Mannan implementation/review: https://github.com/HazimAli07/resl-capstone/pull/20
- Full 86-test run: https://github.com/HazimAli07/resl-capstone/actions/runs/40428409304
- Verified current PR model run: https://github.com/HazimAli07/resl-capstone/actions/runs/40428645928
- Sweta merged baseline implementation: https://github.com/HazimAli07/resl-capstone/pull/19
- Hazim tasks: issues #1, #5, #9 and #13 in the same repository.
