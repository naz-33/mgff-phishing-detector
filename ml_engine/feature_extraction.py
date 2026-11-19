"""Multi-granularity feature extraction and fusion for ZanderEtAlFishing.

Extracts three feature groups:
1. Word-level TF-IDF (10,000 max features, n-gram range (1, 2), sublinear TF)
2. Character-level TF-IDF (5,000 max features, n-gram range (3, 5), sublinear TF)
3. 9 Scaled Stylometric Features computed on lightly cleaned/raw text

Fuses into CSR sparse matrix: [Word TF-IDF | Character TF-IDF | Scaled Stylometric Features]
Total dimensionality: 10,000 + 5,000 + 9 = 15,009 features.
"""

import math
import re
from typing import List, Sequence, Union
import numpy as np
import scipy.sparse as sp

# 16 domain urgency keywords from the original research
URGENCY_WORDS = {
    'urgent',
    'immediately',
    'verify',
    'suspended',
    'click',
    'password',
    'security',
    'alert',
    'expire',
    'action',
    'required',
    'login',
    'bank',
    'confirm',
    'final',
    'notice',
}

EXPECTED_FEATURE_DIM = 15009
STYLO_FEATURE_NAMES = [
    'char_count',
    'word_count',
    'uppercase_ratio',
    'exclamation_count',
    'question_count',
    'numeric_ratio',
    'url_count',
    'urgency_density',
    'shannon_entropy',
]


def extract_stylometrics_row(text: str) -> List[float]:
    """Compute the 9 stylometric features for a single text in exact research order."""
    text_str = str(text)
    words = text_str.split()
    word_count = len(words) + 1e-5
    char_count = len(text_str) + 1e-5

    # Character-level Shannon entropy
    prob = [float(text_str.count(c)) / char_count for c in set(text_str)]
    entropy = -sum([p * math.log(p, 2) for p in prob]) if prob else 0.0

    return [
        char_count,
        word_count,
        sum(1 for c in text_str if c.isupper()) / char_count,
        float(text_str.count('!')),
        float(text_str.count('?')),
        sum(1 for c in text_str if c.isdigit()) / char_count,
        float(len(re.findall(r'https?://\S+|www\.\S+', text_str))),
        sum(1 for w in words if w.lower() in URGENCY_WORDS) / word_count,
        entropy,
    ]


def extract_stylometrics(texts: Union[str, Sequence[str]]) -> np.ndarray:
    """Extract 9 stylometric features for one or multiple texts.

    Returns:
        np.ndarray of shape (N, 9) where N is number of samples.
    """
    if isinstance(texts, str):
        texts = [texts]

    matrix = [extract_stylometrics_row(t) for t in texts]
    return np.array(matrix, dtype=np.float64)


def fuse_features(
    word_vectorizer,
    char_vectorizer,
    scaler,
    lexical_text: Union[str, Sequence[str]],
    raw_text: Union[str, Sequence[str]],
) -> sp.csr_matrix:
    """Transform and fuse lexical and stylometric features.

    Parameters:
        word_vectorizer: Fitted TfidfVectorizer for word-level n-grams
        char_vectorizer: Fitted TfidfVectorizer for char-level n-grams
        scaler: Fitted StandardScaler for stylometric features
        lexical_text: Cleaned text(s) for TF-IDF branches
        raw_text: Lightly cleaned / raw text(s) for stylometric branch

    Returns:
        scipy.sparse.csr_matrix of shape (N, 15009)
    """
    if isinstance(lexical_text, str):
        lexical_text = [lexical_text]
    if isinstance(raw_text, str):
        raw_text = [raw_text]

    if len(lexical_text) != len(raw_text):
        raise ValueError(
            f"Length mismatch: lexical ({len(lexical_text)}) vs raw ({len(raw_text)})"
        )

    # 1. Word TF-IDF
    w_tfidf = word_vectorizer.transform(lexical_text)

    # 2. Character TF-IDF
    c_tfidf = char_vectorizer.transform(lexical_text)

    # 3. Scaled Stylometric Features
    raw_stylo = extract_stylometrics(raw_text)
    scaled_stylo = scaler.transform(raw_stylo)
    scaled_stylo_csr = sp.csr_matrix(scaled_stylo)

    # 4. Fusion in exact order: [Word TF-IDF | Char TF-IDF | Scaled Stylometrics]
    fused = sp.hstack([w_tfidf, c_tfidf, scaled_stylo_csr], format='csr')

    if fused.shape[1] != EXPECTED_FEATURE_DIM:
        raise ValueError(
            f"Feature dimension mismatch: expected {EXPECTED_FEATURE_DIM}, got {fused.shape[1]}"
        )

    return fused

