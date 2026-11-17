"""Runnable local RESL demonstration using a packaged synthetic-trained model."""
import argparse
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
import json
import threading
from urllib.parse import urlsplit
import webbrowser
from pathlib import Path

from resl.data_checks import FEATURES
from resl.hazim_app import demo_prediction
from resl.hazim_bundle import load_bundle
from resl.hazim_contract import CATEGORIES, validate_application
from resl.mannan_demo import EXAMPLES
from resl.mannan_preprocessing import NUMERIC


ROOT = Path(__file__).resolve().parents[1]
FIXTURE = ROOT / "data" / "synthetic" / "mini_demo"
SCENARIOS = {
    "Purchase example": EXAMPLES["Example A"],
    "Refinance example": EXAMPLES["Example B"],
    "Missing credit score": EXAMPLES["Missing information"],
}
LABELS = {
    "credit_score": "Credit score", "dti": "Debt-to-income ratio (%)",
    "ltv": "Loan-to-value ratio (%)", "original_balance": "Original loan amount (USD)",
    "original_rate": "Original annual rate (%)", "original_term": "Original term (months)",
    "loan_purpose": "Loan purpose", "occupancy": "Occupancy", "property_type": "Property type",
}
CHOICES = {
    "purchase": "Purchase", "refinance": "Refinance", "cash_out": "Cash-out refinance",
    "primary": "Primary residence", "second_home": "Second home", "investment": "Investment",
    "single_family": "Single-family home", "condo": "Condominium", "cooperative": "Cooperative",
    "manufactured": "Manufactured home", "pud": "Planned unit development",
}


def load_demo_bundle(folder=FIXTURE):
    """Verify the saved fixture and refuse actual-data models in this demo."""
    folder = Path(folder)
    manifest = json.loads((folder / "manifest.json").read_text(encoding="utf-8"))
    if (not isinstance(manifest, dict) or manifest.get("synthetic") is not True
            or manifest.get("format") != "resl-mini-demo-fixture-v1"):
        raise ValueError("Expected the synthetic mini-demo fixture")
    bundle = load_bundle(folder / "forest.json", expected_hash=manifest.get("model_hash"))
    if bundle.payload["synthetic"] is not True:
        raise ValueError("The mini demo accepts only a synthetic-trained model")
    return bundle


def evaluate_application(bundle, values):
    """Return a real model calculation and its exact submitted input snapshot."""
    clean = validate_application(values)
    prediction = demo_prediction(bundle, clean)
    return {"mode": "fictional application / synthetic-trained model",
            "inputs": clean, "demo_score": prediction["probability"] * 100,
            "missing_fields": prediction["missing_fields"],
            "real_mortgage_probability": None, "lending_decision": None}


def comparison_rows(bundle):
    rows = []
    for name, values in SCENARIOS.items():
        result = evaluate_application(bundle, values)
        rows.append({"Fictional example": name, "Demo score / 100": round(result["demo_score"], 1),
                     "Credit score": str(values["credit_score"]) if values["credit_score"] != "" else "Missing",
                     "DTI (%)": values["dti"], "LTV (%)": values["ltv"],
                     "Missing inputs": len(result["missing_fields"])})
    return rows



WEB_ROOT = Path(__file__).resolve().parent / "demo_web"


def make_handler(bundle):
    """Serve only fixed local assets and bounded, same-origin inference requests."""
    from .build_demo_site import browser_files
    public_model_files = browser_files(bundle)
    class Handler(BaseHTTPRequestHandler):
        def log_message(self, *args):
            pass  # Application inputs are never written to an access log.

        def respond(self, status, body, content_type="application/json"):
            if not isinstance(body, bytes):
                body = json.dumps(body, allow_nan=False).encode("utf-8")
            self.send_response(status)
            self.send_header("Content-Type", content_type)
            self.send_header("Content-Length", str(len(body)))
            self.send_header("Cache-Control", "no-store")
            self.send_header("X-Content-Type-Options", "nosniff")
            self.send_header("Content-Security-Policy", "default-src 'self'; script-src 'self'; "
                             "style-src 'self'; img-src 'self' data:; object-src 'none'; "
                             "base-uri 'none'; frame-ancestors 'none'")
            self.end_headers()
            self.wfile.write(body)

        def do_GET(self):
            path = urlsplit(self.path).path
            if path.lstrip('/') in public_model_files:
                return self.respond(200, public_model_files[path.lstrip('/')])
            if path == "/api/health":
                return self.respond(200, {"status": "ready", "synthetic_model": True})
            if path == "/api/demo":
                return self.respond(200, {"scenarios": SCENARIOS, "labels": LABELS,
                                         "options": CATEGORIES, "option_labels": CHOICES,
                                         "comparison": comparison_rows(bundle),
                                         "model_status": "verified synthetic fixture"})
            assets = {"/": ("index.html", "text/html; charset=utf-8"),
                      "/assets/app.css": ("app.css", "text/css; charset=utf-8"),
                      "/assets/app.js": ("app.js", "text/javascript; charset=utf-8"),
                      "/assets/model.mjs": ("model.mjs", "text/javascript; charset=utf-8")}
            if path not in assets:
                return self.respond(404, {"error": "Not found"})
            filename, content_type = assets[path]
            return self.respond(200, (WEB_ROOT / filename).read_bytes(), content_type)

        def do_POST(self):
            if urlsplit(self.path).path != "/api/predict":
                return self.respond(404, {"error": "Not found"})
            port = self.server.server_port
            origin = self.headers.get("Origin")
            if origin and origin not in {f"http://localhost:{port}", f"http://127.0.0.1:{port}"}:
                return self.respond(403, {"error": "Use this demo from its local page"})
            if self.headers.get_content_type() != "application/json":
                return self.respond(415, {"error": "Expected JSON inputs"})
            try:
                size = int(self.headers.get("Content-Length", "0"))
                if not 0 < size <= 8192:
                    raise ValueError("Invalid request size")
                payload = json.loads(self.rfile.read(size))
                if not isinstance(payload, dict) or set(payload) != {"inputs"} or not isinstance(payload["inputs"], dict):
                    raise ValueError("Expected the nine application inputs")
                result = evaluate_application(bundle, payload["inputs"])
                return self.respond(200, result)
            except (ValueError, TypeError, OverflowError) as exc:
                message = str(exc)
                for field, label in LABELS.items():
                    message = message.replace(field, label)
                return self.respond(400, {"error": message})
    return Handler


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--port", type=int, default=8501)
    parser.add_argument("--open-browser", action="store_true")
    args = parser.parse_args()
    try:
        bundle = load_demo_bundle()
        server = ThreadingHTTPServer(("127.0.0.1", args.port), make_handler(bundle))
    except (OSError, ValueError, KeyError, TypeError) as exc:
        parser.error(str(exc))
    url = f"http://localhost:{server.server_port}"
    print(f"RESL demo is running at {url}. Keep this window open; Ctrl+C stops it.", flush=True)
    if args.open_browser:
        threading.Timer(.5, lambda: webbrowser.open(url)).start()
    try:
        with server:
            server.serve_forever()
    except KeyboardInterrupt:
        pass


if __name__ == "__main__":
    main()
