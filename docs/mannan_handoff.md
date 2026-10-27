# Mannan — independent implementation and handoff

Prepared October 26, 2026 with AI coding assistance for review under Mannan's
account. This is technical work and a review aid, not submitted report prose.
Related tasks: #2 (1.2), #6 (2.2), #10 (3.2), #14 (4.2).
No task is declared fully accepted by this contribution.

## What is implemented

| File | Purpose |
|---|---|
| resl/mannan_mapping.py | Explicit header-export mapping; aggregate missingness, duplicate and join audit |
| resl/mannan_preprocessing.py | Training-only median imputation, scaling, one-hot encoding and missing/unknown flags |
| resl/mannan_comparison.py | Matched-cohort validation metrics and a single frozen-candidate final-test audit |
| resl/mannan_demo.py | Validated synthetic application service and offline HTML fallback |
| resl/mannan_app.py | Optional local Streamlit form over the same service |
| tests/test_mannan_work.py | Mapping, leakage, hand-calculated metrics, censoring and demo checks |

Existing teammate code, access record, labels, split choices and task ownership
were not changed. Work does not depend on unmerged Sweta PR #19.

## 1.2 — proposed mapping and unresolved source decisions

Public reference inspected: Freddie Mac General User Guide, retrieved October 26,
2026, whose cover reads January 2026:
https://www.freddiemac.com/fmac-resources/research/pdf/user_guide.pdf

This is a reference proposal, not the selected-release dictionary. Compare the
release notes and downloaded file layout before implementing a positional parser.
Store exact file hashes and release identity locally.

| Normalized field | Source concept | Unit/conversion or unresolved decision |
|---|---|---|
| loan_id | Loan sequence number | Opaque join key; never a predictor |
| origination_date | No equivalent date accepted yet | First payment month is not the note/origination date; agree a date proxy before splitting |
| credit_score | Credit score | Points; 9999 is missing; verify availability timing |
| dti | Original DTI | Percentage; 999 is missing; selected-release bounds required |
| ltv | Original LTV | Percentage; 999 is missing; vintage-specific bounds required |
| original_balance | Original UPB | Original USD amount; preserve disclosed rounding |
| original_rate | Original interest rate | Annual percentage; no fraction conversion |
| original_term | Original loan term | Months |
| loan_purpose | Loan purpose | Explicit code dictionary still needs approval |
| occupancy | Occupancy status | Explicit code dictionary still needs approval |
| property_type | Property type | Keep PUD distinct; app categories are illustrative |
| month_on_book | Reporting month and agreed start anchor | Derive a continuous month index; modified loan age can reset |
| delinquency_days | Delinquency status bucket | Bucket is not an exact day count; agree lower-bound encoding with Sweta |
| status | Delinquency and terminal-event fields | Preserve REO and terminal-code meaning; unknown codes must stop conversion |

The adapter intentionally handles only reviewed *header exports*. It does not
interpret raw pipe positions or performance codes. Calling it with
synthetic=False requires reviewed=True and a named release, but those arguments
are attestations, not evidence or access permission. The existing real-data CLI
access gate remains authoritative. Do not set approval flags to bypass it.

Mapping shape (identity example for made-up normalized data):

    mapping = {field: {"source": field} for field in ORIGINATION_FIELDS}
    rows = normalize_origination(rows, mapping, release="synthetic-v1", synthetic=True)

A spec may include source missing-code strings and date_format. If using YYYYMM,
the conversion explicitly emits day 1; this must not silently become a true
origination date. Categorical code conversion is an outstanding upstream step.

audit_cohort(origination, performance) returns aggregates only, including the
normalized structural pass/fail flag. Missing follow-up is reported separately;
a structural pass does not mean every loan has an observable 24-month outcome.
The numeric bounds in preprocessing are broad proposed interface checks, not
selected-release validation or underwriting policy. Null/sentinel rates count as
missing; invalid numeric rates remain separately inspectable.

## 2.2 — preprocessing API and leakage boundary

    prep = TrainPreprocessor().fit(training_rows)
    X_train = prep.transform(training_rows)
    X_validation = prep.transform(validation_rows)
    X_test = prep.transform(test_rows)
    columns = prep.feature_names()

