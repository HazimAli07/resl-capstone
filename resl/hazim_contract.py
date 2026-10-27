"""Research input and review gates. AI-assisted Hazim D2 1.1/2.1."""
from datetime import date
import hashlib
import json

from .data_checks import FEATURES
from .mannan_preprocessing import numeric_value, category_value, NUMERIC

VERSION = "hazim-input-contract-v1"
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

def check_access(record):
    required = ("source", "release", "selected_years", "terms_reference",
                "confirmed_by", "confirmed_on")
    if record.get("permitted_access_confirmed") is not True or any(not record.get(f) for f in required):
        raise ValueError("Permitted access and selected release remain unconfirmed")
    date.fromisoformat(record["confirmed_on"])
    if not isinstance(record["selected_years"], list) or not all(
            type(y) is int and 1900 <= y <= 2100 for y in record["selected_years"]):
        raise ValueError("Selected years must be a list of integer years")

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
