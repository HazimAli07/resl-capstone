"""Synthetic software-invariant tests for Tommy's logistic candidate."""
import copy
import json
import subprocess
import sys
import unittest

from resl.hazim_contract import canonical_hash
from resl.tommy_logistic import (
    PREDICTION_COLUMNS, REGULARIZATION_GRID, synthetic_cohort, train_candidates,
)

try:
    import sklearn  # noqa: F401
    HAS_MODEL = True
except ImportError:
    HAS_MODEL = False


@unittest.skipUnless(HAS_MODEL, "optional model requirements unavailable")
class TommyLogisticTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.train, cls.validation, cls.review = synthetic_cohort()
        cls.preprocessor, cls.model, cls.report, cls.predictions = train_candidates(
            cls.train, cls.validation, cls.review, synthetic=True)

    def test_preprocessing_and_fit_exclude_censored_training_labels(self):
        observed = sum(row["target"] is not None for row in self.train)
        self.assertEqual(self.preprocessor.training_count, observed)
        self.assertEqual(self.report["preprocessing_fit_rows"], observed)
        self.assertGreater(self.report["counts"]["train_censored_excluded"], 0)
        self.assertEqual(self.report["final_test_used"], False)

    def test_predictions_use_comparison_schema_and_matching_validation_cohorts(self):
        self.assertEqual(self.report["prediction_schema"], list(PREDICTION_COLUMNS))
        self.assertEqual(self.report["candidate_count"], len(REGULARIZATION_GRID))
        for name in {row["model"] for row in self.predictions}:
            cohort = [row for row in self.predictions if row["model"] == name]
            self.assertEqual(len(cohort), len(self.validation))
            self.assertEqual({row["loan_id"] for row in cohort},
                             {row["loan_id"] for row in self.validation})
            self.assertTrue(all(tuple(row) == PREDICTION_COLUMNS for row in cohort))

    def test_candidate_is_reproducible(self):
        _, model, report, predictions = train_candidates(
            self.train, self.validation, self.review, synthetic=True)
        self.assertEqual(report["proposed_candidate"], self.report["proposed_candidate"])
        self.assertEqual(report["validation"], self.report["validation"])
        self.assertEqual(model.coef_.tolist(), self.model.coef_.tolist())
        self.assertEqual(canonical_hash(predictions), canonical_hash(self.predictions))

    def test_validation_values_do_not_change_fitted_preprocessing(self):
        validation = copy.deepcopy(self.validation)
        for row in validation:
            row["credit_score"] = 300
            row["loan_purpose"] = "cash_out"
        altered_preprocessor, _, _, _ = train_candidates(
            self.train, validation, self.review, synthetic=True)
        self.assertEqual(altered_preprocessor.metadata(), self.preprocessor.metadata())

    def test_duplicate_overlap_and_wrong_chronology_rejected(self):
        validation = copy.deepcopy(self.validation)
        validation[0]["loan_id"] = self.train[0]["loan_id"]
        with self.assertRaisesRegex(ValueError, "overlap"):
            train_candidates(self.train, validation, self.review, synthetic=True)
        validation = copy.deepcopy(self.validation)
        validation[0]["origination_date"] = "2021-01-01"
        with self.assertRaises(ValueError):
            train_candidates(self.train, validation, self.review, synthetic=True)

    def test_label_after_fit_or_selection_cutoff_rejected(self):
        train = copy.deepcopy(self.train)
        observed = next(row for row in train if row["target"] is not None)
        observed["label_available_on"] = "2018-01-01"
        with self.assertRaisesRegex(ValueError, "unavailable"):
            train_candidates(train, self.validation, self.review, synthetic=True)
        validation = copy.deepcopy(self.validation)
        observed = next(row for row in validation if row["target"] is not None)
        observed["label_available_on"] = "2021-01-01"
        with self.assertRaisesRegex(ValueError, "unavailable"):
            train_candidates(self.train, validation, self.review, synthetic=True)

    def test_final_test_has_no_training_interface(self):
        with self.assertRaises(ValueError):
            train_candidates(self.train, self.validation + [dict(self.validation[0],
                loan_id="MADEUP-test", split="test", origination_date="2021-01-01")],
                self.review, synthetic=True)

    def test_actual_mode_fails_closed_without_permission_and_timing_contract(self):
        with self.assertRaisesRegex(ValueError, "Permitted access"):
            train_candidates(self.train, self.validation,
                             dict(self.review, synthetic=False), synthetic=False, access={})

    def test_synthetic_cli_rejects_external_input_files(self):
        result = subprocess.run(
            [sys.executable, "-m", "resl.tommy_logistic", "--synthetic", "--train-csv", "private.csv"],
            capture_output=True, text=True)
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("external inputs prohibited", result.stderr)


if __name__ == "__main__":
    unittest.main()
