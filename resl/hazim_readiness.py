"""Read-only actual-data readiness check; does not read loans or train models.

AI-assisted implementation for Hazim's D2 1.1/2.1 work. Passing this check
validates required evidence fields; it does not grant data permission or replace
independent source, label, timing and split review.
"""
import argparse
import json
from pathlib import Path

from .hazim_contract import check_access, check_review, check_timing_review


def readiness_report(access, review):
    checks = {}
    for name, check in (
        ("permitted_access", lambda: check_access(access)),
        ("feature_timing", lambda: check_timing_review(review)),
        ("source_labels_and_splits", lambda: check_review(review, access, synthetic=False)),
    ):
        try:
            check()
            checks[name] = {"passed": True}
        except (ValueError, TypeError, KeyError) as exc:
            checks[name] = {"passed": False, "reason": str(exc)}
    digest_fields = ("train_csv_sha256", "validation_csv_sha256")
    digests = [review.get(key) for key in digest_fields]
    valid = all(isinstance(d, str) and len(d) == 64 and
                all(c in "0123456789abcdef" for c in d) for d in digests)
    checks["reviewed_input_digests"] = {
        "passed": valid,
        **({} if valid else {"reason": "Exact train/validation SHA-256 digests are required"}),
    }
    return {
        "format": "resl-actual-data-readiness-v1",
        "ready": all(c["passed"] for c in checks.values()),
        "checks": checks,
        "loan_files_read": False,
        "model_trained": False,
        "final_test_used": False,
        "limitation": "Evidence-record checks only; human/source acceptance is still required.",
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--access-record", type=Path, default=Path("docs/data_access.json"))
    parser.add_argument("--review", type=Path, default=Path("docs/hazim_review.example.json"))
    parser.add_argument("--out", type=Path)
    args = parser.parse_args()
    try:
        access = json.loads(args.access_record.read_text(encoding="utf-8"))
        review = json.loads(args.review.read_text(encoding="utf-8"))
        if not isinstance(access, dict) or not isinstance(review, dict):
            raise ValueError("Access and review records must be JSON objects")
        report = readiness_report(access, review)
        text = json.dumps(report, indent=2) + "\n"
        if args.out:
            root = Path(__file__).resolve().parents[1]
            if not args.out.resolve().is_relative_to(root / "results"):
                raise ValueError("Readiness outputs must stay in ignored repository results/ storage")
            args.out.parent.mkdir(parents=True, exist_ok=True)
            args.out.write_text(text, encoding="utf-8")
        print(text, end="")
        return 0 if report["ready"] else 2
    except (ValueError, TypeError, OSError) as exc:
        parser.error(str(exc))


if __name__ == "__main__":
    raise SystemExit(main())
