"""Bounded train/validation-only forest experiment; no final-test reader."""
import argparse
import csv
import hashlib
import importlib.metadata
import json
import platform
from pathlib import Path

from .data_checks import FEATURES
from .mannan_preprocessing import TrainPreprocessor
from .mannan_comparison import compare_candidates
from .hazim_contract import VERSION, canonical_hash, check_review, validate_partition
from .hazim_bundle import FORMAT, ModelBundle, export_forest

SEED = 42
GRID = ({"n_estimators": 64, "max_depth": 4, "min_samples_leaf": 5},
        {"n_estimators": 64, "max_depth": 8, "min_samples_leaf": 5})

def synthetic_cohort():
    """Invented deterministic loans, unrelated to any Freddie Mac records."""
    import random
    rng = random.Random(SEED)
    groups = []
    for split, year, size in (("train", 2014, 120), ("validation", 2018, 40)):
        rows = []
        for i in range(size):
            score, dti, ltv = rng.randint(560, 820), rng.randint(10, 60), rng.randint(40, 100)
            p = max(.05, min(.85, .1 + (700 - score) / 500 + (dti - 30) / 100 + (ltv - 70) / 200))
            target = int(rng.random() < p)
            rows.append({"loan_id": f"MADEUP-{split}-{i:03d}",
                         "origination_date": f"{year}-{i % 12 + 1:02d}-01",
                         "split": split, "target": None if i % 19 == 0 else target,
                         "label_available_on": f"{year + 2}-{i % 12 + 1:02d}-01",
                         "credit_score": score, "dti": dti, "ltv": ltv,
                         "original_balance": 150000 + i * 1000, "original_rate": 4.0,
                         "original_term": 360, "loan_purpose": "purchase",
                         "occupancy": "primary", "property_type": "single_family"})
        groups.append(rows)
    return (*groups, {"synthetic": True, "train_before": "2018-01-01",
                     "test_from": "2021-01-01", "training_as_of": "2017-12-31",
                     "validation_as_of": "2020-12-31", "release": "made-up-software-fixture-v1"})

