"""Hand-calculated synthetic tests for Sweta's research-only components."""

from copy import deepcopy
import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

from resl.rule_score import PROPOSED_SETTINGS, score_application, validate_settings
from resl.validation_review import review_validation, wilson_interval


def application(**changes):
    return {"credit_score": 750, "dti": 25, "ltv": 60, **changes}


def prediction(identity, probability, target, split="validation"):
    return dict(loan_id=identity, probability=probability, target=target, split=split)


class RuleScoreTests(unittest.TestCase):
    def test_low_and_high_scenarios(self):
        self.assertEqual(score_application(application())["score"], 0)
        result = score_application(application(credit_score=600, dti=50, ltv=95))
        self.assertEqual(result["score"], 6)
        self.assertEqual(result["maximum_score"], 6)

    def test_credit_boundaries_are_inclusive(self):
        for value, expected in ((619, 2), (620, 2), (621, 1), (679, 1), (680, 1), (681, 0)):
            with self.subTest(value=value):
                self.assertEqual(score_application(application(credit_score=value))["score"], expected)

    def test_ratio_boundaries_are_inclusive(self):
        for field, cases in (("dti", ((35.99, 0), (36, 1), (42.99, 1), (43, 2))),
                             ("ltv", ((79.99, 0), (80, 1), (89.99, 1), (90, 2)))):
            for value, expected in cases:
                with self.subTest(field=field, value=value):
                    self.assertEqual(score_application(application(**{field: value}))["score"], expected)

    def test_missing_and_unavailable_values_abstain(self):
        for field, values in (("credit_score", (None, "", " ", 9999)),
                              ("dti", (None, 999)), ("ltv", (None, 999))):
            for value in values:
                with self.subTest(field=field, value=value):
                    result = score_application(application(**{field: value}))
                    self.assertIsNone(result["score"])
                    self.assertIn(field, result["invalid_inputs"])

    def test_nonfinite_bool_and_out_of_range_abstain(self):
        for field, value in (("credit_score", 299), ("credit_score", 851), ("dti", -1),
                             ("dti", 66), ("ltv", 0), ("ltv", 999), ("ltv", float("nan")),
                             ("dti", float("inf")), ("credit_score", True), ("dti", "bad")):
            with self.subTest(field=field, value=value):
                self.assertIsNone(score_application(application(**{field: value}))["score"])

    def test_metadata_and_outcomes_cannot_change_score(self):
        baseline = score_application(application())
        extra = application(loan_id="x", target=1, delinquency_days=180, current_balance=0,
                            status="reo", origination_date="2040-01-01")
        self.assertEqual(score_application(extra), baseline)

    def test_strings_are_parsed_without_mutating_inputs_or_settings(self):
        row = application(credit_score="620", dti="43", ltv="90")
        saved, settings = deepcopy(row), deepcopy(PROPOSED_SETTINGS)
        self.assertEqual(score_application(row)["score"], 6)
        self.assertEqual(row, saved)
        self.assertEqual(PROPOSED_SETTINGS, settings)

    def test_settings_hash_changes_with_documented_rules(self):
        other = deepcopy(PROPOSED_SETTINGS)
        other["rules"]["dti"]["thresholds"] = [35, 42]
        self.assertNotEqual(validate_settings(other), validate_settings(PROPOSED_SETTINGS))

    def test_invalid_or_leaking_configuration_rejected(self):
        variants = []
        for field, key, value in (("dti", "thresholds", [43, 36]),
                                  ("dti", "thresholds", [36, 36]),
                                  ("dti", "thresholds", [36, float("nan")]),
                                  ("dti", "thresholds", ["36", 43]),
                                  ("dti", "minimum", True), ("dti", "direction", "guess")):
            settings = deepcopy(PROPOSED_SETTINGS)
            settings["rules"][field][key] = value
            variants.append(settings)
        leaking = deepcopy(PROPOSED_SETTINGS)
        leaking["rules"]["target"] = leaking["rules"]["dti"]
        variants.append(leaking)
        for settings in variants:
            with self.subTest(settings=settings), self.assertRaises(ValueError):
                validate_settings(settings)


