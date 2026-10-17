# Draft outcome and censoring policy

Owner: Sweta, D2 task 1.3. Independent reviewer: Tommy. Status: proposed, awaiting team review against an authorized sample and the selected release guide.

- Horizon: months 1 through 24, inclusive, after the agreed origination/first-payment mapping.
- Positive: observed 90+ days overdue, foreclosure or REO in that window. An observed adverse event is positive even if other months are missing.
- Negative: every month 1-24 is observed, without an adverse event. Payoff at month 24 can meet the horizon; payoff before month 24 is censored.
- Early payoff without a prior event: `target=null`, `censored_early_payoff`.
- Gaps without an observed event: `target=null`, `censored_followup_gap`.
- Short/no follow-up without an event: `target=null`, `censored_incomplete_followup`.
- Unknown status, duplicate months or records after terminal payoff: stop and review. No implicit conversion to negative.

These are conservative starting rules. The team must document time-zero conventions, delinquency-code conversion, terminal outcomes, observation end date and any sensitivity analysis before modelling. Re-run comparisons when label rules change. The starter implementation does not validate a real mortgage cohort or establish a treatment for every possible source-data status.
