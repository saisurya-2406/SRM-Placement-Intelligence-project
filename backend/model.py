"""Lazy-failure-safe loading and inference for exported Colab model artifacts."""

from __future__ import annotations

import json
from importlib.metadata import PackageNotFoundError, version
from pathlib import Path
from typing import Any
import warnings

import joblib
try:
    import numpy as np
except Exception as error:  # keep Flask available when optional ML binaries are blocked
    np = None
    NUMPY_IMPORT_ERROR = str(error)
else:
    NUMPY_IMPORT_ERROR = None

try:
    import pandas as pd
except Exception as error:  # keep Flask available when the optional ML stack is incomplete
    pd = None
    PANDAS_IMPORT_ERROR = str(error)
else:
    PANDAS_IMPORT_ERROR = None

try:
    from .config import MODEL_DIR
except ImportError:
    from config import MODEL_DIR


MODEL_FILES = {
    "Decision Tree": "decision_tree.pkl",
    "Random Forest": "best_random_forest.pkl",
    "SVM": "svm.pkl",
    "KNN": "knn.pkl",
    "Naive Bayes": "naive_bayes.pkl",
}

EXPECTED_FEATURES = [
    "cgpa", "coding_skill_score", "aptitude_score", "communication_skill_score",
    "logical_reasoning_score", "mock_interview_score", "backlogs", "github_repos",
    "internships_count", "projects_count", "branch_ECE", "branch_EEE", "branch_IT",
    "role_category_Data Analyst", "role_category_Data Engineer", "role_category_Data Scientist",
    "role_category_Machine Learning Engineer", "role_category_Python Developer",
    "work_mode_On-site", "work_mode_Remote",
]

CATEGORY_BASELINES = {"branch": "CSE", "role_category": "Business Analyst", "work_mode": "Hybrid"}


