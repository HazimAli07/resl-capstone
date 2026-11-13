"""Stream July 2026 SFLLD files for private structural checks, without training."""

import argparse
from collections import Counter
import json
from pathlib import Path
import re
import zipfile

from .freddie_source import validate_manifest, verify_archives
from .hazim_contract import check_access


LAYOUT_URL = "https://www.freddiemac.com/fmac-resources/research/pdf/file_layout_july_2026.xlsx"
LAYOUT_SHA256 = "e4ee4ba00b5b1a8d18e2debe3acafdd019b48bafafdeb907cf5b19b49c989f23"
MAX_LINE_BYTES = 16384
# Positional aliases transcribed from the official workbook, not CSV headers.
ORIGINATION = (
    "credit_score", "first_payment_month", "first_time_homebuyer", "maturity_month",
    "msa", "mortgage_insurance_pct", "number_of_units", "occupancy", "cltv",
    "dti", "original_balance", "ltv", "original_rate", "channel",
    "prepayment_penalty", "amortization_type", "property_state", "property_type",
    "postal_code", "loan_id", "loan_purpose", "original_term", "number_of_borrowers",
    "seller_name", "super_conforming", "pre_harp_loan_id", "special_eligibility",
    "harp_indicator", "property_valuation_method", "interest_only", "vantage_score",
)
PERFORMANCE = (
    "loan_id", "reporting_month", "current_balance", "delinquency_code", "loan_age",
    "remaining_term", "defect_settlement_month", "modification_flag",
    "zero_balance_code", "zero_balance_month", "current_rate", "non_interest_balance",
    "ddlpi", "mi_recoveries", "net_sales_proceeds", "non_mi_recoveries",
    "total_expenses", "legal_costs", "maintenance_costs", "taxes_insurance",
    "misc_expenses", "actual_loss", "cumulative_modification_costs",
    "interest_rate_step", "payment_deferral", "estimated_ltv",
    "zero_balance_removal_balance", "delinquent_accrued_interest",
    "disaster_delinquency", "borrower_assistance", "current_modification_costs",
    "interest_bearing_balance", "mi_cancellation", "servicer_name",
    "bankruptcy_cramdown_costs",
)
COLUMNS = {"origination": ORIGINATION, "performance": PERFORMANCE}
MISSING_CODES = {
    "credit_score": {"", "9999"}, "dti": {"", "999"}, "ltv": {"", "999"},
    "original_balance": {""}, "original_rate": {""}, "original_term": {""},
    "loan_purpose": {"", "9"}, "occupancy": {"", "9"},
    "property_type": {"", "99"},
}


def month_index(value):
    """Validate a disclosed YYYYMM month; never invent an origination day."""
    if not isinstance(value, str) or re.fullmatch(r"[0-9]{6}", value) is None:
        raise ValueError("Expected a YYYYMM month")
    year, month = int(value[:4]), int(value[4:])
    if not 1 <= year <= 9999 or not 1 <= month <= 12:
        raise ValueError("Invalid calendar month")
    return year * 12 + month - 1


def iter_records(stream, kind):
    """Read binary lines strictly. Errors identify positions, never row contents."""
    if kind not in COLUMNS:
        raise ValueError("Unknown source file kind")
    columns = COLUMNS[kind]
    line_number = 0
    while True:
        raw = stream.readline(MAX_LINE_BYTES + 1)
        if not raw:
            return
        line_number += 1
        location = f"{kind} line {line_number}"
        if len(raw) > MAX_LINE_BYTES:
            raise ValueError(f"{location}: oversized record")
        try:
            line = raw.rstrip(b"\r\n").decode("utf-8")
        except UnicodeDecodeError:
            raise ValueError(f"{location}: invalid UTF-8") from None
        if not line or any(ord(c) < 32 for c in line):
            raise ValueError(f"{location}: blank record or control character")
        values = line.split("|")  # Keep empty final columns; no CSV quote semantics.
        if len(values) != len(columns):
            raise ValueError(f"{location}: expected {len(columns)} fields, got {len(values)}")
        row = dict(zip(columns, values))
        if row["loan_id"].strip().lower() in {"loan_id", "loan identifier", "loan sequence number"}:
            raise ValueError(f"{location}: unexpected header row")
        if not row["loan_id"].strip() or row["loan_id"] != row["loan_id"].strip():
            raise ValueError(f"{location}: blank or noncanonical loan identifier")
        field = "first_payment_month" if kind == "origination" else "reporting_month"
        try:
            month_index(row[field])
        except ValueError:
            raise ValueError(f"{location}: invalid {field}") from None
        yield row


