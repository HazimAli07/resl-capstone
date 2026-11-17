# RESL mini demo: 3–5 minutes

Open https://hazimali07.github.io/resl-capstone/ in a browser. GitHub Pages hosts
the website. The saved model runs in the page; your laptop does not need to host
a server, install Python or stay switched on for others to use their copies.
Fictional application inputs remain in each visitor's browser.

## Understand the model first

The demo uses a **random forest**: 64 decision trees process nine origination
inputs. Each tree follows learned questions to an output. The forest averages
those outputs and multiplies by 100 for the displayed illustrative signal.

This package was trained on **113 observed invented loans**. It proves that the
software calculation works. The real Freddie Mac training/evaluation is still
pending. Accuracy must be measured by comparing predictions with known outcomes
on appropriate evaluation loans. The signal for one example is a separate value.
Real-data accuracy is currently unmeasured.

## Walkthrough

**0:00–0:45 — Explain the model.**

Open **How the model works**. Explain the nine inputs, saved preprocessing and
64-tree average. Point out that today's training examples are fictional.

**0:45–1:45 — Run and compare applications.**

Open **Application**, keep **Purchase** and click **Review application**. Its
illustrative signal is 8.1/100. Run **Refinance** to see 49.2/100, then open
**Compare examples**. Lower output means a smaller synthetic-model risk signal;
the values are not calibrated real default probabilities or lending risk bands.

**1:45–2:45 — Missing data and invalid inputs.**

Choose **Missing information** and run it. Show the missing-credit-score note,
saved training median and missingness flag. Enter `1000` as Credit score and
review again: the app rejects it and clears the previous result.

**2:45–3:45 — Project progress and remaining work.**

Open **Project progress**. The source reader and structural checks are merged.
This app demonstrates validation, saved preprocessing and forest inference.
The remaining research is source/date/label/split acceptance, actual mortgage
training/comparison, calibration and untouched final-test evaluation.

**3:45–5:00 — Questions.**

- **What is the accuracy?** Real-mortgage predictive accuracy is not measured
  yet. Software test pass counts measure program behavior.
- **What does 8.1 mean?** The average output of the demo's trees, expressed on a
  0–100 scale for that fictional application.
- **Does this approve a loan?** No. It supports a research workflow and human
  review; no approval, rejection or pricing decision is produced.
- **Does my laptop have to stay on?** No. GitHub serves the website and each
  visitor's browser runs the saved model.
- **Where is the licensed data?** Outside public GitHub. The hosted site has
  only code, fictional examples and the synthetic-trained model.

## Before class

Open the public link, run all three examples and keep the app tab open. Use
this document for the rehearsal steps.
No localhost address or Terminal session is needed for the hosted demo.

## Developer reproduction

Run `python -m resl.build_demo_site --out _site` to produce the eight explicit
site files. Publish those files to the configured `gh-pages` branch. The
repository's Python runner remains available for development checks, while the
public website uses the JavaScript inference tested for Python parity.
