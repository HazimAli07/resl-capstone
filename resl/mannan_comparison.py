"""Validation-only candidate comparison with a frozen one-model test audit.

AI-assisted D2 3.2. No training, tuning or release/provenance claims.
"""
from collections import defaultdict
import math

def _number(value):
    if isinstance(value, bool):
        raise ValueError("Boolean probability")
    try:
        result = float(value)
    except (TypeError, ValueError) as exc:
        raise ValueError("Invalid probability") from exc
    if not math.isfinite(result) or not 0 <= result <= 1:
        raise ValueError("Probability must be finite and between zero and one")
    return result

def _metrics(rows, threshold, capacity):
    observed = [r for r in rows if r["target"] is not None]
    n = len(observed)
    if not n:
        raise ValueError("No observed labels")
    positives = sum(r["target"] for r in observed)
    flagged = [r for r in observed if r["probability"] >= threshold]
    tp = sum(r["target"] for r in flagged)
    ranked = sorted(observed, key=lambda r: -r["probability"])
    # Include whole tied groups only; never choose within a tie using ID/outcome.
    selected, start = [], 0
    while start < n:
        stop = start + 1
        while stop < n and ranked[stop]["probability"] == ranked[start]["probability"]:
            stop += 1
        if len(selected) + stop - start > capacity:
            break
        selected.extend(ranked[start:stop])
        start = stop
    found = sum(r["target"] for r in selected)
    return {"cohort_size": len(rows), "observed_labels": n,
            "censored": len(rows) - n, "events": positives,
            "event_rate": positives / n, "threshold": threshold,
            "precision": tp / len(flagged) if flagged else None,
            "recall": tp / positives if positives else None,
            "false_alerts": len(flagged) - tp, "flagged": len(flagged),
            "review_capacity": capacity, "reviewed_within_capacity": len(selected),
            "cases_found_within_capacity": found,
            "recall_within_capacity": found / positives if positives else None,
            "brier": sum((r["probability"] - r["target"]) ** 2 for r in observed) / n,
            "capacity_scope": "Observed-label cohort only; censored workload is excluded."}

def compare_candidates(rows, *, capacity, threshold=0.5, split="validation",
                       frozen_model=None):
    """Require identical IDs/labels for each validation candidate.

    Test audits accept exactly the preselected frozen model, preventing this
    interface from selecting/tuning candidates on final-test results.
    """
    if isinstance(capacity, bool) or not isinstance(capacity, int) or capacity < 0:
        raise ValueError("Capacity must be a nonnegative integer")
    threshold = _number(threshold)
    if split not in {"validation", "test"}:
        raise ValueError("Training predictions cannot be evaluated here")
    if split == "test" and not frozen_model:
        raise ValueError("Final-test audit requires a validation-frozen model name")
    groups, seen = defaultdict(list), set()
    labels = {}
    for row in rows:
        if row.get("split") != split:
            raise ValueError("Mixed or incorrect prediction split")
        model = "" if row.get("model") is None else str(row["model"]).strip()
        loan = "" if row.get("loan_id") is None else str(row["loan_id"]).strip()
        target = row.get("target")
        if not model or not loan or (model, loan) in seen:
            raise ValueError("Blank or duplicate model/loan ID")
        if isinstance(target, bool) or (target is not None and
                (not isinstance(target, int) or target not in (0, 1))):
            raise ValueError("Target must be integer zero/one or None")
        seen.add((model, loan))
        if loan in labels and labels[loan] != target:
            raise ValueError("Models disagree on labels")
        labels[loan] = target
        groups[model].append({"loan_id": loan, "target": target,
                              "probability": _number(row.get("probability"))})
    if not groups:
        raise ValueError("No predictions")
    if split == "test" and set(groups) != {frozen_model}:
        raise ValueError("Test audit accepts only the frozen candidate")
    cohorts = [{r["loan_id"] for r in values} for values in groups.values()]
    if any(cohort != cohorts[0] for cohort in cohorts):
        raise ValueError("Candidates must use identical evaluation cohorts")
    return {"split": split, "models": {
        model: _metrics(groups[model], threshold, capacity) for model in sorted(groups)},
        "selection": "Human selects using validation evidence before final-test audit.",
        "provenance": "Caller must verify split dates, hashes and fitted-model provenance."}
