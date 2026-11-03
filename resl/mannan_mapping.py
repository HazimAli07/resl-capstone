"""Explicit normalized-column adapter and aggregate cohort audit (D2 1.2).

Not a Freddie Mac positional parser. Do not guess a release, date anchor or
delinquency/status conversion. Keep licensed records and row-level outputs local.
"""
from collections import Counter
from collections.abc import Mapping
from contextlib import nullcontext
from datetime import datetime
import csv
import math
from pathlib import Path
from .data_checks import FEATURES, ORIGINATION_FIELDS, check_records
from .mannan_preprocessing import NUMERIC, numeric_value, category_value

# Public documentation proposal only: not an access or selected-release approval.
FREDDIE_REFERENCE = {
    "url": "https://www.freddiemac.com/fmac-resources/research/pdf/user_guide.pdf",
    "document": "Single-Family Loan-Level Dataset General User Guide",
    "edition": "Release 48, October 2026", "checked_on": "2026-11-02",
    "pages": "4-8 (origination glossary)",
}
NORMALIZED_UNITS = dict(zip(FEATURES, (
    "score", "percent", "percent", "USD", "annual_percent", "months",
    "category", "category", "category")))
NORMALIZED_CATEGORIES = {
    "loan_purpose": {"purchase", "cash_out", "refinance"},
    "occupancy": {"primary", "investment", "second_home"},
    "property_type": {"cooperative", "condo", "pud", "single_family", "manufactured"},
}
FREDDIE_CODES = {
    # Current model contract deliberately coarsens N and R to refinance. The
    # source meanings stay explicit here; accepting that information loss for
    # the study requires review, or a coordinated richer contract in a later PR.
    "loan_purpose": {"P": "purchase", "C": "cash_out", "N": "refinance",
                     "R": "refinance"},
    "occupancy": {"P": "primary", "I": "investment", "S": "second_home"},
    "property_type": {"CP": "cooperative", "CO": "condo", "PU": "pud",
                      "SF": "single_family", "MH": "manufactured"},
}
FREDDIE_PURPOSE_MEANINGS = {"P": "purchase", "C": "cash-out refinance",
                            "N": "no-cash-out refinance", "R": "refinance not specified"}
FREDDIE_MISSING = {"credit_score": ["9999"], "dti": ["999"], "ltv": ["999"],
                   "loan_purpose": ["9"], "occupancy": ["9"], "property_type": ["99"]}


def read_header_export(source):
    """Read a named-column CSV without losing schema errors in DictReader.

    ``source`` is a local path or an open text stream. Headers must be unique,
    nonblank canonical strings. Every row must have exactly the header width;
    explicit empty cells remain empty strings. Source values never appear in
    error messages. This reads an export, not the original headerless raw files.
    Call normalize_origination next to validate the selected field mapping.
    """
    context = (nullcontext(source) if hasattr(source, "read") else
               Path(source).open(encoding="utf-8-sig", newline=""))
    with context as stream:
        reader = csv.reader(stream, strict=True)
        try:
            headers = next(reader, [])
            if (not headers or any(not h or h != h.strip() for h in headers) or
                    len(set(headers)) != len(headers)):
                raise ValueError("Export headers must be nonblank, canonical and unique")
            rows = []
            for values in reader:
                if len(values) != len(headers):
                    raise ValueError(f"Export row width differs from header at line {reader.line_num}")
                rows.append(dict(zip(headers, values)))
        except csv.Error as exc:
            raise ValueError("Malformed header-export CSV") from exc
    return rows


