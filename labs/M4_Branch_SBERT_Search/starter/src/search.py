"""
Semantic Search Engine for SBERT News Search.

This module implements the core search logic:
  1. Preprocess the user's query text (lowercase, lemmatize, etc.)
  2. Generate a 384-dim embedding using SBERT
  3. Search the Annoy index for the k nearest neighbors
  4. Compute cosine similarity between query and each result
  5. Filter out results below the relevance threshold (0.4)
  6. Return ranked results with article metadata

Students: You do NOT need to modify this file. It is called by server.py
when the /search endpoint receives a request.
"""

import os
import json
import numpy as np
import pandas as pd

from src import preprocessor
from src import embeddings
from src import build_index
from src import config


# ── Load the article lookup table ────────────────────────────────────
# This CSV contains the original article data (titles, categories) so we
# can return metadata alongside search results.
_PROCESSED_CSV = os.path.join(
    config.DATA_DIR, "processed",
    f"{config.TEXT_SECTION_TYPE}_{'_'.join(config.TRAIN_DATA_INPUT_TYPES)}_processed.csv"
)

_RAW_CSV = os.path.join(config.DATA_DIR, "raw", "raw.csv")

# We try the raw CSV for full article metadata; fall back to processed
_article_lookup = {}

def _load_article_lookup():
    """Load article metadata (title, category, subcategory) into a dict."""
    global _article_lookup
    if os.path.exists(_RAW_CSV):
        df = pd.read_csv(_RAW_CSV)
        df = df[["article_id", "title", "text", "category", "subcategory"]]
        df.index = df.article_id
        _article_lookup = df[["title", "text", "category", "subcategory"]].drop_duplicates().to_dict(orient="index")
        print(f"Article lookup loaded: {len(_article_lookup)} articles from raw.csv")
    else:
        print(f"WARNING: {_RAW_CSV} not found. Article metadata will be unavailable.")

# Load on import
_load_article_lookup()


def _compute_cosine_similarity(v1, v2):
    """
    Compute cosine similarity between two vectors.

    Cosine similarity measures the angle between two vectors:
      - 1.0 = identical direction (very similar meaning)
      - 0.0 = perpendicular (unrelated)
      - -1.0 = opposite direction (opposite meaning, rare in practice)

    Parameters
    ----------
    v1 : np.ndarray
        First vector (e.g., query embedding).
    v2 : np.ndarray
        Second vector (e.g., article embedding).

    Returns
    -------
    float
        Cosine similarity rounded to RELEVANCE_SCORE_ROUNDING decimal places.
    """
    v1 = np.asarray(v1)
    v2 = np.asarray(v2)
    dot_product = np.dot(v1, v2)
    norm_product = np.linalg.norm(v1) * np.linalg.norm(v2)
    if norm_product == 0:
        return 0.0
    return round(float(dot_product / norm_product), config.RELEVANCE_SCORE_ROUNDING)


def _get_article_embedding(article_id):
    """
    Get the embedding for an article by re-encoding its title.

    This is used to compute cosine similarity between the query and
    each candidate result. We preprocess the title and embed it fresh.

    Parameters
    ----------
    article_id : int
        The article's ID in the lookup table.

    Returns
    -------
    list of float
        The 384-dim embedding of the article's preprocessed title.
    """
    if article_id not in _article_lookup:
        return None
    title = _article_lookup[article_id]["title"]
    preprocessed = preprocessor.preprocess_text(title)
    emb = embeddings.get_embeddings([preprocessed])
    return emb[0]


def search(index, queries, k, ids_mapper, sections_stats):
    """
    Search the index for articles relevant to the given queries.

    This is the main search function called by server.py. It:
      1. Determines how many candidates to fetch (based on section stats)
      2. Preprocesses each query
      3. Generates query embeddings
      4. Searches the Annoy index for nearest neighbors
      5. Computes cosine similarity and filters by threshold
      6. Returns results with article metadata

    Parameters
    ----------
    index : annoy.AnnoyIndex
        The loaded Annoy index.
    queries : list of str
        One or more search queries (e.g., ["carbon emissions"]).
    k : int
        Number of results to return per query.
    ids_mapper : dict
        Contains "section_id_to_article_id" mapping from the JSON file.
    sections_stats : dict
        Statistics about sections per article (mean, std) used to
        determine how many extra candidates to fetch.

    Returns
    -------
    list of dict
        Each dict has "query" (str) and "results" (list of dicts with
        article_id, score, title, category, subcategory).
    """
    # Fetch extra candidates to account for duplicates and filtered results
    stats_mean = sections_stats.get("mean", 1)
    stats_std = sections_stats.get("std", 0)
    _k = max(k, int(stats_mean + stats_std) * k)

    # Preprocess all queries
    preprocessed_queries = [preprocessor.preprocess_text(q) for q in queries]

    # Generate embeddings for all queries at once
    query_embeddings = embeddings.get_embeddings(preprocessed_queries)

    # Search the Annoy index for each query embedding
    section_to_article = ids_mapper.get("section_id_to_article_id", {})

    all_results = []
    for i, query_emb in enumerate(query_embeddings):
        # Get nearest neighbors from Annoy
        candidates = build_index.search_annoy_index(
            index, query_emb, _k, ids_lookup=section_to_article
        )

        # Build results for this query, filtering by cosine similarity
        query_result = {"query": queries[i], "results": []}
        seen_articles = set()

        for article_id, distance in candidates:
            # Stop if we have enough results
            if len(query_result["results"]) >= k:
                break

            # Skip duplicate articles
            if article_id in seen_articles:
                continue

            # Compute cosine similarity between query and article embeddings
            article_emb = _get_article_embedding(int(article_id))
            if article_emb is None:
                continue

            score = _compute_cosine_similarity(query_embeddings[i], article_emb)

            # Filter by relevance threshold
            if score < config.RELEVANCE_SCORE_THRESHOLD:
                continue

            # Look up article metadata
            aid = int(article_id)
            title = _article_lookup.get(aid, {}).get("title", "Unknown")
            category = _article_lookup.get(aid, {}).get("category", "Unknown")
            subcategory = _article_lookup.get(aid, {}).get("subcategory", "Unknown")

            query_result["results"].append({
                "article_id": aid,
                "score": score,
                "title": title,
                "category": category,
                "subcategory": subcategory,
            })
            seen_articles.add(article_id)

        all_results.append(query_result)

    return all_results
