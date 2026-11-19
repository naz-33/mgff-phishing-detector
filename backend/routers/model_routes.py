"""Model information and architecture API routes."""

import json
import os
from fastapi import APIRouter, Depends

from backend.auth import get_current_user
from backend.config import BASE_DIR
from backend.schemas import EnsembleWeights, ModelInfo

router = APIRouter(prefix="/api/model", tags=["Model"])


@router.get("/info", response_model=ModelInfo)
def get_model_info(current_user: str = Depends(get_current_user)):
    """Retrieve ML engine metadata, feature engineering specs, and ensemble configuration."""
    models_dir = BASE_DIR / "models"
    config_path = models_dir / "inference_config.json"

    system_name = "ZanderEtAlFishing"
    model_version = "v1.0"
    threshold = 0.50
    high_confidence_threshold = 0.70
    w_lr = 0.50
    w_lgb = 0.50

    if config_path.exists():
        try:
            with open(config_path, "r", encoding="utf-8") as f:
                cfg = json.load(f)
                system_name = cfg.get("system_name", system_name)
                model_version = cfg.get("model_version", model_version)
                threshold = float(cfg.get("threshold", threshold))
                high_confidence_threshold = float(cfg.get("high_confidence_threshold", high_confidence_threshold))
                w_lr = float(cfg.get("ensemble_weight_lr", w_lr))
                w_lgb = float(cfg.get("ensemble_weight_lgbm", w_lgb))
        except Exception:
            pass

    # Check presence of model artifacts
    artifacts = {
        "logistic_regression": (models_dir / "logistic_regression_model.joblib").exists() or (models_dir / "logistic_regression_model.pkl").exists(),
        "lightgbm": (models_dir / "lightgbm_model.joblib").exists() or (models_dir / "lightgbm_model.pkl").exists(),
        "word_vectorizer": (models_dir / "word_vectorizer.joblib").exists() or (models_dir / "word_vectorizer.pkl").exists(),
        "char_vectorizer": (models_dir / "char_vectorizer.joblib").exists() or (models_dir / "char_vectorizer.pkl").exists(),
        "scaler": (models_dir / "scaler.joblib").exists() or (models_dir / "scaler.pkl").exists(),
    }

    architecture = {
        "feature_fusion": "Multi-Granularity Feature Fusion",
        "feature_breakdown": [
            {"stream": "Lexical Word-Level TF-IDF", "dimension": 10000, "ngrams": "1-2 grams", "details": "Sublinear TF, english stopwords removed"},
            {"stream": "Lexical Character-Level TF-IDF", "dimension": 5000, "ngrams": "3-5 grams", "details": "Sublinear TF, char analyzer"},
            {"stream": "Stylometric Features", "dimension": 9, "ngrams": "N/A", "details": "Length, word count, uppercase ratio, !/?, digit ratio, URL count, urgency words, Shannon entropy (StandardScaler)"},
        ],
        "ensemble_classifiers": [
            {"model": "Logistic Regression", "weight": f"{int(w_lr*100)}%", "hyperparameters": "C=5.0, L2 penalty, max_iter=1500"},
            {"model": "LightGBM Classifier", "weight": f"{int(w_lgb*100)}%", "hyperparameters": "n_estimators=200, depth=7, lr=0.08, leaves=63"},
        ],
        "decision_threshold": threshold,
        "high_confidence_threshold": high_confidence_threshold,
    }

    return ModelInfo(
        system_name=system_name,
        model_version=model_version,
        threshold=threshold,
        high_confidence_threshold=high_confidence_threshold,
        ensemble_weights=EnsembleWeights(
            logistic_regression=w_lr,
            lightgbm=w_lgb,
        ),
        models_loaded=artifacts,
        architecture=architecture,
    )

