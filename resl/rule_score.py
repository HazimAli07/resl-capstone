"""D2 2.3: proposed research ranking; points are never probabilities."""

import hashlib
import json
import math


# Illustrative hypotheses for team review, not Freddie Mac underwriting rules.
# Ratios are percentages (40 means 40%, not 0.40). Boundaries are inclusive.
PROPOSED_SETTINGS = {
    "version": "sweta-rule-v0.1",
    "status": "proposed_synthetic_only",
    "rules": {
        "credit_score": {"direction": "below", "thresholds": [620, 680],
                         "minimum": 300, "maximum": 850, "sentinels": [9999]},
        "dti": {"direction": "above", "thresholds": [36, 43],
                "minimum": 0, "maximum": 65, "sentinels": [999]},
        "ltv": {"direction": "above", "thresholds": [80, 90],
                "minimum": 1, "maximum": 998, "sentinels": [999]},
    },
}
ALLOWED_FIELDS = {"credit_score", "dti", "ltv"}


def number(value, name):
    if isinstance(value, bool):
        raise ValueError(f"{name} must be a finite number")
    try:
        result = float(value)
    except (TypeError, ValueError) as exc:
        raise ValueError(f"{name} must be a finite number") from exc
    if not math.isfinite(result):
        raise ValueError(f"{name} must be a finite number")
    return result


def validate_settings(settings):
    if not settings.get("version") or settings.get("status") != "proposed_synthetic_only":
        raise ValueError("This implementation supports proposed synthetic-only settings")
    rules = settings.get("rules", {})
    if not rules or set(rules) - ALLOWED_FIELDS:
        raise ValueError("Rules must use only the explicit origination-input allowlist")
    for field, rule in rules.items():
        if (not isinstance(rule, dict)
                or not {"minimum", "maximum", "thresholds", "direction"}.issubset(rule)
                or not isinstance(rule["thresholds"], list)
                or any(type(v) not in (int, float) for v in
                       [rule["minimum"], rule["maximum"], *rule["thresholds"]])):
            raise ValueError(f"Rule settings for {field} require numeric bounds/thresholds")
        low = number(rule["minimum"], field)
        high = number(rule["maximum"], field)
        cuts = [number(v, field) for v in rule["thresholds"]]
        if (low >= high or not cuts or cuts != sorted(set(cuts))
                or any(not low <= v <= high for v in cuts)
                or rule["direction"] not in {"below", "above"}):
            raise ValueError(f"Invalid rule settings for {field}")
        for value in rule.get("sentinels", []):
            number(value, field)
    return hashlib.sha256(json.dumps(settings, sort_keys=True, allow_nan=False).encode()).hexdigest()


def score_application(row, settings=PROPOSED_SETTINGS):
    """Return an auditable point sum; abstain on missing/sentinel/out-of-range input.

    Only the configured allowlisted inputs are read. IDs, dates, targets and
    repayment fields have no effect. One point per crossed threshold, equal
    weights; ties share a rank. No imputation or fitting is performed.
    """
    fingerprint = validate_settings(settings)
    components, invalid = {}, {}
    for field, rule in settings["rules"].items():
        raw = row.get(field)
        if raw is None or (isinstance(raw, str) and not raw.strip()):
            invalid[field] = "missing"
            continue
        try:
            value = number(raw, field)
        except ValueError:
            invalid[field] = "not_finite_numeric"
            continue
        if value in rule.get("sentinels", []):
            invalid[field] = "unavailable_sentinel"
        elif not rule["minimum"] <= value <= rule["maximum"]:
            invalid[field] = "outside_proposed_input_range"
        else:
            points = sum(value <= cut if rule["direction"] == "below" else value >= cut
                         for cut in rule["thresholds"])
            components[field] = {"value": value, "points": points}
    return {"score": None if invalid else sum(c["points"] for c in components.values()),
            "maximum_score": sum(len(r["thresholds"]) for r in settings["rules"].values()),
            "components": components, "invalid_inputs": invalid,
            "status": "abstain_invalid_input" if invalid else "proposed_research_ranking",
            "settings_version": settings["version"], "settings_sha256": fingerprint,
            "limitation": "Synthetic development only; not a probability or approval policy."}
