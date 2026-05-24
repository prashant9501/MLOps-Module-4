"""
Configuration for the SBERT News Search system.

This module defines all constants used across the search pipeline:
- Model selection and embedding dimensions
- Annoy index parameters (trees, metric, size)
- Relevance scoring thresholds
- Directory paths for data and model artifacts

Students: You do NOT need to modify this file. These values are pre-set
to match the provided model artifacts. Changing them will break the index.
"""

# ── Directory Paths ──────────────────────────────────────────────────
DATA_DIR = "data"
MODELS_DIR = "models"

# ── SBERT Model Configuration ────────────────────────────────────────
# all-MiniLM-L6-v2 is a lightweight, fast model that produces 384-dim
# embeddings. It offers a good balance of speed and quality for semantic
# search tasks. See: https://www.sbert.net/docs/pretrained_models.html
SENTENCE_TRANSFORMER_MODEL_TYPE = "all-MiniLM-L6-v2"

# ── Annoy Index Configuration ────────────────────────────────────────
# Annoy (Approximate Nearest Neighbors Oh Yeah) builds a forest of
# random projection trees for fast approximate similarity search.
#
# ANNOY_N_TREES: More trees = better accuracy but slower build time.
#   50 trees is a solid default for ~13k documents.
# ANNOY_METRIC: "euclidean" measures straight-line distance between
#   embedding vectors. Other options: "angular", "manhattan".
# ANNOY_SIZE: Must match the embedding dimension of the SBERT model.
#   all-MiniLM-L6-v2 produces 384-dimensional vectors.
SEARCH_INDEX_TYPE = "annoy"
ANNOY_N_TREES = 50
ANNOY_METRIC = "euclidean"
ANNOY_SIZE = 384

# ── Relevance Scoring ────────────────────────────────────────────────
# After retrieving nearest neighbors from the Annoy index, we compute
# cosine similarity between the query embedding and each result embedding.
# Results with cosine similarity below the threshold are filtered out.
#
# RELEVANCE_SCORE_THRESHOLD: Minimum cosine similarity to include a
#   result. 0.4 filters out loosely related articles.
# RELEVANCE_SCORE_ROUNDING: Decimal places for displayed scores.
RELEVANCE_SCORE_THRESHOLD = 0.4
RELEVANCE_SCORE_ROUNDING = 2

# ── Training Data Configuration ──────────────────────────────────────
# These settings control what text was used to build the index.
# TEXT_SECTION_TYPE=None means titles were indexed as whole strings
#   (not split into sentences or paragraphs).
# TRAIN_DATA_INPUT_TYPES=["title"] means only article titles were
#   embedded, not full article text.
TRAIN_DATA_INPUT_TYPES = ["title"]
TEXT_SECTION_TYPE = None

# ── Derived Constants (do not modify) ────────────────────────────────
# The index filename follows the pattern: {section_type}_{input_types}.annoy
# With TEXT_SECTION_TYPE=None and TRAIN_DATA_INPUT_TYPES=["title"],
# the files are named: None_title.annoy, None_title_ids.json, etc.
SEARCH_INDEX = f"{TEXT_SECTION_TYPE}_" + "_".join(TRAIN_DATA_INPUT_TYPES) + f".{SEARCH_INDEX_TYPE}"
