# Tommy — logistic baseline handoff

Prepared November 3, 2026 with Codex assistance for issues #4 and #8. This
handoff documents software behavior and dependencies; it is not a report
submission or independent acceptance of source/model results.

## Candidate implementation

`resl/tommy_logistic.py` reuses the nine-field input validator, Hazim's
train/validation date and label-cutoff checks, Mannan's `TrainPreprocessor`, and
Mannan's matched-cohort validation comparison. The predeclared L2 grid is
`C=(0.1, 1.0, 10.0)` with seed 42, `liblinear`, one CPU worker, at most 100,000
rows per partition and 1,000 iterations. The preprocessor and models fit only
on observed training labels. Censored training rows are counted and excluded.
All validation rows receive predictions, with censored validation targets left
null. Candidates are compared on the identical validation cohort by Brier score;
the selected item remains a candidate proposal. There is no final-test fitting,
reading or tuning interface.

Actual-data CLI execution checks access and the accepted review before opening
loan CSVs, verifies input digests against the review record, and requires
Hazim's PR #24 versioned per-feature source/timing check. Since PR #24 is still
unmerged from this branch's base, actual-data execution currently fails closed.
Synthetic fixture dates and generated predictions are explicitly marked and do
not constitute mortgage performance evidence. Local output defaults to ignored
`models/tommy-logistic/` and contains a manifest plus validation predictions;
never copy actual-data predictions or fitted artifacts into GitHub.

## Review and owner dependencies

- **Hazim:** merge/integrate PR #24, complete genuine access/release/year
  evidence and accepted source/date/input-timing review before actual execution.
- **Mannan:** provide the selected-release mapping and cohort files through
  permitted local access; independently verify the expected train/validation
  cohorts, preprocessing metadata and digest workflow. No shared schema change
  was made by this branch.
- **Sweta:** confirm the selected-release label/censoring mapping and that the
  supplied observed-label dates reflect actual follow-up/availability. The
  committed policy review identifies these as unresolved source decisions.
- **Independent teammate:** review the code and chronology/quality findings;
  this handoff does not count as approval.

Issues #4 and #8 remain open. Final-test evaluation, calibration and operational
cutoff selection remain separate and must wait until a candidate is frozen.

## Verification record

- `python -m unittest tests.test_tommy_logistic -v`: **9 passed**.
- `python -m resl.tommy_logistic --synthetic`: completed; proposal
  `logistic-l2-c-1`, 113 observed training labels, 7 censored training rows
  excluded, 40 validation predictions (37 observed, 3 censored), and no
  final-test use. This is an invented software fixture only.
- `python -m unittest discover -s tests -q`: **131 passed, 0 failed, 0 skipped**
  on the successful rerun. The first run hit three Windows temporary-directory
  permission errors in existing tests; rerunning with `TEMP`/`TMP` in the task
  workspace passed.
- `python -m compileall -q resl tests`: passed.
- The first PR GitHub Actions data-check job failed because that lightweight
  workflow does not install optional scikit-learn; it reported the new test
  class as an import error. The dedicated tests now follow the repository's
  optional-model test convention and skip when that dependency is absent. The
  local full suite still runs all 9 dedicated tests with the pinned model
  requirement installed. After the fix, all three GitHub Actions checks passed
  on commit `529c3751e81afe07fc331a6affc76e0d214b3988`; the model-checks job
  reports 131 tests run.
- Runtime was Python **3.13.15**, scikit-learn **1.7.2**, NumPy **2.5.4**, SciPy
  **1.18.1**, joblib **1.6.0**, threadpoolctl **3.7.0**, and Streamlit **1.50.0**.
  The pinned model/demo dependencies were installed into an isolated local venv.
- Python 3.12 was not available in this environment. Attempting to install the
  official 3.12 runtime was blocked by the sandbox, so the required Python 3.12
  verification remains outstanding; the Python 3.13 run is not a substitute.
