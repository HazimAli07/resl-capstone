"""Synthetic acceptance checks for Mannan's independent implementation."""
import copy
import importlib.util
import math
import unittest
from resl.data_checks import FEATURES, ORIGINATION_FIELDS
from resl.mannan_mapping import normalize_origination, audit_cohort
from resl.mannan_preprocessing import TrainPreprocessor, numeric_value
from resl.mannan_comparison import compare_candidates
from resl.mannan_demo import EXAMPLES, preview_application, offline_html

def loan(ident="a", score=700, split="train", **changes):
    return {**EXAMPLES["Example A"], "loan_id": ident, "origination_date": "2017-01-01",
            "credit_score": score, "split": split, **changes}

def predictions(model="rule", split="validation"):
    return [{"model": model, "loan_id": str(i), "target": target,
             "probability": p, "split": split}
            for i, (target, p) in enumerate([(1, .9), (0, .8), (1, .4), (0, .1), (None, .7)])]

class MappingTests(unittest.TestCase):
    def setUp(self):
        self.mapping = {f: {"source": f} for f in ORIGINATION_FIELDS}

    def test_unreviewed_real_mapping_rejected(self):
        with self.assertRaises(ValueError):
            normalize_origination([loan()], self.mapping, release="unselected")

    def test_explicit_mapping_and_sentinel_conversion(self):
        result = normalize_origination([loan(credit_score="9999")], self.mapping,
                                       release="synthetic-v1", synthetic=True)
        self.assertIsNone(result[0]["credit_score"])
        self.assertEqual(set(result[0]), set(ORIGINATION_FIELDS))

    def test_unknown_header_cannot_silently_disappear(self):
        mapping = copy.deepcopy(self.mapping)
        mapping["dti"]["source"] = "missing"
        with self.assertRaises(ValueError):
            normalize_origination([loan()], mapping, release="synthetic", synthetic=True)

    def test_duplicate_mapped_id_rejected(self):
        with self.assertRaises(ValueError):
            normalize_origination([loan(), loan()], self.mapping,
                                   release="synthetic", synthetic=True)

    def test_monthly_date_proxy_is_explicit(self):
        mapping = copy.deepcopy(self.mapping)
        mapping["origination_date"]["date_format"] = "%Y%m"
        row = loan(origination_date="201701")
        result = normalize_origination([row], mapping, release="synthetic", synthetic=True)
        self.assertEqual(result[0]["origination_date"], "2017-01-01")

    def test_invalid_date_and_reused_sources_rejected(self):
        for row in (loan(origination_date="2017-02-30"), loan(origination_date="2017-1-1")):
            with self.assertRaises(ValueError):
                normalize_origination([row], self.mapping, release="synthetic", synthetic=True)
        mapping = copy.deepcopy(self.mapping)
        mapping["ltv"]["source"] = "dti"
        with self.assertRaises(ValueError):
            normalize_origination([loan()], mapping, release="synthetic", synthetic=True)

    def test_aggregate_audit_reports_join_and_missing_errors(self):
        rows = [loan(dti="999"), loan(dti="999")]
        perf = [{"loan_id": "orphan", "month_on_book": "1",
                 "delinquency_days": "0", "status": "active"}]
        result = audit_cohort(rows, perf)
        self.assertEqual(result["duplicate_origination_rows"], 1)
        self.assertEqual(result["unmatched_performance_rows"], 1)
        self.assertEqual(result["loans_without_performance"], 1)
        self.assertEqual(result["missing_inputs"]["dti"]["rate"], 1)
        self.assertFalse(result["normalized_checks_passed"])
        self.assertNotIn("orphan", str(result))

    def test_valid_audit_and_invalid_numeric(self):
        self.assertTrue(audit_cohort([loan()], [])["normalized_checks_passed"])
        self.assertEqual(audit_cohort([loan(dti="NaN")], [])
                         ["invalid_numeric_values"], {"dti": 1})

class PreprocessingTests(unittest.TestCase):
    def test_train_statistics_and_missing_indicator(self):
        prep = TrainPreprocessor().fit([loan("a", 600), loan("b", 800),
                                       loan("c", "")])
        self.assertEqual(prep.stats["credit_score"]["median"], 700)
        matrix = prep.transform([loan("z", "", split="test")])
        self.assertEqual(matrix[0][:2], [0, 1])
        self.assertEqual(len(matrix[0]), len(prep.feature_names()))

    def test_validation_transform_never_changes_training_stats(self):
        prep = TrainPreprocessor().fit([loan("a", 600), loan("b", 800)])
        before = copy.deepcopy(prep.metadata())
        prep.transform([loan("v", 850, split="validation", loan_purpose="cash_out")])
        self.assertEqual(prep.metadata(), before)

    def test_fit_rejects_validation_test_duplicate_and_missing_ids(self):
        for rows in ([loan(split="test")], [loan(split="validation")],
                     [loan(), loan()], [loan(ident="")], []):
            with self.subTest(rows=rows), self.assertRaises(ValueError):
                TrainPreprocessor().fit(rows)

    def test_all_missing_and_refit_rejected(self):
        with self.assertRaises(ValueError):
            TrainPreprocessor().fit([loan(credit_score="9999")])
        prep = TrainPreprocessor().fit([loan()])
        with self.assertRaises(ValueError):
            prep.fit([loan()])

    def test_unknown_category_is_separate_from_missing(self):
        prep = TrainPreprocessor().fit([loan()])
        names = prep.feature_names()
        unknown = prep.transform([loan(loan_purpose="cash_out")])[0]
        missing = prep.transform([loan(loan_purpose="")])[0]
        self.assertEqual(unknown[names.index("loan_purpose:unknown")], 1)
        self.assertEqual(missing[names.index("loan_purpose:missing")], 1)
        self.assertNotEqual(unknown, missing)

    def test_future_columns_and_identifiers_do_not_change_matrix(self):
        prep = TrainPreprocessor().fit([loan()])
        original = prep.transform([loan()])
        extra = prep.transform([loan(target=1, delinquency_days=999, current_balance=0)])
        self.assertEqual(original, extra)
        self.assertTrue(all(math.isfinite(v) for v in original[0]))

    def test_invalid_numeric_values_rejected(self):
        for field, value in [("dti", "inf"), ("credit_score", "299"),
                             ("original_balance", 0), ("original_term", "1.5"),
                             ("original_rate", True), ("ltv", "-1")]:
            with self.subTest(field=field), self.assertRaises(ValueError):
                numeric_value(field, value)

    def test_not_fitted_and_missing_input_rejected(self):
        with self.assertRaises(ValueError):
            TrainPreprocessor().transform([])
        row = loan()
        del row["ltv"]
        with self.assertRaises(ValueError):
            TrainPreprocessor().fit([row])

