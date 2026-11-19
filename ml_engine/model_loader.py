"""Model artifact loader for ZanderEtAlFishing.

Loads and verifies:
- Logistic Regression model (joblib)
- LightGBM model (joblib)
- Word TfidfVectorizer (joblib)
- Character TfidfVectorizer (joblib)
- Stylometric StandardScaler (joblib)
- Configuration (JSON / fallback PKL)
"""

import json
import os
import pickle
import warnings
from dataclasses import dataclass
from typing import Any, Dict, Optional
import joblib
from sklearn.exceptions import InconsistentVersionWarning

from ml_engine.preprocessing import ensure_nltk_resources

DEFAULT_MODELS_DIR = os.path.abspath(
    os.path.join(os.path.dirname(__file__), "..", "models")
)


@dataclass
class ModelArtifacts:
    """Container for all loaded and verified model artifacts."""
    logistic_regression: Any
    lightgbm: Any
    word_vectorizer: Any
    char_vectorizer: Any
    scaler: Any
    config: Dict[str, Any]
    models_dir: str


class ModelLoader:
    """Manages secure loading, verification, and caching of model artifacts."""

    _cached_artifacts: Optional[ModelArtifacts] = None

    @classmethod
    def load_artifacts(
        cls,
        models_dir: Optional[str] = None,
        force_reload: bool = False,
    ) -> ModelArtifacts:
        """Load, validate, and cache model artifacts from the models directory."""
        target_dir = os.path.abspath(models_dir or DEFAULT_MODELS_DIR)

        if cls._cached_artifacts is not None and not force_reload:
            if os.path.abspath(cls._cached_artifacts.models_dir) == target_dir:
                return cls._cached_artifacts
        if not os.path.isdir(target_dir):
            raise FileNotFoundError(f"Models directory not found: {target_dir}")

        # Artifact filenames
        lr_path = os.path.join(target_dir, "logistic_regression_model.joblib")
        lgb_path = os.path.join(target_dir, "lightgbm_model.joblib")
        word_vec_path = os.path.join(target_dir, "word_vectorizer.joblib")
        char_vec_path = os.path.join(target_dir, "char_vectorizer.joblib")
        scaler_path = os.path.join(target_dir, "scaler.joblib")
        json_cfg_path = os.path.join(target_dir, "inference_config.json")
        pkl_cfg_path = os.path.join(target_dir, "config.pkl")

        # Verify existence
        for name, p in [
            ("Logistic Regression model", lr_path),
            ("LightGBM model", lgb_path),
            ("Word vectorizer", word_vec_path),
            ("Character vectorizer", char_vec_path),
            ("Stylometric scaler", scaler_path),
        ]:
            if not os.path.isfile(p):
                raise FileNotFoundError(f"Required model artifact missing: {name} at {p}")

        # Pre-warm NLTK resources so first inference is not delayed
        ensure_nltk_resources()

        # Load artifacts with clean warning handling for known Colab 1.6.1 -> 1.7.2 minor serialization delta
        with warnings.catch_warnings():
            warnings.filterwarnings("ignore", category=InconsistentVersionWarning)
            lr_model = joblib.load(lr_path)
            lgb_model = joblib.load(lgb_path)
            word_vectorizer = joblib.load(word_vec_path)
            char_vectorizer = joblib.load(char_vec_path)
            scaler = joblib.load(scaler_path)

        # Load configuration (prefer inference_config.json, inspect config.pkl)
        config: Dict[str, Any] = {}
        if os.path.isfile(json_cfg_path):
            with open(json_cfg_path, "r", encoding="utf-8") as f:
                config = json.load(f)
        elif os.path.isfile(pkl_cfg_path):
            with open(pkl_cfg_path, "rb") as f:
                config = pickle.load(f)
        else:
            config = {
                "system_name": "ZanderEtAlFishing",
                "ensemble_weight_lr": 0.5,
                "ensemble_weight_lgbm": 0.5,
                "threshold": 0.5,
                "lexical_remove_digits": True,
                "lexical_remove_special_characters": True,
                "model_version": "v1.0",
            }

        # Validate classes and feature dimensions
        cls._validate_artifacts(
            lr_model, lgb_model, word_vectorizer, char_vectorizer, scaler
        )

        artifacts = ModelArtifacts(
            logistic_regression=lr_model,
            lightgbm=lgb_model,
            word_vectorizer=word_vectorizer,
            char_vectorizer=char_vectorizer,
            scaler=scaler,
            config=config,
            models_dir=target_dir,
        )

        cls._cached_artifacts = artifacts
        return artifacts

    @classmethod
    def _validate_artifacts(cls, lr, lgb, word_vec, char_vec, scaler) -> None:
        """Validate artifact integrity and feature compatibility."""
        # 1. Check positive class index
        for model_name, model in [("LogisticRegression", lr), ("LightGBM", lgb)]:
            if not hasattr(model, "classes_"):
                raise AttributeError(f"{model_name} missing classes_ attribute")
            classes = list(model.classes_)
            if 1 not in classes:
                raise ValueError(f"{model_name} classes {classes} does not contain positive class 1")

        # 2. Check feature expectations
        word_dim = len(word_vec.vocabulary_) if hasattr(word_vec, "vocabulary_") else 10000
        char_dim = len(char_vec.vocabulary_) if hasattr(char_vec, "vocabulary_") else 5000
        stylo_dim = scaler.n_features_in_ if hasattr(scaler, "n_features_in_") else 9
        total_dim = word_dim + char_dim + stylo_dim

        for model_name, model in [("LogisticRegression", lr), ("LightGBM", lgb)]:
            n_features = getattr(model, "n_features_in_", None)
            if n_features is not None and n_features != total_dim:
                raise ValueError(
                    f"{model_name} expects {n_features} features, but combined artifacts provide {total_dim}"
                )

    @classmethod
    def clear_cache(cls) -> None:
        """Clear cached artifacts."""
        cls._cached_artifacts = None
