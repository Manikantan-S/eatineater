"""Configuration helpers for the Flask application."""
from __future__ import annotations

import os
from pathlib import Path


def get_graph_path() -> Path:
    """Return the path to the RDF graph file.

    The path can be configured using the ``RECIPE_GRAPH_PATH`` environment
    variable; otherwise we fall back to the main recipes graph.
    """

    override = os.getenv("RECIPE_GRAPH_PATH")
    if override:
        return Path(override).expanduser().resolve()
    return Path(__file__).resolve().parent.parent / "data" / "recipes.ttl"
