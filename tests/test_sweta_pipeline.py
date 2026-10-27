"""Integration with the existing RESL checks, labels, feature allowlist and splits."""

import csv
import hashlib
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

from resl.data_checks import summarize
from resl.sweta_pipeline import build_rule_baseline


ROOT = Path(__file__).resolve().parents[1]


def fixtures():
    with (ROOT / "data/synthetic/origination.csv").open(newline="") as stream:
        origination = list(csv.DictReader(stream))
    with (ROOT / "data/synthetic/performance.csv").open(newline="") as stream:
        performance = list(csv.DictReader(stream))
    return origination, performance


def build(origination, performance):
    return build_rule_baseline(origination, performance, train_before="2018-01-01", test_from="2019-01-01")


class ExistingPipelineIntegrationTests(unittest.TestCase):
    def test_labels_and_counts_match_existing_project_pipeline(self):
        origination, performance = fixtures()
        rows, report = build(origination, performance)
        original = summarize(origination, performance, "2018-01-01", "2019-01-01")
        self.assertEqual(report["outcome_counts"], original["outcome_counts"])
        self.assertEqual(report["quality"], original["quality"])
        for row in rows:
            self.assertEqual(row["target"], original["outcomes"][row["loan_id"]]["target"])
            self.assertEqual(row["label_reason"], original["outcomes"][row["loan_id"]]["reason"])

    def test_same_chronological_boundaries_and_unique_loans(self):
        rows, report = build(*fixtures())
        self.assertEqual([r["split"] for r in rows], ["train", "train", "validation", "validation", "test", "test"])
        self.assertEqual(len({r["loan_id"] for r in rows}), 6)
        self.assertEqual([v["loans"] for v in report["by_split"].values()], [2, 2, 2])

    def test_labels_and_repayment_do_not_change_scores(self):
        origination, performance = fixtures()
        before, _ = build(origination, performance)
        # Label-only data changes; no new predictor is constructed from it.
        for row in performance:
            if row["status"] == "active":
                row["delinquency_days"] = "90"
        for row in origination:
            row.update(target=1, current_balance=0, delinquency_days=180)
        after, _ = build(origination, performance)
        self.assertEqual([r["score"] for r in before], [r["score"] for r in after])

    def test_censored_loans_remain_explicitly_ineligible(self):
        rows, _ = build(*fixtures())
        censored = [r for r in rows if r["target"] is None]
        self.assertEqual(len(censored), 3)
        self.assertTrue(all(not r["eligible_for_evaluation"] for r in censored))

    def test_missing_scoring_input_abstains_without_relabelling(self):
        origination, performance = fixtures()
        origination[0]["credit_score"] = ""
        rows, report = build(origination, performance)
        self.assertIsNone(rows[0]["score"])
        self.assertFalse(rows[0]["eligible_for_evaluation"])
        self.assertEqual(report["quality"]["missing_candidate_inputs"]["credit_score"], 1)

    def test_upstream_invalid_joins_and_duplicate_months_still_fail(self):
        for kind in ("orphan", "duplicate"):
            origination, performance = fixtures()
            if kind == "orphan":
                performance[0]["loan_id"] = "missing"
            else:
                performance.append(dict(performance[0]))
            with self.subTest(kind=kind), self.assertRaises(ValueError):
                build(origination, performance)

    def test_cli_exports_validation_scores_and_reproducible_manifest(self):
        (ROOT / "results").mkdir(exist_ok=True)
        with tempfile.TemporaryDirectory(dir=ROOT / "results") as directory:
            subprocess.run([sys.executable, "-m", "resl.sweta_pipeline", "--synthetic",
                            "--train-before", "2018-01-01", "--test-from", "2019-01-01",
                            "--out", directory], cwd=ROOT, check=True, capture_output=True, text=True)
            root = Path(directory)
            with (root / "validation_rule_scores.csv").open(newline="") as stream:
                validation = list(csv.DictReader(stream))
            self.assertEqual(len(validation), 2)
            self.assertTrue(all(r["split"] == "validation" for r in validation))
            self.assertNotIn("probability", validation[0])
            manifest = json.loads((root / "manifest.json").read_text())
            self.assertTrue(manifest["synthetic"])
            self.assertFalse(manifest["model_fitted"])
            for name, digest in manifest["output_checksums"].items():
                self.assertEqual(digest, hashlib.sha256((root / name).read_bytes()).hexdigest())

    def test_cli_rejects_real_mode_external_inputs_and_untracked_outputs(self):
        base = [sys.executable, "-m", "resl.sweta_pipeline", "--train-before", "2018-01-01", "--test-from", "2019-01-01"]
        for extra, expected in (([], "synthetic-only"),
                                (["--synthetic", "--origination", "/tmp/loan.csv"], "data/synthetic"),
                                (["--synthetic", "--out", "/tmp/sweta-export"], "ignored results")):
            with self.subTest(extra=extra):
                result = subprocess.run(base + extra, cwd=ROOT, capture_output=True, text=True)
                self.assertNotEqual(result.returncode, 0)
                self.assertIn(expected, result.stderr)
