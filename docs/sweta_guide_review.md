# D2 1.3 — guide review supplement, October 26, 2026

AI-assisted technical review aid for Sweta and the team; not progress-report prose.

## Public reference checked

Freddie Mac, *Single-Family Loan-Level Dataset General User Guide*, public PDF retrieved October 26, 2026:
https://www.freddiemac.com/fmac-resources/research/pdf/user_guide.pdf

The retrieved cover says January 2026, whereas D2 cites July 2026. Hazim must identify the guide matching the selected release; this review does not select a release or confirm permission.

## Guide findings (printed page numbers)

- Pages 10–11: delinquency codes describe bands; code 3 corresponds to 90–119 days. RA identifies REO acquisition. A raw code must not be interpreted directly as days.
- Page 11: loan age uses first-payment timing and can reset for modifications. Review chronology against original dates before applying a 24-month window.
- Pages 11–12: zero-balance reasons differ; voluntary payoff is distinct from sales, charge-offs and REO disposition. A zero balance alone cannot establish the outcome.

## Decisions still owned by the team

These are study choices, not rules supplied by the guide: the exact time origin/window, whether gaps without an observed event are excluded, payoff censoring, and treatment of non-payoff exits. The existing conservative normalized policy remains unchanged. No raw adapter, field mapping, split or permission record has been modified.

For the selected release, record the guide version, column definitions, date calculation and handling of unknown/terminal cases; inspect authorized examples outside Git. Compare aggregate counts by vintage and split and obtain review. This completes a public-reference check only; #3 remains open for release-specific and real-data acceptance.
