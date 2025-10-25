"""Flask application exposing a semantic recipe search API."""
from __future__ import annotations

import logging
from pathlib import Path

from flask import Flask, jsonify, request, send_from_directory

from .config import get_graph_path
from .graph_loader import RecipeGraph, load_graph

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def create_app() -> Flask:
    app = Flask(__name__, static_folder=None)

    try:
        graph_path = get_graph_path()
        frontend_dir = Path(__file__).resolve().parent.parent / "frontend"
        recipe_graph: RecipeGraph = load_graph(graph_path)
        logger.info(f"Loaded knowledge graph from {graph_path}")
    except Exception as e:
        logger.error(f"Failed to load knowledge graph: {e}")
        raise

    @app.route("/api/health")
    def health() -> tuple[str, int]:
        return "ok", 200

    @app.route("/api/cuisines")
    def cuisines() -> tuple[str, int]:
        return jsonify(sorted(recipe_graph.list_cuisines())), 200

    @app.route("/api/diets")
    def diets() -> tuple[str, int]:
        return jsonify(sorted(recipe_graph.list_diets())), 200

    @app.route("/api/search")
    def search() -> tuple[str, int]:
        try:
            ingredient = request.args.get("ingredient") or None
            cuisine = request.args.get("cuisine") or None
            diet = request.args.get("diet") or None
            max_time = request.args.get("maxTime") or request.args.get("max_time")
            max_time_int = int(max_time) if max_time and max_time.isdigit() else None

            logger.info(f"Search request: ingredient={ingredient}, cuisine={cuisine}, diet={diet}, max_time={max_time_int}")
            
            results = recipe_graph.search(
                ingredient=ingredient,
                cuisine=cuisine,
                diet=diet,
                max_total_time=max_time_int,
            )
            
            logger.info(f"Search returned {len(results)} results")
            
            payload = []
            for summary in results:
                try:
                    payload.append({
                        "uri": summary.uri,
                        "label": summary.label,
                        "url": summary.url,
                        "rating": summary.rating,
                        "total_time": summary.total_time,
                        "cuisines": summary.cuisines,
                        "diets": summary.diets,
                    })
                except Exception as e:
                    logger.error(f"Error processing recipe {summary.uri}: {e}")
                    continue
            
            logger.info(f"Successfully processed {len(payload)} recipes")
            return jsonify(payload), 200
        except Exception as e:
            logger.error(f"Search error: {e}")
            import traceback
            logger.error(f"Traceback: {traceback.format_exc()}")
            return jsonify({"error": "Search failed"}), 500

    @app.route("/api/recipes")
    def recipe_lookup() -> tuple[str, int]:
        try:
            uri = request.args.get("uri")
            if not uri:
                return jsonify({"error": "Missing 'uri' query parameter"}), 400
            
            logger.info(f"Recipe lookup request for URI: {uri}")
            detail = recipe_graph.recipe_detail(uri)
            if detail is None:
                logger.warning(f"Recipe not found for URI: {uri}")
                return jsonify({"error": "Recipe not found"}), 404
            
            logger.info(f"Recipe found: {detail.label}")
            return (
                jsonify(
                    {
                        "uri": detail.uri,
                        "label": detail.label,
                        "url": detail.url,
                        "rating": detail.rating,
                        "total_time": detail.total_time,
                        "cuisines": detail.cuisines,
                        "diets": detail.diets,
                        "ingredients": detail.ingredients,
                        "directions": detail.directions,
                    }
                ),
                200,
            )
        except Exception as e:
            logger.error(f"Recipe lookup error: {e}")
            return jsonify({"error": "Recipe lookup failed"}), 500

    @app.route("/")
    def index() -> str:
        return send_from_directory(frontend_dir, "index.html")

    @app.route("/assets/<path:filename>")
    def assets(filename: str):
        return send_from_directory(frontend_dir, filename)

    return app


if __name__ == "__main__":
    app = create_app()
    app.run(host="0.0.0.0", port=5000, debug=True)