class ModelRegistry:
    def __init__(self) -> None:
        self.config: dict[str, Any] = {}
        self.models: dict[str, Any] = {}
        self.medians: Any = None
        self.scaler: Any = None
        self.errors: list[str] = []
        self.features: list[str] = []
        self._load()

    def _load(self) -> None:
        if np is None:
            self.errors.append(f"ML runtime dependency unavailable: NumPy could not load ({NUMPY_IMPORT_ERROR}).")
            return
        config_path = MODEL_DIR / "feature_config.json"
        try:
            self.config = json.loads(config_path.read_text(encoding="utf-8"))
            self.features = self.config["feature_names"]
        except Exception as error:
            self.errors.append(f"Feature configuration unavailable: {error}")
            return
        if self.features != EXPECTED_FEATURES:
            self.errors.append("Feature configuration does not match the verified notebook feature order.")
            return
        numeric_features = self.config.get("numeric_features")
        if numeric_features != EXPECTED_FEATURES[:10]:
            self.errors.append("Numeric feature configuration does not match the verified notebook schema.")
            return
        mappings = self.config.get("categorical_features", {})
        expected_categories = {
            "branch": {"CSE": None, "ECE": "branch_ECE", "EEE": "branch_EEE", "IT": "branch_IT"},
            "role_category": {
                "Business Analyst": None, "Data Analyst": "role_category_Data Analyst",
                "Data Engineer": "role_category_Data Engineer", "Data Scientist": "role_category_Data Scientist",
                "Machine Learning Engineer": "role_category_Machine Learning Engineer",
                "Python Developer": "role_category_Python Developer",
            },
            "work_mode": {"Hybrid": None, "On-site": "work_mode_On-site", "Remote": "work_mode_Remote"},
        }
        if mappings != expected_categories:
            self.errors.append("Categorical mappings do not match the explicit notebook one-hot encoding.")
            return
        if self.config.get("category_encoding_verified") is not True:
            self.errors.append("Category encoding has not been verified against the explicit notebook encoder.")

        trained_version = self.config.get("scikit_learn_version")
        if trained_version:
            try:
                runtime_version = version("scikit-learn")
            except PackageNotFoundError:
                runtime_version = None
            if runtime_version != trained_version:
                self.errors.append(
                    f"Model artifacts were trained with scikit-learn {trained_version}; "
                    f"runtime has {runtime_version or 'no scikit-learn installation'}. Rerun the notebook export with this environment."
                )
                return

        for name, filename in MODEL_FILES.items():
            path = MODEL_DIR / filename
            if not path.exists():
                continue
            try:
                with warnings.catch_warnings(record=True) as artifact_warnings:
                    warnings.simplefilter("always")
                    candidate = joblib.load(path)
                count = getattr(candidate, "n_features_in_", None)
                incompatibilities = []
                if count != len(self.features):
                    incompatibilities.append(f"model expects {count} features; config requires {len(self.features)}")
                version_warnings = [
                    str(item.message) for item in artifact_warnings
                    if item.category.__name__ == "InconsistentVersionWarning"
                ]
                if version_warnings:
                    incompatibilities.append(version_warnings[0])
                if not {0, 1}.issubset(set(getattr(candidate, "classes_", []))):
                    incompatibilities.append("model does not expose both synthetic target classes 0 and 1")
                if incompatibilities:
                    raise ValueError("; ".join(incompatibilities))
                self.models[name] = candidate
            except Exception as error:
                self.errors.append(f"{name} artifact could not be loaded: {error}")

        median_path = MODEL_DIR / "train_medians.pkl"
        try:
            if not median_path.exists():
                raise FileNotFoundError("train_medians.pkl is not present in model/")
            self.medians = joblib.load(median_path)
            median_names = list(getattr(self.medians, "index", []))
            if median_names and median_names != self.features:
                raise ValueError("training medians do not match feature order")
            median_values = np.asarray(self.medians, dtype=float)
            if median_values.shape != (len(self.features),) or not np.isfinite(median_values).all():
                raise ValueError("training medians have invalid shape or non-finite values")
        except Exception as error:
            self.medians = None
            self.errors.append(f"Training medians unavailable: {error}")

        scaler_path = MODEL_DIR / "standard_scaler.pkl"
        try:
            if not scaler_path.exists():
                raise FileNotFoundError("standard_scaler.pkl is not present in model/")
            self.scaler = joblib.load(scaler_path)
            if getattr(self.scaler, "n_features_in_", None) != len(self.features):
                raise ValueError("scaler feature count does not match config")
            scaler_names = list(getattr(self.scaler, "feature_names_in_", []))
            if scaler_names and scaler_names != self.features:
                raise ValueError("scaler does not match feature order")
            if not np.isfinite(self.scaler.scale_).all() or not np.isfinite(self.scaler.mean_).all():
                raise ValueError("scaler contains non-finite fitted values")
        except Exception as error:
            self.scaler = None
            self.errors.append(f"Fitted scaler unavailable: {error}")

    @property
    def ready(self) -> bool:
        return (
            bool(self.models)
            and self.medians is not None
            and self.scaler is not None
            and self.config.get("category_encoding_verified") is True
        )

    def status(self) -> dict[str, Any]:
        return {
            "ready": self.ready,
            "available_algorithms": list(self.models),
            "required_algorithms": list(MODEL_FILES),
            "missing_algorithms": [name for name in MODEL_FILES if name not in self.models],
            "medians_ready": self.medians is not None,
            "scaler_ready": self.scaler is not None,
            "preprocessing_ready": self.medians is not None and self.scaler is not None,
            "category_encoding_verified": self.config.get("category_encoding_verified") is True,
            "errors": self.errors,
        }

    def _preprocess(self, row: dict[str, float]) -> np.ndarray:
        if set(row) != set(self.features):
            raise ValueError("Prediction row does not contain the complete configured feature set.")
        frame = np.asarray([[row[name] for name in self.features]], dtype=float)
        if hasattr(self.medians, "reindex"):
            medians = np.asarray(self.medians.reindex(self.features), dtype=float)
        else:
            medians = np.asarray(self.medians, dtype=float)
        frame = np.where(np.isnan(frame), medians.reshape(1, -1), frame)
        if getattr(self.scaler, "feature_names_in_", None) is not None:
            if pd is None:
                raise RuntimeError(f"Pandas is needed to preserve fitted scaler feature names: {PANDAS_IMPORT_ERROR}")
            frame = pd.DataFrame(frame, columns=self.features)
        return self.scaler.transform(frame)

    def predict(self, row: dict[str, float], algorithms: list[str] | None = None) -> dict[str, Any]:
        if self.config.get("category_encoding_verified") is not True:
            raise RuntimeError("Colab category encoding has not been verified against the explicit notebook encoder.")
        if self.medians is None or self.scaler is None:
            reason = "; ".join(self.errors) or "training medians and fitted scaler are unavailable."
            raise RuntimeError(f"Prediction preprocessing is unavailable: {reason}")
        selected = algorithms or list(self.models)
        unavailable = [name for name in selected if name not in self.models]
        if unavailable:
            raise RuntimeError("Model artifacts unavailable: " + ", ".join(unavailable))
        processed = self._preprocess(row)
        outputs: dict[str, Any] = {}
        for name in selected:
            model = self.models[name]
            label_raw = model.predict(processed)[0]
            label = label_raw.item() if np is not None and isinstance(label_raw, np.generic) else label_raw
            result: dict[str, Any] = {"predicted_label": int(label)}
            if hasattr(model, "predict_proba"):
                scores = model.predict_proba(processed)[0]
                result["class_probabilities"] = {
                    str(class_label): float(score)
                    for class_label, score in zip(model.classes_, scores)
                }
            elif hasattr(model, "decision_function"):
                score = model.decision_function(processed)[0]
                result["decision_score"] = float(score)
            if hasattr(model, "feature_importances_"):
                result["feature_importance"] = sorted(
                    [{"feature": feature, "importance": float(value)}
                     for feature, value in zip(self.features, model.feature_importances_)],
                    key=lambda item: item["importance"], reverse=True,
                )[:10]
            outputs[name] = result
        return outputs
