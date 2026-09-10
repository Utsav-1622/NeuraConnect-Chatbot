"""Deterministic English text preprocessing built on NLTK."""

from __future__ import annotations

from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path
import re

import nltk
from nltk.corpus import stopwords
from nltk.stem import PorterStemmer
from nltk.tokenize import wordpunct_tokenize


# NLTK rejects writable shared mounts as unsafe download locations.  Use a
# dynamically resolved private user directory rather than a machine-specific path.
NLTK_DATA_DIR = Path.home() / "nltk_data"
_STOPWORDS_RESOURCE = "corpora/stopwords"
_PUNCTUATION_TRANSLATION = str.maketrans({"’": "'", "‘": "'", "–": "-", "—": "-"})
_STEMMER = PorterStemmer()


@dataclass(frozen=True)
class PreprocessingResult:
    """Text representations retained for later NLP and retrieval components."""

    original_text: str | None
    normalized_text: str
    tokens: tuple[str, ...]
    filtered_tokens: tuple[str, ...]
    stemmed_tokens: tuple[str, ...]

    @property
    def normalized_tokens(self) -> tuple[str, ...]:
        """Return the stemmed representation used by lightweight text matching."""
        return self.stemmed_tokens


def _configure_nltk_data_path() -> None:
    NLTK_DATA_DIR.mkdir(parents=True, exist_ok=True)
    NLTK_DATA_DIR.chmod(0o700)
    path_string = str(NLTK_DATA_DIR)
    if path_string not in nltk.data.path:
        nltk.data.path.insert(0, path_string)


@lru_cache(maxsize=1)
def ensure_nltk_resources() -> None:
    """Ensure the NLTK English stopword corpus is installed and usable once per process."""
    _configure_nltk_data_path()
    try:
        nltk.data.find(_STOPWORDS_RESOURCE)
    except LookupError:
        downloaded = nltk.download("stopwords", download_dir=str(NLTK_DATA_DIR), quiet=True)
        if not downloaded:
            raise RuntimeError("Unable to download the NLTK English stopword corpus.")
        try:
            nltk.data.find(_STOPWORDS_RESOURCE)
        except LookupError as error:
            raise RuntimeError("The NLTK stopword corpus could not be initialized.") from error


def normalize_text(text: str | None) -> str:
    """Normalize optional customer text while retaining meaningful punctuation."""
    if text is None:
        return ""
    if not isinstance(text, str):
        raise TypeError("text must be a string or None")
    return re.sub(r"\s+", " ", text.translate(_PUNCTUATION_TRANSLATION).strip().lower())


def preprocess_text(text: str | None) -> PreprocessingResult:
    """Return NLTK-tokenized, stopword-filtered, and stemmed English text."""
    ensure_nltk_resources()
    normalized_text = normalize_text(text)
    tokens = tuple(wordpunct_tokenize(normalized_text))
    english_stopwords = frozenset(stopwords.words("english"))
    filtered_tokens = tuple(
        token for token in tokens if token.isalnum() and token not in english_stopwords
    )
    stemmed_tokens = tuple(_STEMMER.stem(token) for token in filtered_tokens)
    return PreprocessingResult(
        original_text=text,
        normalized_text=normalized_text,
        tokens=tokens,
        filtered_tokens=filtered_tokens,
        stemmed_tokens=stemmed_tokens,
    )
