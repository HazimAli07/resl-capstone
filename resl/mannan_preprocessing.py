"""Train-only preprocessing for normalized inputs; AI-assisted D2 2.2 work."""
import math
from statistics import median, mean, pstdev
from .data_checks import FEATURES

NUMERIC = FEATURES[:6]
CATEGORICAL = FEATURES[6:]
# Interface validation, not lending rules. Units require selected-release review.
BOUNDS = {"credit_score": (300, 850), "dti": (0, 998), "ltv": (0, 998),
          "original_balance": (0, None), "original_rate": (0, 100),
          "original_term": (1, 600)}
SENTINELS = {"credit_score": {9999}, "dti": {999}, "ltv": {999}}

def numeric_value(field, value):
    if value is None or str(value).strip() == "":
        return None
    if isinstance(value, bool):
        raise ValueError(f"{field}: boolean is not a number")
    try:
        number = float(value)
    except (TypeError, ValueError) as exc:
        raise ValueError(f"{field}: expected a number") from exc
    if not math.isfinite(number):
        raise ValueError(f"{field}: nonfinite value")
    if number in SENTINELS.get(field, set()):
        return None
    low, high = BOUNDS[field]
    if number < low or (high is not None and number > high):
        raise ValueError(f"{field}: outside normalized interface bounds")
    if field == "original_balance" and number == 0:
        raise ValueError("original_balance must be positive")
    if field in {"credit_score", "original_term"} and not number.is_integer():
        raise ValueError(f"{field}: expected an integer")
    return number

def category_value(value):
    return None if value is None or str(value).strip() == "" else str(value).strip()

class TrainPreprocessor:
    """Fit once on tagged train loans; transform never changes fitted settings.

    Median imputation, z-scaling, numeric missing flags and explicit missing/
    unknown category columns. Caller verifies split provenance; tags are not proof.
    Only FEATURES enter the matrix, regardless of metadata/future columns.
    """
    def __init__(self):
        self.fitted = False

    def fit(self, rows):
        if self.fitted:
            raise ValueError("Already fitted; use a fresh training-only instance")
        rows = list(rows)
        if not rows or any(row.get("split") != "train" for row in rows):
            raise ValueError("Fit requires nonempty, explicitly tagged train rows")
        ids = [str(row.get("loan_id", "")).strip() for row in rows]
        if any(row.get("loan_id") is None for row in rows) or not all(ids) or len(set(ids)) != len(ids):
            raise ValueError("Training IDs must be nonblank and unique")
        if any(not set(FEATURES).issubset(row) for row in rows):
            raise ValueError("Missing normalized input columns")
        stats, categories = {}, {}
        for field in NUMERIC:
            values = [numeric_value(field, row[field]) for row in rows]
            observed = [v for v in values if v is not None]
            if not observed:
                raise ValueError(f"{field}: all training values are missing")
            fill = median(observed)
            imputed = [fill if v is None else v for v in values]
            stats[field] = {"median": fill, "mean": mean(imputed),
                            "scale": pstdev(imputed) or 1.0}
        for field in CATEGORICAL:
            categories[field] = tuple(sorted(
                {category_value(row[field]) for row in rows} - {None}))
        self.stats, self.categories = stats, categories
        self.training_count, self.fitted = len(rows), True
        return self

    def feature_names(self):
        if not self.fitted:
            raise ValueError("Preprocessor has not been fitted")
        names = []
        for field in NUMERIC:
            names.extend((field + ":scaled", field + ":missing"))
        for field in CATEGORICAL:
            names.extend(f"{field}:value:{len(v)}:{v}" for v in self.categories[field])
            names.extend((field + ":missing", field + ":unknown"))
        return names

    def transform(self, rows):
        self.feature_names()
        result = []
        for row in rows:
            if not set(FEATURES).issubset(row):
                raise ValueError("Missing normalized input columns")
            vector = []
            for field in NUMERIC:
                value = numeric_value(field, row[field])
                stat = self.stats[field]
                imputed = stat["median"] if value is None else value
                vector.extend(((imputed - stat["mean"]) / stat["scale"],
                               float(value is None)))
            for field in CATEGORICAL:
                value, known = category_value(row[field]), self.categories[field]
                vector.extend(float(value == category) for category in known)
                vector.extend((float(value is None),
                               float(value is not None and value not in known)))
            if not all(math.isfinite(v) for v in vector):
                raise ValueError("Nonfinite transformed value")
            result.append(vector)
        return result

    def metadata(self):
        """Fitted metadata can be sensitive: keep actual-data settings local."""
        return {"version": "mannan-preprocessing-v1", "fit_split": "train",
                "training_count": getattr(self, "training_count", 0),
                "feature_names": self.feature_names(), "numeric": self.stats,
                "categories": self.categories}
