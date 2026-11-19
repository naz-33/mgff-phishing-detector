"""Unit tests for preprocessing pipelines in ZanderEtAlFishing."""

import pytest
from ml_engine.preprocessing import (
    clean_for_stylometrics,
    clean_lexical,
    clean_lexical_original,
    ensure_nltk_resources,
)


def setup_module():
    ensure_nltk_resources()


class TestStylometricPreprocessing:
    """Tests for the lightly cleaned / raw text representation."""

    def test_html_tag_removal(self):
        text = "<html><body><p>Alert! Click <b>here</b> now.</p></body></html>"
        cleaned = clean_for_stylometrics(text)
        assert "<" not in cleaned
        assert ">" not in cleaned
        assert "Alert! Click here now." in cleaned

    def test_whitespace_normalization(self):
        text = "  URGENT:   Multiple    spaces\nand\ttabs.   "
        cleaned = clean_for_stylometrics(text)
        assert cleaned == "URGENT: Multiple spaces and tabs."

    def test_preserves_case_digits_and_punctuation(self):
        text = "WARNING: You have 3 UNREAD alerts! Visit https://bank.com or email alert@bank.com."
        cleaned = clean_for_stylometrics(text)
        assert "WARNING" in cleaned
        assert "3" in cleaned
        assert "!" in cleaned
        assert "https://bank.com" in cleaned
        assert "alert@bank.com" in cleaned

    def test_invalid_type_raises(self):
        with pytest.raises(TypeError):
            clean_for_stylometrics(12345)  # type: ignore


class TestLexicalPreprocessing:
    """Tests for the lexical TF-IDF representation."""

    def test_html_and_url_and_email_removal(self):
        text = "<p>Visit https://secure-bank.com/login or email security@bank.com immediately.</p>"
        cleaned = clean_lexical(text)
        assert "https" not in cleaned
        assert "secure-bank" not in cleaned
        assert "bank.com" not in cleaned
        assert "@" not in cleaned
        assert "<p>" not in cleaned

    def test_numeric_digit_removal_in_updated_pipeline(self):
        text = "Your account 987654 had 3 failed logins on October 30th 2026."
        cleaned = clean_lexical(text, remove_digits=True)
        # Verify no digits remain
        assert not any(char.isdigit() for char in cleaned)
        assert "account" in cleaned
        assert "fail" in cleaned or "failed" in cleaned

    def test_special_character_removal_in_updated_pipeline(self):
        text = "URGENT!!! Account #123 $$$ suspended & locked [action required]???"
        cleaned = clean_lexical(text, remove_digits=True, remove_special_characters=True)
        assert "!" not in cleaned
        assert "?" not in cleaned
        assert "#" not in cleaned
        assert "$" not in cleaned
        assert "[" not in cleaned
        assert "]" not in cleaned

    def test_original_pipeline_preserves_digits(self):
        text = "Reference code 999 123 verified"
        cleaned_orig = clean_lexical_original(text)
        # Original Colab pipeline preserves alphanumeric digits
        assert "999" in cleaned_orig
        assert "123" in cleaned_orig

        # But updated pipeline removes digits
        cleaned_updated = clean_lexical(text, remove_digits=True)
        assert "999" not in cleaned_updated
        assert "123" not in cleaned_updated

    def test_lowercasing_and_stopword_removal(self):
        text = "This is a serious notification from the department"
        cleaned = clean_lexical(text)
        # 'this', 'is', 'a', 'from', 'the' are English stopwords
        words = cleaned.split()
        assert "this" not in words
        assert "is" not in words
        assert "the" not in words
        assert "serious" in words
        assert "notification" in words

    def test_wordnet_lemmatization(self):
        text = "running accounts suspended"
        cleaned = clean_lexical(text)
        # 'running' verb -> 'run', 'accounts' noun -> 'account', 'suspended' verb -> 'suspend'
        words = cleaned.split()
        assert "run" in words
        assert "account" in words
        assert "suspend" in words

    def test_invalid_type_raises(self):
        with pytest.raises(TypeError):
            clean_lexical(None)  # type: ignore

