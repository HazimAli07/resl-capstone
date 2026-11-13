# PR6: Freddie Mac source reader

Work in progress on `hazim/pr6-source-reader`. No teammate reviewers are
required or requested.

## Reference verified November 13, 2026

- [Official dataset resources](https://www.freddiemac.com/research/datasets/sf-loanlevel-dataset)
- [July 2026 file layout](https://www.freddiemac.com/fmac-resources/research/pdf/file_layout_july_2026.xlsx)
- [Release 48 guide, October 2026](https://www.freddiemac.com/fmac-resources/research/pdf/user_guide.pdf)
- [Release notes](https://www.freddiemac.com/fmac-resources/research/pdf/release_notes.pdf)

The official layout workbook was downloaded and read locally. Its SHA-256 is
`e4ee4ba00b5b1a8d18e2debe3acafdd019b48bafafdeb907cf5b19b49c989f23`.
It specifies 31 origination fields and 35 monthly performance fields. The initial
first-row check matched those widths. The subsequent local structural profile
read all three acquired pairs successfully; row counts were independently checked
by counting line endings in decompressed byte chunks. Detailed profiles and
source-date findings remain private, not uploaded in this PR.

July's changes moved servicer/MI fields and added new fields. An older positional
reader would be unsafe. First Payment Date is a month, not an exact origination
date; the reader must preserve that distinction. Loan Age can reset after
modification and must not silently define the study clock.

## Work in this PR

- [x] Verify the current official layout and acquired first-row widths.
- [x] Add strict streaming readers for both headerless pipe-delimited files.
- [x] Reject wrong widths, invalid required months, headers and oversized rows.
- [x] Produce private aggregate key, join, date and missing-code checks.
- [x] Test failures using invented records; existing CI discovers the new tests.
- [x] Run local checks on the acquired archives and record their scope honestly.

Licensed archives and row-level outputs remain in ignored local storage. No real
data will be uploaded to this PR or GitHub Actions. This work does not accept
study partitions, invent source/timing approvals, generate labels or train a
model. Those remaining decisions stay explicit.

## Local use

```bash
python -m resl.freddie_reader --archive-dir data/raw/freddie_mac/2026-11-07 --out results/pr6/source-structural-profile.json
```

This requires the recorded access and exact archive sizes, SHA-256 values, member
names and CRCs before reading records. It streams without extraction, checks
unique loan and loan/month keys, join coverage, source month ranges and explicit
candidate-input missing codes. Empty/invalid records stop with a line number,
without printing loan IDs or row values. It does not treat Loan Age as the study
clock or rename First Payment Date to an exact origination date.

Profiles stay under ignored `results/`. Exit 2 indicates a key/join issue; parse
errors also stop. The missing-input denominator is all origination rows, so
duplicates must be resolved before treating it as a per-loan missingness rate.
Same-width column reordering cannot be detected from headerless row width alone.
Other numeric bounds, category conversions, 24-month labels, follow-up, source
timing and chronology are separate acceptance work. No predictor normalization
or model fitting is performed. Existing Data and Hazim model workflows discover
the invented reader tests; GitHub Actions never invokes this command on actual
archives or receives private profiles.
