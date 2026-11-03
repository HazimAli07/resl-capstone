# Hazim PR4 input and experiment readiness - November 2, 2026

AI-assisted implementation for review, linked to D2 tasks 1.1 / #1, 2.1 / #5 and 3.1 / #9. This record does not attest to data permission, a teammate meeting or independent acceptance.

## Completed in this change

- Added a read-only readiness command reporting access, source/timing review, labels/splits and exact input-digest blockers. It reads JSON evidence records, not loan CSVs, and cannot train a model or inspect the final test.
- Actual-data training now requires a versioned, per-feature source/timing review. Each of the nine inputs needs a source field, dictionary reference, explicit missing-code list, conversion, normalized unit and accepted origination availability. A single accepted boolean does not substitute for this record.
- The implemented nine-input contract requires an origination-stage review. It cannot be relabelled as a model for an earlier application decision; that would require a separately reviewed feature contract.
- Access records reject non-text/blank evidence, duplicate/boolean/future years and future confirmation dates.
- Retained closed defaults: committed access and review records are unaccepted. No licensed data, approvals or real-model results were invented.

## What was run

The isolated local Python 3.12.14 environment installed the repository's pinned scikit-learn 1.7.2 and Streamlit 1.50.0. All **134 tests passed, with no skips**, including existing Streamlit/model cases and 12 new source/readiness regression tests. These verify software using synthetic fixtures and invented test attestations.

    .venv/bin/python -m unittest discover -s tests -v
    .venv/bin/python -m resl.hazim_readiness --out results/pr4-readiness.json

The readiness command returned exit 2 and ready=false, correctly identifying unconfirmed permitted access, missing accepted timing/source review and absent reviewed file hashes. It reported loan_files_read=false, model_trained=false and final_test_used=false. Expected blocked output is not a passing data-acceptance result.

## Current official reference and access route

Freddie Mac's public general guide currently identifies Release 48, October 2026. It describes an origination snapshot and a first-payment date; the latter must not silently become an exact origination date. Original rate is a term at origination, so availability at an earlier decision point remains a separate question. Public documentation does not approve the team's source, selected years, proxy or conversions.

- Dataset resource: https://www.freddiemac.com/research/datasets/sf-loanlevel-dataset
- Current general guide: https://www.freddiemac.com/fmac-resources/research/pdf/user_guide.pdf
- Official portal: https://claritydownload.fmapps.freddiemac.com/CRT/#/sflld
- Dataset terms: https://capitalmarkets.freddiemac.com/crt/docs/pdfs/fre_terms_conditions_sflld.pdf

A Clarity account/access request is being prepared with Hazim. Do not record successful access, a downloaded release or permission confirmation until the actual portal result and applicable terms have been checked. Selected vintage years are still unset. Raw records must remain in ignored local data/raw/ and data/processed/ storage. Do not distribute source loan records through GitHub or paste them into cloud chats.

## Team handoff

1. Hazim completes account/access evidence and source/input timing review with genuine human/source confirmation.
2. Mannan maps the selected release, records conversions/missing codes and passes accepted normalized fields to the existing preprocessing.
3. Sweta checks label/status/censoring and dictionary interpretations. Tommy independently checks cohort/split and label-observation dates.
4. Populate a controlled local copy of docs/hazim_review.example.json only after these facts are established. Then run the read-only readiness command. Human approval of the facts is still required even if all structural checks pass.
5. Actual training stays behind these gates. Final-test data remains outside this development workflow.
