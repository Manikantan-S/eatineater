"""Build an RDF knowledge graph from a recipe dataset."""
from __future__ import annotations

import argparse
import json
import math
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable, List, Optional

import pandas as pd
from rdflib import BNode, Graph, Literal, Namespace, RDF, RDFS, URIRef
from rdflib.namespace import OWL, XSD


BASE_URI = "http://example.org/recipes#"
REC = Namespace(BASE_URI)
SCHEMA = Namespace("http://schema.org/")


@dataclass
class RecipeRecord:
    name: str
    prep_time: Optional[int]
    cook_time: Optional[int]
    total_time: Optional[int]
    servings: Optional[int]
    ingredients: List[str]
    directions: List[str]
    rating: Optional[float]
    url: Optional[str]
    cuisine_path: Optional[str]


ANIMAL_PRODUCTS = {
    "anchovy",
    "bacon",
    "beef",
    "butter",
    "chicken",
    "egg",
    "fish",
    "gelatin",
    "honey",
    "lamb",
    "milk",
    "pork",
    "shrimp",
    "turkey",
    "yogurt",
    "parmesan",
    "cream",
    "cheese",
}

GLUTEN_GRAINS = {"wheat", "barley", "rye", "spelt", "farro", "semolina", "flour", "spaghetti", "pasta", "bread"}


def normalise_text(value: str) -> str:
    value = value.strip().lower()
    value = re.sub(r"[^a-z0-9]+", "-", value)
    return re.sub(r"-+", "-", value).strip("-")


def parse_sequence(value) -> List[str]:
    if isinstance(value, list):
        return [str(v).strip() for v in value if str(v).strip()]
    if isinstance(value, str):
        value = value.strip()
        if not value:
            return []
        try:
            parsed = json.loads(value)
            if isinstance(parsed, list):
                return [str(v).strip() for v in parsed if str(v).strip()]
        except json.JSONDecodeError:
            pass
        return [part.strip() for part in re.split(r"[\n;]+", value) if part.strip()]
    return []


def to_optional_int(value) -> Optional[int]:
    if value is None or (isinstance(value, float) and math.isnan(value)):
        return None
    try:
        return int(value)
    except (TypeError, ValueError):
        return None


def to_optional_float(value) -> Optional[float]:
    if value is None or (isinstance(value, float) and math.isnan(value)):
        return None
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def load_records(path: Path) -> List[RecipeRecord]:
    if path.suffix.lower() == ".json":
        data = json.loads(path.read_text())
        rows = data if isinstance(data, list) else data.get("data", [])
    else:
        df = pd.read_csv(path)
        rows = df.to_dict(orient="records")

    records: List[RecipeRecord] = []
    for row in rows:
        records.append(
            RecipeRecord(
                name=str(row.get("recipe_name", "")).strip(),
                prep_time=to_optional_int(row.get("prep_time")),
                cook_time=to_optional_int(row.get("cook_time")),
                total_time=to_optional_int(row.get("total_time")),
                servings=to_optional_int(row.get("servings")),
                ingredients=parse_sequence(row.get("ingredients")),
                directions=parse_sequence(row.get("directions")),
                rating=to_optional_float(row.get("rating")),
                url=str(row.get("url")) if row.get("url") else None,
                cuisine_path=str(row.get("cuisine_path")) if row.get("cuisine_path") else None,
            )
        )
    return records


def add_ontology_schema(graph: Graph) -> None:
    graph.bind("rec", REC)
    graph.bind("schema", SCHEMA)

    graph.add((REC.Recipe, RDF.type, OWL.Class))
    graph.add((REC.Ingredient, RDF.type, OWL.Class))
    graph.add((REC.Cuisine, RDF.type, OWL.Class))
    graph.add((REC.DietType, RDF.type, OWL.Class))
    graph.add((REC.AnimalProduct, RDF.type, OWL.Class))
    graph.add((REC.GlutenIngredient, RDF.type, OWL.Class))

    graph.add((REC.hasIngredient, RDF.type, OWL.ObjectProperty))
    graph.add((REC.hasCuisine, RDF.type, OWL.ObjectProperty))
    graph.add((REC.hasDiet, RDF.type, OWL.ObjectProperty))
    graph.add((REC.avoidsIngredientCategory, RDF.type, OWL.ObjectProperty))

    graph.add((REC.hasPrepTime, RDF.type, OWL.DatatypeProperty))
    graph.add((REC.hasCookTime, RDF.type, OWL.DatatypeProperty))
    graph.add((REC.hasTotalTime, RDF.type, OWL.DatatypeProperty))
    graph.add((REC.hasServings, RDF.type, OWL.DatatypeProperty))
    graph.add((REC.hasRating, RDF.type, OWL.DatatypeProperty))

    for diet_name in ("Vegan", "Vegetarian", "GlutenFree"):
        diet_uri = REC[diet_name]
        graph.add((diet_uri, RDF.type, REC.DietType))
        graph.add((diet_uri, RDFS.label, Literal(diet_name)))


