"""Prediction engine for ZanderEtAlFishing.

Implements the hybrid Logistic Regression and LightGBM soft-blending predictor
with multi-granularity feature fusion.
"""

import math
import time
from typing import Any, Dict, Optional, Union

from ml_engine.feature_extraction import fuse_features
from ml_engine.model_loader import ModelArtifacts, ModelLoader
from ml_engine.preprocessing import clean_for_stylometrics, clean_lexical


class PhishingPredictor:
    """Inference engine managing hybrid model predictions."""

    def __init__(self, artifacts: Optional[ModelArtifacts] = None, models_dir: Optional[str] = None):
        """Initialize the predictor with loaded model artifacts."""
        if artifacts is not None:
            self.artifacts = artifacts
        else:
            self.artifacts = ModelLoader.load_artifacts(models_dir=models_dir)

        # Ensemble weights & threshold from configuration
        self.config = self.artifacts.config
        self.w_lr = float(self.config.get("ensemble_weight_lr", 0.50))
        self.w_lgb = float(self.config.get("ensemble_weight_lgbm", 0.50))
        self.threshold = float(self.config.get("threshold", 0.50))
        self.high_confidence_threshold = float(self.config.get("high_confidence_threshold", 0.70))
        self.remove_digits = bool(self.config.get("lexical_remove_digits", True))
        self.remove_special_chars = bool(self.config.get("lexical_remove_special_characters", True))
        self.model_version = str(self.config.get("model_version", "v1.0"))

        # Map class 1 index for LR and LightGBM
        lr_classes = list(self.artifacts.logistic_regression.classes_)
        lgb_classes = list(self.artifacts.lightgbm.classes_)
        self.lr_pos_idx = lr_classes.index(1)
        self.lgb_pos_idx = lgb_classes.index(1)

        # Pre-warm vectorizers and model inference engines
        self._warmup()

    def _warmup(self) -> None:
        """Run a minimal dummy pass to initialize JIT/Cython/OpenMP caches."""
        try:
            fused = fuse_features(
                word_vectorizer=self.artifacts.word_vectorizer,
                char_vectorizer=self.artifacts.char_vectorizer,
                scaler=self.artifacts.scaler,
                lexical_text="warmup system",
                raw_text="warmup system",
            )
            self.artifacts.logistic_regression.predict_proba(fused)
            self.artifacts.lightgbm.predict_proba(fused)
        except Exception:
            pass

    def predict(
        self,
        email_text: str,
        override_remove_digits: Optional[bool] = None,
        override_w_lr: Optional[float] = None,
        override_w_lgb: Optional[float] = None,
        override_threshold: Optional[float] = None,
        override_high_confidence_threshold: Optional[float] = None,
    ) -> Dict[str, Any]:
        """Predict whether an email is Phishing or Legitimate.

        Parameters:
            email_text: Raw or lightly-cleaned email text.
            override_remove_digits: Override lexical digit removal setting.
            override_w_lr: Override Logistic Regression blending weight.
            override_w_lgb: Override LightGBM blending weight.
            override_threshold: Override lower classification threshold (Legitimate boundary).
            override_high_confidence_threshold: Override upper threshold (High-Confidence Phishing boundary).

        Returns:
            Dictionary with prediction, probabilities, risk_tier, weights, latency, and metadata.
        """
        # Step 1: Input validation
        if not isinstance(email_text, str):
            raise TypeError(f"Email text must be a string, got {type(email_text).__name__}")
        if not email_text.strip():
            raise ValueError("Email text cannot be empty or contain only whitespace.")

        # Latency timer starts
        start_time = time.perf_counter()

        # Step 2 & 3: Maintain two separate text representations
        raw_repr = clean_for_stylometrics(email_text)

        remove_digits = (
            override_remove_digits
            if override_remove_digits is not None
            else self.remove_digits
        )
        lexical_repr = clean_lexical(
            email_text,
            remove_digits=remove_digits,
            remove_special_characters=self.remove_special_chars,
        )

        # Step 4-8: Feature extraction & fusion
        fused_features = fuse_features(
            word_vectorizer=self.artifacts.word_vectorizer,
            char_vectorizer=self.artifacts.char_vectorizer,
            scaler=self.artifacts.scaler,
            lexical_text=lexical_repr,
            raw_text=raw_repr,
        )

        # Step 9: Stream 1 - Logistic Regression positive probability
        lr_prob_raw = float(
            self.artifacts.logistic_regression.predict_proba(fused_features)[0, self.lr_pos_idx]
        )

        # Step 10: Stream 2 - LightGBM positive probability
        lgb_prob_raw = float(
            self.artifacts.lightgbm.predict_proba(fused_features)[0, self.lgb_pos_idx]
        )

        # Step 11: 50/50 weighted probability blend
        w_lr = override_w_lr if override_w_lr is not None else self.w_lr
        w_lgb = override_w_lgb if override_w_lgb is not None else self.w_lgb
        threshold = override_threshold if override_threshold is not None else self.threshold
        high_confidence_threshold = (
            override_high_confidence_threshold
            if override_high_confidence_threshold is not None
            else self.high_confidence_threshold
        )

        p_final = (w_lr * lr_prob_raw) + (w_lgb * lgb_prob_raw)

        # Probability validation
        if not math.isfinite(p_final) or p_final < 0.0 or p_final > 1.0:
            raise ValueError(f"Computed final probability is invalid or out of bounds: {p_final}")

        # Step 12: Binary decision threshold (academic ML label — preserved unchanged)
        prediction = 1 if p_final >= threshold else 0
        classification = "Phishing" if prediction == 1 else "Legitimate"

        # Step 12b: Three-tier operational risk classification
        # Legitimate  : p < threshold (0.50)
        # Suspicious  : threshold (0.50) <= p < high_confidence_threshold (0.70)
        # High-Confidence Phishing: p >= high_confidence_threshold (0.70)
        if p_final < threshold:
            risk_tier = "Legitimate"
        elif p_final < high_confidence_threshold:
            risk_tier = "Suspicious"
        else:
            risk_tier = "High-Confidence Phishing"

        # Step 13: Latency measurement
        inference_time_ms = (time.perf_counter() - start_time) * 1000.0

        return {
            "prediction": prediction,
            "classification": classification,
            "risk_tier": risk_tier,
            "phishing_probability": round(p_final, 4),
            "logistic_regression_probability": round(lr_prob_raw, 4),
            "lightgbm_probability": round(lgb_prob_raw, 4),
            "ensemble_weights": {
                "logistic_regression": round(w_lr, 2),
                "lightgbm": round(w_lgb, 2),
            },
            "threshold": round(threshold, 2),
            "high_confidence_threshold": round(high_confidence_threshold, 2),
            "inference_time_ms": round(inference_time_ms, 2),
            "model_version": self.model_version,
        }


# Singleton engine instance for reusable predict_email calls
_DEFAULT_PREDICTOR: Optional[PhishingPredictor] = None


def get_default_predictor() -> PhishingPredictor:
    """Get or initialize the singleton PhishingPredictor."""
    global _DEFAULT_PREDICTOR
    if _DEFAULT_PREDICTOR is None:
        _DEFAULT_PREDICTOR = PhishingPredictor()
    return _DEFAULT_PREDICTOR


def predict_email(email_text: str) -> Dict[str, Any]:
    """Reusable prediction function for email phishing classification.

    Loads model artifacts once, validates input, applies multi-granularity feature fusion,
    computes hybrid probability blend, and returns prediction details.
    """
    predictor = get_default_predictor()
    return predictor.predict(email_text)
