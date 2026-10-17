"""Checks for the proposed normalized schema, not a Freddie Mac raw-file parser."""

from collections import Counter, defaultdict
from datetime import date


FEATURES = ("credit_score", "dti", "ltv", "original_balance", "original_rate",
            "original_term", "loan_purpose", "occupancy", "property_type")
ORIGINATION_FIELDS = ("loan_id", "origination_date", *FEATURES)
PERFORMANCE_FIELDS = ("loan_id", "month_on_book", "delinquency_days", "status")
STATUSES = {"active", "paid_off", "foreclosure", "reo"}


def _integer(value, field, minimum=0):
    try:
        result = int(value)
    except (TypeError, ValueError) as exc:
        raise ValueError(f"{field} must be an integer") from exc
    if str(result) != str(value).strip() or result < minimum:
        raise ValueError(f"Invalid {field}: {value!r}")
    return result


def check_records(origination, performance):
    """Reject ambiguous joins/fields; report missing candidate input values."""
    if not origination:
        raise ValueError("No origination records")
    ids = set()
    missing = Counter()
    for row in origination:
        if not set(ORIGINATION_FIELDS).issubset(row):
            raise ValueError("Origination schema is missing required columns")
        loan_id = str(row["loan_id"]).strip()
        if not loan_id or loan_id in ids:
            raise ValueError("Blank or duplicate origination loan_id")
        ids.add(loan_id)
        date.fromisoformat(row["origination_date"])
        for field in FEATURES:
            if row[field] is None or not str(row[field]).strip():
                missing[field] += 1
    seen = set()
    for row in performance:
        if not set(PERFORMANCE_FIELDS).issubset(row):
            raise ValueError("Performance schema is missing required columns")
        if row["loan_id"] not in ids:
            raise ValueError("Performance record has no matching origination loan")
        month = _integer(row["month_on_book"], "month_on_book", minimum=1)
        key = (row["loan_id"], month)
        if key in seen:
            raise ValueError("Duplicate loan/month performance record")
        seen.add(key)
        _integer(row["delinquency_days"], "delinquency_days")
        if row["status"] not in STATUSES:
            raise ValueError("Unknown normalized performance status")
    return {"loan_count": len(ids), "performance_rows": len(performance),
            "missing_candidate_inputs": dict(sorted(missing.items()))}


def outcome(rows, horizon=24):
    """Proposed horizon/censoring policy; requires team review on real data."""
    if horizon < 1:
        raise ValueError("Horizon must be positive")
    records = []
    seen = set()
    for row in rows:
        month = _integer(row["month_on_book"], "month_on_book", minimum=1)
        days = _integer(row["delinquency_days"], "delinquency_days")
        status = row["status"]
        if status not in STATUSES or month in seen:
            raise ValueError("Unknown status or duplicate performance month")
        seen.add(month)
        records.append((month, days, status))
    records.sort()
    paid_months = [m for m, _, s in records if s == "paid_off"]
    if paid_months and any(m > min(paid_months) for m, _, _ in records):
        raise ValueError("Records after terminal payoff require review")
    window = [(m, d, s) for m, d, s in records if m <= horizon]
    if any(d >= 90 or s in {"foreclosure", "reo"} for _, d, s in window):
        return {"target": 1, "reason": "observed_adverse_outcome"}
    if any(s == "paid_off" and m < horizon for m, _, s in window):
        return {"target": None, "reason": "censored_early_payoff"}
    months = {m for m, _, _ in window}
    if months == set(range(1, horizon + 1)):
        return {"target": 0, "reason": "complete_followup_no_event"}
    if months and months != set(range(1, max(months) + 1)):
        return {"target": None, "reason": "censored_followup_gap"}
    return {"target": None, "reason": "censored_incomplete_followup"}


def feature_record(origination_row):
    """Explicit allowlist prevents IDs, dates and repayment fields entering X."""
    missing = set(FEATURES) - set(origination_row)
    if missing:
        raise ValueError(f"Missing candidate input fields: {sorted(missing)}")
    return {field: origination_row[field] for field in FEATURES}


def chronological_split(origination, train_before, test_from):
    """Assign a loan once by origination date, using [start,end) boundaries."""
    train_end = date.fromisoformat(train_before)
    test_start = date.fromisoformat(test_from)
    if train_end >= test_start:
        raise ValueError("Validation period must lie between training and test")
    split = {"train": [], "validation": [], "test": []}
    seen = set()
    for row in origination:
        if row["loan_id"] in seen:
            raise ValueError("Loan appears more than once")
        seen.add(row["loan_id"])
        started = date.fromisoformat(row["origination_date"])
        group = "train" if started < train_end else "validation" if started < test_start else "test"
        split[group].append(row["loan_id"])
    return split


def summarize(origination, performance, train_before, test_from):
    checks = check_records(origination, performance)
    by_loan = defaultdict(list)
    for row in performance:
        by_loan[row["loan_id"]].append(row)
    outcomes = {row["loan_id"]: outcome(by_loan[row["loan_id"]]) for row in origination}
    splits = chronological_split(origination, train_before, test_from)
    return {"quality": checks, "outcomes": outcomes,
            "outcome_counts": dict(Counter(x["reason"] for x in outcomes.values())),
            "split_counts": {key: len(value) for key, value in splits.items()},
            "split_boundaries": {"train_before": train_before, "test_from": test_from},
            "eligible_features": list(FEATURES),
            "limitation": "Software checks only; no fitted model or performance estimate."}
