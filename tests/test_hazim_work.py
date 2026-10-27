"""Behavioral checks for Hazim's research gates, tree export and local integration."""
import copy
import importlib.util
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

from resl.data_checks import FEATURES
from resl.mannan_demo import EXAMPLES
from resl.mannan_preprocessing import TrainPreprocessor
from resl.hazim_contract import (VERSION, canonical_hash, check_access, check_review,
                                  validate_application, validate_partition)
from resl.hazim_bundle import FORMAT, ModelBundle, load_bundle
from resl.hazim_training import synthetic_cohort, train_candidates
from resl.hazim_app import demo_prediction

HAS_MODEL = importlib.util.find_spec("sklearn") is not None
HAS_APP = importlib.util.find_spec("streamlit") is not None

def tiny_payload():
    rows = [dict(EXAMPLES["Example A"], loan_id="A", split="train"),
            dict(EXAMPLES["Example B"], loan_id="B", split="train")]
    prep = TrainPreprocessor().fit(rows)
    return {"format": FORMAT, "contract": VERSION, "features": list(FEATURES),
            "synthetic": True, "bands": None, "preprocessing": prep.metadata(),
            "trees": [{"left": [1, -1, -1], "right": [2, -1, -1],
                       "feature": [0, -2, -2], "threshold": [0., -2., -2.],
                       "positive": [.5, .2, .8]}]}

class ContractTests(unittest.TestCase):
    def setUp(self):
        self.train, self.val, self.review = synthetic_cohort()

    def test_allowlist_rejects_identifier_and_future_input(self):
        for field in ("loan_id", "delinquency_days", "current_balance"):
            with self.assertRaises(ValueError):
                validate_application(dict(EXAMPLES["Example A"], **{field: 1}))

    def test_missing_column_rejected(self):
        row = dict(EXAMPLES["Example A"])
        del row["dti"]
        with self.assertRaises(ValueError):
            validate_application(row)

    def test_nonfinite_boolean_and_bounds_rejected(self):
        for value in ("NaN", "inf", True, 100):
            with self.assertRaises(ValueError):
                validate_application(dict(EXAMPLES["Example A"], original_rate=value if value != 100 else 101))

    def test_missing_sentinel_and_pud_retained(self):
        result = validate_application(dict(EXAMPLES["Example A"], credit_score=9999, property_type="pud"))
        self.assertIsNone(result["credit_score"])
        self.assertEqual(result["property_type"], "pud")
        with self.assertRaises(ValueError):
            validate_application(dict(EXAMPLES["Example A"], property_type="unmapped-source-code"))

    def test_actual_access_gate_remains_closed(self):
        with self.assertRaises(ValueError):
            check_access({"permitted_access_confirmed": False})
        with self.assertRaises(ValueError):
            check_review(dict(self.review, synthetic=False), {}, synthetic=False)

    def test_synthetic_attestation_cannot_be_relabelled_actual(self):
        with self.assertRaises(ValueError):
            check_review(self.review, {}, synthetic=False)

    def test_tags_cannot_override_dates(self):
        rows = copy.deepcopy(self.train)
        rows[0]["origination_date"] = "2022-01-01"
        with self.assertRaises(ValueError):
            validate_partition(rows, "train", self.review)

    def test_duplicate_or_missing_ids_rejected(self):
        for value in (None, "", " " + self.train[1]["loan_id"]):
            rows = copy.deepcopy(self.train)
            rows[0]["loan_id"] = value
            with self.assertRaises(ValueError):
                validate_partition(rows, "train", self.review)
        with self.assertRaises(ValueError):
            validate_partition(self.train + [self.train[0]], "train", self.review)

    def test_late_training_label_rejected(self):
        rows = copy.deepcopy(self.train)
        rows[1]["label_available_on"] = "2018-01-01"
        with self.assertRaises(ValueError):
            validate_partition(rows, "train", self.review)

    def test_late_validation_label_rejected(self):
        rows = copy.deepcopy(self.val)
        rows[1]["label_available_on"] = "2021-01-01"
        with self.assertRaises(ValueError):
            validate_partition(rows, "validation", self.review)

    def test_selection_cutoff_must_precede_test(self):
        with self.assertRaises(ValueError):
            check_review(dict(self.review, validation_as_of="2021-01-01"), synthetic=True)

