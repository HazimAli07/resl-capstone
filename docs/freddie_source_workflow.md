# Freddie Mac source workflow - November 7, 2026

Hazim completed individual Clarity registration and acquired the official Standard sample archives for 2016, 2019 and 2022. Each archive contains an origination file and its monthly performance file. The samples and their vintage-to-partition assignments remain provisional.

The public acquisition manifest records filenames, archive byte sizes, SHA-256 checksums, expected member names, the download date, portal, guide reference and performance cutoff. It contains no loan records, borrower IDs, local paths or credentials. The downloaded ZIPs remain in ignored local storage.

## What runs on GitHub

The Freddie Mac source checks workflow validates the public manifest and exercises file-integrity failures using tiny invented ZIP contents. It verifies that the access record passes while the unaccepted source/timing/label/split review still blocks actual training. The metadata-only report explicitly says that local archives were not verified in CI. GitHub-hosted jobs do not download, receive, analyze or train on licensed loan records, and need no Freddie Mac password or token.

## Repeat the local acquisition verification

Register and download the samples directly from the official [Clarity portal](https://claritydownload.fmapps.freddiemac.com/CRT/#/sflld) under your own permitted access. The repository records Hazim's acquisition; it does not transfer his account or acceptance to another person. Read the applicable [dataset terms](https://capitalmarkets.freddiemac.com/crt/docs/pdfs/fre_terms_conditions_sflld.pdf) before use. Their restrictions on redistribution are why the public repository contains provenance and code rather than the source archives.

Place the original sample ZIPs in `data/raw/freddie_mac/2026-11-07/`, then run from the repository root:

```bash
python -m resl.freddie_source --archive-dir data/raw/freddie_mac/2026-11-07 --out results/freddie-source-local.json
python -m resl.hazim_readiness --out results/actual-data-readiness.json
```

The first command checks all three files against the recorded sizes and SHA-256 values, exact origination/performance member names and ZIP CRCs. It does not extract or interpret loan rows. Missing or changed files fail; it never silently substitutes a metadata-only check.

The readiness command currently returns exit 2 and `ready=false`. Access is now recorded, but the nine-feature origination timing review, raw-to-normalized source/label/calendar mapping, chronological splits and exact prepared-input hashes are still unaccepted. The examples in `docs/data_access.example.json` and `docs/hazim_review.example.json` remain deliberately unaccepted.

## Next processing step

The source text is headerless and pipe delimited. Prepare a reviewed adapter before feeding it into the existing normalized CSV tools. First-payment month is not an exact origination date. Agree the calendar anchor, terminal/unknown codes, 24-month follow-up, label availability and study partitions. Save prepared files under ignored `data/processed/`; record their hashes in a genuine accepted review. Fit preprocessing and candidate models on accepted observed training rows only, compare on the same validation loans and keep the final test outside selection.

An archive-integrity pass does not accept those decisions or establish mortgage-model performance. No real-data model training, calibration or final-test evaluation is claimed by this acquisition workflow. Code and documentation were prepared with Codex assistance.
