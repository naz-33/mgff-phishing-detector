"""Unit tests for the hybrid predictor and reusable predict_email function."""

import math
import pytest
from ml_engine.model_loader import ModelLoader
from ml_engine.predictor import PhishingPredictor, predict_email


@pytest.fixture(scope="module")
def predictor():
    return PhishingPredictor()


class TestPredictorInputValidation:
    """Tests for input validation and error handling."""

    def test_invalid_types_raise_type_error(self, predictor):
        with pytest.raises(TypeError):
            predictor.predict(12345)  # type: ignore
        with pytest.raises(TypeError):
            predictor.predict(None)  # type: ignore
        with pytest.raises(TypeError):
            predict_email(["email line 1", "email line 2"])  # type: ignore

    def test_empty_input_raises_value_error(self, predictor):
        with pytest.raises(ValueError):
            predictor.predict("")
        with pytest.raises(ValueError):
            predictor.predict("   \n\t  ")
        with pytest.raises(ValueError):
            predict_email("")


class TestPredictorOutputSchema:
    """Tests verifying output dictionary schema and datatypes."""

    def test_output_schema_keys_and_types(self, predictor):
        sample_email = "URGENT: Please verify your bank login at https://secure-bank.example.com immediately!"
        res = predictor.predict(sample_email)

        # Check all required keys exist
        required_keys = [
            "prediction",
            "classification",
            "risk_tier",
            "phishing_probability",
            "logistic_regression_probability",
            "lightgbm_probability",
            "ensemble_weights",
            "threshold",
            "high_confidence_threshold",
            "inference_time_ms",
            "model_version",
        ]
        for key in required_keys:
            assert key in res, f"Missing key: {key}"

        # Check types
        assert isinstance(res["prediction"], int)
        assert res["prediction"] in (0, 1)
        assert res["classification"] in ("Phishing", "Legitimate")
        assert res["risk_tier"] in ("Legitimate", "Suspicious", "High-Confidence Phishing")
        assert isinstance(res["phishing_probability"], float)
        assert isinstance(res["logistic_regression_probability"], float)
        assert isinstance(res["lightgbm_probability"], float)
        assert isinstance(res["ensemble_weights"], dict)
        assert "logistic_regression" in res["ensemble_weights"]
        assert "lightgbm" in res["ensemble_weights"]
        assert isinstance(res["threshold"], float)
        assert isinstance(res["high_confidence_threshold"], float)
        assert isinstance(res["inference_time_ms"], float)
        assert isinstance(res["model_version"], str)

        # Value bounds
        assert 0.0 <= res["phishing_probability"] <= 1.0
        assert 0.0 <= res["logistic_regression_probability"] <= 1.0
        assert 0.0 <= res["lightgbm_probability"] <= 1.0
        assert res["inference_time_ms"] > 0.0
        assert math.isfinite(res["inference_time_ms"])

    def test_reusable_predict_email_function(self):
        sample = "Hi team, please find attached the weekly report."
        res = predict_email(sample)
        assert "prediction" in res
        assert "phishing_probability" in res


class TestEnsembleBlendingAndThreshold:
    """Tests for exact 50/50 probability blending and threshold decision logic."""

    def test_exact_50_50_probability_blend(self, predictor):
        sample_email = "Action required: Security update needed for your payroll account."
        res = predictor.predict(sample_email)

        lr_p = res["logistic_regression_probability"]
        lgb_p = res["lightgbm_probability"]
        expected_blend = round(0.50 * lr_p + 0.50 * lgb_p, 4)

        assert pytest.approx(res["phishing_probability"], abs=1e-4) == expected_blend
        assert res["ensemble_weights"]["logistic_regression"] == 0.50
        assert res["ensemble_weights"]["lightgbm"] == 0.50

    def test_threshold_decision_logic(self, predictor):
        sample_email = "Your account is suspended. Verify password now."
        res = predictor.predict(sample_email)

        if res["phishing_probability"] >= 0.50:
            assert res["prediction"] == 1
            assert res["classification"] == "Phishing"
        else:
            assert res["prediction"] == 0
            assert res["classification"] == "Legitimate"

    def test_three_tier_risk_classification(self, predictor):
        sample_email = "Important security update: Please review your profile settings."

        # Case 1: Legitimate (override threshold to 0.99 so p < threshold)
        res_legit = predictor.predict(sample_email, override_threshold=0.99, override_high_confidence_threshold=0.999)
        assert res_legit["classification"] == "Legitimate"
        assert res_legit["risk_tier"] == "Legitimate"

        # Case 2: Suspicious (override threshold to 0.01 and high_confidence to 0.99 so 0.01 <= p < 0.99)
        res_susp = predictor.predict(sample_email, override_threshold=0.01, override_high_confidence_threshold=0.99)
        assert res_susp["classification"] == "Phishing"
        assert res_susp["risk_tier"] == "Suspicious"

        # Case 3: High-Confidence Phishing (override both to 0.01 so p >= high_confidence)
        res_high = predictor.predict(sample_email, override_threshold=0.01, override_high_confidence_threshold=0.01)
        assert res_high["classification"] == "Phishing"
        assert res_high["risk_tier"] == "High-Confidence Phishing"

    def test_repeatable_predictions(self, predictor):
        sample_email = "URGENT notice from your bank administrator."
        res1 = predictor.predict(sample_email)
        res2 = predictor.predict(sample_email)

        assert res1["prediction"] == res2["prediction"]
        assert res1["phishing_probability"] == res2["phishing_probability"]
        assert res1["logistic_regression_probability"] == res2["logistic_regression_probability"]
        assert res1["lightgbm_probability"] == res2["lightgbm_probability"]


class TestModelLoaderErrors:
    """Tests error handling for missing model artifacts."""

    def test_missing_directory_raises(self, tmp_path):
        with pytest.raises(FileNotFoundError):
            ModelLoader.load_artifacts(models_dir=str(tmp_path / "non_existent"))

    def test_missing_artifact_file_raises(self, tmp_path):
        empty_dir = tmp_path / "empty_models"
        empty_dir.mkdir()
        with pytest.raises(FileNotFoundError):
            ModelLoader.load_artifacts(models_dir=str(empty_dir))

