"""Run normalized data checks; real loan files require an access record."""

import argparse
import csv
import json
import platform
from pathlib import Path

from .data_checks import summarize


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--origination", type=Path, required=True)
    parser.add_argument("--performance", type=Path, required=True)
    parser.add_argument("--train-before", required=True)
    parser.add_argument("--test-from", required=True)
    parser.add_argument("--out", type=Path, required=True)
    parser.add_argument("--synthetic", action="store_true")
    parser.add_argument("--access-record", type=Path, default=Path("docs/data_access.json"))
    args = parser.parse_args()
    if args.synthetic:
        allowed = (Path(__file__).resolve().parents[1] / "data" / "synthetic").resolve()
        if any(not path.resolve().is_relative_to(allowed) for path in (args.origination, args.performance)):
            parser.error("Synthetic mode accepts only this repository's data/synthetic files")
    else:
        record = json.loads(args.access_record.read_text())
        required = ("source", "release", "selected_years", "terms_reference", "confirmed_by", "confirmed_on")
        if record.get("permitted_access_confirmed") is not True or any(not record.get(k) for k in required):
            parser.error("Permitted access and the dataset release have not been recorded")
    with args.origination.open(newline="") as source:
        origination = list(csv.DictReader(source))
    with args.performance.open(newline="") as source:
        performance = list(csv.DictReader(source))
    try:
        report = summarize(origination, performance, args.train_before, args.test_from)
    except ValueError as error:
        parser.error(str(error))
    report.update({"synthetic": args.synthetic, "python": platform.python_version(),
                   "label_policy": "Draft policy; real-data mapping and review pending."})
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(report, indent=2) + "\n")
    print(json.dumps({"synthetic": args.synthetic, "loans": len(origination),
                      "outcome_counts": report["outcome_counts"], "output": str(args.out)}, indent=2))


if __name__ == "__main__":
    main()
