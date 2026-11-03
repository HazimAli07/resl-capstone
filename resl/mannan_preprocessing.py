"""Train-only preprocessing for normalized inputs; Codex-assisted D2 2.2 work."""
import copy
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
    Only FEATURES enter the matrix, regardless of metadata/future columns. If
    labels are supplied, every fit row must have an observed binary target;
    censoring is handled by the training runner before fitting. Unlabelled rows
    remain supported for standalone software checks, not as cohort acceptance.
    """
    def __init__(self):
        self.fitted = False

    def fit(self, rows):
        if self.fitted:
            raise ValueError("Already fitted; use a fresh training-only instance")
        rows = list(rows)
        if not rows or any(row.get("split") != "train" for row in rows):
            raise ValueError("Fit requires nonempty, explicitly tagged train rows")
        if any("target" in row for row in rows) and any(
                type(row.get("target")) is not int or row["target"] not in (0, 1)
                for row in rows):
            raise ValueError("Fit requires observed binary targets when labels are supplied")
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
        """Return detached v1 package metadata; actual-data settings stay local."""
        return copy.deepcopy({"version": "mannan-preprocessing-v1", "fit_split": "train",
                "training_count": getattr(self, "training_count", 0),
                "feature_names": self.feature_names(), "numeric": self.stats,
                "categories": self.categories})

    @classmethod
    def from_metadata(cls, metadata):
        """Restore fitted v1 JSON settings without observing or fitting any rows.

        This uses the existing model-package schema. File digests, access,
        software versions and independently reviewed splits remain the package
        owner's responsibility; metadata alone cannot establish provenance.
        """
        expected = {"version", "fit_split", "training_count", "feature_names",
                    "numeric", "categories"}
        if not isinstance(metadata, dict) or set(metadata) != expected:
            raise ValueError("Invalid preprocessing metadata schema")
        if (metadata["version"] != "mannan-preprocessing-v1" or
                metadata["fit_split"] != "train"):
            raise ValueError("Unsupported preprocessing metadata")
        count = metadata["training_count"]
        if type(count) is not int or count < 1:
            raise ValueError("Invalid training count")
        stats, categories = metadata["numeric"], metadata["categories"]
        if (not isinstance(stats, dict) or set(stats) != set(NUMERIC) or
                not isinstance(categories, dict) or set(categories) != set(CATEGORICAL)):
            raise ValueError("Preprocessing fields differ from contract")
        for field, stat in stats.items():
            if (not isinstance(stat, dict) or set(stat) != {"median", "mean", "scale"}
                    or any(type(v) not in (int, float) or not math.isfinite(v)
                           for v in stat.values()) or stat["scale"] <= 0):
                raise ValueError("Invalid numeric fitted settings")
            # A median can be fractional even for integer-valued inputs.
            low, high = BOUNDS[field]
            for key in ("median", "mean"):
                if (stat[key] < low or (high is not None and stat[key] > high)
                        or (field == "original_balance" and stat[key] == 0)):
                    raise ValueError("Numeric fitted settings outside interface bounds")
        for values in categories.values():
            if (not isinstance(values, (list, tuple)) or
                    any(not isinstance(v, str) or not v or v != v.strip() for v in values) or
                    len(set(values)) != len(values)):
                raise ValueError("Invalid category vocabulary")
        prep = cls()
        prep.stats = copy.deepcopy(stats)
        prep.categories = {field: tuple(values) for field, values in categories.items()}
        prep.training_count, prep.fitted = count, True
        if metadata["feature_names"] != prep.feature_names():
            raise ValueError("Fitted feature order mismatch")
        return prep
