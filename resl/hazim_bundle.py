"""Portable, non-executable JSON forest package and strict inference boundary."""
import json
import math
from pathlib import Path
import struct

from .data_checks import FEATURES
from .mannan_preprocessing import TrainPreprocessor, NUMERIC, CATEGORICAL
from .hazim_contract import VERSION, canonical_hash, validate_application

FORMAT = "resl-forest-json-v1"

def export_forest(model):
    if list(model.classes_) != [0, 1]:
        raise ValueError("Binary classes zero/one required")
    trees = []
    for estimator in model.estimators_:
        tree = estimator.tree_
        values = tree.value[:, 0, :]
        trees.append({"left": tree.children_left.tolist(), "right": tree.children_right.tolist(),
                      "feature": tree.feature.tolist(), "threshold": tree.threshold.tolist(),
                      "positive": [float(v[1] / sum(v)) for v in values]})
    return trees

def _finite(number):
    return type(number) in (int, float) and math.isfinite(number)

class ModelBundle:
    def __init__(self, payload):
        self.payload = payload
        if payload.get("format") != FORMAT or payload.get("contract") != VERSION:
            raise ValueError("Unsupported package/contract version")
        if payload.get("features") != list(FEATURES) or type(payload.get("synthetic")) is not bool:
            raise ValueError("Package feature/provenance mismatch")
        prep = payload["preprocessing"]
        if prep.get("version") != "mannan-preprocessing-v1" or prep.get("fit_split") != "train":
            raise ValueError("Unsupported preprocessing")
        if type(prep.get("training_count")) is not int or prep["training_count"] < 2:
            raise ValueError("Invalid training count")
        if set(prep["numeric"]) != set(NUMERIC) or set(prep["categories"]) != set(CATEGORICAL):
            raise ValueError("Preprocessing fields differ from contract")
        for stat in prep["numeric"].values():
            if set(stat) != {"median", "mean", "scale"} or not all(_finite(x) for x in stat.values()) or stat["scale"] <= 0:
                raise ValueError("Invalid numeric fitted settings")
        for values in prep["categories"].values():
            if not isinstance(values, (list, tuple)) or any(not isinstance(v, str) or not v for v in values) or len(set(values)) != len(values):
                raise ValueError("Invalid category vocabulary")
        self.preprocessor = TrainPreprocessor()
        self.preprocessor.stats = prep["numeric"]
        self.preprocessor.categories = {f: tuple(v) for f, v in prep["categories"].items()}
        self.preprocessor.training_count, self.preprocessor.fitted = prep["training_count"], True
        self.names = self.preprocessor.feature_names()
        if prep["feature_names"] != self.names:
            raise ValueError("Fitted feature order mismatch")
        trees = payload["trees"]
        if not isinstance(trees, list) or not 1 <= len(trees) <= 128:
            raise ValueError("Invalid forest size")
        for tree in trees:
            if set(tree) != {"left", "right", "feature", "threshold", "positive"}:
                raise ValueError("Invalid tree schema")
            n = len(tree["left"])
            if not 1 <= n <= 1023 or any(len(v) != n for v in tree.values()):
                raise ValueError("Invalid tree dimensions")
            for i in range(n):
                left, right, f = tree["left"][i], tree["right"][i], tree["feature"][i]
                if not all(type(v) is int for v in (left, right, f)):
                    raise ValueError("Invalid tree index")
                if not _finite(tree["positive"][i]) or not 0 <= tree["positive"][i] <= 1 or not _finite(tree["threshold"][i]):
                    raise ValueError("Invalid tree value")
                if left == right == -1:
                    continue
                if not (i < left < n and i < right < n and left != right and 0 <= f < len(self.names)):
                    raise ValueError("Cyclic or invalid tree children")
        if payload.get("bands") is not None:
            raise ValueError("Accepted calibrated risk bands are not implemented")

    def predict(self, application):
        clean = validate_application(application)
        vector = self.preprocessor.transform([clean])[0]
        # sklearn trees evaluate float32 inputs. Match threshold-boundary rounding.
        vector = [struct.unpack("f", struct.pack("f", v))[0] for v in vector]
        if not all(math.isfinite(v) for v in vector):
            raise ValueError("Input overflows model precision")
        probabilities = []
        for tree in self.payload["trees"]:
            node = 0
            while tree["left"][node] != -1:
                node = tree["left"][node] if vector[tree["feature"][node]] <= tree["threshold"][node] else tree["right"][node]
            probabilities.append(tree["positive"][node])
        return {"probability": sum(probabilities) / len(probabilities),
                "band": "Uncalibrated research score", "synthetic_model": self.payload["synthetic"],
                "missing_fields": [f for f, v in clean.items() if v is None],
                "warning": "Synthetic software demo only." if self.payload["synthetic"] else
                           "Research output; calibration and human acceptance remain pending."}

    def save(self, path):
        path = Path(path)
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(self.payload, sort_keys=True, allow_nan=False) + "\n", encoding="utf-8")
        return canonical_hash(self.payload)

def load_bundle(path, *, expected_hash):
    """Check a separately recorded digest before accepting local JSON."""
    path = Path(path)
    if path.stat().st_size > 20_000_000:
        raise ValueError("Model package exceeds size limit")
    payload = json.loads(path.read_text(encoding="utf-8"))
    if not expected_hash or canonical_hash(payload) != expected_hash:
        raise ValueError("Model checksum mismatch")
    return ModelBundle(payload)
