"""ZanderEtAlFishing — ML Inference Engine for Phishing Email Detection.

Multi-Granularity Feature Fusion with Hybrid Logistic Regression and LightGBM.
"""

from ml_engine.feature_extraction import (
    STYLO_FEATURE_NAMES,
    URGENCY_WORDS,
    extract_stylometrics,
    fuse_features,
)
from ml_engine.model_loader import ModelArtifacts, ModelLoader
from ml_engine.predictor import (
    PhishingPredictor,
    get_default_predictor,
    predict_email,
)
from ml_engine.preprocessing import (
    clean_for_stylometrics,
    clean_lexical,
    clean_lexical_original,
    ensure_nltk_resources,
)

__version__ = "1.0.0"

__all__ = [
    "predict_email",
    "PhishingPredictor",
    "get_default_predictor",
    "ModelLoader",
    "ModelArtifacts",
    "clean_for_stylometrics",
    "clean_lexical",
    "clean_lexical_original",
    "ensure_nltk_resources",
    "extract_stylometrics",
    "fuse_features",
    "URGENCY_WORDS",
    "STYLO_FEATURE_NAMES",
]

