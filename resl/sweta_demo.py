"""Run Sweta's independent synthetic development checks; reads no loan files."""

import argparse
import csv
import json
import platform
from pathlib import Path

from .rule_score import PROPOSED_SETTINGS, score_application
from .validation_review import review_validation


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--out", type=Path, default=Path("results/sweta-synthetic"))
    args = parser.parse_args()
    args.out.mkdir(parents=True, exist_ok=True)
    # Hand-designed scenarios, unrelated to licensed source records.
    cases = [(760, 25, 60), (680, 36, 80), (620, 43, 90), (600, 50, 95),
             (700, 40, 85), (None, 30, 70)]
    scores = [{"loan_id": f"SYNTHETIC_RULE_{i:02}",
               **score_application(dict(zip(("credit_score", "dti", "ltv"), values)))}
              for i, values in enumerate(cases, 1)]
    # Invented probabilities for diagnostic arithmetic only; no model ran.
    predictions = [{"loan_id": f"SYNTHETIC_PROB_{i:02}", "split": "validation",
                    "target": y, "probability": p}
                   for i, (p, y) in enumerate([(0.05, 0), (0.15, 0), (0.25, 1),
                                              (0.40, 0), (0.60, 1), (0.60, 0),
                                              (0.80, 1), (0.95, 1)], 1)]
    report = review_validation(predictions, max_reviews=3, bins=5)
    payload = {"synthetic": True, "model_fitted": False, "python": platform.python_version(),
               "rule_settings": PROPOSED_SETTINGS, "rule_examples": scores,
               "invented_probability_diagnostics": report}
    (args.out / "report.json").write_text(json.dumps(payload, indent=2, allow_nan=False) + "\n")
    with (args.out / "synthetic_predictions.csv").open("w", newline="") as stream:
        writer = csv.DictWriter(stream, fieldnames=["loan_id", "split", "target", "probability"])
        writer.writeheader()
        writer.writerows(predictions)
    # Dependency-free, colour-blind-friendly diagnostic plot.
    marks = []
    for item in report["reliability_bins"]:
        if item["count"]:
            x, y = 70 + 400 * item["mean_probability"], 470 - 400 * item["observed_rate"]
            lo, hi = item["observed_rate_wilson95"]
            marks.append(f'<line x1="{x}" x2="{x}" y1="{470-400*hi}" y2="{470-400*lo}" stroke="#0072B2"/>'
                         f'<circle cx="{x}" cy="{y}" r="5" fill="#0072B2"><title>n={item["count"]}; invented predictions</title></circle>')
    svg = ('<svg xmlns="http://www.w3.org/2000/svg" width="560" height="550" viewBox="0 0 560 550">'
           '<rect width="560" height="550" fill="white"/>'
           '<g font-family="sans-serif" fill="#222">'
           '<text x="30" y="25" font-size="19">SYNTHETIC reliability diagnostic</text>'
           '<text x="30" y="47" font-size="12">Invented probabilities; no trained model or real loan results</text>'
           '<path d="M70 70V470H470" fill="none" stroke="#222"/>'
           '<path d="M70 470L470 70" fill="none" stroke="#666" stroke-dasharray="5 5"/>'
           '<text x="65" y="491">0</text><text x="465" y="491">1</text>'
           '<text x="45" y="474">0</text><text x="45" y="75">1</text>'
           '<text x="180" y="515">Mean predicted probability</text>'
           '<text transform="translate(20 350) rotate(-90)">Observed event fraction</text>'
           '<text x="70" y="540" font-size="11">Bars: descriptive Wilson 95% intervals; small synthetic sample</text>'
           + ''.join(marks) + '</g></svg>')
    (args.out / "synthetic_reliability.svg").write_text(svg)
    print(json.dumps({"synthetic": True, "model_fitted": False,
                      "scored_examples": len(scores), "prediction_examples": len(predictions),
                      "output": str(args.out)}, indent=2))


if __name__ == "__main__":
    main()