def annotate_ingredient(graph: Graph, ingredient_label: str) -> URIRef:
    ingredient_id = normalise_text(ingredient_label)
    ingredient_uri = REC[f"ingredient-{ingredient_id}"]
    if (ingredient_uri, RDF.type, REC.Ingredient) not in graph:
        graph.add((ingredient_uri, RDF.type, REC.Ingredient))
        graph.add((ingredient_uri, RDFS.label, Literal(ingredient_label)))

        lowered = ingredient_label.lower()
        if any(token in lowered for token in ANIMAL_PRODUCTS):
            graph.add((ingredient_uri, RDF.type, REC.AnimalProduct))
        if any(token in lowered for token in GLUTEN_GRAINS):
            graph.add((ingredient_uri, RDF.type, REC.GlutenIngredient))
    return ingredient_uri


def infer_diets(graph: Graph, recipe_uri: URIRef, ingredient_uris: Iterable[URIRef]) -> None:
    ingredient_uris = list(ingredient_uris)
    has_animal = any((uri, RDF.type, REC.AnimalProduct) in graph for uri in ingredient_uris)
    has_gluten = any((uri, RDF.type, REC.GlutenIngredient) in graph for uri in ingredient_uris)

    if not has_animal:
        graph.add((recipe_uri, REC.hasDiet, REC.Vegan))
        graph.add((recipe_uri, REC.hasDiet, REC.Vegetarian))
    else:
        # even with animal products, there might be vegetarian-friendly recipes, but
        # for simplicity we mark vegetarian only if there are no obvious meats.
        has_meat = any(
            token in graph.value(uri, RDFS.label).lower()
            for uri in ingredient_uris
            for token in ("chicken", "beef", "pork", "lamb", "fish", "shrimp", "turkey")
            if graph.value(uri, RDFS.label)
        )
        if not has_meat:
            graph.add((recipe_uri, REC.hasDiet, REC.Vegetarian))

    if not has_gluten:
        graph.add((recipe_uri, REC.hasDiet, REC.GlutenFree))

    if has_animal:
        graph.add((recipe_uri, REC.avoidsIngredientCategory, REC.AnimalProduct))
    if has_gluten:
        graph.add((recipe_uri, REC.avoidsIngredientCategory, REC.GlutenIngredient))


def populate_graph(graph: Graph, records: List[RecipeRecord]) -> None:
    for record in records:
        if not record.name:
            continue
        recipe_id = normalise_text(record.name)
        recipe_uri = REC[f"recipe-{recipe_id}"]
        graph.add((recipe_uri, RDF.type, REC.Recipe))
        graph.add((recipe_uri, RDFS.label, Literal(record.name)))

        if record.url:
            graph.add((recipe_uri, SCHEMA.url, Literal(record.url)))
        if record.rating is not None:
            graph.add((recipe_uri, REC.hasRating, Literal(record.rating, datatype=XSD.float)))
        if record.prep_time is not None:
            graph.add((recipe_uri, REC.hasPrepTime, Literal(record.prep_time, datatype=XSD.integer)))
        if record.cook_time is not None:
            graph.add((recipe_uri, REC.hasCookTime, Literal(record.cook_time, datatype=XSD.integer)))
        if record.total_time is not None:
            graph.add((recipe_uri, REC.hasTotalTime, Literal(record.total_time, datatype=XSD.integer)))
        if record.servings is not None:
            graph.add((recipe_uri, REC.hasServings, Literal(record.servings, datatype=XSD.integer)))

        ingredient_uris: List[URIRef] = []
        for ingredient in record.ingredients:
            ingredient_uri = annotate_ingredient(graph, ingredient)
            ingredient_uris.append(ingredient_uri)
            graph.add((recipe_uri, REC.hasIngredient, ingredient_uri))

        infer_diets(graph, recipe_uri, ingredient_uris)

        for idx, direction in enumerate(record.directions, start=1):
            step_bnode = BNode()
            graph.add((step_bnode, RDF.type, SCHEMA.HowToStep))
            graph.add((step_bnode, RDFS.label, Literal(direction)))
            graph.add((step_bnode, SCHEMA.position, Literal(idx, datatype=XSD.integer)))
            graph.add((recipe_uri, SCHEMA.step, step_bnode))

        if record.cuisine_path:
            cuisines = [segment.strip() for segment in record.cuisine_path.split(">") if segment.strip()]
            parent_uri: Optional[URIRef] = None
            for cuisine in cuisines:
                cuisine_id = normalise_text(cuisine)
                cuisine_uri = REC[f"cuisine-{cuisine_id}"]
                if (cuisine_uri, RDF.type, REC.Cuisine) not in graph:
                    graph.add((cuisine_uri, RDF.type, REC.Cuisine))
                    graph.add((cuisine_uri, RDFS.label, Literal(cuisine)))
                if parent_uri is not None:
                    graph.add((cuisine_uri, RDFS.subClassOf, parent_uri))
                parent_uri = cuisine_uri
            if parent_uri is not None:
                graph.add((recipe_uri, REC.hasCuisine, parent_uri))


def build_graph(records: List[RecipeRecord]) -> Graph:
    graph = Graph()
    add_ontology_schema(graph)
    populate_graph(graph, records)
    return graph


def main() -> None:
    parser = argparse.ArgumentParser(description="Build an RDF graph from recipe data")
    parser.add_argument("input", type=Path, help="Path to the recipe dataset (CSV or JSON)")
    parser.add_argument("output", type=Path, help="Destination TTL file")
    args = parser.parse_args()

    records = load_records(args.input)
    graph = build_graph(records)
    graph.serialize(destination=args.output, format="turtle")
    print(f"Wrote {len(graph)} triples to {args.output}")


if __name__ == "__main__":
    main()