class ComparisonTests(unittest.TestCase):
    def test_hand_calculated_metrics_and_censoring(self):
        metric = compare_candidates(predictions(), capacity=2)["models"]["rule"]
        self.assertEqual(metric["precision"], .5)
        self.assertEqual(metric["recall"], .5)
        self.assertAlmostEqual(metric["brier"], .255)
        self.assertEqual(metric["censored"], 1)
        self.assertEqual(metric["cases_found_within_capacity"], 1)
        self.assertEqual(metric["observed_labels"], 4)

    def test_capacity_preserves_ties_without_using_labels(self):
        rows = predictions()
        rows[1]["probability"] = .9
        metric = compare_candidates(rows, capacity=1)["models"]["rule"]
        self.assertEqual(metric["reviewed_within_capacity"], 0)

    def test_identical_cohort_required_for_comparison(self):
        with self.assertRaises(ValueError):
            compare_candidates(predictions() + predictions("tree")[:-1], capacity=2)
        result = compare_candidates(predictions() + predictions("tree"), capacity=2)
        self.assertEqual(set(result["models"]), {"rule", "tree"})

    def test_duplicate_ids_labels_and_bad_probabilities_rejected(self):
        cases = [predictions() + [predictions()[0]], predictions(), predictions()]
        cases[1][0]["target"] = "1"
        cases[2][0]["probability"] = "NaN"
        for rows in cases:
            with self.assertRaises(ValueError):
                compare_candidates(rows, capacity=2)

    def test_cross_model_label_disagreement_rejected(self):
        other = predictions("tree")
        other[0]["target"] = 0
        with self.assertRaises(ValueError):
            compare_candidates(predictions() + other, capacity=2)

    def test_test_requires_single_frozen_candidate(self):
        rows = predictions(split="test")
        with self.assertRaises(ValueError):
            compare_candidates(rows, capacity=2, split="test")
        result = compare_candidates(rows, capacity=2, split="test", frozen_model="rule")
        self.assertEqual(result["split"], "test")
        with self.assertRaises(ValueError):
            compare_candidates(rows + predictions("tree", "test"), capacity=2,
                               split="test", frozen_model="rule")

    def test_wrong_split_capacity_and_all_censored_rejected(self):
        for rows, capacity in [(predictions(split="train"), 2),
                               (predictions(), -1), (predictions(), True),
                               ([{**r, "target": None} for r in predictions()], 2)]:
            with self.assertRaises(ValueError):
                compare_candidates(rows, capacity=capacity)

    def test_undefined_precision_and_recall_are_null(self):
        rows = [{**r, "target": 0, "probability": 0} for r in predictions()]
        result = compare_candidates(rows, capacity=0)["models"]["rule"]
        self.assertIsNone(result["precision"])
        self.assertIsNone(result["recall"])

class DemoTests(unittest.TestCase):
    def test_valid_application_stays_unscored(self):
        result = preview_application({**EXAMPLES["Example A"], "target": 1})
        self.assertTrue(result["ready_for_model"])
        self.assertIsNone(result["probability"])
        self.assertEqual(result["band"], "Unscored")
        self.assertNotIn("target", result["inputs"])

    def test_missing_and_sentinel_values_abstain(self):
        for score in ("", 9999, None):
            result = preview_application({**EXAMPLES["Example A"], "credit_score": score})
            self.assertFalse(result["ready_for_model"])
            self.assertIn("credit_score", result["missing_fields"])

    def test_invalid_demo_categories_and_numbers_rejected(self):
        for extra in ({"original_rate": "NaN"}, {"loan_purpose": "<script>"},
                      {"credit_score": 1000}):
            with self.assertRaises(ValueError):
                preview_application({**EXAMPLES["Example A"], **extra})

    def test_offline_fallback_has_all_presets_and_no_external_assets(self):
        page = offline_html()
        self.assertTrue(all(name in page for name in EXAMPLES))
        self.assertIn("No fitted model", page)
        self.assertNotIn("https://", page)
        self.assertNotIn("<script", page)

@unittest.skipUnless(importlib.util.find_spec("streamlit"), "Optional Streamlit not installed")
class StreamlitUITests(unittest.TestCase):
    def test_form_runs_and_validates(self):
        from pathlib import Path
        from streamlit.testing.v1 import AppTest
        app = AppTest.from_file(str(Path(__file__).resolve().parents[1] /
                                   "resl/mannan_app.py")).run()
        self.assertFalse(app.exception)
        app.button[0].click().run()
        self.assertFalse(app.exception)
        self.assertEqual(app.metric[0].value, "Unscored")

if __name__ == "__main__":
    unittest.main()