Every fit row must have a unique nonblank loan_id and split="train". Only the
nine existing FEATURES are used. Missing numeric values use training medians;
scaling uses the imputed training distribution. Constant columns use scale 1.
All-missing training numeric columns stop processing. Missing and unknown
categories have distinct indicators. Transform and repeated inference never fit.
A fitted object cannot be refitted. NaN/infinity, invalid bounds and fractional
integer fields stop processing. Source sentinels become missing, not large values.

The training owner must independently verify split IDs, dates, hashes and label
availability. A supplied split tag does not prove provenance. Reuse this same
fitted object at inference; Hazim's model packaging task must persist it with
the selected model and compatible software metadata. Actual-data categories and
fitted metadata stay local. No serialization/model package is claimed here.

## 3.2 — comparison API

    report = compare_candidates(prediction_rows, capacity=100, threshold=0.5)

Each record contains model, loan_id, split, target (integer 0/1 or None) and
probability (finite 0..1). Validation candidates must share exactly the same IDs
and labels. Output includes cohort/event counts, censoring, precision/recall,
false alerts, Brier score and cases found within an integer review budget.
Whole tied groups are kept together; the first group that exceeds capacity is
not partially selected. Undefined rates are None, not an invented zero.

Metrics and review capacity apply to the observed-label evaluation cohort;
censored applications are excluded from those workload figures. Report them
separately before claiming operational review demand.

Human selection must use validation evidence. Then freeze candidate, preprocessing,
cutoff, capacity and run metadata. The final audit accepts only that candidate:

    final = compare_candidates(test_rows, capacity=100, threshold=frozen_threshold,
                               split="test", frozen_model="chosen_name")

This interface cannot prove that a caller has never examined the test set.
Access controls and a real experiment record remain required. No actual model
predictions or loan-cohort performance have been produced by this work.

## 4.2 — local demonstration

From the repository root:

    python -m resl.mannan_demo
    python -m streamlit run resl/mannan_app.py --server.address 127.0.0.1

The first command uses only the standard library and produces
results/mannan-demo/offline_demo.html and synthetic_previews.json. Open the HTML
offline; it has three expandable made-up examples and no external assets.

Streamlit is an optional dependency and was not available in the execution
environment. The package installation attempt could not resolve a distribution.
Install Streamlit from its official package, record the resolved version and
rerun the optional AppTest before accepting the UI. No unverified dependency
pin was added to the existing requirements.

The app validates inputs and displays an Unscored band, missing-field feedback
and input summaries. These are not model attributions. It cannot invent a risk
probability while the reviewed model and accepted bands are unavailable.
Connect Hazim's saved-model contract and Sweta's accepted calibration/bands later.
The app neither loads arbitrary artifacts nor writes applications to disk.
Use made-up inputs and localhost only.

## Validation actually completed

Python 3.12.14:

    python -m unittest discover -s tests -v

55 tests discovered: 54 passed and 1 optional Streamlit AppTest skipped because
Streamlit is not installed. The 29 new checks include the optional UI test.
The standard-library demo completed with three made-up cases and no model.
The original synthetic pipeline also passed: six loans, two positives, one
negative and three censored. These are software checks, not fitted-model results.

Official API references:
- https://docs.streamlit.io/develop/api-reference/app-testing/st.testing.v1.apptest
- https://scikit-learn.org/stable/common_pitfalls.html (train/transform boundary guidance; no sklearn dependency introduced)

## Required review before acceptance

Hazim: access/release and eligible-input timing; date anchor; saved-model contract.
Tommy: split provenance and preprocessing/matched-cohort checks.
Sweta: raw outcome-code conversion, censoring and reviewed band integration.
Mannan: inspect and understand the assisted implementation and run it locally.

Selected-release mapping, actual cohort results, fitted-model comparisons,
Streamlit runtime testing and end-to-end trained-model app behavior remain open.
No independent teammate review, meeting, signature or actual-data result is claimed.
