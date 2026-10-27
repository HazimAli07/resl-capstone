"""Explicit normalized-column adapter and aggregate cohort audit (D2 1.2).

Not a Freddie Mac positional parser. Do not guess a release, date anchor or
delinquency/status conversion. Keep licensed records and row-level outputs local.
"""
from collections import Counter
from datetime import date, datetime
from .data_checks import FEATURES, ORIGINATION_FIELDS, check_records
from .mannan_preprocessing import NUMERIC, numeric_value, category_value

def normalize_origination(rows, mapping, *, release, reviewed=False, synthetic=False):
    """Map an explicitly reviewed header export to the candidate interface.

    mapping: {normalized: {"source": header, "missing": [...],
                          "date_format": "%Y-%m-%d"}}
    YYYYMM conversion uses day 1 and must be approved as a monthly proxy.
    Performance conversion deliberately remains a separate reviewed dependency.
    """
    if not release or (not synthetic and reviewed is not True):
        raise ValueError("A named release and independently reviewed mapping are required")
    if set(mapping) != set(ORIGINATION_FIELDS):
        raise ValueError("Mapping must cover exactly the normalized origination contract")
    sources = [spec["source"] for spec in mapping.values()]
    if len(set(sources)) != len(sources):
        raise ValueError("Source fields must not be reused")
    output, ids = [], set()
    for row in rows:
        record = {}
        for field, spec in mapping.items():
            if spec["source"] not in row:
                raise ValueError(f"Missing source header for {field}")
            raw = row[spec["source"]]
            value = "" if raw is None else str(raw).strip()
            if value in {str(v) for v in spec.get("missing", [])}:
                value = ""
            if field in NUMERIC:
                record[field] = numeric_value(field, value)
            elif field == "origination_date":
                if not value:
                    raise ValueError("Missing split date")
                fmt = spec.get("date_format", "%Y-%m-%d")
                parsed = datetime.strptime(value, fmt).date()
                if parsed.strftime(fmt) != value:
                    raise ValueError("Noncanonical source date")
                record[field] = parsed.isoformat()
            elif field == "loan_id":
                if not value or value in ids:
                    raise ValueError("Blank or duplicate mapped loan ID")
                ids.add(value)
                record[field] = value
            else:
                record[field] = category_value(value)
        output.append(record)
    if not output:
        raise ValueError("No origination rows")
    return output

def audit_cohort(origination, performance):
    """Aggregate-only audit, including failures; never emits IDs or raw rows."""
    origination, performance = list(origination), list(performance)
    ids = ["" if r.get("loan_id") is None else str(r["loan_id"]).strip() for r in origination]
    known = {v for v in ids if v}
    perf_ids = ["" if r.get("loan_id") is None else str(r["loan_id"]).strip() for r in performance]
    months = [(str(r.get("loan_id", "")).strip(),
               str(r.get("month_on_book", "")).strip()) for r in performance]
    duplicate_months = sum(n - 1 for n in Counter(months).values() if n > 1)
    report = {
        "origination_rows": len(origination), "performance_rows": len(performance),
        "unique_origination_ids": len(known),
        "blank_origination_ids": sum(not v for v in ids),
        "duplicate_origination_rows": sum(n - 1 for v, n in Counter(ids).items() if v and n > 1),
        "duplicate_performance_rows": duplicate_months,
        "unmatched_performance_rows": sum(v not in known for v in perf_ids),
        "loans_without_performance": len(known - set(perf_ids)),
        "missing_inputs": {}, "invalid_numeric_values": {},
    }
    for field in FEATURES:
        missing, invalid = 0, 0
        for row in origination:
            try:
                value = (numeric_value(field, row.get(field)) if field in NUMERIC
                         else category_value(row.get(field)))
                missing += value is None
            except ValueError:
                invalid += 1
        report["missing_inputs"][field] = {
            "count": missing, "rate": missing / len(origination) if origination else None}
        if invalid:
            report["invalid_numeric_values"][field] = invalid
    try:
        check_records(origination, performance)
        report["normalized_checks_passed"] = not bool(report["invalid_numeric_values"] or report["blank_origination_ids"])
    except (ValueError, TypeError, KeyError):
        report["normalized_checks_passed"] = False
    report["limitation"] = "Aggregate software audit; not selected-release acceptance."
    return report
