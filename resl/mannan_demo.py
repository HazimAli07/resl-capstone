"""Synthetic local-demo service and offline fallback for D2 4.2.

No fitted mortgage model is available. Valid applications remain unscored.
Run: python -m resl.mannan_demo --out results/mannan-demo
"""
import argparse
import html
import json
from pathlib import Path
from .data_checks import FEATURES
from .mannan_preprocessing import NUMERIC, numeric_value, category_value

EXAMPLES = {
    "Example A": dict(zip(FEATURES, (740, 28, 70, 250000, 4.5, 360,
                                   "purchase", "primary", "single_family"))),
    "Example B": dict(zip(FEATURES, (660, 44, 90, 350000, 5.5, 300,
                                   "refinance", "primary", "condo"))),
    "Missing information": dict(zip(FEATURES, ("", 35, 80, 200000, 4.0, 360,
                                              "purchase", "primary", "single_family"))),
}
OPTIONS = {"loan_purpose": {"purchase", "refinance", "cash_out"},
           "occupancy": {"primary", "second_home", "investment"},
           "property_type": {"single_family", "condo", "cooperative", "manufactured"}}

def preview_application(application):
    """Validate made-up inputs without storing them or manufacturing predictions."""
    if not set(FEATURES).issubset(application):
        raise ValueError("All nine normalized fields must be provided")
    values, missing = {}, []
    for field in FEATURES:
        value = (numeric_value(field, application[field]) if field in NUMERIC
                 else category_value(application[field]))
        if field in OPTIONS and value is not None and value not in OPTIONS[field]:
            raise ValueError(f"{field}: unsupported demo category")
        values[field] = value
        if value is None:
            missing.append(field)
    return {"synthetic_only": True, "ready_for_model": not missing,
            "band": "Unscored", "probability": None, "missing_fields": missing,
            "inputs": values,
            "message": ("Complete missing fields before a future model call." if missing else
                        "Inputs valid. Reviewed trained model and band contract are pending."),
            "warning": "Made-up applications only. No loan approval, rejection or pricing.",
            "explanation": "Input summaries are not model contributions or causal explanations."}

def offline_html():
    """Self-contained offline demonstration; same validated preset service."""
    blocks = []
    for name, record in EXAMPLES.items():
        preview = preview_application(record)
        fields = "".join("<tr><td>" + html.escape(k) + "</td><td>" +
                         html.escape(str(v) if v is not None else "Missing") + "</td></tr>"
                         for k, v in preview["inputs"].items())
        blocks.append("<details><summary>" + html.escape(name) +
                      " — Unscored</summary><p>" + html.escape(preview["message"]) +
                      "</p><table>" + fields + "</table></details>")
    return """<!doctype html><html lang="en"><meta charset="utf-8">
<title>RESL — offline synthetic preview</title><meta name="viewport" content="width=device-width">
<style>body{font:17px system-ui;margin:4rem auto;padding:0 1.5rem;max-width:880px;
background:#f6f4ef;color:#243331}h1{font-size:2.7rem}small{letter-spacing:.1em}
details{background:white;padding:1.3rem;margin:1rem 0;border-radius:12px}
summary{cursor:pointer;font-weight:650}td{padding:.35rem 1rem .35rem 0}
aside{padding:1rem;border-left:4px solid #688577}</style>
<small>TEAM 2B · RESEARCH PROTOTYPE</small><h1>Application review preview</h1>
<aside>Synthetic examples only. No fitted model, risk estimate or lending decision.</aside>
<p>Open an example to inspect normalized inputs and missing-value handling.
Input summaries are not model contributions. Live custom input is in the local Streamlit app.</p>
""" + "".join(blocks) + "<p>Offline fallback · no network, uploads or persistent input storage.</p></html>"

def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--out", type=Path, default=Path("results/mannan-demo"))
    args = parser.parse_args()
    args.out.mkdir(parents=True, exist_ok=True)
    path = args.out / "offline_demo.html"
    path.write_text(offline_html(), encoding="utf-8")
    (args.out / "synthetic_previews.json").write_text(
        json.dumps({name: preview_application(row) for name, row in EXAMPLES.items()},
                   indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"synthetic_only": True, "examples": len(EXAMPLES),
                      "model_loaded": False, "offline_html": str(path)}))

if __name__ == "__main__":
    main()
