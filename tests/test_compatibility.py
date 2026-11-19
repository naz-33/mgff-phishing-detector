"""Compatibility tests between original research training and updated inference pipeline.

Compares:
1. Local environment compatibility with serialized Colab artifacts.
2. Prediction and probability deltas between:
   - Original research lexical preprocessing (digits preserved)
   - Updated inference lexical preprocessing (digits removed)
"""

import pytest
from ml_engine.model_loader import ModelLoader
from ml_engine.predictor import PhishingPredictor


@pytest.fixture(scope="module")
def artifacts():
    return ModelLoader.load_artifacts()


@pytest.fixture(scope="module")
def predictor():
    return PhishingPredictor()


class TestArtifactCompatibility:
    """Verifies that Colab-trained artifacts load and match required feature spaces."""

    def test_logistic_regression_parameters(self, artifacts):
        lr = artifacts.logistic_regression
        assert hasattr(lr, "classes_")
        assert list(lr.classes_) == [0, 1]
        assert getattr(lr, "n_features_in_", 15009) == 15009
        # Check coefficients match 15009 features
        assert lr.coef_.shape == (1, 15009)

    def test_lightgbm_parameters(self, artifacts):
        lgb = artifacts.lightgbm
        assert hasattr(lgb, "classes_")
        assert list(lgb.classes_) == [0, 1]
        assert getattr(lgb, "n_features_in_", 15009) == 15009

    def test_vectorizer_vocabularies(self, artifacts):
        w_vec = artifacts.word_vectorizer
        c_vec = artifacts.char_vectorizer

        assert hasattr(w_vec, "vocabulary_")
        assert len(w_vec.vocabulary_) == 10000
        assert hasattr(c_vec, "vocabulary_")
        assert len(c_vec.vocabulary_) == 5000

    def test_scaler_parameters(self, artifacts):
        scaler = artifacts.scaler
        assert hasattr(scaler, "mean_")
        assert len(scaler.mean_) == 9
        assert getattr(scaler, "n_features_in_", 9) == 9


class TestPreprocessingDiscrepancyReport:
    """Tests and measures differences caused by removing numeric digits in lexical pipeline."""

    # Representative test inputs across different categories
    SAMPLE_EMAILS = [
        # Phishing with numeric account codes & dates
        (
            "Phishing with digits",
            "URGENT: Your account 98234471 has been locked on 10/30/2026. "
            "Call 1-800-555-0199 or click https://verify-bank.com/code999 immediately!",
        ),
        # Phishing without digits
        (
            "Phishing without digits",
            "CRITICAL SECURITY ALERT: Suspended mailbox access. "
            "Click here immediately to verify your email password and avoid termination.",
        ),
        # Legitimate corporate email with digits
        (
            "Legitimate with digits",
            "Hi team, attached is the Q3 financial summary for FY2026. "
            "Revenue reached $4.2M across 1,450 transactions. See page 12.",
        ),
        # Legitimate conversational email without digits
        (
            "Legitimate without digits",
            "Hello Nazlah, thanks for sending over the revised meeting schedule. "
            "Let us catch up after lunch in the conference room. Best regards.",
        ),
    ]

    def test_compare_original_vs_updated_lexical_pipeline(self, predictor):
        """Compare probabilities and classifications between original and updated preprocessing."""
        discrepancies = []

        for label, email in self.SAMPLE_EMAILS:
            # Predict with updated pipeline (remove_digits=True)
            res_updated = predictor.predict(email, override_remove_digits=True)

            # Predict with original Colab pipeline (remove_digits=False)
            res_original = predictor.predict(email, override_remove_digits=False)

            p_up = res_updated["phishing_probability"]
            p_orig = res_original["phishing_probability"]
            diff = abs(p_up - p_orig)

            classification_matched = (
                res_updated["classification"] == res_original["classification"]
            )

            discrepancies.append({
                "label": label,
                "p_updated": p_up,
                "p_original": p_orig,
                "diff": diff,
                "classification_updated": res_updated["classification"],
                "classification_original": res_original["classification"],
                "matched": classification_matched,
            })

            # Check that both returned valid probabilities
            assert 0.0 <= p_up <= 1.0
            assert 0.0 <= p_orig <= 1.0

            # On emails without digits, the outputs must be virtually identical
            if "without digits" in label:
                assert diff < 1e-4, f"Unexpected difference on text without digits: {diff}"

        # Ensure all test samples maintained the same final classification
        for d in discrepancies:
            assert d["matched"] is True, f"Classification flipped for {d['label']}"

