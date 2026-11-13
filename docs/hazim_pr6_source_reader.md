# PR6: Freddie Mac source reader

Work in progress on `hazim/pr6-source-reader`. Codex-assisted implementation
under Hazim's account. No teammate reviewers are required or requested.

## Reference verified November 13, 2026

- [Official dataset resources](https://www.freddiemac.com/research/datasets/sf-loanlevel-dataset)
- [July 2026 file layout](https://www.freddiemac.com/fmac-resources/research/pdf/file_layout_july_2026.xlsx)
- [Release 48 guide, October 2026](https://www.freddiemac.com/fmac-resources/research/pdf/user_guide.pdf)
- [Release notes](https://www.freddiemac.com/fmac-resources/research/pdf/release_notes.pdf)

The official layout workbook was downloaded and read locally. Its SHA-256 is
`e4ee4ba00b5b1a8d18e2debe3acafdd019b48bafafdeb907cf5b19b49c989f23`.
It specifies 31 origination fields and 35 monthly performance fields. The first
row of each acquired 2016/2019/2022 pair has those widths. This is a first-row
check, not a complete file or cohort validation.

July's changes moved servicer/MI fields and added new fields. An older positional
reader would be unsafe. First Payment Date is a month, not an exact origination
date; the reader must preserve that distinction. Loan Age can reset after
modification and must not silently define the study clock.

## Work in this PR

- [x] Verify the current official layout and acquired first-row widths.
- [ ] Add strict streaming readers for both headerless pipe-delimited files.
- [ ] Reject wrong widths, invalid required months, headers and oversized rows.
- [ ] Produce private aggregate key, join, date and missing-code checks.
- [ ] Test failures using invented records and update synthetic-only CI.
- [ ] Run local checks on the acquired archives and record their scope honestly.

Licensed archives and row-level outputs remain in ignored local storage. No real
data will be uploaded to this PR or GitHub Actions. This work does not accept
study partitions, invent source/timing approvals, generate labels or train a
model. Those remaining decisions stay explicit.
