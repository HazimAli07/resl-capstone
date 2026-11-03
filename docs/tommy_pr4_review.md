# Tommy — independent quality and chronological-split review

Prepared November 3, 2026 (America/Toronto), with Codex assistance. This is an
independent software and evidence review for issue #4. It is not source
acceptance, an access attestation, or a claim of real-cohort validation.

## Evidence reviewed

Reviewed current `main` at `5bc462dd64d60cd39eb5cdae7b37acb8485ce2a4` and the
open draft PR #24 head `5e3e2a54c9f68a784b9483ffa773f4ce3f26ac78` separately.
PR #24 is still unmerged; its supplemental source/timing gate is a dependency
for actual-data model runs. Repository `docs/data_access.json` currently records
`permitted_access_confirmed: false`, no release, no selected years, no terms
reference, and no confirmer/date. Hazim's PR #24 review template also has
`accepted: false`, no source/date/label/split values, and nine unaccepted
per-feature timing entries. These are the repository's current recorded facts;
they do not establish whether access might exist outside the repository.

Read the README, proposed normalized data contract, access record, data checks,
Mannan mapping/preprocessing/comparison handoff and implementations, Sweta's
label review and validation tools, Hazim's input/training code and PR #24
handoff. The input allowlist is nine proposed origination fields. The data
contract explicitly says it is not the official source schema. Mannan notes
that first payment month is not an accepted origination date and that several
source mappings, category codes, status conversions and bounds remain pending.

## Review findings

| Check | Software evidence | Source/study acceptance |
| --- | --- | --- |
| Source years and cutoffs | `data_access.json` has no selected years. `hazim_contract` requires `train_before`, `test_from`, `training_as_of` and `validation_as_of`; observed labels are checked against the appropriate cutoff. | Unresolved: permitted source/release, selected vintages, calendar cutoffs, observation end, date anchor and rationale. Do not use README example dates or Tommy's invented fixtures as study dates. |
| Chronological ordering | `chronological_split` assigns `[start, train_before)` to train, `[train_before, test_from)` to validation, and `[test_from, +∞)` to test. Hazim's `validate_partition` independently checks row tags against origination dates and rejects test rows from this runner. | Unresolved: whether the source field can represent actual origination dates, any accepted proxy, and whether the proposed vintage/time windows permit 24-month follow-up. |
| Loan IDs and overlap | `check_records` rejects blank/duplicate origination IDs and orphan performance IDs. The logistic runner checks unique canonical IDs in each partition and disjoint train/validation IDs. | No source IDs or cohort counts were inspected. Require aggregate counts and overlap evidence from the permitted, mapped cohort before acceptance. |
| Duplicate, orphan and gap handling | Data checks reject duplicate loan/month performance rows, orphan loan IDs, unknown normalized statuses and invalid months. Sweta's reviewed software policy labels an observed event positive despite incomplete history; otherwise gaps/incomplete follow-up are censored. | Raw codes, duplicate/orphan/gap frequencies and edge cases remain unverified against the selected release. Distinguish a missing monthly row from an unknown code and release truncation. |
| Censoring and adequate follow-up | Draft 24-month policy includes months 1–24; an adverse event is positive, a negative needs all 24 months without an event, and early payoff or inadequate/gapped follow-up is censored. Month 25 is outside the label window. | Sweta explicitly leaves status-code interpretation, time-zero, payoff meanings and follow-up availability to selected-release review. Verify vintage coverage and the source's actual end date. Passing synthetic tests does not show adequate real follow-up. |
| Label availability | Hazim's training/validation contract requires `label_available_on` for each observed target and rejects it if earlier than origination or later than `training_as_of` / `validation_as_of`. Censored labels are null. | Availability timestamps and 24-month observation windows must be derived from real source snapshots, not inferred from loan origination or fixture dates. Confirm each label was observable by the cutoff used for fitting or validation selection. |
| Fitting and test isolation | Mannan's preprocessor fits medians, scales and category levels once on tagged training rows. Hazim's runner fits it only on observed training labels, checks train/validation disjointness and has no final-test reader. `compare_candidates` matches cohorts and only permits a test audit with a frozen model name. | A caller-provided split tag/hash is not proof of cohort provenance. Freeze candidate, preprocessing, calibration and cutoffs before a separate final-test workflow. |

## Independent assessment and remaining acceptance checks

The software has useful defensive invariants for IDs, chronology, duplicate and
orphan rows, unknown normalized statuses, censoring, preprocessing leakage and
label cutoffs. My independent acceptance remains **pending** because the code
operates on a proposed normalized schema and all committed records reviewed here
are synthetic or unaccepted. No actual Freddie Mac loan records were opened or
used. The repository does not establish selected source years, genuine access,
field mapping, actual label observability or suitable follow-up.

Before any actual model run, the owners need to complete and independently
review: (1) permitted access, source/release and selected years; (2) the
selected-release dictionary and raw-to-normalized mappings/units/missing codes;
(3) a valid origination date anchor and nine-input availability at the declared
prediction stage; (4) Sweta's actual performance/status-code, horizon, payoff,
gap and censoring interpretation; (5) train/validation/final-test dates with
adequate observation windows and actual label-availability cutoffs; and (6)
aggregate cohort, duplicate, orphan, gap, censoring and overlap counts. PR #24
is open as a draft and supplies the versioned nine-input timing gate; coordinate
its merge/integration before unblocking actual runs. Keep final-test rows out of
fitting, model selection, calibration and cutoff selection.

The November 2–8 fixture in the logistic module uses made-up 2014 and 2018
origination dates and made-up two-year label-availability dates solely to test
software. The 2018/2021 boundary values in that fixture are not recommended or
accepted mortgage study cutoffs.
