# Sweta PR4 technical evidence — November 2–8, 2026

Codex-assisted implementation and review notes for Sweta (`shwetachd1`), recorded November 2. Relates to #3, #7 and #15; all remain open. These are factual technical aids, not assessed report prose or participant certification. The repository's prior course-policy notes prohibit AI-generated submitted narrative; students must author the report and verify current assistance rules. No report, GPS, signature, message, merge or deployment is authorized by this handoff.

## Checkout and preserved integration

Fresh clean clone; no pre-existing unrelated changes. Fetched main at `5bc462dd64d60cd39eb5cdae7b37acb8485ce2a4`; created `sweta/pr4-label-baseline`. No AGENTS.md was found. Read README, PR template, label policy/tests, Sweta handoffs, Mannan handoff, requested modules and live issues. GitHub connector authenticated account: `shwetachd1` (ID 15314311), verified before publication.

Preserved merged PRs [#18](https://github.com/HazimAli07/resl-capstone/pull/18), [#19](https://github.com/HazimAli07/resl-capstone/pull/19), [#23](https://github.com/HazimAli07/resl-capstone/pull/23). Their merge commits respectively: [6f3b62b](https://github.com/HazimAli07/resl-capstone/commit/6f3b62bf689e95fde2f0a00357d461c35fbfa86c), [3412a58](https://github.com/HazimAli07/resl-capstone/commit/3412a5858d62a69e27ea9f42635d8f3acdfd7269), [5bc462d](https://github.com/HazimAli07/resl-capstone/commit/5bc462dd64d60cd39eb5cdae7b37acb8485ce2a4).

## #3: public reference and review questions for Mannan

The live [public General User Guide](https://www.freddiemac.com/fmac-resources/research/pdf/user_guide.pdf), checked November 2, identifies Release 48, October 2026. This supersedes the January-cover reference in historical notes, but does not select our release or grant access. `docs/data_access.json` still has permission false, release null and no years. No authorized records were accessed. Joint review with Mannan has **not** occurred; the following is the review agenda.

| Public reference finding (printed pages) | Pending team/source decision |
| --- | --- |
| p10: delinquency `00` <30 days, `01` 30–59, `02` 60–89, `03` 90–119; `RA` REO acquisition; `XX` unavailable. Before October 2025, `00` may precede first payment. | Mannan: match dictionary/layout to selected release. Never parse `03` as three days; unknown/missing meaning stays unresolved. No raw adapter added. |
| p10: loan age uses first payment, switching to modification first payment for modified loans; deferrals do not reset it. | Agree original continuous calendar anchor and modified-loan inclusion; do not restart the 24-month study clock from reset age. |
| p11: zero-balance `01` voluntary payoff; `02` third-party sale; `03` short sale/charge-off; `09` REO disposition; `15` whole-loan sale; `16` reperforming securitization; `96` defect. Effective date is YYYYMM. | Do not infer payoff from balance alone. Non-payoff exits/defect updates need explicit endpoint decisions; do not collapse them into active or negative. |
| p16: reporting cycles differ before May 2019, May 2019–September 2025, and October 2025 onward; later event reporting may differ from effective dates. | Agree event-date versus reporting-date use and availability cutoff; inspect horizon crossings before acceptance. |

These are reference notes, not accepted conversions. Blank/unknown codes must not become zero delinquency. Require exact guide/release, field names, missing codes, conversion rationale, continuous month calculation and independently reviewed aggregate counts by vintage/split. Resolve defects, sales and date conflicts explicitly before actual processing. Hazim owns access evidence; Mannan mapping; Tommy independent label/chronology review. No coordination messages were sent.

Normalized policy remains unchanged: months 1–24 inclusive; observed event wins over censoring after all records validate; complete 24-month no-event history is negative; earlier payoff, gaps and short history remain censored. Four additional invented regression methods cover month-24 event plus gap/payoff, month-25 event after complete follow-up, raw/missing-code refusal, and early-payoff/gap reason precedence. Existing tests retain 89/90-day, month-one, payoff-at-24 and invalid-positive-record cases. Passing normalized tests cannot prove that raw dictionary conversion is correct.

## #7: comparison handoff

The existing proposed score remains version `sweta-rule-v0.1`: credit <=620/680, DTI >=36/43 and LTV >=80/90, equal points, total 0–6. No thresholds or weights changed. Missing required inputs still abstain; points remain research ranks, never probabilities, calibration or lending policy.

`matched_review(validation, predictions, max_reviews=...)` still requires exact model IDs/labels and validation-only rows; it now also rejects bool targets masquerading as integer labels. It retains every score row with invalid-input reasons. Existing `models` diagnostics remain the full observed-label cohort for coverage inspection. **Compare `matched_comparison.models` against `rule_ranking`**: both now use exactly the labelled, scoreable loan intersection. The new block records censored and labelled-abstention exclusions separately plus a deterministic sorted ID/target SHA-256. Zero common loans yields an explicit status and no model metrics. Ties remain whole and within the declared capacity. Capacity applies only to labelled evaluation loans, not operational workload for censored applications.

Use the other models' same accepted nine-input origination contract, reviewed chronology, validation IDs/targets and source digests. The score reads only three allowlisted raw normalized inputs and intentionally does not adopt model imputation. Do not change cohort membership based on outcomes or optimize thresholds on final-test data. Preserve full-cohort model diagnostics alongside the common cohort to show selection/coverage limitations. Split tags and hashes do not prove source/date acceptance. Current API/CLI evidence remains synthetic; actual use requires an explicit reviewed integration change, accepted source/inputs/labels/splits, and independent review.

Reuse `sweta_pipeline` for unchanged QA/outcome/split composition; reuse `validation_review` for probability diagnostics. No teammate source or training files changed. Save actual row outputs only in approved local ignored storage, never public GitHub or cloud chat. Freeze settings, cohort, preprocessing, capacity, calibration design and cutoff before one final-test evaluation. No actual fit, calibration or final-test use occurred here.

## Unmerged dependency #24

[Hazim PR #24](https://github.com/HazimAli07/resl-capstone/pull/24) was open, draft, unmerged and mergeable when inspected; head `5e3e2a54c9f68a784b9483ffa773f4ce3f26ac78`. Existing inference contract is unchanged; actual-data review moves to `hazim-source-review-v2`, per-feature source/timing evidence, `check_access`, `check_timing_review`, `check_review` and read-only `readiness_report`/CLI. This branch does not copy or merge Hazim's implementation. Reconcile/retest after it merges; do not mark source ready from the earlier boolean review flag.

Verified successful current-head CI: [model checks](https://github.com/HazimAli07/resl-capstone/actions/runs/41484612807), [data checks](https://github.com/HazimAli07/resl-capstone/actions/runs/41484612871). These belong to #24, not this branch. An isolated detached worktree was used for compatibility testing, without changing its upstream branch. Committed templates return readiness exit 2, ready=false, all four readiness checks false; no loans read, model trained or final test used.

## #15: genuine facts and remaining course verification

- Sweta reports PR3 submission confirmed by Hazim. No submission receipt independently inspected here.
- Sweta confirms all four members attended October 31 and November 2 meetings: Sweta, Hazim, Mannan and Tommy. Exact times, detailed decisions, actions and participant-confirmed minutes remain pending; no inferred agenda is recorded as a decision.
- Live SLATE attempt on November 2 reached its login page with no signed-in course session. PR4–PR7, D3–D5 requirements and exact presentation slot could not be verified. PR4's **last verified** due date remains November 3, 3 p.m. America/Toronto, as recorded in issue #15 and Hazim's plan; it is not newly verified by this session. Do not infer team submission from an individual's Not Submitted label.
- Sweta handles current GPS and team submission. No signatures reused or requested, no private course files copied. Students must verify current requirements and assistance rules in SLATE and author their own assessed report.
- November 5 technical handoff and later week targets are plans, not completed results. Independent teammate review, selected-release/source acceptance and actual aggregate cohort evidence remain blockers. Leave #3/#7/#15 open.

## Verification commands and actual environment

Isolated Python 3.12.14 environment, installed `requirements-model.txt` (scikit-learn 1.7.2) and `requirements-demo.txt` (Streamlit 1.50.0). Full resolved versions below; these are observed versions, not a claim that transitive requirements were previously locked.

- `python -m unittest discover -s tests -p 'test_*review.py' -v`: 23 passed, 0 failures/errors/skips.
- `python -m unittest discover -s tests -v`: 130 passed, 0 failures/errors/skips (including all optional UI/model tests).
- `python -m resl.sweta_model_review --synthetic --max-reviews 7`: exit 0. Existing invented 120 train/40 validation applications retained; 37 observed validation loans scoreable, 3 censored. Outputs stay under ignored results/. No mortgage-performance claim.
- `git diff --check`: passed.

Resolved packages (`pip freeze`):

```text
altair==5.5.0
attrs==26.1.0
blinker==1.9.0
cachetools==6.2.6
certifi==2026.10.23
charset-normalizer==3.5.2
click==8.5.0
cloudpickle==3.1.2
gitdb==4.0.12
GitPython==3.2.1
idna==3.20
Jinja2==3.1.6
joblib==1.6.0
jsonschema==4.26.0
jsonschema-specifications==2025.9.1
MarkupSafe==3.0.4
narwhals==2.28.0
numpy==2.5.4
packaging==25.0
pandas==2.3.3
pillow==11.3.0
protobuf==6.33.6
pyarrow==26.0.0
pydeck==0.9.3
python-dateutil==4.0.0
pytz==2026.6
referencing==0.37.0
requests==2.34.2
rpds-py==2026.9.1
scikit-learn==1.7.2
scipy==1.18.1
smmap==5.0.3
streamlit==1.50.0
tenacity==9.2.1
threadpoolctl==3.7.0
toml==0.10.2
tornado==6.6
typing_extensions==4.16.0
tzdata==2026.6
urllib3==2.8.0
watchdog==6.0.0

```

Additional dependency verification: #24's unmodified detached head passed 134/134 tests; overlaying only this branch's three code/test files passed 142/142, with 0 failures/errors/skips in both runs. This is a local compatibility check, not a merge or acceptance of #24. `python -m resl.hazim_readiness` on its committed templates returned expected exit 2 and ready=false.

## Publication checkpoint

Local implementation commit: `3f5906b` (Codex-assisted). Publication was attempted after re-verifying GitHub identity as shwetachd1. GitHub's create-tree API returned HTTP 403, `Resource not accessible by integration`; terminal `git push -u origin sweta/pr4-label-baseline` failed because no HTTPS GitHub username/credential was available. No remote branch or draft PR was created, and no current-branch CI result is claimed. GitHub write access/authentication must be restored before push and draft-PR creation. Existing #24 CI links above remain clearly attributed to that PR.

Prepared draft PR title: **Sweta PR4: matched rule-baseline cohorts, endpoint regressions and evidence**.

Prepared PR description: Codex-assisted technical work for #3, #7 and #15. Preserves merged #18/#19/#23. Adds an explicit common labelled/scoreable validation cohort for rule/model comparison, abstention reasons and cohort fingerprint; rejects boolean target mismatches; adds eight regression methods for cohort and normalized 24-month endpoint behaviour. Targeted checks: 23 passed; full suite: 130 passed; local #24 compatibility overlay: 142 passed, all without failures/errors/skips. Python 3.12.14, scikit-learn 1.7.2, Streamlit 1.50.0. Source access/release, Mannan/Tommy review, actual cohort acceptance, live SLATE requirements and presentation slot remain pending. Synthetic evidence only; no raw records, actual row outputs, credentials or private course files included. No final-test tuning, calibration acceptance, submission, signatures, messages, merge or deployment. Keep issues open. Please review labels/date semantics and the matched-cohort interface before accepting.
