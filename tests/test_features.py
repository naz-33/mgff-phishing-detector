"""Unit tests for multi-granularity feature extraction and fusion."""

import numpy as np
import pytest
import scipy.sparse as sp
from ml_engine.feature_extraction import (
    EXPECTED_FEATURE_DIM,
    STYLO_FEATURE_NAMES,
    URGENCY_WORDS,
    extract_stylometrics,
    fuse_features,
)
from ml_engine.model_loader import ModelLoader


@pytest.fixture(scope="module")
def artifacts():
    return ModelLoader.load_artifacts()


class TestStylometricFeatureExtraction:
    """Tests for the 9 stylometric features."""

    def test_feature_count_and_names(self):
        assert len(STYLO_FEATURE_NAMES) == 9
        feats = extract_stylometrics("Hello World")
        assert feats.shape == (1, 9)

    def test_feature_order_and_synthetic_values(self):
        # Construct synthetic text with known properties:
        # 1 word: "ABC!?"
        # char_count: 5 + 1e-5
        # word_count: 1 + 1e-5
        # uppercase: 3 ('A', 'B', 'C') -> 3 / (5 + 1e-5)
        # exclamation: 1
        # question: 1
        # digits: 0
        # urls: 0
        # urgency: 0
        text = "ABC!?"
        feats = extract_stylometrics(text)[0]

        assert pytest.approx(feats[0], abs=1e-4) == 5.0  # char count
        assert pytest.approx(feats[1], abs=1e-4) == 1.0  # word count
        assert pytest.approx(feats[2], abs=1e-4) == 3.0 / 5.0  # uppercase ratio
        assert feats[3] == 1.0  # exclamation count
        assert feats[4] == 1.0  # question count
        assert feats[5] == 0.0  # digit ratio
        assert feats[6] == 0.0  # url count
        assert feats[7] == 0.0  # urgency density
        assert feats[8] > 0.0  # Shannon entropy

    def test_digits_and_urgency_words(self):
        text = "urgent 12345"
        feats = extract_stylometrics(text)[0]
        # 'urgent' is in URGENCY_WORDS
        # 5 digits out of 12 chars
        assert feats[5] > 0.0  # digit ratio
        assert feats[7] > 0.0  # urgency keyword density

    def test_url_detection_in_stylometrics(self):
        text = "Check http://example.com and https://secure.org/now"
        feats = extract_stylometrics(text)[0]
        assert feats[6] == 2.0  # URL count

    def test_batch_extraction(self):
        texts = ["First email text", "Second email text with http://link.com"]
        feats = extract_stylometrics(texts)
        assert feats.shape == (2, 9)


class TestFeatureFusion:
    """Tests for vectorizer transforms and feature fusion."""

    def test_vectorizer_dimensions(self, artifacts):
        w_vec = artifacts.word_vectorizer
        c_vec = artifacts.char_vectorizer
        scaler = artifacts.scaler

        sample_lexical = "urgent security alert verify account immediately"
        sample_raw = "URGENT: Security alert! Verify account immediately."

        w_feat = w_vec.transform([sample_lexical])
        c_feat = c_vec.transform([sample_lexical])
        stylo = extract_stylometrics(sample_raw)
        scaled_stylo = scaler.transform(stylo)

        assert w_feat.shape == (1, 10000)
        assert c_feat.shape == (1, 5000)
        assert scaled_stylo.shape == (1, 9)

    def test_fused_matrix_shape_and_type(self, artifacts):
        sample_lexical = "urgent security alert verify account immediately"
        sample_raw = "URGENT: Security alert! Verify account immediately."

        fused = fuse_features(
            word_vectorizer=artifacts.word_vectorizer,
            char_vectorizer=artifacts.char_vectorizer,
            scaler=artifacts.scaler,
            lexical_text=sample_lexical,
            raw_text=sample_raw,
        )

        assert sp.issparse(fused)
        assert isinstance(fused, sp.csr_matrix)
        assert fused.shape == (1, EXPECTED_FEATURE_DIM)
        assert fused.shape[1] == 15009

    def test_classifiers_accept_fused_features(self, artifacts):
        sample_lexical = "meeting notes project plan update"
        sample_raw = "Hi, here are the meeting notes and project plan."

        fused = fuse_features(
            word_vectorizer=artifacts.word_vectorizer,
            char_vectorizer=artifacts.char_vectorizer,
            scaler=artifacts.scaler,
            lexical_text=sample_lexical,
            raw_text=sample_raw,
        )

        lr_proba = artifacts.logistic_regression.predict_proba(fused)
        lgb_proba = artifacts.lightgbm.predict_proba(fused)

        assert lr_proba.shape == (1, 2)
        assert lgb_proba.shape == (1, 2)