def freddie_origination_mapping(headers, *, ltv_regime, date_anchor):
    """Build a *proposed* glossary-based spec for explicitly supplied headers.

    ``headers`` maps each normalized field to its reviewed export header; no raw
    positions or source header spelling are inferred. ``ltv_regime`` is one of
    pre_2018q2, from_2018q2 or harp, chosen from the actual cohort provenance.
    USD balances retain the source's disclosed $1,000 rounding; ratios/rates stay
    in percent units, without dividing by 100. This helper does not authorize use.
    Purpose N and R map explicitly to the existing model's ``refinance`` category;
    their different source meanings remain in FREDDIE_PURPOSE_MEANINGS. Acceptance
    of this coarsening remains pending, rather than expanding teammates' contract.

    The guide supplies a first-payment *month*, not an exact origination date.
    An independently sourced exact date is required by the current split contract.
    A future monthly proxy requires a coordinated contract/split-policy review.
    """
    if not isinstance(headers, Mapping) or set(headers) != set(ORIGINATION_FIELDS):
        raise ValueError("Explicit headers must cover the normalized origination contract")
    if ltv_regime not in {"pre_2018q2", "from_2018q2", "harp"}:
        raise ValueError("A documented LTV vintage/program regime is required")
    if date_anchor != "exact_origination_date":
        raise ValueError("First payment month cannot supply an exact origination date")
    specs = {field: {"source": header} for field, header in headers.items()}
    for field in FEATURES:
        specs[field]["unit"] = NORMALIZED_UNITS[field]
        specs[field]["missing"] = list(FREDDIE_MISSING.get(field, []))
    for field, codes in FREDDIE_CODES.items():
        specs[field]["codes"] = dict(codes)
    specs["credit_score"]["bounds"] = (300, 850)
    specs["dti"]["bounds"] = (0, 65)
    if ltv_regime == "harp":
        # The public glossary discloses DTI as unavailable for all HARP loans.
        specs["dti"]["must_be_missing"] = True
    specs["ltv"]["bounds"] = ((6, 105) if ltv_regime == "pre_2018q2" else (1, 998))
    specs["origination_date"]["date_anchor"] = date_anchor
    _validate_mapping(specs, synthetic=False)
    return specs


def _validate_mapping(mapping, *, synthetic):
    if not isinstance(mapping, Mapping) or set(mapping) != set(ORIGINATION_FIELDS):
        raise ValueError("Mapping must cover exactly the normalized origination contract")
    allowed = {"source", "missing", "codes", "unit", "bounds", "date_format", "date_anchor",
               "must_be_missing"}
    for field, spec in mapping.items():
        if not isinstance(spec, Mapping) or set(spec) - allowed:
            raise ValueError(f"Invalid mapping specification for {field}")
        source = spec.get("source")
        if not isinstance(source, str) or not source.strip() or source != source.strip():
            raise ValueError(f"A nonblank explicit source header is required for {field}")
        missing = spec.get("missing", [])
        if not isinstance(missing, (list, tuple, set)) or any(
                not isinstance(v, str) or v != v.strip() for v in missing):
            raise ValueError(f"Missing codes must be explicit canonical strings for {field}")
        if "unit" in spec and spec["unit"] != NORMALIZED_UNITS.get(field):
            raise ValueError(f"Unsupported unit for {field}; no implicit unit conversion")
        if "codes" in spec:
            codes = spec["codes"]
            if field not in NORMALIZED_CATEGORIES or not isinstance(codes, Mapping) or not codes:
                raise ValueError(f"Invalid categorical dictionary for {field}")
            if any(not isinstance(k, str) or not k or k != k.strip() or
                   not isinstance(v, str) or v not in NORMALIZED_CATEGORIES[field]
                   for k, v in codes.items()):
                raise ValueError(f"Invalid categorical dictionary for {field}")
            if set(codes) & set(missing):
                raise ValueError(f"Category and missing codes overlap for {field}")
        if "bounds" in spec:
            bounds = spec["bounds"]
            if field not in NUMERIC or not isinstance(bounds, (list, tuple)) or len(bounds) != 2:
                raise ValueError(f"Invalid source bounds for {field}")
            if any(isinstance(v, bool) or not isinstance(v, (int, float)) or
                   not math.isfinite(v) for v in bounds) or bounds[0] > bounds[1]:
                raise ValueError(f"Invalid source bounds for {field}")
        if "must_be_missing" in spec and (field not in NUMERIC or
                                          type(spec["must_be_missing"]) is not bool):
            raise ValueError(f"Invalid source missingness rule for {field}")
        if field != "origination_date" and ({"date_format", "date_anchor"} & set(spec)):
            raise ValueError("Date settings belong only to origination_date")
    sources = [spec["source"] for spec in mapping.values()]
    if len(set(sources)) != len(sources):
        raise ValueError("Source fields must not be reused")
    date_spec = mapping["origination_date"]
    if not isinstance(date_spec.get("date_format", "%Y-%m-%d"), str):
        raise ValueError("Date format must be explicit text")
    if "date_anchor" in date_spec and date_spec["date_anchor"] not in {
            "exact_origination_date", "synthetic_month_proxy"}:
        raise ValueError("Unsupported date anchor; source/date review remains required")
    source_concept = "".join(c for c in date_spec["source"].lower() if c.isalpha())
    if "firstpayment" in source_concept:
        raise ValueError("First payment month cannot supply an exact origination date")
    if not synthetic and (date_spec.get("date_anchor") != "exact_origination_date" or
                          date_spec.get("date_format", "%Y-%m-%d") != "%Y-%m-%d"):
        raise ValueError("Actual mapping requires an independently reviewed exact date anchor")
    return set(sources)