def profile_streams(origination, performance, *, performance_cutoff):
    """Check raw grain/joins; omit loan IDs, labels and predictor values in output."""
    cutoff = month_index(performance_cutoff[:4] + performance_cutoff[5:7])
    first_payments, missing = {}, Counter({f: 0 for f in MISSING_CODES})
    orig_rows = duplicate_orig = 0
    for row in iter_records(origination, "origination"):
        orig_rows += 1
        loan = row["loan_id"]
        duplicate_orig += loan in first_payments
        first_payments.setdefault(loan, month_index(row["first_payment_month"]))
        for field, sentinels in MISSING_CODES.items():
            missing[field] += row[field].strip() in sentinels
    # A compact calendar bitmap per loan catches nonadjacent duplicate months
    # without retaining millions of performance rows or assuming file sorting.
    masks = {}
    perf_rows = duplicates = orphan_rows = before_first_payment = 0
    minimum = maximum = None
    base = month_index("199901")
    for row in iter_records(performance, "performance"):
        perf_rows += 1
        loan, period = row["loan_id"], month_index(row["reporting_month"])
        if not base <= period <= cutoff:
            raise ValueError(f"performance line {perf_rows}: reporting month outside acquisition range")
        bit = 1 << (period - base)
        previous = masks.get(loan, 0)
        duplicates += bool(previous & bit)
        masks[loan] = previous | bit
        minimum = period if minimum is None else min(minimum, period)
        maximum = period if maximum is None else max(maximum, period)
        if loan not in first_payments:
            orphan_rows += 1
        elif period < first_payments[loan]:
            before_first_payment += 1
    without_performance = len(first_payments.keys() - masks.keys())
    def display_month(value):
        return None if value is None else f"{value // 12:04d}{value % 12 + 1:02d}"
    return {
        "origination_rows": orig_rows, "unique_origination_loans": len(first_payments),
        "duplicate_origination_rows": duplicate_orig, "performance_rows": perf_rows,
        "unique_performance_loans": len(masks), "duplicate_loan_month_rows": duplicates,
        "orphan_performance_rows": orphan_rows,
        "orphan_performance_loans": len(masks.keys() - first_payments.keys()),
        "loans_without_performance": without_performance,
        "performance_before_first_payment_rows": before_first_payment,
        "first_payment_month_range": [display_month(min(first_payments.values())) if first_payments else None,
                                      display_month(max(first_payments.values())) if first_payments else None],
        "reporting_month_range": [display_month(minimum), display_month(maximum)],
        "missing_or_sentinel_input_rows": dict(missing),
        "missing_input_denominator": orig_rows,
        "key_and_join_checks_passed": bool(orig_rows and perf_rows and not any(
            (duplicate_orig, duplicates, orphan_rows, without_performance))),
    }


def profile_archives(manifest, archive_dir, access):
    """Require recorded access and exact acquired ZIP integrity before row reads."""
    if not isinstance(access, dict) or not isinstance(manifest, dict):
        raise ValueError("Access and source manifest must be JSON objects")
    check_access(access)
    validate_manifest(manifest)
    if (access["source"] != manifest["source"]
            or access["terms_reference"] != manifest["terms_reference"]
            or set(access["selected_years"]) != {a["vintage_year"] for a in manifest["archives"]}):
        raise ValueError("Access record and acquisition manifest differ")
    verified = verify_archives(manifest, archive_dir)
    profiles = []
    for item in manifest["archives"]:
        year = item["vintage_year"]
        with zipfile.ZipFile(Path(archive_dir) / item["filename"]) as archive:
            with archive.open(f"sample_orig_{year}.txt") as orig:
                with archive.open(f"sample_perf_{year}.txt") as perf:
                    profile = profile_streams(orig, perf,
                                              performance_cutoff=manifest["performance_cutoff"])
        profiles.append({"vintage_year": year, **profile})
    return {
        "format": "resl-freddie-structural-profile-v1", "layout_reference": LAYOUT_URL,
        "layout_sha256": LAYOUT_SHA256, "guide_release": manifest["guide_release"],
        "performance_cutoff": manifest["performance_cutoff"], "verified_archives": verified,
        "profiles": profiles, "loan_rows_read": True, "loan_ids_published": False,
        "normalized_inputs_written": False, "model_inputs_validated": False,
        "labels_constructed": False, "study_partitions_accepted": False,
        "model_trained": False, "final_test_evaluated": False,
        "limitation": "Structural profile only. Same-width column reordering is not detectable; "
                      "the exact source layout must be reviewed. Date/label/input/split acceptance remains pending.",
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--archive-dir", type=Path, required=True)
    parser.add_argument("--manifest", type=Path, default=Path("docs/freddie_source_manifest.json"))
    parser.add_argument("--access-record", type=Path, default=Path("docs/data_access.json"))
    parser.add_argument("--out", type=Path, required=True)
    args = parser.parse_args()
    try:
        root = Path(__file__).resolve().parents[1]
        if not args.out.resolve().is_relative_to(root / "results"):
            raise ValueError("Profiles must stay in ignored repository results/ storage")
        manifest = json.loads(args.manifest.read_text(encoding="utf-8"))
        access = json.loads(args.access_record.read_text(encoding="utf-8"))
        report = profile_archives(manifest, args.archive_dir, access)
        args.out.parent.mkdir(parents=True, exist_ok=True)
        args.out.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
        print(json.dumps({"profiles_written": len(report["profiles"]),
                          "model_trained": False, "labels_constructed": False}))
        return 0 if all(p["key_and_join_checks_passed"] for p in report["profiles"]) else 2
    except (ValueError, TypeError, OSError, zipfile.BadZipFile) as exc:
        parser.error(str(exc))


if __name__ == "__main__":
    raise SystemExit(main())
