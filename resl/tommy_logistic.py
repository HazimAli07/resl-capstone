"""Bounded logistic-regression candidate on synthetic or reviewed cohorts.

AI-assisted implementation for Tommy's D2 #4/#8 work. Actual-data execution
remains gated on permitted access and Hazim's versioned source/timing review.
"""
import argparse
import csv
import hashlib
import importlib.metadata
import json
import platform
from datetime import date
from pathlib import Path

from .data_checks import FEATURES
from .hazim_contract import canonical_hash, check_review, validate_partition
from .mannan_comparison import compare_candidates
from .mannan_preprocessing import TrainPreprocessor

SEED = 42
REGULARIZATION_GRID = (0.1, 1.0, 10.0)  # inverse L2 strength, frozen before validation
MAX_ROWS_PER_PARTITION = 100_000
MAX_ITERATIONS = 1_000
CPU_WORKERS = 1
PREDICTION_COLUMNS = ("loan_id", "split", "target", "probability", "model")


def synthetic_cohort():
    """Return deterministic invented records; dates are software fixtures only."""
    import random

    rng = random.Random(SEED)
    groups = []
    for split, year, size in (("train", 2014, 120), ("validation", 2018, 40)):
        rows = []
        for index in range(size):
            score = rng.randint(560, 820)
            dti = rng.randint(10, 60)
            ltv = rng.randint(40, 100)
            chance = max(.05, min(.85, .1 + (700 - score) / 500 +
                                  (dti - 30) / 100 + (ltv - 70) / 200))
            target = int(rng.random() < chance)
            rows.append({
                "loan_id": f"MADEUP-{split}-{index:03d}",
                "origination_date": f"{year}-{index % 12 + 1:02d}-01",
                "split": split,
                "target": None if index % 19 == 0 else target,
                "label_available_on": f"{year + 2}-{index % 12 + 1:02d}-01",
                "credit_score": score, "dti": dti, "ltv": ltv,
                "original_balance": 150000 + index * 1000,
                "original_rate": 4.0, "original_term": 360,
                "loan_purpose": "purchase", "occupancy": "primary",
                "property_type": "single_family",
            })
        groups.append(rows)
    review = {
        "synthetic": True, "train_before": "2018-01-01", "test_from": "2021-01-01",
        "training_as_of": "2017-12-31", "validation_as_of": "2020-12-31",
        "release": "invented-fixture-dates-not-study-dates-v1",
    }
    return groups[0], groups[1], review


def _check_actual_prerequisites(review, access):
    """Fail closed until PR #24's accepted timing-review interface is on main."""
    check_review(review, access, synthetic=False)
    from . import hazim_contract

    timing_check = getattr(hazim_contract, "check_timing_review", None)
    if timing_check is None:
        raise ValueError(
            "Actual-data execution requires Hazim PR #24's versioned per-input "
            "source/timing contract; PR #24 is not merged into this branch base"
        )
    timing_check(review)


