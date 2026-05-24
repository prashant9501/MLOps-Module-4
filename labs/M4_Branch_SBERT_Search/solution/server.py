"""
SBERT News Search API -- Complete Solution
Module 4 Branch Project: Search Relevancy with SBERT

Business Context:
    NewsWire India aggregates 12,972 news articles across 13 categories.
    This API provides semantic search -- given a natural-language query,
    it returns the most relevant articles ranked by meaning similarity.

Architecture:
    query -> preprocess -> SBERT embed -> Annoy index -> cosine filter -> results

Endpoints:
    GET  /ping    -> Health check (returns status and timestamp)
    POST /search  -> Search articles (accepts JSON with "query" and "k")

How to test:
    curl http://localhost:5001/ping
    curl -X POST http://localhost:5001/search \\
      -H "Content-Type: application/json" \\
      -d '{"query": ["artificial intelligence"], "k": 5}'
"""

from flask import Flask, request, jsonify
import json
import os
from datetime import datetime

# Import search modules
from src.config import ANNOY_SIZE, ANNOY_METRIC, SEARCH_INDEX, MODELS_DIR, TEXT_SECTION_TYPE, TRAIN_DATA_INPUT_TYPES
from src.search import search as semantic_search
from src.build_index import load_annoy_index

app = Flask(__name__)

# ── Global variables (loaded at startup) ─────────────────────────────
index = None
ids_mapper = None
stats = None


def load_artifacts():
    """
    Load all model artifacts needed for search.

    Loads the Annoy index, ID mapper, and section statistics from the
    models/ directory. These files must exist before the server starts.
    """
    global index, ids_mapper, stats

    # Construct file paths from config constants
    index_path = os.path.join(MODELS_DIR, SEARCH_INDEX)
    ids_path = os.path.join(
        MODELS_DIR,
        f"{TEXT_SECTION_TYPE}_{'_'.join(TRAIN_DATA_INPUT_TYPES)}_ids.json"
    )
    stats_path = os.path.join(
        MODELS_DIR,
        f"{TEXT_SECTION_TYPE}_{'_'.join(TRAIN_DATA_INPUT_TYPES)}_stats.json"
    )

    # Load the Annoy index from disk
    index = load_annoy_index(index_path)
    print(f"Annoy index loaded from {index_path}")

    # Load the ID mapper (section_id -> article_id)
    with open(ids_path, "r") as f:
        ids_mapper = json.load(f)
    print(f"ID mapper loaded from {ids_path}")

    # Load section statistics (used to tune candidate retrieval count)
    with open(stats_path, "r") as f:
        raw_stats = json.load(f)
    stats = raw_stats["sections_by_article"]
    print(f"Section stats loaded from {stats_path}")

    print("All artifacts loaded successfully!")


@app.route("/ping", methods=["GET"])
def ping():
    """
    Health check endpoint.

    Returns a JSON response confirming the server is running,
    along with the current timestamp.
    """
    return jsonify({
        "status": "healthy",
        "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
    })


@app.route("/search", methods=["POST"])
def search_endpoint():
    """
    Search for relevant news articles.

    Accepts a JSON body with:
        - "query": list of search strings (e.g., ["carbon emissions"])
        - "k": number of results to return per query (e.g., 5)

    Returns a JSON list of results, each containing:
        - query: the original search term
        - results: list of {article_id, score, title, category, subcategory}
    """
    # Parse the JSON request body
    req = request.get_json()

    # Validate required fields
    if req is None or "query" not in req or "k" not in req:
        return jsonify({"error": "Missing 'query' or 'k' in request body"}), 400

    query = req["query"]
    k = int(req["k"])

    # Validate types
    if not isinstance(query, list) or len(query) == 0:
        return jsonify({"error": "'query' must be a non-empty list of strings"}), 400
    if k < 1:
        return jsonify({"error": "'k' must be a positive integer"}), 400

    # Run semantic search
    results = semantic_search(index, query, k, ids_mapper, stats)

    # Return results as JSON
    return jsonify(results)


if __name__ == "__main__":
    # Load model artifacts before starting the server
    load_artifacts()

    # Start the Flask development server
    app.run(host="0.0.0.0", port=5001, debug=False)
