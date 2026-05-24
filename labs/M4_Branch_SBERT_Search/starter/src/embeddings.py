"""
SBERT Embedding Generation for News Search.

This module loads the Sentence-BERT model and provides a function to
generate dense vector embeddings from text. The model (all-MiniLM-L6-v2)
maps any text string to a 384-dimensional vector.

How it works:
  1. The SentenceTransformer model is loaded once at import time.
  2. When get_embeddings() is called, it passes texts through the
     transformer and returns a list of 384-dim vectors.
  3. These vectors can be compared using cosine similarity -- texts
     with similar meanings produce vectors that point in similar directions.

Students: You do NOT need to modify this file. It is used by the search
module to embed preprocessed queries.
"""

from sentence_transformers import SentenceTransformer
from src.config import SENTENCE_TRANSFORMER_MODEL_TYPE

# Load the SBERT model once at module import time.
# The first time this runs, it downloads ~90 MB from HuggingFace.
# Subsequent runs use the cached model from ~/.cache/huggingface/
print(f"Loading SBERT model: {SENTENCE_TRANSFORMER_MODEL_TYPE} ...")
model = SentenceTransformer(SENTENCE_TRANSFORMER_MODEL_TYPE)
print("SBERT model loaded successfully.")


def get_embeddings(texts):
    """
    Generate 384-dimensional embeddings for a list of text strings.

    Parameters
    ----------
    texts : list of str
        One or more text strings to embed. Each string should already be
        preprocessed (lowercased, stopwords removed, lemmatized).

    Returns
    -------
    list of list of float
        A list where each element is a 384-dimensional embedding vector.

    Example
    -------
    >>> embeddings = get_embeddings(["climate change policy"])
    >>> len(embeddings)       # 1 text -> 1 embedding
    1
    >>> len(embeddings[0])    # 384-dimensional vector
    384
    """
    embeddings = model.encode(texts, show_progress_bar=False, device="cpu")
    return embeddings.tolist()