def train_candidates(train, validation, review, *, synthetic=False, access=None):
    """Fit fixed L2 candidates on observed training labels; select on validation."""
    if synthetic:
        check_review(review, synthetic=True)
    else:
        _check_actual_prerequisites(review, access)

    train, validation = list(train), list(validation)
    if len(train) > MAX_ROWS_PER_PARTITION or len(validation) > MAX_ROWS_PER_PARTITION:
        raise ValueError("CPU budget exceeded: at most 100000 rows per partition")
    train_ids = validate_partition(train, "train", review)
    validation_ids = validate_partition(validation, "validation", review)
    if train_ids & validation_ids:
        raise ValueError("Loan ID overlap between training and validation")

    observed_train = [row for row in train if row["target"] is not None]
    observed_validation = [row for row in validation if row["target"] is not None]
    if {row["target"] for row in observed_train} != {0, 1}:
        raise ValueError("Observed training labels must include both classes")
    if {row["target"] for row in observed_validation} != {0, 1}:
        raise ValueError("Observed validation labels must include both classes")

    # Censored training labels are excluded before any preprocessing is fitted.
    preprocessor = TrainPreprocessor().fit(observed_train)
    x_train = preprocessor.transform(observed_train)
    x_validation = preprocessor.transform(validation)

    from sklearn.linear_model import LogisticRegression

    models, predictions = {}, []
    targets = [row["target"] for row in observed_train]
    for c_value in REGULARIZATION_GRID:
        name = f"logistic-l2-c-{c_value:g}"
        model = LogisticRegression(
            C=c_value, penalty="l2", solver="liblinear", random_state=SEED,
            n_jobs=CPU_WORKERS, max_iter=MAX_ITERATIONS,
        )
        model.fit(x_train, targets)
        models[name] = model
        probabilities = model.predict_proba(x_validation)[:, 1]
        predictions.extend({
            "loan_id": row["loan_id"], "split": "validation",
            "target": row["target"], "probability": float(probability), "model": name,
        } for row, probability in zip(validation, probabilities))

    metrics = compare_candidates(predictions, capacity=len(observed_validation) // 5)
    selected = min(models, key=lambda name: (metrics["models"][name]["brier"], name))
    packages = ("scikit-learn", "numpy", "scipy", "joblib", "threadpoolctl")
    versions = {package: importlib.metadata.version(package) for package in packages}
    report = {
        "execution": "synthetic" if synthetic else "actual_candidate",
        "python": platform.python_version(), "versions": versions,
        "seed": SEED, "regularization_grid_C": list(REGULARIZATION_GRID),
        "penalty": "l2", "solver": "liblinear", "max_iter": MAX_ITERATIONS,
        "cpu_workers": CPU_WORKERS, "max_rows_per_partition": MAX_ROWS_PER_PARTITION,
        "preprocessing_fit_rows": len(observed_train),
        "counts": {
            "train": len(train), "train_observed": len(observed_train),
            "train_censored_excluded": len(train) - len(observed_train),
            "validation": len(validation), "validation_observed": len(observed_validation),
            "validation_censored": len(validation) - len(observed_validation),
        },
        "train_digest": canonical_hash(train),
        "validation_digest": canonical_hash(validation),
        "review_digest": canonical_hash(review),
        "validation": metrics,
        "proposed_candidate": selected,
        "selection_metric": "validation Brier ascending, model-name tie-break",
        "prediction_schema": list(PREDICTION_COLUMNS),
        "accepted_for_final_test": False, "final_test_used": False,
        "limitation": "Invented software fixture; not a mortgage performance estimate."
        if synthetic else "Candidate only; independent source/model acceptance pending.",
    }
    # Explicit schema and cohort parity checks before handing predictions onward.
    expected_ids = {row["loan_id"] for row in validation}
    for name in models:
        rows = [row for row in predictions if row["model"] == name]
        if len(rows) != len(validation) or {row["loan_id"] for row in rows} != expected_ids:
            raise ValueError("Candidate validation cohorts do not match")
        if any(tuple(row) != PREDICTION_COLUMNS for row in rows):
            raise ValueError("Prediction schema drift")
    report["candidate_validation_rows"] = len(expected_ids)
    report["candidate_count"] = len(models)
    return preprocessor, models[selected], report, predictions


def _csv_rows(path):
    with Path(path).open(newline="", encoding="utf-8") as source:
        rows = list(csv.DictReader(source))
    for row in rows:
        target = row.get("target", "")
        if target not in ("", "0", "1"):
            raise ValueError("CSV target must be blank, 0 or 1")
        row["target"] = None if target == "" else int(target)
    return rows


def _write_outputs(output, preprocessor, model, report, predictions):
    output.mkdir(parents=True, exist_ok=True)
    (output / "manifest.json").write_text(json.dumps({
        "report": report,
        "preprocessing": preprocessor.metadata(),
        "coefficient": model.coef_[0].tolist(),
        "intercept": model.intercept_.tolist(),
        "classes": model.classes_.tolist(),
    }, indent=2, allow_nan=False) + "\n", encoding="utf-8")
    with (output / "validation_predictions.csv").open("w", newline="", encoding="utf-8") as sink:
        writer = csv.DictWriter(sink, fieldnames=PREDICTION_COLUMNS)
        writer.writeheader()
        writer.writerows(predictions)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--synthetic", action="store_true")
    parser.add_argument("--train-csv", type=Path)
    parser.add_argument("--validation-csv", type=Path)
    parser.add_argument("--review", type=Path)
    parser.add_argument("--access-record", type=Path, default=Path("docs/data_access.json"))
    parser.add_argument("--out", type=Path, default=Path("models/tommy-logistic"))
    args = parser.parse_args()
    try:
        root = Path(__file__).resolve().parents[1]
        if not args.out.resolve().is_relative_to(root / "models"):
            raise ValueError("Outputs must stay in ignored repository models/ storage")
        if args.synthetic:
            if args.train_csv or args.validation_csv or args.review:
                raise ValueError("Synthetic mode creates its own fixture; external inputs prohibited")
            train, validation, review = synthetic_cohort()
            access = None
        else:
            if not all((args.train_csv, args.validation_csv, args.review)):
                raise ValueError("Actual run requires train/validation CSVs and reviewed manifests")
            # Gate from reviewed metadata before opening either loan-level CSV.
            access = json.loads(args.access_record.read_text(encoding="utf-8"))
            review = json.loads(args.review.read_text(encoding="utf-8"))
            _check_actual_prerequisites(review, access)
            for key, path in (("train_csv_sha256", args.train_csv),
                              ("validation_csv_sha256", args.validation_csv)):
                if review.get(key) != hashlib.sha256(path.read_bytes()).hexdigest():
                    raise ValueError("Input file checksum differs from reviewed manifest")
            train, validation = _csv_rows(args.train_csv), _csv_rows(args.validation_csv)

        preprocessor, model, report, predictions = train_candidates(
            train, validation, review, synthetic=args.synthetic, access=access)
        _write_outputs(args.out, preprocessor, model, report, predictions)
        print(json.dumps({
            "execution": report["execution"], "proposed_candidate": report["proposed_candidate"],
            "counts": report["counts"], "final_test_used": False,
            "candidate_validation_rows": report["candidate_validation_rows"],
            "output": str(args.out),
        }, indent=2))
    except (ValueError, KeyError, OSError) as error:
        parser.error(str(error))


if __name__ == "__main__":
    main()
