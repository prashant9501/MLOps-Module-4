"""
Text Preprocessing Pipeline for SBERT News Search.

This module cleans and normalises raw text before it is passed to the
SBERT model for embedding generation. The pipeline follows these steps:

  1. Separate camelCase words  ("BigData" -> "Big Data")
  2. Lowercase                 ("Big Data" -> "big data")
  3. Remove non-alphanumeric   ("big data!" -> "big data")
  4. Remove digits             ("data 2024" -> "data")
  5. Fix whitespace            (collapse multiple spaces)
  6. Remove stopwords          ("the big data" -> "big data")
  7. Tokenize with spaCy       (split into tokens)
  8. Lemmatize with spaCy      ("running" -> "run")

Students: You do NOT need to modify this file. It is used by the search
module to preprocess queries before generating embeddings.
"""

import re
import spacy
from spacy.lang.en.stop_words import STOP_WORDS as spacy_stop_words
import nltk

# Download NLTK stopwords on first import (needed inside Docker)
nltk.download("stopwords", quiet=True)
from nltk.corpus import stopwords as nltk_stop_words

# Combine spaCy and NLTK stopword lists for comprehensive coverage
STOP_WORDS = set(spacy_stop_words).union(set(nltk_stop_words.words("english")))

# Load the small English spaCy model for tokenization and lemmatization
# This model is ~12 MB and supports tokenization, POS tagging, and lemmas
SPACY_NLP = spacy.load("en_core_web_sm")


def separate_camelcase_words(text):
    """
    Insert a space before each capital letter that follows a lowercase letter.

    Example: "BigDataAnalytics" -> "Big Data Analytics"

    Parameters
    ----------
    text : str
        Input text that may contain camelCase words.

    Returns
    -------
    str
        Text with spaces inserted between camelCase boundaries.
    """
    return re.sub(r"([a-z])([A-Z])", r"\1 \2", text)


def lowercase(text):
    """Convert text to lowercase."""
    return text.lower()


def remove_non_alphanumeric(text):
    """
    Remove all characters except letters, digits, percent signs, and spaces.

    Example: "GDP growth: +3.5%!" -> "GDP growth 35"
    """
    return re.sub(r"[^a-zA-Z0-9% \n]+", "", text)


def remove_digits(text):
    """Remove all digit characters from text."""
    return re.sub(r"\d+", "", text)


def fix_whitespace(text):
    """Collapse multiple spaces into a single space on each line."""
    return "\n".join(" ".join(text.split()).split("\n"))


def remove_stopwords(text):
    """
    Remove common English stopwords (e.g., "the", "is", "at", "which").

    Uses the union of spaCy and NLTK stopword lists for broad coverage.
    """
    words = text.lower().split()
    filtered = [word for word in words if word not in STOP_WORDS]
    return " ".join(filtered)


def spacy_tokenize(text):
    """Tokenize text using spaCy and rejoin as a space-separated string."""
    doc = SPACY_NLP(text)
    return " ".join([token.text for token in doc])


def spacy_lemmatize(text):
    """
    Lemmatize text using spaCy to find root forms of words.

    Example: "running companies" -> "run company"
    """
    doc = SPACY_NLP(text)
    return " ".join([token.lemma_ for token in doc])


def preprocess_text(text):
    """
    Apply the full preprocessing pipeline to a text string.

    This is the main entry point used by the search module. The pipeline:
      1. Separate camelCase words
      2. Lowercase
      3. Remove non-alphanumeric characters
      4. Remove digits
      5. Fix whitespace
      6. Remove stopwords
      7. Tokenize (spaCy)
      8. Lemmatize (spaCy)

    Parameters
    ----------
    text : str
        Raw input text (e.g., an article title or search query).

    Returns
    -------
    str
        Cleaned, lemmatized text ready for embedding generation.
    """
    text = str(text)
    text = separate_camelcase_words(text)
    text = lowercase(text)
    text = remove_non_alphanumeric(text)
    text = remove_digits(text)
    text = fix_whitespace(text)
    text = remove_stopwords(text)
    text = spacy_tokenize(text)
    text = spacy_lemmatize(text)
    return text
