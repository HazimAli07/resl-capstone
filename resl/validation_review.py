"""D2 3.3: diagnostics and proposed cutoffs for validation predictions only."""

import math

from .rule_score import number


def _divide(a, b):
    return a / b if b else None


def wilson_interval(events, count):
    """Descriptive 95% binomial interval; not a time-series uncertainty model."""
    if not count:
        return None
    z = 1.959963984540054
    rate = events / count
    denominator = 1 + z * z / count
    centre = (rate + z * z / (2 * count)) / denominator
    width = z * math.sqrt(rate * (1 - rate) / count + z * z / (4 * count * count)) / denominator
    return [max(0.0, centre - width), min(1.0, centre + width)]


def _prepare(rows):
    seen, usable, excluded = set(), [], 0
    for row in rows:
        if not {"loan_id", "split", "target", "probability"}.issubset(row):
            raise ValueError("Prediction schema requires loan_id, split, target, probability")
        if row.get("split") != "validation":
            raise ValueError("Only validation rows are accepted; no training/test cutoff tuning")
        identity = row.get("loan_id")
        if not isinstance(identity, str) or not identity.strip() or identity != identity.strip():
            raise ValueError("loan_id must be a nonblank canonical string")
        if identity in seen:
            raise ValueError("Duplicate loan_id: evaluate each loan once per model")
        seen.add(identity)
        target = row.get("target")
        probability = number(row.get("probability"), "probability")
        if not 0 <= probability <= 1:
            raise ValueError("probability must lie in [0,1]; rule points are not probabilities")
        if target is None or target == "":
            excluded += 1
            continue
        if isinstance(target, bool) or str(target) not in {"0", "1"}:
            raise ValueError("target must be 0, 1, or null for censored loans")
        usable.append((probability, int(target)))
    if not usable:
        raise ValueError("No eligible labelled validation predictions")
    return usable, excluded, len(seen)


def _metrics(positives, negatives, tp, fp, threshold):
    reviewed = tp + fp
    return {"threshold": threshold, "review_none": threshold is None,
            "reviewed": reviewed, "tp": tp, "fp": fp,
            "fn": positives - tp, "tn": negatives - fp,
            "review_fraction": reviewed / (positives + negatives),
            "precision": _divide(tp, reviewed), "recall": _divide(tp, positives),
            "false_positive_rate": _divide(fp, negatives),
            "false_alert_share": _divide(fp, reviewed)}


def review_validation(rows, *, max_reviews, bins=5):
    """Evaluate ONE model's untouched validation predictions.

    max_reviews is an explicit integer capacity, not inferred from outcomes.
    A proposal maximizes captured positives within that budget, then minimizes
    false alerts/review volume. Equal probabilities stay together; this may
    leave capacity unused. No fitted calibration or final model is returned.
    Split names are checked, but provenance/disjointness still need team audit.
    """
    if type(max_reviews) is not int or max_reviews < 0:
        raise ValueError("max_reviews must be a nonnegative integer")
    if type(bins) is not int or not 1 <= bins <= 50:
        raise ValueError("bins must be an integer between 1 and 50")
    data, excluded, total = _prepare(rows)
    n = len(data)
    positives = sum(y for _, y in data)
    negatives = n - positives
    bucket_values = [[] for _ in range(bins)]
    for probability, target in data:
        bucket_values[min(int(probability * bins), bins - 1)].append((probability, target))
    reliability = []
    for i, values in enumerate(bucket_values):
        count = len(values)
        events = sum(y for _, y in values)
        reliability.append({"lower": i / bins, "upper": (i + 1) / bins,
                            "upper_inclusive": i == bins - 1, "count": count,
                            "events": events,
                            "mean_probability": _divide(sum(p for p, _ in values), count),
                            "observed_rate": _divide(events, count),
                            "observed_rate_wilson95": wilson_interval(events, count)})
    candidates = [_metrics(positives, negatives, 0, 0, None)]
    groups = {}
    for probability, target in data:
        group = groups.setdefault(probability, [0, 0])
        group[0] += target
        group[1] += 1 - target
    tp = fp = 0
    for probability in sorted(groups, reverse=True):
        events, nonevents = groups[probability]
        tp += events
        fp += nonevents
        candidates.append(_metrics(positives, negatives, tp, fp, probability))
    feasible = [c for c in candidates if c["reviewed"] <= max_reviews]
    proposal = (max(feasible, key=lambda c: (c["tp"], -c["fp"], -c["reviewed"]))
                if positives and negatives else None)
    return {"input_count": total, "labelled_count": n, "excluded_censored_count": excluded,
            "events": positives, "event_rate": positives / n,
            "event_rate_wilson95": wilson_interval(positives, n),
            "brier_score": sum((p - y) ** 2 for p, y in data) / n,
            "reliability_bins": reliability, "threshold_candidates": candidates,
            "max_reviews": max_reviews, "proposed_cutoff": proposal,
            "proposal_status": ("requires_team_review" if proposal else "insufficient_class_support"),
            "selection_rule": "Maximize validation TP within capacity, then minimize false alerts and volume; keep ties together.",
            "limitations": ["No model or calibration transform was fitted.",
                            "Brier score combines calibration and discrimination; inspect bins too.",
                            "Wilson intervals assume independent Bernoulli outcomes; temporal dependence is not modelled.",
                            "Selection metrics are optimistic; freeze choices before separate test evaluation.",
                            "Caller must audit split provenance, censoring and natural event prevalence."]}