def normalize_origination(rows, mapping, *, release, reviewed=False, synthetic=False,
                          ignored_headers=None):
    """Map an explicitly reviewed header export to the candidate interface.

    Specs accept explicit ``codes``, ``unit`` and selected-source ``bounds``.
    Unknown categorical codes, unknown spec keys and unexpected headers fail.
    The legacy normalized synthetic adapter may ignore ``split``; every other
    unused export column must be explicitly listed in ``ignored_headers``.
    YYYYMM/day-1 formatting is retained only for legacy invented fixtures. It
    cannot establish an actual origination date or an accepted split proxy.
    Performance conversion deliberately remains a separate reviewed dependency.
    """
    if not isinstance(synthetic, bool) or not isinstance(reviewed, bool):
        raise ValueError("synthetic and reviewed must be booleans")
    if not isinstance(release, str) or not release.strip() or (not synthetic and reviewed is not True):
        raise ValueError("A named release and independently reviewed mapping are required")
    sources = _validate_mapping(mapping, synthetic=synthetic)
    if ignored_headers is None:
        ignored_headers = ("split",) if synthetic else ()
    if not isinstance(ignored_headers, (list, tuple, set)) or any(
            not isinstance(h, str) or not h.strip() for h in ignored_headers):
        raise ValueError("Ignored headers must be explicitly named")
    ignored = set(ignored_headers)
    if sources & ignored:
        raise ValueError("Mapped source headers must not be ignored")
    output, ids = [], set()
    observed_headers = None
    for row in rows:
        if not isinstance(row, Mapping):
            raise ValueError("Source rows must be header mappings")
        headers = set(row)
        if not sources.issubset(headers):
            raise ValueError("Missing required source headers")
        if headers - sources - ignored:
            raise ValueError("Unexpected source headers; explicitly review schema changes")
        if observed_headers is not None and headers != observed_headers:
            raise ValueError("Source schema drift between rows")
        observed_headers = headers
        record = {}
        for field, spec in mapping.items():
            if spec["source"] not in row:
                raise ValueError(f"Missing source header for {field}")
            raw = row[spec["source"]]
            value = "" if raw is None else str(raw).strip()
            if value in set(spec.get("missing", [])):
                value = ""
            if field in NUMERIC:
                # Keep booleans distinguishable from the string "True".
                result = numeric_value(field, raw if isinstance(raw, bool) else value)
                if result is not None and spec.get("must_be_missing"):
                    raise ValueError(f"{field}: documented source regime requires missing values")
                if result is not None and "bounds" in spec:
                    low, high = spec["bounds"]
                    if not low <= result <= high:
                        raise ValueError(f"{field}: outside documented source bounds")
                record[field] = result
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
                if value and "codes" in spec:
                    if value not in spec["codes"]:
                        raise ValueError(f"Unknown source category code for {field}")
                    value = spec["codes"][value]
                result = category_value(value)
                if result is not None and result not in NORMALIZED_CATEGORIES[field]:
                    raise ValueError(f"Unknown normalized category for {field}")
                record[field] = result
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
        "missing_inputs": {}, "invalid_numeric_values": {}, "invalid_categories": {},
    }
    for field in FEATURES:
        missing, invalid = 0, 0
        for row in origination:
            try:
                value = (numeric_value(field, row.get(field)) if field in NUMERIC
                         else category_value(row.get(field)))
                if (field in NORMALIZED_CATEGORIES and value is not None and
                        value not in NORMALIZED_CATEGORIES[field]):
                    raise ValueError("Unknown normalized category")
                missing += value is None
            except ValueError:
                invalid += 1
        report["missing_inputs"][field] = {
            "count": missing, "rate": missing / len(origination) if origination else None}
        if invalid:
            report["invalid_numeric_values" if field in NUMERIC else "invalid_categories"][field] = invalid
    try:
        check_records(origination, performance)
        report["normalized_checks_passed"] = not bool(
            report["invalid_numeric_values"] or report["invalid_categories"] or
            report["blank_origination_ids"])
    except (ValueError, TypeError, KeyError):
        report["normalized_checks_passed"] = False
    report["limitation"] = "Aggregate software audit; not selected-release acceptance."
    return report
