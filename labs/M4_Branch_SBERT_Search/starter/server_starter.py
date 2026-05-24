"""
SBERT News Search API -- Starter Code
Module 4 Branch Project: Search Relevancy with SBERT

Business Context:
    NewsWire India aggregates 12,972 news articles across 13 categories.
    This API provides semantic search -- given a natural-language query,
    it returns the most relevant articles ranked by meaning similarity.

Architecture:
    query -> preprocess -> SBERT embed -> Annoy index -> cosine filter -> results

YOUR TASK: Complete the 8 TODOs below to build a working Flask search API.

Endpoints:
    GET  /ping    -> Health check (returns status and timestamp)
    POST /search  -> Search articles (accepts JSON with "query" and "k")

How to test (after completing and running):
    curl http://localhost:5001/ping
    curl -X POST http://localhost:5001/search \\
      -H "Content-Type: application/json" \\
      -d '{"query": ["artificial intelligence"], "k": 5}'
"""

from flask import Flask, request, jsonify
import json
import os
from datetime import datetime

# Import search modules (provided -- do not modify these imports)
from src.config import ANNOY_SIZE, ANNOY_METRIC, SEARCH_INDEX, MODELS_DIR, TEXT_SECTION_TYPE, TRAIN_DATA_INPUT_TYPES
from src.search import search as semantic_search
from src.build_index import load_annoy_index

app = Flask(__name__)

# ── Global variables (loaded at startup) ─────────────────────────────
# These are populated by load_artifacts() before the server starts
# accepting requests.
index = None          # The Annoy index (loaded from .annoy file)
ids_mapper = None     # Dict mapping section IDs to article IDs
stats = None          # Section statistics (mean, std) for search tuning


def load_artifacts():
    """
    Load all model artifacts needed for search.

    This function runs once at startup. It loads:
      1. The Annoy index (pre-built, ~28 MB)
      2. The ID mapper (section_id -> article_id)
      3. Section statistics (used to tune candidate retrieval)

    The file paths are derived from config.py constants:
      - Index:  models/None_title.annoy
      - IDs:    models/None_title_ids.json
      - Stats:  models/None_title_stats.json
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

    # TODO 1: Load the Annoy index from disk
    # ──────────────────────────────────────────────────────────────────
    # Use the load_annoy_index() function imported from src.build_index.
    # Pass it the index_path variable defined above.
    #
    # Hint: index = load_annoy_index(index_path)
    # ──────────────────────────────────────────────────────────────────

    # TODO 2: Load the ID mapper JSON file
    # ──────────────────────────────────────────────────────────────────
    # Open ids_path with json.load() and assign to the global ids_mapper.
    #
    # Hint:
    #   with open(ids_path, "r") as f:
    #       ids_mapper = json.load(f)
    # ──────────────────────────────────────────────────────────────────

    # TODO 3: Load the section statistics JSON file
    # ──────────────────────────────────────────────────────────────────
    # Open stats_path with json.load(). The JSON has a top-level key
    # "sections_by_article" -- assign that nested dict to the global stats.
    #
    # Hint:
    #   with open(stats_path, "r") as f:
    #       raw = json.load(f)
    #   stats = raw["sections_by_article"]
    # ──────────────────────────────────────────────────────────────────

    print("All artifacts loaded successfully!")


@app.route("/ping", methods=["GET"])
def ping():
    """
    Health check endpoint.

    Returns a JSON response confirming the server is running,
    along with the current timestamp.

    Expected response format:
        {"status": "healthy", "timestamp": "2026-04-13 10:30:00"}
    """
    # TODO 4: Return a JSON response with status and timestamp
    # ──────────────────────────────────────────────────────────────────
    # Use jsonify() to return a dict with two keys:
    #   - "status": the string "healthy"
    #   - "timestamp": current time as a formatted string
    #
    # Hint: datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    # ──────────────────────────────────────────────────────────────────
    pass


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

    Example request:
        POST /search
        {"query": ["climate change policy"], "k": 5}
    """
    # TODO 5: Parse the JSON request body
    # ──────────────────────────────────────────────────────────────────
    # Use request.get_json() to parse the incoming JSON body.
    # Assign it to a variable (e.g., req).
    #
    # Hint: req = request.get_json()
    # ──────────────────────────────────────────────────────────────────

    # TODO 6: Extract and validate 'query' and 'k' from the request
    # ──────────────────────────────────────────────────────────────────
    # Extract req["query"] and int(req["k"]).
    # If either is missing, return an error response with status 400:
    #   return jsonify({"error": "Missing 'query' or 'k' in request"}), 400
    #
    # Hint: Use a try/except or check with 'in' operator.
    # ──────────────────────────────────────────────────────────────────

    # TODO 7: Call the semantic_search() function
    # ──────────────────────────────────────────────────────────────────
    # The semantic_search function (imported as search from src.search)
    # takes 5 arguments:
    #   - index:     the loaded Annoy index (global variable)
    #   - queries:   the list of query strings from the request
    #   - k:         the number of results per query
    #   - ids_mapper: the loaded ID mapper dict (global variable)
    #   - stats:     the loaded section statistics (global variable)
    #
    # Hint: results = semantic_search(index, query, k, ids_mapper, stats)
    # ──────────────────────────────────────────────────────────────────

    # TODO 8: Return the results as a JSON response
    # ──────────────────────────────────────────────────────────────────
    # Use jsonify() to serialize the results list and return it.
    #
    # Hint: return jsonify(results)
    # ──────────────────────────────────────────────────────────────────
    pass


if __name__ == "__main__":
    # Load model artifacts before starting the server
    load_artifacts()

    # Start the Flask development server
    # host="0.0.0.0" makes it accessible from outside the container
    # port=5001 matches the Docker port mapping
    # debug=False for production-like behaviour inside a container
    app.run(host="0.0.0.0", port=5001, debug=False)