class BundleTests(unittest.TestCase):
    def test_known_tree_paths_and_roundtrip(self):
        bundle = ModelBundle(tiny_payload())
        self.assertEqual(bundle.predict(EXAMPLES["Example A"])["probability"], .8)
        self.assertEqual(bundle.predict(EXAMPLES["Example B"])["probability"], .2)
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / "forest.json"
            digest = bundle.save(path)
            restored = load_bundle(path, expected_hash=digest)
            self.assertEqual(restored.predict(EXAMPLES["Example A"]), bundle.predict(EXAMPLES["Example A"]))

    def test_package_tampering_rejected(self):
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / "forest.json"
            digest = ModelBundle(tiny_payload()).save(path)
            payload = json.loads(path.read_text())
            payload["trees"][0]["positive"][2] = .99
            path.write_text(json.dumps(payload))
            with self.assertRaises(ValueError):
                load_bundle(path, expected_hash=digest)

    def test_cycle_and_bad_child_rejected(self):
        for child in (0, 100, True):
            payload = tiny_payload()
            payload["trees"][0]["left"][0] = child
            with self.assertRaises(ValueError):
                ModelBundle(payload)

    def test_nonfinite_or_out_of_range_probability_rejected(self):
        for value in (float("nan"), 1.1, -0.1):
            payload = tiny_payload()
            payload["trees"][0]["positive"][0] = value
            with self.assertRaises(ValueError):
                ModelBundle(payload)

    def test_feature_order_version_and_bands_rejected(self):
        for field, value in (("features", list(reversed(FEATURES))), ("contract", "other"),
                             ("bands", {"high": .5})):
            payload = tiny_payload()
            payload[field] = value
            with self.assertRaises(ValueError):
                ModelBundle(payload)

    def test_bad_preprocessing_rejected(self):
        payload = tiny_payload()
        payload["preprocessing"]["numeric"]["dti"]["scale"] = 0
        with self.assertRaises(ValueError):
            ModelBundle(payload)

    def test_actual_package_cannot_enter_synthetic_app(self):
        payload = tiny_payload()
        payload["synthetic"] = False
        with self.assertRaises(ValueError):
            demo_prediction(ModelBundle(payload), EXAMPLES["Example A"])

    def test_missing_inference_field_is_imputed_with_feedback(self):
        result = ModelBundle(tiny_payload()).predict(EXAMPLES["Missing information"])
        self.assertIn("credit_score", result["missing_fields"])
        self.assertEqual(result["band"], "Uncalibrated research score")

@unittest.skipUnless(HAS_MODEL, "optional model requirements unavailable")
class TrainingTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.train, cls.val, cls.review = synthetic_cohort()
        cls.bundle, cls.report, cls.predictions = train_candidates(
            cls.train, cls.val, cls.review, synthetic=True)

    def test_censoring_preprocessing_counts_and_test_isolation(self):
        self.assertEqual(self.bundle.preprocessor.training_count, self.report["counts"]["train_observed"])
        self.assertGreater(self.report["counts"]["train_censored"], 0)
        self.assertEqual(self.report["export_parity_validation_rows"], 40)
        self.assertFalse(self.report["final_test_used"])
        self.assertFalse(self.report["accepted_for_final_test"])

    def test_export_matches_selected_validation_predictions(self):
        selected = self.report["proposed_candidate"]
        expected = {p["loan_id"]: p["probability"] for p in self.predictions if p["model"] == selected}
        for row in self.val:
            result = self.bundle.predict({f: row[f] for f in FEATURES})
            self.assertAlmostEqual(result["probability"], expected[row["loan_id"]], places=12)

    def test_repeated_seed_is_deterministic(self):
        bundle, report, _ = train_candidates(self.train, self.val, self.review, synthetic=True)
        self.assertEqual(canonical_hash(bundle.payload), canonical_hash(self.bundle.payload))
        self.assertEqual(report["validation"], self.report["validation"])

    def test_cross_partition_duplicate_rejected(self):
        val = copy.deepcopy(self.val)
        val[0]["loan_id"] = self.train[0]["loan_id"]
        with self.assertRaises(ValueError):
            train_candidates(self.train, val, self.review, synthetic=True)

    def test_final_test_tag_and_dates_rejected(self):
        val = copy.deepcopy(self.val)
        val[0].update(split="test", origination_date="2022-01-01")
        with self.assertRaises(ValueError):
            train_candidates(self.train, val, self.review, synthetic=True)

    def test_single_class_training_rejected(self):
        train = [dict(r, target=0) for r in self.train]
        with self.assertRaises(ValueError):
            train_candidates(train, self.val, self.review, synthetic=True)

    def test_cli_synthetic_cannot_load_external_files(self):
        result = subprocess.run([sys.executable, "-m", "resl.hazim_training", "--synthetic",
                                 "--train-csv", "forbidden.csv"], capture_output=True, text=True)
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("external inputs prohibited", result.stderr)

@unittest.skipUnless(HAS_MODEL and HAS_APP, "optional model and Streamlit requirements unavailable")
class ModelAppTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        subprocess.run([sys.executable, "-m", "resl.hazim_training", "--synthetic"], check=True, capture_output=True)

    def app(self):
        from streamlit.testing.v1 import AppTest
        return AppTest.from_file("resl/hazim_app.py", default_timeout=20).run()

    def test_valid_synthetic_prediction(self):
        app = self.app()
        app.button[0].click().run()
        self.assertFalse(app.exception)
        self.assertFalse(app.error)
        self.assertEqual(app.metric[0].label, "Synthetic model output")
        self.assertTrue(0 <= float(app.metric[0].value) <= 1)

    def test_invalid_input_prevents_prediction(self):
        app = self.app()
        app.text_input[0].set_value("NaN")
        app.button[0].click().run()
        self.assertFalse(app.exception)
        self.assertTrue(app.error)
        self.assertFalse(app.metric)

    def test_missing_input_prediction_has_imputation_feedback(self):
        app = self.app()
        app.selectbox[0].select("Missing information").run()
        app.button[0].click().run()
        self.assertFalse(app.exception)
        self.assertFalse(app.error)
        self.assertTrue(any("Imputed missing fields" in item.value for item in app.markdown))

if __name__ == "__main__":
    unittest.main()
