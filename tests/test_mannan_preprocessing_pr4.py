"""Codex-assisted PR4 regressions using exclusively invented loan fixtures."""
import copy
import importlib.util
import json
from pathlib import Path
import tempfile
import unittest

from resl.data_checks import FEATURES
from resl.hazim_bundle import FORMAT, ModelBundle, load_bundle
from resl.hazim_contract import VERSION
from resl.hazim_training import synthetic_cohort, train_candidates
from resl.mannan_preprocessing import TrainPreprocessor


def invented_loan(ident="INVENTED-A", **changes):
    """Hand-created values; no source records or release column positions."""
    return {"loan_id": ident, "split": "train", "target": 0,
            "credit_score": 600, "dti": 20, "ltv": 70,
            "original_balance": 100000, "original_rate": 4.5,
            "original_term": 360, "loan_purpose": "purchase",
            "occupancy": "primary", "property_type": "pud", **changes}


def invented_training():
    return [invented_loan(),
            invented_loan("INVENTED-B", credit_score=800, dti=40, target=1,
                          property_type="cooperative"),
            invented_loan("INVENTED-C", credit_score=None, dti=999,
                          loan_purpose=None, property_type=None)]


class PreprocessingPR4Tests(unittest.TestCase):
    def setUp(self):
        self.rows = invented_training()
        self.prep = TrainPreprocessor().fit(self.rows)

    def test_hand_calculated_training_imputation_and_scaling(self):
        self.assertEqual(self.prep.stats["credit_score"]["median"], 700)
        self.assertEqual(self.prep.stats["credit_score"]["mean"], 700)
        self.assertAlmostEqual(self.prep.stats["credit_score"]["scale"],
                               (20000 / 3) ** .5)
        vector = self.prep.transform([self.rows[2]])[0]
        names = self.prep.feature_names()
        self.assertEqual(vector[names.index("credit_score:scaled")], 0)
        self.assertEqual(vector[names.index("credit_score:missing")], 1)
        self.assertEqual(vector[names.index("dti:missing")], 1)
        self.assertEqual(vector[names.index("original_term:scaled")], 0)
        self.assertEqual(self.prep.stats["original_term"]["scale"], 1)

    def test_censored_missing_and_invalid_targets_cannot_be_fit(self):
        for target in (None, "", "1", True, 2, -1):
            with self.subTest(target=target), self.assertRaises(ValueError):
                TrainPreprocessor().fit([invented_loan(target=target)])
        row = invented_loan("INVENTED-UNLABELLED")
        del row["target"]
        with self.assertRaises(ValueError):
            TrainPreprocessor().fit([invented_loan(), row])

    def test_standalone_unlabelled_compatibility_does_not_claim_label_review(self):
        row = invented_loan()
        del row["target"]
        self.assertEqual(TrainPreprocessor().fit([row]).training_count, 1)

    def test_validation_final_test_and_mixed_rows_cannot_be_fit(self):
        for split in ("validation", "test", "final_test", None):
            with self.subTest(split=split), self.assertRaises(ValueError):
                TrainPreprocessor().fit([invented_loan(split=split)])
            with self.subTest(mixed=split), self.assertRaises(ValueError):
                TrainPreprocessor().fit(self.rows + [invented_loan("HELDOUT", split=split)])

    def test_metadata_cannot_mutate_fitted_preprocessing(self):
        before = self.prep.transform(self.rows)
        metadata = self.prep.metadata()
        metadata["numeric"]["credit_score"]["median"] = 350
        metadata["categories"]["property_type"] = ("invented-mutation",)
        metadata["feature_names"].clear()
        self.assertEqual(self.prep.transform(self.rows), before)
        self.assertEqual(self.prep.stats["credit_score"]["median"], 700)

    def test_validation_and_final_test_mutations_leave_fit_unchanged(self):
        before = self.prep.metadata()
        train_vectors = self.prep.transform(self.rows)
        for split in ("validation", "test"):
            heldout = invented_loan("INVENTED-HELDOUT", split=split,
                                     credit_score=850, dti=998, ltv=998,
                                     original_balance=9000000, original_rate=99,
                                     original_term=600, loan_purpose="unseen-purpose",
                                     occupancy=None, property_type="unseen-property")
            self.prep.transform([heldout])
            heldout.update(credit_score=None, dti=999, ltv=999,
                           loan_purpose=None, occupancy="unseen-occupancy", target=None)
            self.prep.transform([heldout])
            self.assertEqual(self.prep.metadata(), before)
            self.assertEqual(self.prep.transform(self.rows), train_vectors)
        self.assertNotIn("unseen-purpose", self.prep.categories["loan_purpose"])

    def test_missing_unknown_and_distinct_property_categories(self):
        names = self.prep.feature_names()
        for value, missing, unknown in ((None, 1, 0), ("", 1, 0),
                                        ("unseen", 0, 1), ("pud", 0, 0),
                                        ("cooperative", 0, 0)):
            with self.subTest(value=value):
                vector = self.prep.transform([invented_loan(property_type=value)])[0]
                self.assertEqual(vector[names.index("property_type:missing")], missing)
                self.assertEqual(vector[names.index("property_type:unknown")], unknown)
                known_count = sum(vector[i] for i, name in enumerate(names)
                                  if name.startswith("property_type:value:"))
                self.assertEqual(known_count, 1 - missing - unknown)

    def test_failed_transform_does_not_change_settings(self):
        before = self.prep.metadata()
        with self.assertRaises(ValueError):
            self.prep.transform([invented_loan(credit_score=float("nan"))])
        with self.assertRaises(ValueError):
            self.prep.fit(self.rows)
        self.assertEqual(self.prep.metadata(), before)

    def test_json_metadata_roundtrip_preserves_names_flags_and_values(self):
        serialized = json.dumps(self.prep.metadata(), allow_nan=False)
        restored = TrainPreprocessor.from_metadata(json.loads(serialized))
        applications = [invented_loan(), invented_loan(credit_score=9999,
                        dti=None, property_type="unseen", loan_purpose=None)]
        self.assertEqual(restored.feature_names(), self.prep.feature_names())
        self.assertEqual(restored.transform(applications), self.prep.transform(applications))
        self.assertEqual(restored.metadata(), self.prep.metadata())
        with self.assertRaises(ValueError):
            restored.fit(self.rows)

    def test_restored_metadata_is_detached_from_input(self):
        metadata = self.prep.metadata()
        restored = TrainPreprocessor.from_metadata(metadata)
        before = restored.transform(self.rows)
        metadata["numeric"]["credit_score"]["mean"] = 350
        metadata["categories"]["property_type"] = ("invented-mutation",)
        self.assertEqual(restored.transform(self.rows), before)

    def test_invalid_saved_metadata_is_rejected(self):
        mutations = [lambda m: m.update(version="unreviewed-v2"),
                     lambda m: m.update(fit_split="test"),
                     lambda m: m.update(training_count=True),
                     lambda m: m.update(training_count=0),
                     lambda m: m.update(extra_field="schema drift"),
                     lambda m: m["numeric"].pop("dti"),
                     lambda m: m["numeric"]["dti"].update(scale=0),
                     lambda m: m["numeric"]["dti"].update(mean=float("nan")),
                     lambda m: m["numeric"]["dti"].update(median=True),
                     lambda m: m["numeric"]["credit_score"].update(median=9999),
                     lambda m: m["categories"].update(property_type=["pud", "pud"]),
                     lambda m: m["categories"].update(property_type=[" "]),
                     lambda m: m["categories"].update(property_type=[1]),
                     lambda m: m["feature_names"].reverse()]
        for change in mutations:
            metadata = self.prep.metadata()
            change(metadata)
            with self.subTest(metadata=metadata), self.assertRaises(ValueError):
                TrainPreprocessor.from_metadata(metadata)

    def test_fractional_training_median_of_integer_inputs_roundtrips(self):
        prep = TrainPreprocessor().fit([invented_loan(credit_score=600),
                invented_loan("INVENTED-B", credit_score=601)])
        restored = TrainPreprocessor.from_metadata(prep.metadata())
        self.assertEqual(restored.stats["credit_score"]["median"], 600.5)

    def test_existing_model_package_roundtrip_reuses_preprocessing(self):
        payload = {"format": FORMAT, "contract": VERSION, "features": list(FEATURES),
                   "synthetic": True, "bands": None, "preprocessing": self.prep.metadata(),
                   "trees": [{"left": [1, -1, -1], "right": [2, -1, -1],
                              "feature": [0, -2, -2], "threshold": [0., -2., -2.],
                              "positive": [.5, .2, .8]}]}
        bundle = ModelBundle(payload)
        application = {f: invented_loan(credit_score=None, property_type="cooperative")[f]
                       for f in FEATURES}
        before = bundle.preprocessor.metadata()
        with tempfile.TemporaryDirectory(prefix="resl-invented-pr4-") as directory:
            path = Path(directory) / "invented-forest.json"
            digest = bundle.save(path)
            loaded = load_bundle(path, expected_hash=digest)
            self.assertEqual(loaded.predict(application), bundle.predict(application))
            self.assertEqual(loaded.preprocessor.metadata(), before)
            with self.assertRaises(ValueError):
                load_bundle(path, expected_hash="0" * 64)
        self.assertEqual(bundle.preprocessor.metadata(), before)


@unittest.skipUnless(importlib.util.find_spec("sklearn"), "Optional model requirements unavailable")
class ObservedTrainingIntegrationPR4Tests(unittest.TestCase):
    def test_validation_and_censored_training_changes_cannot_change_fitted_settings(self):
        train, validation, review = synthetic_cohort()
        original, report, _ = train_candidates(train, validation, review, synthetic=True)
        train_changed, validation_changed = copy.deepcopy(train), copy.deepcopy(validation)
        for row in train_changed:
            if row["target"] is None:
                row.update(credit_score=850, dti=998, ltv=998,
                           original_balance=9000000, property_type="cooperative")
        for row in validation_changed:
            row.update(credit_score=300, dti=0, original_balance=1,
                       property_type="cooperative")
        changed, changed_report, _ = train_candidates(
            train_changed, validation_changed, review, synthetic=True)
        self.assertEqual(original.preprocessor.metadata(), changed.preprocessor.metadata())
        self.assertEqual(original.preprocessor.training_count,
                         sum(row["target"] is not None for row in train))
        self.assertFalse(report["final_test_used"])
        self.assertFalse(changed_report["final_test_used"])


if __name__ == "__main__":
    unittest.main()
