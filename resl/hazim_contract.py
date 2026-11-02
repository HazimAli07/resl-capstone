"""Research input and review gates. AI-assisted Hazim D2 1.1/2.1."""
from datetime import date
import hashlib
import json

from .data_checks import FEATURES
from .mannan_preprocessing import numeric_value, category_value, NUMERIC

VERSION = "hazim-input-contract-v1"
REVIEW_VERSION = "hazim-source-review-v2"
NORMALIZED_UNITS = dict(zip(FEATURES, (
    "score", "percent", "percent", "USD", "annual_percent", "months",
    "category", "category", "category")))
CATEGORIES = {
    "loan_purpose": ("purchase", "cash_out", "refinance"),
    "occupancy": ("primary", "second_home", "investment"),
    "property_type": ("single_family", "condo", "cooperative", "manufactured", "pud"),
}
REVIEW_FIELDS = ("release", "date_anchor", "label_policy", "split_rationale",
                 "source_dictionary", "reviewed_by", "reviewed_on")

def canonical_hash(value):
    return hashlib.sha256(json.dumps(value, sort_keys=True, separators=(",", ":"),
                                    allow_nan=False).encode()).hexdigest()

def validate_application(row):
    """Strict inference boundary: exact eligible fields; normalized units."""
    if set(row) != set(FEATURES):
        raise ValueError("Application must contain exactly the nine eligible inputs")
    clean = {}
    for field in FEATURES:
        value = numeric_value(field, row[field]) if field in NUMERIC else category_value(row[field])
        if field in CATEGORIES and value is not None and value not in CATEGORIES[field]:
            raise ValueError(f"{field}: unreviewed category code")
        clean[field] = value
    return clean

def check_access(record, *, as_of=None):
    required = ("source", "release", "terms_reference", "confirmed_by", "confirmed_on")
    if record.get("permitted_access_confirmed") is not True or any(
            not isinstance(record.get(f), str) or not record[f].strip() for f in required):
        raise ValueError("Permitted access and selected release remain unconfirmed")
    today = as_of or date.today()
    if date.fromisoformat(record["confirmed_on"]) > today:
        raise ValueError("Access confirmation cannot be future dated")
    years = record.get("selected_years")
    if (not isinstance(years, list) or not years or not all(
            type(y) is int and 1900 <= y <= today.year for y in years)
            or len(set(years)) != len(years)):
        raise ValueError("Selected years must be unique, non-future integer years")

def check_timing_review(review):
    """Require explicit source evidence for every proposed origination input.

    This validates the review record, not the truth of a human attestation.
    Earlier application decisions need a separately reviewed feature contract.
    """
    if review.get("review_version") != REVIEW_VERSION:
        raise ValueError("A versioned source/timing review is required")
    if review.get("prediction_stage") != "origination":
        raise ValueError("The current nine-input contract requires an origination-stage review")
    rows = review.get("feature_timing_review")
    if not isinstance(rows, list) or len(rows) != len(FEATURES):
        raise ValueError("Timing review must cover every eligible input exactly once")
    seen = set()
    for row in rows:
        if not isinstance(row, dict):
            raise ValueError("Each timing review entry must be an object")
        feature = row.get("feature")
        if not isinstance(feature, str) or feature not in FEATURES or feature in seen:
            raise ValueError("Duplicate, excluded or unknown field in timing review")
        seen.add(feature)
        for key in ("source_field", "dictionary_reference", "conversion"):
            if not isinstance(row.get(key), str) or not row[key].strip():
                raise ValueError(f"{feature}: source field, dictionary reference and conversion required")
        if row.get("normalized_unit") != NORMALIZED_UNITS[feature]:
            raise ValueError(f"{feature}: normalized unit differs from the input contract")
        codes = row.get("missing_codes")
        if not isinstance(codes, list) or not all(isinstance(c, str) for c in codes):
            raise ValueError(f"{feature}: explicit string-list missing codes required")
        if row.get("available_by") != "origination" or row.get("accepted") is not True:
            raise ValueError(f"{feature}: origination availability has not been accepted")
    return tuple(sorted(seen))

def check_review(review, access=None, *, synthetic=False):
    """Attestation gate, not a substitute for source/teammate review."""
    if review.get("synthetic") is not synthetic:
        raise ValueError("Review provenance does not match synthetic/actual mode")
    if not synthetic:
        check_access(access or {})
        if review.get("accepted") is not True or any(not review.get(f) for f in REVIEW_FIELDS):
            raise ValueError("Actual-data mapping, labels, timing and split review are required")
        if review["release"] != access["release"]:
            raise ValueError("Access/review release mismatch")
        if review.get("eligible_features") != list(FEATURES):
            raise ValueError("Reviewed allowlist differs from implemented inputs")
        date.fromisoformat(review["reviewed_on"])
        check_timing_review(review)
    train_end = date.fromisoformat(review["train_before"])
    test_start = date.fromisoformat(review["test_from"])
    if train_end >= test_start:
        raise ValueError("Empty validation time interval")
    fit_as_of = date.fromisoformat(review["training_as_of"])
    selection_as_of = date.fromisoformat(review["validation_as_of"])
    if not fit_as_of < train_end or not train_end <= selection_as_of < test_start:
        raise ValueError("Label cutoffs must precede evaluation/test periods")
    return train_end, test_start

def validate_partition(rows, expected, review):
    """Verify actual dates as well as tags; never accept final-test training rows."""
    if expected not in {"train", "validation"}:
        raise ValueError("Training runner has no test-set interface")
    low, high = date.fromisoformat(review["train_before"]), date.fromisoformat(review["test_from"])
    ids = set()
    for row in rows:
        loan = row.get("loan_id")
        if not isinstance(loan, str) or not loan.strip() or loan != loan.strip() or loan in ids:
            raise ValueError("IDs must be unique, nonblank canonical strings")
        ids.add(loan)
        started = date.fromisoformat(row["origination_date"])
        group = "train" if started < low else "validation" if started < high else "test"
        if row.get("split") != expected or group != expected:
            raise ValueError("Split tag/date mismatch or final-test row")
        target = row.get("target")
        if target is not None and (type(target) is not int or target not in (0, 1)):
            raise ValueError("Target must be integer zero/one or None")
        if target is not None:
            available = date.fromisoformat(row["label_available_on"])
            cutoff = date.fromisoformat(review["training_as_of" if expected == "train" else "validation_as_of"])
            if available < started or available > cutoff:
                raise ValueError("Observed label was unavailable at the declared cutoff")
        validate_application({f: row[f] for f in FEATURES})
    return ids
