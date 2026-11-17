# RESL mini demo: 3–5 minutes

## Start the app

On this Mac, double-click **Launch Demo.command** in the project folder. Keep
its Terminal window open. The app opens at http://localhost:8501.

For another setup, Python 3.12 or later is sufficient:

```bash
python -m resl.mini_demo --port 8501 --open-browser
```

The saved model is bundled under `data/synthetic/mini_demo/`. It was trained on
this repository's deterministic invented cohort, not the Freddie Mac files.
The local app uses Python's standard library: no package installation, external
model service or API key is required. Do not enter real applications in the demo.
The interface is a custom application workspace with three navigation sections.
The Presentation guide button opens the rehearsal steps inside the app.

## Walkthrough

**0:00–0:30 — Introduce the project.**

“Our project studies mortgage outcomes using information available at
origination. This is the working application flow. Today the model and the
applications are synthetic; the actual mortgage experiments are still pending.”

**0:30–1:30 — Run a fictional application.**

Keep **Purchase**, point out the credit score, DTI and LTV, then select
**Review application**. Show the illustrative risk signal and the nine checked fields and the submitted
downloadable submitted summary. Explain that the score comes from an actual saved forest and
its frozen preprocessing. Lower means a smaller synthetic-model risk signal; it is not an accuracy score, a credit score or a calibrated real-world default probability. Real-data predictive accuracy has not been measured yet.

**1:30–2:15 — Show a second example.**

Choose **Refinance** and run it. Open **Compare examples** in the left navigation to show
that the same saved model processes several fictional inputs. Do not describe
the differences as causal feature explanations or accepted risk bands.

**2:15–3:00 — Show missing data and validation.**

Choose **Missing information** and run it. Explain the saved training median
and missingness flag. Then type `1000` in Credit score and run again: the app
rejects the invalid input and clears the prior result.

**3:00–4:00 — Explain progress and remaining work.**

Open **Project progress**. The source reader and structural checks are merged;
the current app demonstrates validation, saved preprocessing and local model
inference. The remaining work is the source/date/label/split acceptance and
actual-data comparison, calibration and final evaluation.

**4:00–5:00 — Questions.**

- **Is this the final mortgage model?** No. It is a synthetic-trained
  development package used to demonstrate working software.
- **Does this approve or reject a loan?** No. The final research output is
  intended to support a qualified reviewer.
- **Where is the real data?** Licensed source files stay outside public GitHub.
  This demo does not require or upload them.
- **What comes next?** Finalize the data/label decisions, compare candidates
  on the same validation loans and connect the accepted model to the tool.

## Before class

Open the app once, run all three examples and leave the tab/Terminal open.
Keep the laptop connected to power. The fixture is synthetic and safe to copy
with the code; licensed data and private data profiles are not part of this demo.
