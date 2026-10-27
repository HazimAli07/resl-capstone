# RESL capstone - Team 2B

INFO53883 pre-loan mortgage-risk research prototype. We use information available at application/origination to study adverse outcomes within 24 months. Later repayment records construct labels only. The eventual app supports human review; it does not approve, reject or price loans.

## Development checkpoint - October 26, 2026

Mannan's [PR #20](https://github.com/HazimAli07/resl-capstone/pull/20) adds normalized-data audits, train-fitted preprocessing, comparison tools and a local input preview. Hazim's [PR #21](https://github.com/HazimAli07/resl-capstone/pull/21) builds on it with label-availability/date gates, bounded random forests, portable JSON model packaging and a separate synthetic-trained Streamlit preview. Mannan approved PR #21 and merged it into his branch; Hazim approved PR #20, which is now merged into main. Sweta's PR #19 is also merged. Source/data/model acceptance remains pending.

The combined development suite passed **86 tests**, including six Streamlit cases, in [CI](https://github.com/HazimAli07/resl-capstone/actions/runs/40428409304). All training checks use invented data. Actual source access/release, source/date/code acceptance, cohort results, model comparison, calibration/bands and final model/demo acceptance remain pending.

See [Hazim's handoff](docs/hazim_handoff.md), [Mannan's handoff](docs/mannan_handoff.md) and the [PR3 working draft/evidence](docs/pr3_evidence.md). To run the synthetic-trained model preview from Hazim's branch:

```bash
python -m pip install -r requirements-model.txt -r requirements-demo.txt
python -m resl.hazim_training --synthetic
python -m streamlit run resl/hazim_app.py --server.address 127.0.0.1
```

## Baseline snapshot - October 17, 2026

The repository and starter data checks were created on October 17. The checks have been exercised on made-up records only. Freddie Mac permission, release selection, raw-field mapping and cohort checks remain pending. No model has been trained and no Streamlit app has been built. The team must review the starter code and label policy before using them for its study.

## Run the starting pipeline

Python 3.12 is the verified starting environment. The current code uses only Python's standard library; no packages need installing.

```bash
python -m unittest discover -s tests -v
python -m resl.check_data --origination data/synthetic/origination.csv --performance data/synthetic/performance.csv --synthetic --train-before 2018-01-01 --test-from 2019-01-01 --out results/synthetic-check.json
```

The output reports missing fields, joins, outcome/censoring counts and a chronological split. It is a software check on synthetic records, not evidence of mortgage-model performance. `results/` stays outside Git; the small synthetic verification summary is in `docs/verification.md`.

## Before working on actual loans

1. Hazim records the permitted source, terms, release and selected years in `docs/data_access.json`.
2. Mannan maps the selected Freddie Mac release into the proposed normalized schema in `docs/data_contract.md` and checks units and dates.
3. Sweta reviews the outcome/censoring rules in `docs/label_policy.md` against the guide and sample records.
4. Tommy reviews the data checks and proposes split dates based on available vintages. The demonstration dates above are examples only.

Use local `data/raw/` and `data/processed/` directories for licensed records. Keep both outside Git. Do not change the access approval flag until permitted access has actually been confirmed. The pipeline rejects real-data runs while that record is unconfirmed.

## Repository layout

- `resl/`: normalized-data checks and a command-line entry point.
- `data/synthetic/`: clearly labelled, hand-created test records.
- `docs/`: data contract, input timing, label policy, access record and team tasks.
- `tests/`: outcome, leakage, join and chronological-split checks.
- `.github/`: automated checks and a teammate-review template.
- `results/`: local outputs excluded from Git.

## Work and reviews

Each D2 task has an issue. Work in a task branch, link the issue in a pull request, include what you ran, and ask another teammate to review. Do not count opening an issue as completing its task. See `docs/team_tasks.md` for near-term work and `docs/sprint_log.md` for the evidence record. Student names in task records are proposed owners from D2, not claims that they wrote or approved this initial code.

Never commit loan records, borrower-level outputs, credentials, trained artifacts containing restricted data, or large output files. Keep aggregate results, run settings, code and permitted documentation. No licence to redistribute the source dataset is granted by this repository.

## Planned final outputs

Rule-score, logistic-regression and tree-model comparisons; precision/recall, review capacity and calibration checks; explanation/fairness limitations; a local Streamlit demo with made-up applications; D3/D4 reports and D5 slides/live demonstration. The D2 plan starts the app in W12, tests it in W13 and demonstrates it in W14. Public cloud hosting is not part of the current commitment.
