"""Mini-demo behavior on fictional applications and a synthetic-only package."""
import json
from pathlib import Path
import shutil
from http.server import ThreadingHTTPServer
import threading
from urllib.error import HTTPError
from urllib.request import Request, urlopen
import tempfile
import unittest

from resl.hazim_contract import canonical_hash
from resl.mini_demo import FIXTURE, SCENARIOS, evaluate_application, load_demo_bundle


class MiniDemoServiceTests(unittest.TestCase):
    def test_packaged_fixture_is_synthetic_verified_and_repeatable(self):
        bundle = load_demo_bundle()
        a = evaluate_application(bundle, SCENARIOS["Purchase example"])
        b = evaluate_application(load_demo_bundle(), SCENARIOS["Purchase example"])
        self.assertTrue(bundle.payload["synthetic"])
        self.assertEqual(a, b)
        self.assertTrue(0 <= a["demo_score"] <= 100)
        self.assertIsNone(a["real_mortgage_probability"])
        self.assertIsNone(a["lending_decision"])

    def test_distinct_examples_produce_calculated_not_fixed_outputs(self):
        bundle = load_demo_bundle()
        a = evaluate_application(bundle, SCENARIOS["Purchase example"])
        b = evaluate_application(bundle, SCENARIOS["Refinance example"])
        self.assertNotEqual(a["demo_score"], b["demo_score"])
        self.assertEqual(a["inputs"]["credit_score"], 740)

    def test_missing_credit_score_is_reported_with_input_snapshot(self):
        result = evaluate_application(load_demo_bundle(), SCENARIOS["Missing credit score"])
        self.assertEqual(result["missing_fields"], ["credit_score"])
        self.assertIsNone(result["inputs"]["credit_score"])

    def test_invalid_and_extra_fields_never_reach_a_prediction(self):
        for change in ({"credit_score": 1000}, {"original_balance": 0}, {"loan_id": "PRIVATE"}):
            with self.subTest(change=change), self.assertRaises(ValueError):
                evaluate_application(load_demo_bundle(), SCENARIOS["Purchase example"] | change)

    def test_tampered_fixture_fails_checksum(self):
        with tempfile.TemporaryDirectory() as directory:
            folder = Path(directory)
            shutil.copy2(FIXTURE / "manifest.json", folder / "manifest.json")
            payload = json.loads((FIXTURE / "forest.json").read_text())
            payload["trees"][0]["positive"][0] = .123456789
            (folder / "forest.json").write_text(json.dumps(payload))
            with self.assertRaisesRegex(ValueError, "checksum"):
                load_demo_bundle(folder)

    def test_actual_package_is_rejected_even_with_matching_checksum(self):
        with tempfile.TemporaryDirectory() as directory:
            folder = Path(directory)
            payload = json.loads((FIXTURE / "forest.json").read_text())
            payload["synthetic"] = False
            manifest = json.loads((FIXTURE / "manifest.json").read_text())
            manifest["model_hash"] = canonical_hash(payload)
            (folder / "forest.json").write_text(json.dumps(payload))
            (folder / "manifest.json").write_text(json.dumps(manifest))
            with self.assertRaisesRegex(ValueError, "synthetic-trained"):
                load_demo_bundle(folder)


class MiniDemoHTTPTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        from resl.mini_demo import make_handler
        cls.server = ThreadingHTTPServer(("127.0.0.1", 0), make_handler(load_demo_bundle()))
        cls.url = f"http://127.0.0.1:{cls.server.server_port}"
        cls.thread = threading.Thread(target=cls.server.serve_forever, daemon=True)
        cls.thread.start()

    @classmethod
    def tearDownClass(cls):
        cls.server.shutdown()
        cls.server.server_close()
        cls.thread.join(timeout=5)

    def request(self, path, body=None, headers=None):
        request = Request(self.url + path, data=body, headers=headers or {})
        try:
            response = urlopen(request, timeout=5)
        except HTTPError as error:
            response = error
        with response:
            return response.status, response.headers, response.read()

    def test_live_page_assets_and_configuration_load(self):
        for path in ("/", "/assets/app.css", "/assets/app.js", "/api/health", "/api/demo"):
            status, headers, body = self.request(path)
            self.assertEqual(status, 200, path)
            self.assertEqual(headers["X-Content-Type-Options"], "nosniff")
            self.assertIn("script-src 'self'", headers["Content-Security-Policy"])
            self.assertTrue(body)
        status, _, body = self.request("/api/demo")
        data = json.loads(body)
        self.assertEqual(len(data["comparison"]), 3)
        self.assertIn("Purchase example", data["scenarios"])

    def test_http_prediction_matches_verified_model(self):
        values = SCENARIOS["Purchase example"]
        status, _, body = self.request("/api/predict", json.dumps({"inputs": values}).encode(),
                                       {"Content-Type": "application/json"})
        self.assertEqual(status, 200)
        self.assertEqual(json.loads(body), evaluate_application(load_demo_bundle(), values))

    def test_invalid_fields_and_bad_json_return_errors_not_predictions(self):
        for payload in ({"inputs": SCENARIOS["Purchase example"] | {"credit_score":1000}},
                        {"inputs": SCENARIOS["Purchase example"] | {"loan_id":"PRIVATE"}},
                        {"inputs": []}, {"unexpected":True}):
            with self.subTest(payload=payload):
                status, _, body = self.request("/api/predict", json.dumps(payload).encode(),
                                               {"Content-Type":"application/json"})
                self.assertEqual(status, 400)
                self.assertIn("error", json.loads(body))
                self.assertNotIn("demo_score", json.loads(body))

    def test_cross_origin_oversized_and_arbitrary_file_requests_are_blocked(self):
        status, _, _ = self.request("/api/predict", b"{}", {"Content-Type":"application/json",
                                                            "Origin":"https://unrelated.example"})
        self.assertEqual(status, 403)
        status, _, _ = self.request("/api/predict", b"x"*8193, {"Content-Type":"application/json"})
        self.assertEqual(status, 400)
        for path in ("/../docs/data_access.json", "/assets/../mini_demo.py", "/forest.json"):
            self.assertEqual(self.request(path)[0], 404)


if __name__ == "__main__":
    unittest.main()
