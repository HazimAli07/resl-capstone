# Hazim - model, input contract and integration handoff

Prepared October 26, 2026 (Toronto), with AI coding assistance. Technical review
material for D2 #1 (1.1), #5 (2.1), #9 (3.1) and #13 (4.1).
No source permission, human approval, meeting or signature is inferred.

## Implementation

- `hazim_contract.py`: exact nine-input inference allowlist, normalized units,
  explicit categories including PUD/cooperative, access/review gates and actual
  date/tag validation. Future repayment, IDs and dates cannot enter inference.
- `hazim_training.py`: training and validation partitions only; two fixed random
  forests (64 trees, depths 4/8, leaf minimum 5, seed 42, one CPU worker).
  At most 100000 rows in each partition. Censored training labels are excluded.
  Preprocessing fits once on observed training loans and is reused everywhere.
- Labels must have `label_available_on` no later than the recorded training or
  validation cutoff. Training cutoff precedes validation loans; validation
  selection cutoff precedes final-test loans. Origination dates alone do not
  establish that a 24-month label was already available.
- Validation Brier score proposes a candidate (name resolves exact ties).
  This is a recorded proposal, not accepted model selection. No final-test
  reader or final-test score exists in this runner. It does not automatically
  compare against untrained logistic/rule baselines.
- `hazim_bundle.py`: fitted preprocessing plus forest arrays saved as JSON;
  checksum and schema checked on load, no pickle/joblib deserialization.
  Float32 threshold behavior matches sklearn. Every validation prediction is
  compared with exported inference before an artifact is saved.
- `hazim_app.py`: reuses Mannan's made-up examples and preprocessing contract,
  displays actual output from an explicitly synthetic-trained forest, reports
  imputation, and rejects real-data model packages in this preview. No accepted
  bands, personal feature attributions or lending decisions are fabricated.

The original Mannan app stays available as an unscored input preview.
This work depends on PR #20; its changes are not silently copied into main.

## Run the software experiment

From the repository root, with Python 3.12:

    python -m pip install -r requirements-model.txt -r requirements-demo.txt
    python -m resl.hazim_training --synthetic
    python -m unittest discover -s tests -v
    python -m streamlit run resl/hazim_app.py --server.address 127.0.0.1

The runner invents 120 training and 40 validation applications. These do not
come from Freddie Mac, estimate study performance or establish suitable cohort
sizes. They exist to exercise fitting, export, validation metrics and UI behavior.
A fixed test partition is deliberately absent.

Local outputs in ignored `models/hazim/`:
`forest.json`, `manifest.json`, `validation_predictions.json`.
The manifest records resolved Python/package versions, seed, fixed grid, counts,
dataset/review digests, aggregate validation diagnostics and model checksum.
Never commit fitted settings, predictions or restricted records from actual data.
The JSON checksum is an integrity check, not authentication of an unknown source;
obtain an actual artifact and its digest through controlled team access.

## Before actual-data execution

Keep `docs/data_access.json` unconfirmed until the source terms and release
are actually established. A public user guide does not grant dataset permission.

Use the selected-release dictionary to complete the original timing checklist
and the supplemental `hazim_feature_review.csv`. The nine fields are proposed
origination-time research inputs. Original interest rate, term and balance must
not be portrayed as known at an earlier application/decision stage.
First payment month is not a confirmed origination date.

Create a controlled local copy of `hazim_review.example.json`. Genuine review
must establish release, date anchor, source/code dictionary, label policy,
eligible fields, split rationale, reviewer/date and both label-availability
cutoffs. The committed template deliberately fails closed.

Upstream reviewed normalized CSVs need all FEATURES plus loan_id,
origination_date, split, target (0/1/blank) and label_available_on for observed
labels. Training/validation must be distinct chronological cohorts. The label
availability dates must reflect actual observations, not invented dates.
Record the SHA256 of both exact CSV files in the accepted local manifest.

    python -m resl.hazim_training --train-csv data/processed/train.csv --validation-csv data/processed/validation.csv --review data/processed/review.json --out models/hazim

The runner checks access and review facts before reading actual CSVs, then
checks file hashes, split dates/tags, label availability and non-overlap.
Input permission/review fields are attestations; code cannot prove their truth.
Keep final-test records in a separate controlled workflow until a human freezes
candidate, preprocessing, cutoff, calibration and capacity choices.

## Task status

| Task | Implemented | Still required |
|---|---|---|
| #1 access | Existing gate retained; explicit review/run template | Permitted access, terms and selected release |
| #5 timing | Nine-field inference contract, exclusions, timing supplement and leakage tests | Selected-release field/date/cutoff acceptance |
| #9 tree | Bounded reproducible forest runner, validation proposal, export-parity checks | Authorized-data training, baseline comparison, independent selection |
| #13 package | JSON forest and fitted preprocessing, strict load/inference, checksum, local synthetic app | Accepted actual model, calibrated bands and independent acceptance |

All four issues remain open. Synthetic CI checks do not complete actual-data
acceptance requirements. PR3 should report the software implementation and
these blockers separately.

## Review references

- Freddie Mac public general guide (retrieved October 26; January 2026 cover):
  https://www.freddiemac.com/fmac-resources/research/pdf/user_guide.pdf
  This is not a selected-release approval.
- RandomForestClassifier parameters:
  https://scikit-learn.org/1.7/modules/generated/sklearn.ensemble.RandomForestClassifier.html
- Persistence risks and environment reproducibility:
  https://scikit-learn.org/stable/model_persistence.html
- Existing label, data and Mannan handoffs remain authoritative for their scopes.
