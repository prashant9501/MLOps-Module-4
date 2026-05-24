"""
Annoy Index Operations for SBERT News Search.

This module provides functions to create, build, search, save, and load
an Annoy (Approximate Nearest Neighbors Oh Yeah) index.

Annoy works by building a forest of random projection trees. At search
time, it traverses these trees to quickly find approximate nearest
neighbors without scanning every single vector in the index.

Key concepts:
  - n_trees: More trees = better accuracy, slower build time. 50 is solid.
  - metric: "euclidean" measures straight-line distance between vectors.
  - size: Must match the SBERT embedding dimension (384).

Students: You do NOT need to modify this file. It is used by the search
module and by server.py to load and query the pre-built index.
"""

import annoy
from src.config import ANNOY_SIZE, ANNOY_METRIC, ANNOY_N_TREES


def create_annoy_index(size=ANNOY_SIZE, metric=ANNOY_METRIC):
    """
    Create a new empty Annoy index with the specified dimensions.

    Parameters
    ----------
    size : int
        Dimensionality of the vectors (384 for all-MiniLM-L6-v2).
    metric : str
        Distance metric: "euclidean", "angular", or "manhattan".

    Returns
    -------
    annoy.AnnoyIndex
        An empty Annoy index ready for adding items or loading from disk.
    """
    return annoy.AnnoyIndex(size, metric)


def build_annoy_index(embeddings_dict, size=ANNOY_SIZE, n_trees=ANNOY_N_TREES, metric=ANNOY_METRIC):
    """
    Build an Annoy index from a dictionary of embeddings.

    Parameters
    ----------
    embeddings_dict : dict
        Keys are string IDs (section indices), values are embedding vectors.
    size : int
        Embedding dimensionality (must be 384).
    n_trees : int
        Number of trees in the Annoy forest.
    metric : str
        Distance metric for the index.

    Returns
    -------
    annoy.AnnoyIndex
        A built Annoy index ready for searching.
    """
    index = annoy.AnnoyIndex(size, metric)
    for item_id, embedding in embeddings_dict.items():
        index.add_item(int(item_id), embedding)
    index.build(n_trees)
    return index


def search_annoy_index(index, query_embedding, k, ids_lookup=None):
    """
    Search the Annoy index for the k nearest neighbors of a query vector.

    Parameters
    ----------
    index : annoy.AnnoyIndex
        A loaded or built Annoy index.
    query_embedding : list of float
        A single 384-dimensional query vector.
    k : int
        Number of nearest neighbors to retrieve.
    ids_lookup : dict or None
        Maps internal Annoy IDs to article IDs. If None, raw IDs are returned.

    Returns
    -------
    list of tuple
        Each tuple is (article_id, distance), sorted by distance ascending
        for euclidean metric.
    """
    raw_ids, distances = index.get_nns_by_vector(query_embedding, k, include_distances=True)

    if ids_lookup is not None:
        mapped_ids = [ids_lookup[str(rid)] for rid in raw_ids]
    else:
        mapped_ids = raw_ids

    # Sort by distance (ascending for euclidean = closest first)
    results = sorted(set(zip(mapped_ids, distances)), key=lambda x: x[1])
    return results


def save_annoy_index(index, filepath):
    """
    Save an Annoy index to disk.

    Parameters
    ----------
    index : annoy.AnnoyIndex
        The index to save.
    filepath : str
        Destination path (e.g., "models/None_title.annoy").
    """
    index.save(filepath)


def load_annoy_index(filepath, size=ANNOY_SIZE, metric=ANNOY_METRIC):
    """
    Load a pre-built Annoy index from disk.

    Parameters
    ----------
    filepath : str
        Path to the .annoy file (e.g., "models/None_title.annoy").
    size : int
        Embedding dimensionality (must match the index that was built).
    metric : str
        Distance metric (must match the index that was built).

    Returns
    -------
    annoy.AnnoyIndex
        A loaded index ready for searching.
    """
    index = annoy.AnnoyIndex(size, metric)
    index.load(filepath)
    return index