def train_candidates(train, validation, review, *, synthetic=False, access=None):
    """Fit preprocessing and two fixed candidates on observed training loans only."""
    check_review(review, access, synthetic=synthetic)
    train, validation = list(train), list(validation)
    if len(train) > 100_000 or len(validation) > 100_000:
        raise ValueError("Declared CPU budget: at most 100000 rows per partition")
    ids = validate_partition(train, "train", review)
    val_ids = validate_partition(validation, "validation", review)
    if ids & val_ids:
        raise ValueError("Loan occurs in both training and validation")
    observed = [r for r in train if r["target"] is not None]
    val_observed = [r for r in validation if r["target"] is not None]
    if {r["target"] for r in observed} != {0, 1} or {r["target"] for r in val_observed} != {0, 1}:
        raise ValueError("Both classes required in observed train and validation cohorts")
    from sklearn.ensemble import RandomForestClassifier
    prep = TrainPreprocessor().fit(observed)
    x_train, x_val = prep.transform(observed), prep.transform(validation)
    models, predictions = {}, []
    for index, settings in enumerate(GRID):
        name = f"rf-depth-{settings['max_depth']}"
        model = RandomForestClassifier(**settings, random_state=SEED, n_jobs=1,
                                       class_weight=None, max_features="sqrt")
        model.fit(x_train, [r["target"] for r in observed])
        models[name] = model
        predictions.extend({"model": name, "loan_id": r["loan_id"], "split": "validation",
                            "target": r["target"], "probability": float(p[1])}
                           for r, p in zip(validation, model.predict_proba(x_val)))
    # Predeclared software proposal; independent acceptance remains pending.
    metrics = compare_candidates(predictions, capacity=len(val_observed) // 5)
    selected = min(models, key=lambda name: (metrics["models"][name]["brier"], name))
    versions = {p: importlib.metadata.version(p) for p in
                ("scikit-learn", "numpy", "scipy", "joblib", "threadpoolctl")}
    report = {"synthetic": synthetic, "python": platform.python_version(), "versions": versions,
              "seed": SEED, "grid": list(GRID), "n_jobs": 1, "max_rows_per_partition": 100000,
              "counts": {"train": len(train), "train_observed": len(observed),
                         "train_censored": len(train) - len(observed), "validation": len(validation),
                         "validation_observed": len(val_observed),
                         "validation_censored": len(validation) - len(val_observed)},
              "train_digest": canonical_hash(train), "validation_digest": canonical_hash(validation),
              "review_digest": canonical_hash(review), "validation": metrics,
              "proposed_candidate": selected, "selection_metric": "validation Brier ascending, name tie-break",
              "accepted_for_final_test": False, "final_test_used": False,
              "limitation": "Software experiment only." if synthetic else
                            "Proposed candidate; review, calibration and final-test acceptance pending."}
    best = models[selected]
    payload = {"format": FORMAT, "contract": VERSION, "features": list(FEATURES),
               "synthetic": synthetic, "bands": None, "preprocessing": prep.metadata(),
               "trees": export_forest(best), "metadata": report}
    bundle = ModelBundle(payload)
    # Verify exported inference against sklearn for every validation application.
    for row, expected in zip(validation, best.predict_proba(x_val)):
        result = bundle.predict({f: row[f] for f in FEATURES})["probability"]
        if abs(result - float(expected[1])) > 1e-12:
            raise ValueError("Portable forest differs from sklearn predictions")
    report["export_parity_validation_rows"] = len(validation)
    return bundle, report, predictions

def _csv_rows(path):
    with Path(path).open(newline="", encoding="utf-8") as source:
        rows = list(csv.DictReader(source))
    for row in rows:
        value = row.get("target", "")
        if value not in ("", "0", "1"):
            raise ValueError("CSV target must be blank, 0 or 1")
        row["target"] = None if value == "" else int(value)
    return rows

def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--synthetic", action="store_true")
    parser.add_argument("--train-csv", type=Path)
    parser.add_argument("--validation-csv", type=Path)
    parser.add_argument("--review", type=Path)
    parser.add_argument("--access-record", type=Path, default=Path("docs/data_access.json"))
    parser.add_argument("--out", type=Path, default=Path("models/hazim"))
    args = parser.parse_args()
    try:
        root = Path(__file__).resolve().parents[1]
        if not args.out.resolve().is_relative_to(root / "models"):
            raise ValueError("Model outputs must stay in ignored repository models/ storage")
        if args.synthetic:
            if args.train_csv or args.validation_csv or args.review:
                raise ValueError("Synthetic mode generates its own fixture; external inputs prohibited")
            train, validation, review = synthetic_cohort()
            access = None
        else:
            if not all((args.train_csv, args.validation_csv, args.review)):
                raise ValueError("Actual run requires train/validation CSVs and a reviewed manifest")
            access = json.loads(args.access_record.read_text(encoding="utf-8"))
            review = json.loads(args.review.read_text(encoding="utf-8"))
            check_review(review, access, synthetic=False)
            for key, path in (("train_csv_sha256", args.train_csv),
                              ("validation_csv_sha256", args.validation_csv)):
                if review.get(key) != hashlib.sha256(path.read_bytes()).hexdigest():
                    raise ValueError("Input file checksum differs from reviewed manifest")
            train, validation = _csv_rows(args.train_csv), _csv_rows(args.validation_csv)
        bundle, report, predictions = train_candidates(train, validation, review,
                                                        synthetic=args.synthetic, access=access)
        digest = bundle.save(args.out / "forest.json")
        (args.out / "manifest.json").write_text(json.dumps(
            {"model_hash": digest, "report": report}, indent=2) + "\n", encoding="utf-8")
        (args.out / "validation_predictions.json").write_text(json.dumps(predictions) + "\n", encoding="utf-8")
        print(json.dumps({"synthetic": args.synthetic, "proposed_candidate": report["proposed_candidate"],
                          "counts": report["counts"], "final_test_used": False,
                          "export_parity_validation_rows": report["export_parity_validation_rows"],
                          "output": str(args.out)}, indent=2))
    except (ValueError, KeyError, OSError) as exc:
        parser.error(str(exc))

if __name__ == "__main__":
    main()
