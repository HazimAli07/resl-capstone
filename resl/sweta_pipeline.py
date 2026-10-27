"""D2 2.3: connect Sweta's score to the repository's existing synthetic pipeline."""

import argparse
from collections import Counter
import csv
import hashlib
import json
import platform
from pathlib import Path

from .data_checks import chronological_split, feature_record, summarize
from .rule_score import PROPOSED_SETTINGS, score_application


def build_rule_baseline(origination, performance, *, train_before, test_from):
    """Reuse project QA, outcome and split rules; keep outcomes out of scoring.

    Development-only composition on normalized synthetic records. This does not
    change or approve the upstream schema, labels, time origin or split dates.
    Points remain ranking values, never inputs to probability calibration.
    """
    summary = summarize(origination, performance, train_before, test_from)
    splits = chronological_split(origination, train_before, test_from)
    split_by_id = {identity: group for group, identities in splits.items() for identity in identities}
    rows = []
    for record in origination:
        identity = record["loan_id"]
        result = score_application(feature_record(record))
        label = summary["outcomes"][identity]
        rows.append({"loan_id": identity, "split": split_by_id[identity],
                     "target": label["target"], "label_reason": label["reason"],
                     "score": result["score"], "score_status": result["status"],
                     "eligible_for_evaluation": label["target"] is not None and result["score"] is not None,
                     "settings_version": result["settings_version"],
                     "settings_sha256": result["settings_sha256"],
                     "components_json": json.dumps(result["components"], sort_keys=True),
                     "invalid_inputs_json": json.dumps(result["invalid_inputs"], sort_keys=True)})
    counts = {group: {"loans": len(identities),
                      "eligible_labelled_scored": sum(r["eligible_for_evaluation"] for r in rows if r["split"] == group)}
              for group, identities in splits.items()}
    return rows, {"quality": summary["quality"], "outcome_counts": summary["outcome_counts"],
                  "split_boundaries": summary["split_boundaries"], "by_split": counts,
                  "score_status_counts": dict(Counter(r["score_status"] for r in rows)),
                  "limitation": "Synthetic integration check only; no model fit, performance claim or calibration."}


def _checksum(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main():
    root = Path(__file__).resolve().parents[1]
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--origination", type=Path, default=root / "data/synthetic/origination.csv")
    parser.add_argument("--performance", type=Path, default=root / "data/synthetic/performance.csv")
    parser.add_argument("--train-before", required=True)
    parser.add_argument("--test-from", required=True)
    parser.add_argument("--synthetic", action="store_true")
    parser.add_argument("--out", type=Path, default=root / "results/sweta-pipeline")
    args = parser.parse_args()
    if not args.synthetic:
        parser.error("This proposed rule baseline is synthetic-only; real-data integration requires team review")
    allowed = (root / "data/synthetic").resolve()
    if any(not path.resolve().is_relative_to(allowed) for path in (args.origination, args.performance)):
        parser.error("Synthetic mode accepts only the repository's data/synthetic files")
    if not args.out.resolve().is_relative_to((root / "results").resolve()):
        parser.error("Outputs must remain under the repository's ignored results/ directory")
    try:
        with args.origination.open(newline="") as stream:
            origination = list(csv.DictReader(stream))
        with args.performance.open(newline="") as stream:
            performance = list(csv.DictReader(stream))
        rows, summary = build_rule_baseline(origination, performance,
                                            train_before=args.train_before, test_from=args.test_from)
    except (ValueError, OSError) as exc:
        parser.error(str(exc))
    args.out.mkdir(parents=True, exist_ok=True)
    for name, selected in (("rule_scores.csv", rows),
                           ("validation_rule_scores.csv", [r for r in rows if r["split"] == "validation"])):
        with (args.out / name).open("w", newline="") as stream:
            writer = csv.DictWriter(stream, fieldnames=list(rows[0]))
            writer.writeheader()
            writer.writerows(selected)
    code_paths = [Path(__file__), root / "resl/data_checks.py", root / "resl/rule_score.py"]
    summary.update({"synthetic": True, "model_fitted": False, "python": platform.python_version(),
                    "source_checksums": {"origination": _checksum(args.origination),
                                         "performance": _checksum(args.performance)},
                    "code_checksums": {p.name: _checksum(p) for p in code_paths},
                    "output_checksums": {name: _checksum(args.out / name) for name in
                                         ("rule_scores.csv", "validation_rule_scores.csv")},
                    "settings": PROPOSED_SETTINGS})
    (args.out / "manifest.json").write_text(json.dumps(summary, indent=2, allow_nan=False) + "\n")
    print(json.dumps({"synthetic": True, "loans": len(rows), "by_split": summary["by_split"],
                      "outcome_counts": summary["outcome_counts"], "output": str(args.out)}, indent=2))


if __name__ == "__main__":
    main()
