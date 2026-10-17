# Local verification - October 17, 2026

Environment: Python 3.12.14, git version 2.54.0 (Apple Git-157). The current pipeline and tests use Python's standard library. Third-party modelling, database and UI tools listed in D1/PR1 are planned; their execution has not been verified in this starter project.

Commands run from the repository root:

```bash
python -m unittest discover -s tests -v
python -m resl.check_data --origination data/synthetic/origination.csv --performance data/synthetic/performance.csv --synthetic --train-before 2018-01-01 --test-from 2019-01-01 --out results/synthetic-check.json
```

Result: all 16 tests passed locally. The synthetic example processed 6 made-up loans and 92 monthly rows: 2 positive examples, 1 complete-follow-up negative and 3 censored examples (early payoff, short follow-up and an internal gap). Split counts: 2 training, 2 validation and 2 test loans, based on arbitrary fixture dates. These are software-check outputs, not fitted-model metrics or observed borrower results.

Covered cases include event/horizon boundaries, foreclosure/REO, missing follow-up, early payoff, duplicate IDs/months, orphan joins, excluded repayment fields and disjoint chronological splits. Actual source-code mapping, units, date alignment and real cohort validation are pending.

A GitHub Actions workflow is configured separately. Its verified status and run URL must be read from GitHub, not inferred from this local test.
