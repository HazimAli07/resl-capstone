# D2 1.3 — outcome review, October 26, 2026

Status: normalized-policy implementation checked using synthetic cases; source-guide verification and independent review remain pending. Prepared with AI assistance for Sweta's review. Related issues: #3 and #15. This is not evidence that the full task is accepted.

## Scope and results

Reviewed `docs/label_policy.md`, `resl/data_checks.py`, existing tests and the committed access record. No rule was changed. Added `tests/test_label_review.py` with ten tests. Together with the original sixteen, all 26 tests passed locally on Python 3.12.14. The six-loan synthetic CLI example also passed, preserving two positive, one negative and three censored examples. These results do not validate a Freddie Mac cohort.

| Decision | Implementation checked | Remaining source question |
| --- | --- | --- |
| Adverse event | >=90 normalized days, foreclosure or REO in months 1–24 | Confirm selected release's delinquency and terminal-status mapping; do not treat a raw monthly delinquency code as days. |
| Horizon | Month 1 and month 24 included; month 25 excluded | Agree calendar-month/time-zero mapping from source dates, including first payment and loan age. |
| Negative | All 24 months present and no event | Confirm observation end date and eligible vintage coverage. |
| Payoff | Before 24 censored; at 24 negative only with full follow-up | Verify zero-balance reasons and payoff date against the guide. |
| Gaps | Observed event remains positive; otherwise gaps censored | Separate absent rows, unknown codes and release truncation; quantify exclusions. |
| Short follow-up | No event and insufficient months censored | Establish follow-up cutoff and cohort eligibility before fitting. |
| Ambiguity | Unknown status, duplicate month or records after payoff stop processing | Resolve actual examples explicitly; do not silently discard records. |

Additional checks cover 89/90/120-day boundaries, month-one events, month-23 payoff, payoff at 24 with/without a missing month, month-25 events with short follow-up, foreclosure/REO before payoff, reversed row order, invalid month/day values and invalid records even when another row is positive.

## Review observations

- Current gap policy gives early payoff precedence over a missing-month reason when there is no event; both are excluded from binary training. Preserve the reason priority or document a change.
- Foreclosure/REO are normalized events here, not declared terminal records. Their source treatment still requires a guide review.
- The code can identify a positive from an observed event despite incomplete history. This matches the draft policy but does not remove selection bias from censoring; compare label/censoring counts across vintages and splits.
- The horizon remains fixed at 24 for this study. No actual input-timing approval or source mapping is established by passing these tests.

## Acceptance checklist still open

1. Hazim confirms permitted access, release, years, terms reference and observation end.
2. Mannan supplies the reviewed raw-to-normalized mapping and authorized edge-case examples outside Git.
3. Check guide references and source examples for each row above; record the guide version and section.
4. Produce aggregate real-cohort label/censoring counts by vintage and split, without uploading loan-level data.
5. Tommy independently reviews the policy and PR. Record any decisions and rerun tests after changes.

Do not close #3 until these requirements are satisfied. No meeting, signature or teammate review is fabricated by this record.
