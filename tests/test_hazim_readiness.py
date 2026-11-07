"""Regression checks for source/timing acceptance before actual-data runs."""
import copy
from datetime import date
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

from resl.data_checks import FEATURES
from resl.hazim_contract import (REVIEW_VERSION, NORMALIZED_UNITS, check_access,
                                  check_review, check_timing_review)
from resl.hazim_readiness import readiness_report
from resl.hazim_training import synthetic_cohort


def example_records():
    """Invented attestations exercise validation; they are not real approvals."""
    _, _, synthetic = synthetic_cohort()
    access = {"permitted_access_confirmed": True, "source": "Invented test source",
              "release": "TEST-ONLY", "selected_years": [2014, 2018],
              "terms_reference": "TEST-ONLY", "confirmed_by": "Test fixture",
              "confirmed_on": "2020-12-31"}
    review = dict(synthetic, synthetic=False, accepted=True, release="TEST-ONLY",
                  review_version=REVIEW_VERSION, prediction_stage="origination",
                  date_anchor="Test-only documented anchor", label_policy="Test-only label policy",
                  split_rationale="Test-only chronology", source_dictionary="TEST-ONLY",
                  reviewed_by="Test fixture", reviewed_on="2020-12-31",
                  eligible_features=list(FEATURES), train_csv_sha256="a" * 64,
                  validation_csv_sha256="b" * 64)
    review["feature_timing_review"] = [
        {"feature": f, "source_field": "test_" + f, "dictionary_reference": "TEST-ONLY",
         "conversion": "Test fixture conversion", "normalized_unit": NORMALIZED_UNITS[f],
         "missing_codes": [""], "available_by": "origination", "accepted": True}
        for f in FEATURES]
    return access, review


class ReadinessTests(unittest.TestCase):
    def setUp(self):
        self.access, self.review = example_records()

    def test_complete_test_attestations_validate_without_training(self):
        report = readiness_report(self.access, self.review)
        self.assertTrue(report["ready"])
        for flag in ("loan_files_read", "model_trained", "final_test_used"):
            self.assertFalse(report[flag])
        check_review(self.review, self.access, synthetic=False)

    def test_committed_templates_remain_blocked(self):
        root = Path(__file__).resolve().parents[1]
        report = readiness_report(json.loads((root / "docs/data_access.example.json").read_text()),
                                  json.loads((root / "docs/hazim_review.example.json").read_text()))
        self.assertFalse(report["ready"])
        self.assertFalse(report["checks"]["permitted_access"]["passed"])

    def test_acquired_access_does_not_accept_source_or_training(self):
        root = Path(__file__).resolve().parents[1]
        report = readiness_report(json.loads((root / "docs/data_access.json").read_text()),
                                  json.loads((root / "docs/hazim_review.example.json").read_text()))
        self.assertTrue(report["checks"]["permitted_access"]["passed"])
        self.assertFalse(report["ready"])
        for flag in ("loan_files_read", "model_trained", "final_test_used"):
            self.assertFalse(report[flag])

    def test_future_access_confirmation_rejected(self):
        with self.assertRaisesRegex(ValueError, "future dated"):
            check_access(dict(self.access, confirmed_on="2027-01-01"), as_of=date(2026, 11, 2))

    def test_years_reject_duplicate_boolean_future_and_empty(self):
        for years in ([2014, 2014], [True], [2027], [], "2014"):
            with self.subTest(years=years), self.assertRaises(ValueError):
                check_access(dict(self.access, selected_years=years), as_of=date(2026, 11, 2))

    def test_access_requires_nonblank_text_evidence(self):
        for key in ("source", "release", "terms_reference", "confirmed_by", "confirmed_on"):
            for value in ("   ", True, {"claimed": True}):
                with self.subTest(key=key, value=value), self.assertRaises(ValueError):
                    check_access(dict(self.access, **{key: value}))

    def test_earlier_application_stage_cannot_reuse_origination_inputs(self):
        with self.assertRaisesRegex(ValueError, "origination-stage"):
            check_review(dict(self.review, prediction_stage="application"), self.access, synthetic=False)

    def test_old_boolean_acceptance_is_not_enough(self):
        review = dict(self.review)
        del review["feature_timing_review"]
        with self.assertRaisesRegex(ValueError, "every eligible input"):
            check_review(review, self.access, synthetic=False)

    def test_missing_duplicate_and_post_outcome_feature_rejected(self):
        for value in (self.review["feature_timing_review"][:-1],
                      self.review["feature_timing_review"][:-1] + [self.review["feature_timing_review"][0]],
                      self.review["feature_timing_review"][:-1] + [
                          dict(self.review["feature_timing_review"][-1], feature="current_balance")]):
            with self.subTest(value=value), self.assertRaises(ValueError):
                check_timing_review(dict(self.review, feature_timing_review=value))

    def test_each_field_needs_actual_source_evidence_and_units(self):
        for key, value in (("source_field", ""), ("dictionary_reference", " "),
                           ("conversion", None), ("normalized_unit", "unknown"),
                           ("missing_codes", "9999"), ("missing_codes", [9999]),
                           ("available_by", "after_origination"), ("accepted", False)):
            review = copy.deepcopy(self.review)
            review["feature_timing_review"][0][key] = value
            with self.subTest(key=key, value=value), self.assertRaises(ValueError):
                check_timing_review(review)

    def test_digest_format_and_synthetic_relabelling_block_readiness(self):
        for digest in (None, "A" * 64, "not a hash"):
            report = readiness_report(self.access, dict(self.review, train_csv_sha256=digest))
            self.assertFalse(report["ready"])
        self.assertFalse(readiness_report(self.access, dict(self.review, synthetic=True))["ready"])

    def test_cli_reports_blockers_and_does_not_read_loan_files(self):
        result = subprocess.run([sys.executable, "-m", "resl.hazim_readiness"],
                                capture_output=True, text=True)
        self.assertEqual(result.returncode, 2)
        report = json.loads(result.stdout)
        self.assertFalse(report["ready"])
        self.assertFalse(report["loan_files_read"])

    def test_cli_cannot_overwrite_a_tracked_file(self):
        with tempfile.TemporaryDirectory() as folder:
            target = Path(folder) / "must_not_exist.json"
            result = subprocess.run([sys.executable, "-m", "resl.hazim_readiness", "--out", str(target)],
                                    capture_output=True, text=True)
            self.assertNotEqual(result.returncode, 0)
            self.assertFalse(target.exists())


if __name__ == "__main__":
    unittest.main()
