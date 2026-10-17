# Proposed normalized data contract

This is a starter interface for synthetic checks, not the official Freddie Mac schema. Mannan must map the selected release using its current data dictionary before actual data is read. Preserve a mapping table of raw field, normalized field, unit, missing code, timing and conversion. Record file checksums and row counts locally without uploading loan-level data.

## origination.csv

One row per loan. Required identifiers: `loan_id` (nonblank and unique), `origination_date` (ISO date). These fields are metadata and are excluded from prediction inputs.

Candidate inputs: `credit_score`, `dti`, `ltv`, `original_balance`, `original_rate`, `original_term`, `loan_purpose`, `occupancy`, `property_type`. All require documented availability at application/origination. DTI and LTV are percentages, rate is annual percent, balance is original currency amount, term is months. These units are proposed and must be checked against the actual release. Missing values are reported, not silently replaced. Encoding, imputation, bounds and model preprocessing remain future work.

## performance.csv

One row per loan per month. Columns: `loan_id`, `month_on_book` (integer, first month = 1), `delinquency_days` (integer >= 0), `status` (`active`, `paid_off`, `foreclosure`, `reo`).

Freddie Mac delinquency/status codes and first-payment dates require a documented adapter. They must not be passed directly into these normalized fields without validation. Unknown codes, missing delinquency values, duplicate months and orphaned loan IDs stop processing. Later repayment, current balances, zero-balance codes and outcomes never become candidate prediction inputs.

## Output and split

The 24-month target is `1`, `0` or `null` with a reason. Censored records stay separate from negatives. Split by origination date using documented boundaries; final test loans stay out of preprocessing fitting, tuning and cutoff selection. Demonstration boundaries in the README are arbitrary test settings, not a chosen study design.
