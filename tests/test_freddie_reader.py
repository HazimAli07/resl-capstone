"""Raw source reader regressions using invented records only."""
import io
import hashlib
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
import zipfile
from unittest.mock import patch

from resl.freddie_reader import (COLUMNS, ORIGINATION, PERFORMANCE, MAX_LINE_BYTES,
                                 iter_records, month_index, profile_streams, profile_archives)


def line(kind, **values):
    defaults = {"loan_id": "INVENTED-A", "first_payment_month": "201601",
                "reporting_month": "201601", "credit_score": "700", "dti": "30",
                "ltv": "80", "original_balance": "200000", "original_rate": "4.5",
                "original_term": "360", "loan_purpose": "P", "occupancy": "P",
                "property_type": "SF"}
    defaults.update(values)
    return ("|".join(defaults.get(f, "") for f in COLUMNS[kind]) + "\n").encode()


class FreddieReaderTests(unittest.TestCase):
    def profile(self, orig=None, perf=None):
        return profile_streams(io.BytesIO(orig if orig is not None else line("origination")),
                               io.BytesIO(perf if perf is not None else line("performance")),
                               performance_cutoff="2026-06-30")

    def test_current_layout_positions_include_july_changes(self):
        self.assertEqual((len(ORIGINATION), len(PERFORMANCE)), (31, 35))
        self.assertEqual(ORIGINATION[19], "loan_id")
        self.assertEqual(ORIGINATION[-1], "vantage_score")
        self.assertEqual(PERFORMANCE[32:], ("mi_cancellation", "servicer_name", "bankruptcy_cramdown_costs"))

    def test_trailing_empty_column_is_preserved_and_no_date_proxy_added(self):
        row = next(iter_records(io.BytesIO(line("origination")), "origination"))
        self.assertEqual(row["vantage_score"], "")
        self.assertEqual(row["first_payment_month"], "201601")
        self.assertNotIn("origination_date", row)

    def test_short_and_long_rows_fail_without_leaking_contents(self):
        for data in (b"SECRET-ID|too-short\n", line("performance").rstrip(b"\n") + b"|extra\n"):
            with self.subTest(data=data), self.assertRaisesRegex(ValueError, "expected 35 fields") as error:
                list(iter_records(io.BytesIO(data), "performance"))
            self.assertNotIn("SECRET-ID", str(error.exception))

    def test_blank_control_invalid_encoding_and_oversized_rows_fail(self):
        for data in (b"\n", b"\xff\n", b"\x00\n", b"a" * (MAX_LINE_BYTES + 1)):
            with self.subTest(data=data[:5]), self.assertRaises(ValueError):
                list(iter_records(io.BytesIO(data), "origination"))

    def test_headers_blank_and_padded_identifiers_fail(self):
        for loan in ("Loan Identifier", "", " INVENTED-A "):
            with self.subTest(loan=loan), self.assertRaises(ValueError):
                list(iter_records(io.BytesIO(line("origination", loan_id=loan)), "origination"))

    def test_calendar_months_are_strict_without_using_loan_age(self):
        for month in ("201613", "201600", "20161", "000001", "2016-01", "٢٠١٦٠١"):
            with self.subTest(month=month), self.assertRaises(ValueError):
                month_index(month)
        report = self.profile(perf=line("performance", loan_age="-12"))
        self.assertEqual(report["reporting_month_range"], ["201601", "201601"])

    def test_malformed_required_month_error_does_not_echo_value(self):
        with self.assertRaisesRegex(ValueError, "invalid reporting_month") as error:
            self.profile(perf=line("performance", reporting_month="PRIVATE-VALUE"))
        self.assertNotIn("PRIVATE-VALUE", str(error.exception))

    def test_nonadjacent_duplicate_month_and_orphans_detected(self):
        orig = line("origination") + line("origination", loan_id="INVENTED-B")
        perf = (line("performance") + line("performance", loan_id="INVENTED-ORPHAN")
                + line("performance", reporting_month="201602") + line("performance"))
        p = self.profile(orig, perf)
        self.assertEqual(p["duplicate_loan_month_rows"], 1)
        self.assertEqual(p["orphan_performance_rows"], 1)
        self.assertEqual(p["orphan_performance_loans"], 1)
        self.assertEqual(p["loans_without_performance"], 1)
        self.assertFalse(p["key_and_join_checks_passed"])
        self.assertNotIn("INVENTED", json.dumps(p))

    def test_duplicate_origination_rows_and_missing_denominator_preserved(self):
        p = self.profile(line("origination") * 2)
        self.assertEqual(p["origination_rows"], 2)
        self.assertEqual(p["unique_origination_loans"], 1)
        self.assertEqual(p["duplicate_origination_rows"], 1)
        self.assertEqual(p["missing_input_denominator"], 2)
        self.assertFalse(p["key_and_join_checks_passed"])

    def test_missing_sentinels_do_not_treat_legitimate_zero_as_missing(self):
        orig = line("origination", credit_score="9999", dti="0", ltv="999",
                    loan_purpose="9", occupancy="9", property_type="99")
        p = self.profile(orig)
        self.assertEqual(p["missing_or_sentinel_input_rows"]["dti"], 0)
        for f in ("credit_score", "ltv", "loan_purpose", "occupancy", "property_type"):
            self.assertEqual(p["missing_or_sentinel_input_rows"][f], 1)

    def test_empty_files_cannot_pass_quality(self):
        for orig, perf in ((b"", b""), (line("origination"), b"")):
            with self.subTest(orig=bool(orig)):
                self.assertFalse(self.profile(orig, perf)["key_and_join_checks_passed"])

    def test_months_outside_acquisition_range_fail(self):
        for month in ("199812", "202607"):
            with self.subTest(month=month), self.assertRaisesRegex(ValueError, "outside acquisition range"):
                self.profile(perf=line("performance", reporting_month=month))

    def test_pre_first_payment_records_are_reported_without_reanchoring(self):
        p = self.profile(line("origination", first_payment_month="201602"))
        self.assertEqual(p["performance_before_first_payment_rows"], 1)
        self.assertEqual(p["first_payment_month_range"], ["201602", "201602"])
        self.assertEqual(p["reporting_month_range"], ["201601", "201601"])

    def test_access_is_checked_before_archives_are_opened(self):
        with patch("resl.freddie_reader.verify_archives") as verify:
            with self.assertRaises(ValueError):
                profile_archives({}, Path("unused"), {})
            verify.assert_not_called()

    def test_nonobject_access_and_manifest_fail_cleanly(self):
        for manifest, access in (({}, []), ([], {}), ({}, None)):
            with self.subTest(manifest=manifest, access=access), self.assertRaisesRegex(ValueError, "JSON objects"):
                profile_archives(manifest, "unused", access)

    def test_archive_integration_keeps_only_aggregates_and_no_acceptance(self):
        root = Path(__file__).resolve().parents[1]
        manifest = json.loads((root / "docs/freddie_source_manifest.json").read_text())
        manifest["archives"] = manifest["archives"][:1]
        access = {"source": manifest["source"], "terms_reference": manifest["terms_reference"],
                  "release": "INVENTED SOFTWARE FIXTURE", "confirmed_by": "INVENTED TEST",
                  "confirmed_on": "2026-11-07", "selected_years": [2016],
                  "permitted_access_confirmed": True}
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "sample_2016.zip"
            with zipfile.ZipFile(path, "w") as archive:
                archive.writestr("sample_orig_2016.txt", line("origination"))
                archive.writestr("sample_perf_2016.txt", line("performance"))
            manifest["archives"][0].update(bytes=path.stat().st_size,
                                          sha256=hashlib.sha256(path.read_bytes()).hexdigest())
            report = profile_archives(manifest, directory, access)
            self.assertTrue(report["profiles"][0]["key_and_join_checks_passed"])
            self.assertTrue(report["loan_rows_read"])
            for flag in ("loan_ids_published", "normalized_inputs_written", "model_inputs_validated",
                         "labels_constructed", "study_partitions_accepted", "model_trained",
                         "final_test_evaluated"):
                self.assertFalse(report[flag])
            self.assertNotIn("INVENTED-A", json.dumps(report))
            self.assertNotIn(directory, json.dumps(report))
            with patch("resl.freddie_reader.verify_archives") as verify:
                with self.assertRaisesRegex(ValueError, "differ"):
                    profile_archives(manifest, directory, access | {"selected_years": [2019]})
                verify.assert_not_called()
            path.write_bytes(b"tampered")
            with self.assertRaisesRegex(ValueError, "mismatch"):
                profile_archives(manifest, directory, access)

    def test_cli_rejects_public_output_before_reading_archives(self):
        result = subprocess.run([sys.executable, "-m", "resl.freddie_reader",
                                 "--archive-dir", "does-not-exist", "--out", "docs/unsafe.json"],
                                text=True, capture_output=True)
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("ignored repository results", result.stderr)
        self.assertFalse(Path("docs/unsafe.json").exists())


if __name__ == "__main__":
    unittest.main()
