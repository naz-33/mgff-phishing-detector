"""Preprocessing pipeline for ZanderEtAlFishing.

Maintains two separate text representations:
1. Lightly cleaned / raw text branch: used exclusively for stylometric feature extraction.
2. Lexical TF-IDF branch: used for word-level and character-level TF-IDF extraction.
"""

import os
import re
from typing import Optional
import nltk
from nltk.corpus import stopwords
from nltk.stem import WordNetLemmatizer
from nltk.tokenize import word_tokenize

# Track if NLTK resources have been initialized
_NLTK_INITIALIZED = False
_STOPWORDS = None
_LEMMATIZER = None


def ensure_nltk_resources() -> None:
    """Ensure required NLTK resources are available locally without repeated downloads."""
    global _NLTK_INITIALIZED, _STOPWORDS, _LEMMATIZER
    if _NLTK_INITIALIZED:
        return

    required_resources = [
        ('tokenizers/punkt', 'punkt'),
        ('tokenizers/punkt_tab', 'punkt_tab'),
        ('corpora/stopwords', 'stopwords'),
        ('corpora/wordnet', 'wordnet'),
        ('corpora/omw-1.4', 'omw-1.4'),
        ('taggers/averaged_perceptron_tagger', 'averaged_perceptron_tagger'),
        ('taggers/averaged_perceptron_tagger_eng', 'averaged_perceptron_tagger_eng'),
    ]

    for path, package in required_resources:
        try:
            nltk.data.find(path)
        except (LookupError, IndexError):
            nltk.download(package, quiet=True)

    _STOPWORDS = set(stopwords.words('english'))
    _LEMMATIZER = WordNetLemmatizer()
    # Pre-warm lemmatizer and tagger cache so first inference latency is minimal
    _LEMMATIZER.lemmatize('test', 'n')
    nltk.pos_tag(['test'])
    _NLTK_INITIALIZED = True


def _get_stopwords():
    ensure_nltk_resources()
    return _STOPWORDS


def _get_lemmatizer():
    ensure_nltk_resources()
    return _LEMMATIZER


def get_wordnet_pos(nltk_tag: str) -> str:
    """Map NLTK POS tag to WordNet POS tag ('v' for verbs, 'n' for nouns/others)."""
    if nltk_tag.startswith('V'):
        return 'v'
    return 'n'


def clean_for_stylometrics(text: str) -> str:
    """Clean text lightly for stylometric feature extraction.

    Applies:
      - HTML tag removal.
      - Whitespace normalization.

    Preserves:
      - Uppercase and lowercase information.
      - Numeric digits.
      - Special characters and punctuation.
      - URLs and email addresses.
    """
    if not isinstance(text, str):
        raise TypeError(f"Input must be a string, got {type(text).__name__}")

    text = re.sub(r'<[^>]+>', ' ', text)
    text = re.sub(r'\s+', ' ', text)
    return text.strip()


def clean_lexical(
    text: str,
    remove_digits: bool = True,
    remove_special_characters: bool = True,
) -> str:
    """Clean and preprocess text for the lexical TF-IDF branches.

    Pipeline:
      1. HTML tag removal
      2. URL removal (regex)
      3. Email address removal (regex)
      4. Numeric digit removal (when remove_digits=True)
      5. Special-character removal (when remove_special_characters=True)
      6. Whitespace normalization
      7. Lowercasing
      8. Tokenization using NLTK word_tokenize
      9. English stop-word removal
      10. WordNet lemmatization with original POS-tag mapping
    """
    if not isinstance(text, str):
        raise TypeError(f"Input must be a string, got {type(text).__name__}")

    ensure_nltk_resources()
    lemmatizer = _get_lemmatizer()
    stop_words = _get_stopwords()

    # Step 1: HTML tag removal
    text = re.sub(r'<[^>]+>', ' ', text)

    # Step 2: URL removal
    text = re.sub(r'https?://\S+|www\.\S+', ' ', text)

    # Step 3: Email address removal
    text = re.sub(r'\S+@\S+', ' ', text)

    # Step 4: Numeric digit removal (isolated procedure)
    if remove_digits:
        text = re.sub(r'\d+', ' ', text)

    # Step 5: Special-character removal
    if remove_special_characters:
        if remove_digits:
            text = re.sub(r'[^a-zA-Z\s]', ' ', text)
        else:
            text = re.sub(r'[^a-zA-Z0-9\s]', ' ', text)

    # Step 6: Whitespace normalization
    text = re.sub(r'\s+', ' ', text).strip()

    # Step 7: Lowercasing
    text = text.lower()

    # Step 8: Tokenization
    tokens = word_tokenize(text)

    # Step 9: English stop-word removal
    tokens = [t for t in tokens if t not in stop_words]

    # Step 10: POS-tag guided lemmatization
    if tokens:
        tagged = nltk.pos_tag(tokens)
        tokens = [
            lemmatizer.lemmatize(tok, get_wordnet_pos(tag))
            for tok, tag in tagged
        ]

    return ' '.join(tokens)


def clean_lexical_original(text: str) -> str:
    """Original research training preprocessing (preserves numeric digits)."""
    return clean_lexical(text, remove_digits=False, remove_special_characters=True)