class ValidationReviewTests(unittest.TestCase):
    def setUp(self):
        self.rows = [prediction("a", 0.1, 0), prediction("b", 0.8, 1)]

    def test_brier_matches_hand_calculation(self):
        result = review_validation(self.rows, max_reviews=1)
        self.assertAlmostEqual(result["brier_score"], 0.025)
        self.assertEqual(result["event_rate"], 0.5)
        self.assertEqual(result["proposed_cutoff"]["threshold"], 0.8)

    def test_confusion_metrics_match_manual_counts(self):
        rows = [prediction("a", .9, 1), prediction("b", .8, 0),
                prediction("c", .7, 1), prediction("d", .1, 0)]
        result = review_validation(rows, max_reviews=3)
        selected = result["proposed_cutoff"]
        self.assertEqual((selected["tp"], selected["fp"], selected["tn"], selected["fn"]), (2, 1, 1, 0))
        self.assertAlmostEqual(selected["precision"], 2/3)
        self.assertEqual(selected["recall"], 1)
        self.assertEqual(selected["false_positive_rate"], .5)
        self.assertAlmostEqual(selected["false_alert_share"], 1/3)

    def test_probability_ties_never_break_capacity(self):
        rows = [prediction("a", .8, 1), prediction("b", .8, 0), prediction("c", .1, 0)]
        result = review_validation(rows, max_reviews=1)
        self.assertTrue(result["proposed_cutoff"]["review_none"])
        self.assertEqual(result["proposed_cutoff"]["reviewed"], 0)

    def test_zero_capacity_uses_review_none(self):
        selected = review_validation(self.rows, max_reviews=0)["proposed_cutoff"]
        self.assertTrue(selected["review_none"])
        self.assertIsNone(selected["precision"])
        self.assertEqual(selected["recall"], 0)

    def test_equal_capture_chooses_fewer_false_alerts(self):
        rows = [prediction("a", .9, 1), prediction("b", .8, 0), prediction("c", .1, 0)]
        self.assertEqual(review_validation(rows, max_reviews=3)["proposed_cutoff"]["threshold"], .9)

    def test_reliability_bin_boundaries_and_empty_bins(self):
        rows = [prediction("a", 0, 0), prediction("b", .5, 1), prediction("c", 1, 1)]
        bins = review_validation(rows, max_reviews=1, bins=2)["reliability_bins"]
        self.assertEqual([b["count"] for b in bins], [1, 2])
        self.assertEqual(bins[1]["mean_probability"], .75)
        self.assertEqual(bins[1]["observed_rate"], 1)
        empty = review_validation(self.rows, max_reviews=1, bins=10)["reliability_bins"][4]
        self.assertEqual(empty["count"], 0)
        self.assertIsNone(empty["observed_rate"])

    def test_wilson_interval_reference_and_empty(self):
        low, high = wilson_interval(5, 10)
        self.assertAlmostEqual(low, .236593, places=5)
        self.assertAlmostEqual(high, .763407, places=5)
        self.assertIsNone(wilson_interval(0, 0))

    def test_single_class_reports_no_cutoff(self):
        for target in (0, 1):
            result = review_validation([prediction("a", .2, target)], max_reviews=1)
            self.assertIsNone(result["proposed_cutoff"])
            self.assertEqual(result["proposal_status"], "insufficient_class_support")

    def test_censored_rows_excluded_not_negative(self):
        rows = self.rows + [prediction("c", .9, None)]
        result = review_validation(rows, max_reviews=1)
        self.assertEqual(result["input_count"], 3)
        self.assertEqual(result["labelled_count"], 2)
        self.assertEqual(result["excluded_censored_count"], 1)
        self.assertEqual(result["event_rate"], .5)

    def test_invalid_predictions_stop_including_censored_rows(self):
        for key, values in (("split", ("test", "train", "")),
                            ("probability", (-.1, 1.1, float("nan"), float("inf"), True, "")),
                            ("target", (2, -1, True, "unknown")),
                            ("loan_id", (None, "", " a "))):
            for value in values:
                row = prediction("x", .3, 1)
                row[key] = value
                with self.subTest(key=key, value=value), self.assertRaises(ValueError):
                    review_validation(self.rows + [row], max_reviews=1)
        with self.assertRaises(ValueError):
            review_validation(self.rows + [prediction("a", .2, None)], max_reviews=1)
        with self.assertRaises(ValueError):
            review_validation([prediction("a", "bad", None)], max_reviews=1)

    def test_schema_empty_and_invalid_options(self):
        for rows in ([], [prediction("a", .2, None)], [{"split": "validation"}]):
            with self.assertRaises(ValueError):
                review_validation(rows, max_reviews=1)
        for capacity in (-1, .5, True):
            with self.assertRaises(ValueError):
                review_validation(self.rows, max_reviews=capacity)
        for bins in (0, 51, True, 1.5):
            with self.assertRaises(ValueError):
                review_validation(self.rows, max_reviews=1, bins=bins)

    def test_candidate_conservation_and_capacity(self):
        result = review_validation(self.rows, max_reviews=1)
        for c in result["threshold_candidates"]:
            self.assertEqual(c["tp"] + c["fn"], result["events"])
            self.assertEqual(c["tp"] + c["fp"] + c["tn"] + c["fn"], result["labelled_count"])
        self.assertLessEqual(result["proposed_cutoff"]["reviewed"], 1)
        json.dumps(result, allow_nan=False)

    def test_row_order_does_not_change_candidate_selection(self):
        self.assertEqual(review_validation(self.rows, max_reviews=1),
                         review_validation(list(reversed(self.rows)), max_reviews=1))


class SyntheticDemoTests(unittest.TestCase):
    def test_cli_writes_valid_json_csv_and_labelled_chart(self):
        with tempfile.TemporaryDirectory() as directory:
            subprocess.run([sys.executable, "-m", "resl.sweta_demo", "--out", directory],
                           check=True, capture_output=True, text=True)
            root = Path(directory)
            result = json.loads((root / "report.json").read_text())
            self.assertTrue(result["synthetic"])
            self.assertFalse(result["model_fitted"])
            self.assertEqual(len(result["rule_examples"]), 6)
            self.assertIn("SYNTHETIC", (root / "synthetic_reliability.svg").read_text())
            self.assertEqual(len((root / "synthetic_predictions.csv").read_text().splitlines()), 9)
