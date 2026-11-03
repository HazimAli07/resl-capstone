# Mannan — source mapping and preprocessing, November 2–8, 2026

Prepared November 2, 2026 (America/Toronto) for technical review under
`Mannan1398`. Relates to #2 and #6; both remain open. Codex assisted the
implementation, tests and these working notes. Mannan must understand and verify
the contribution; this is not assessed report prose or evidence of human review.

## Starting state and scope

Read the README, normalized data contract, Mannan/Hazim handoffs, current issue
descriptions, repository task/assistance notes and PR #24's owner prompt and week
plan. No repository `AGENTS.md` was present. The initial workspace had no checkout;
a clean clone was fetched and `mannan/pr4-source-preprocessing` created from main
`5bc462dd64d60cd39eb5cdae7b37acb8485ce2a4`. There were no unrelated checkout changes.
The existing Git HTTPS credential was verified against GitHub `/user` as
`Mannan1398`; no new credential or permission was created.

Only Mannan's mapping/preprocessing modules, two dedicated Mannan test files and
this handoff change. The normalized predictor allowlist and Hazim's inference,
training, access and source-review modules are preserved. No actual mortgage
files were acquired, read, fitted or evaluated. All new fixtures are invented.

## Source mapping behavior and reference limits

Public reference checked November 2:
[Freddie Mac General User Guide, Release 48, October 2026](https://www.freddiemac.com/fmac-resources/research/pdf/user_guide.pdf),
cover and printed pages 4–8. This supersedes the January 2026 public-reference
snapshot in the historical handoff; it does **not** select the project's release.
The selected release's dictionary, layout and release notes must still be matched
to genuinely permitted files. No raw column positions have been implemented.

`freddie_origination_mapping(headers, ltv_regime=..., date_anchor=...)` builds a
proposed glossary-based specification from caller-supplied export headers. It
does not infer source names. The source concepts and conversions are:

| Normalized field | Source concept / normalized behavior |
| --- | --- |
| `loan_id` | Loan identifier; opaque nonblank unique join key, excluded from predictors |
| `origination_date` | Independently reviewed exact note/origination date; no accepted source field yet |
| `credit_score` | Classic FICO points; `9999` → missing; observed 300–850 |
| `dti` | Original DTI, percentage points; `999` → missing; observed 0–65; HARP requires missing |
| `ltv` | Original LTV, percentage points; `999` → missing; caller declares pre-2018Q2 (6–105), from-2018Q2 (1–998) or HARP (1–998) regime |
| `original_balance` | Original UPB in USD; retain disclosed $1,000 rounding |
| `original_rate` | Original annual rate in percent; do not divide by 100 |
| `original_term` | Original term in months |
| `loan_purpose` | `P` → `purchase`, `C` → `cash_out`, `N`/`R` → `refinance`, `9` → missing |
| `occupancy` | `P` → `primary`, `I` → `investment`, `S` → `second_home`, `9` → missing |
| `property_type` | `CP` → `cooperative`, `CO` → `condo`, `PU` → `pud`, `SF` → `single_family`, `MH` → `manufactured`, `99` → missing |

The existing model contract has one `refinance` category. Mapping `N` (no cash
out) and `R` (unspecified refinance) into it is explicit, lossy coarsening;
`FREDDIE_PURPOSE_MEANINGS` retains their different source meanings. Sweta/Hazim
must accept that choice or coordinate a richer shared contract before actual
use. Every documented output category is tested against the current inference
validator. PUD and cooperative remain separate.

Use the strict `read_header_export` reader before normalization for a CSV export:
it checks header uniqueness and row width before converting rows to dictionaries.
Then `normalize_origination` rejects absent required headers, unexpected headers,
changing header sets, reused source fields, invalid mapping keys/units, unknown
codes, invalid numeric values and duplicate/blank IDs. Required date/ID values
cannot be missing. Blank/null candidate values and declared sentinels stay
missing, for later training-only imputation. Extra export metadata must be
explicitly allowed; the legacy synthetic adapter retains its `split` exception.
Do not use a lossy `DictReader` conversion to claim that duplicate headers or
short physical rows were checked. Raw Freddie Mac headerless pipe files still
require a separately reviewed release-specific reader.

The date dependency is unresolved. First-payment date is a month, not an exact
origination date. Actual mapping requires `date_anchor="exact_origination_date"`
and canonical ISO dates, and rejects a source header identifying first payment.
These are attestations and guards, not proof of date provenance. Day-one
`%Y%m` conversion remains available only for legacy invented-fixture checks;
it does not establish an accepted date proxy. A monthly/quarterly proxy requires
Hazim/Tommy/Sweta to review the split and label-window contracts together.

`audit_cohort` remains aggregate-only: rows, unique/blank/duplicate origination
keys, duplicate performance months, unmatched performance rows, loans without
performance, per-input missingness and invalid numerics/categories. Structural
success does not mean an observable 24-month label or source acceptance. No
actual-data counts or missingness rates are claimed here.

## Training and saved-preprocessing boundary

`TrainPreprocessor.fit` still accepts only unique nonblank training IDs and the
nine candidate features. If labels are supplied, every row must have an observed
integer 0/1 target; censored, invalid or mixed unlabeled rows fail. Unlabeled
standalone fitting is retained for existing software fixtures. It is not proof
of observed labels, label availability or independent split review.

Hazim's existing `train_candidates` validates chronology, label availability and
partition IDs, then removes censored training rows before fitting. Regression
tests change censored training features and validation distributions and verify
identical fitted preprocessing. Separate invented validation/final-test
mutations cannot change medians, scaling, vocabulary, feature order or training
vectors. Fit rejects held-out tags and cannot be repeated. The training runner
continues to have no final-test reader.

`transform` uses the frozen training medians/scales and separate numeric-missing,
category-missing and category-unknown flags. Missing source codes never become
large numeric predictors. Unknown source codes fail mapping; a valid normalized
category unseen in training gets the preprocessor's unknown flag. All-missing
training numeric columns, nonfinite values and invalid bounds fail.

`metadata()` now returns a detached snapshot. New
`TrainPreprocessor.from_metadata()` validates and restores that snapshot without
fitting. It checks schema/version, training count, finite positive scales,
numeric bounds, vocabulary and feature order. The existing
`mannan-preprocessing-v1` format remains unchanged. JSON round trips and the
existing `ModelBundle.save`/`load_bundle(expected_hash=...)` interface preserve
transformed values, missing/unknown behavior and predictions; invalid metadata
and wrong package digests fail. No teammate package loader was changed.

## PR #24 dependency and remaining acceptance

[Hazim PR #24](https://github.com/HazimAli07/resl-capstone/pull/24) was verified
open, draft and unmerged at head
`5e3e2a54c9f68a784b9483ffa773f4ce3f26ac78`. Its current-head
[model checks](https://github.com/HazimAli07/resl-capstone/actions/runs/41484612807)
and [data checks](https://github.com/HazimAli07/resl-capstone/actions/runs/41484612871)
succeeded; its checkpoint reports 134 tests, no skips. Main's clean baseline was
independently rerun here: 122 passed, no failures or skips.

PR #24 introduces `hazim-source-review-v2`, requiring per-feature source,
dictionary, unit, missing-code, conversion and origination-timing evidence.
Inference stays `hazim-input-contract-v1`. Mannan's branch remains based on main;
Hazim's unmerged modules are not copied into this PR. Actual-data readiness
integration depends on PR #24's review/merge and a postmerge current-head check.
A detached checkout of the above PR #24 head plus only Mannan's four source/test
files passed **172 tests, no failures/errors/skips** before publication. This is
an unmerged compatibility check, not a merge or readiness approval. A draft PR
dependency record is the coordination artifact; no separate
team message or independent human approval is claimed.

The committed access record still has `permitted_access_confirmed=false`,
`release=null` and no selected years. Access/terms/release, dictionary/layout,
date anchor, purpose coarsening, input timing, performance code/label/censoring
rules and Tommy's independent chronology review remain pending. Review labels
are not access evidence. Issues #2/#6 cannot meet their full acceptance until
these dependencies and the permitted-cohort checks exist.

## Conditional local evidence procedure — not executed on actual data

After those facts are genuinely established, the owners should:

1. Record release/program/years, permitted terms and independent source/timing,
   date, label and split decisions in the reviewed manifests, using PR #24's
   accepted interface. Record the exact public dictionary/layout identity and
   local SHA-256 digests of reference files, mapping specification and input
   files. Do not fill approval flags from this document.
2. Read the accepted header export with `read_header_export`, normalize using
   the reviewed explicit mapping, and run `audit_cohort` with Sweta's reviewed
   performance conversion. Save actual aggregate missingness, duplicates,
   unmatched joins and label/censoring counts per vintage/split locally. Stop
   on schema errors. Report intentional exclusions and denominators.
3. Verify nonoverlapping train/validation IDs, date boundaries and label
   availability against independently reviewed file digests. Keep the final
   test physically separate. Use `train_candidates` only on train/validation;
   it fits preprocessing on observed training loans and exports it in the
   existing JSON model package. Do not fit on all eligible loans.
4. Save actual preprocessing/model/manifest in ignored local `models/`; save
   aggregate audit and environment evidence in ignored local `results/`.
   Record code commit, Python/resolved package versions, source/mapping/input
   file SHA-256 hashes, canonical train/validation/review digests and package
   hash. Verify saved/restored feature order, transformations and prediction
   parity before handing off the fitted package.
5. Share only permitted aggregate evidence after review. Borrower records,
   processed loan rows, predictions, actual fitted artifacts and credentials
   remain local and outside Git/cloud chats. Freeze model, calibration, capacity
   and cutoff before a separately authorized final-test evaluation.

## Reproducible software verification

An isolated `.venv` uses CPython 3.12.16. Installed the repository requirements:
`scikit-learn==1.7.2` and `streamlit==1.50.0`; core requirements remain standard
library only. Resolved model versions: NumPy 2.5.4, SciPy 1.18.1, joblib 1.6.0,
threadpoolctl 3.7.0. The complete resolved environment and software-file digests
are saved locally in ignored `results/mannan-pr4/`, not as actual cohort evidence.

Commands below run from the repository root. The setup used a workspace-local
`uv` executable to obtain Python 3.12 and install these pinned direct dependencies:

```bash
uv venv --python 3.12 .venv
uv pip install --python .venv/bin/python -r requirements.txt -r requirements-model.txt -r requirements-demo.txt
.venv/bin/python -m unittest discover -s tests -p 'test_mannan_mapping_pr4.py' -v
.venv/bin/python -m unittest discover -s tests -p 'test_mannan_preprocessing_pr4.py' -v
.venv/bin/python -m unittest discover -s tests -v
.venv/bin/python -m resl.check_data --origination data/synthetic/origination.csv --performance data/synthetic/performance.csv --synthetic --train-before 2018-01-01 --test-from 2019-01-01 --out results/mannan-pr4/synthetic-check.json
.venv/bin/python -m resl.hazim_training --synthetic --out models/mannan-pr4-synthetic
git diff --check
```

Exact local results (all commands exited 0):

| Check | Passed | Failures/errors | Skipped |
| --- | ---: | ---: | ---: |
| Clean main baseline | 122 | 0 | 0 |
| Dedicated mapping regressions | 24 | 0 | 0 |
| Dedicated preprocessing regressions | 14 | 0 | 0 |
| Full branch suite, including optional model/UI checks | 160 | 0 | 0 |
| Unmerged PR #24 head plus Mannan source/tests | 172 | 0 | 0 |

The synthetic data CLI reports six invented loans: two observed positives, one
complete negative and three censored. The synthetic training CLI reports 120
training rows (113 observed, seven censored), 40 validation rows (37 observed,
three censored), export parity on all 40 validation applications and
`final_test_used=false`. Its proposed `rf-depth-4` candidate and saved package
are development fixtures, not actual mortgage-model results. Both CLIs and
`git diff --check` passed. Final branch test logs are local
`results/mannan-pr4/{mapping,preprocessing,full}-tests.txt`; the resolved environment
and software-file SHA-256 digests are in `software-environment.json` in that same
ignored directory (SHA-256
`9b11be80605df1c7582fd2cc44533f14098ea61edcf04ad4de6333e37b3cd1ea`).
No reference-file digest is claimed because direct retrieval returned HTTP 403;
the public guide was inspected through web extraction.

The compatibility check ran from a separate detached sibling worktree based on
PR #24's exact head. It used the main checkout's isolated Python executable:

```bash
../resl-capstone/.venv/bin/python -m unittest discover -s tests -v
git diff --check
```

Its local `results/pr24-integration-tests.log` has SHA-256
`fe5dd2ca9998faffd6af06b1d0ac116b7761fb653a1cb690982116ed744904d9`.
This does not claim future checks or a teammate's approval.

## Factual handoff for Sweta

Review the explicit source/category table, missing codes, regime bounds and N/R
coarsening. Confirm the selected dictionary after permission/release selection;
the public reference alone does not establish that choice. Resolve the exact
date/proxy decision with Hazim and Tommy before source conversion or chronology
acceptance. Your performance delinquency/terminal-code and 24-month censoring
review remains separate: a delinquency bucket such as `03` is not three days.

After source and split acceptance, consume the same normalized observed cohort
and locally persisted training-fitted preprocessing/package. Use validation
outputs for the baseline/calibration comparison, retain censored counts and keep
the final test isolated. No actual baseline, calibrated probability, adopted
band/cutoff, team review, meeting, signature or report submission was produced.

`docs/sweta_work_status.md` records that the PR2 template prohibits AI-generated
text in submitted deliverables, and `docs/team_tasks.md` requires owner
understanding and verification. These notes are disclosed technical review aids;
they do not certify that code assistance is course-approved. Students must apply
the course rules to assessed work. No private course PDF was opened or uploaded.
Merging, report submission, public deployment and separate team messages remain
outside this work's authorization.
