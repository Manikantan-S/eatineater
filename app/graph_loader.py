"""Utility helpers for loading and querying the recipe knowledge graph."""
from __future__ import annotations

from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path
from typing import Dict, List, Optional

from rdflib import Graph


REC_NS = "http://example.org/recipes#"
SCHEMA_NS = "http://schema.org/"
RDFS_NS = "http://www.w3.org/2000/01/rdf-schema#"


@dataclass
class RecipeSummary:
    uri: str
    label: str
    url: Optional[str]
    rating: Optional[float]
    total_time: Optional[int]
    cuisines: List[str]
    diets: List[str]


@dataclass
class RecipeDetail(RecipeSummary):
    ingredients: List[str]
    directions: List[str]


class RecipeGraph:
    """Encapsulates an rdflib graph with helper search methods."""

    def __init__(self, ttl_path: Path) -> None:
        if not ttl_path.exists():
            raise FileNotFoundError(f"Knowledge graph not found at {ttl_path}")
        self.graph = Graph()
        self.graph.parse(ttl_path, format="turtle")

    def _execute(self, query: str, **params) -> List[Dict[str, str]]:
        results = self.graph.query(query, initBindings=params)
        output: List[Dict[str, str]] = []
        for row in results:
            row_dict = {str(var): (value.toPython() if value is not None else None) for var, value in row.asdict().items()}
            output.append(row_dict)
        return output

    def list_cuisines(self) -> List[str]:
        query = f"""
        PREFIX rec: <{REC_NS}>
        PREFIX rdfs: <{RDFS_NS}>
        SELECT DISTINCT ?label WHERE {{
            ?cuisine a rec:Cuisine ;
                     rdfs:label ?label .
        }}
        ORDER BY LCASE(?label)
        """
        return [row["label"] for row in self._execute(query)]

    def list_diets(self) -> List[str]:
        query = f"""
        PREFIX rec: <{REC_NS}>
        PREFIX rdfs: <{RDFS_NS}>
        SELECT DISTINCT ?label WHERE {{
            ?diet a rec:DietType ;
                  rdfs:label ?label .
        }}
        ORDER BY LCASE(?label)
        """
        return [row["label"] for row in self._execute(query)]

    def search(
        self,
        ingredient: Optional[str] = None,
        cuisine: Optional[str] = None,
        diet: Optional[str] = None,
        max_total_time: Optional[int] = None,
    ) -> List[RecipeSummary]:
        # Build query with direct string substitution to avoid parameter binding issues
        where_parts = [
            "?recipe a rec:Recipe ;",
            "        rdfs:label ?label .",
            "OPTIONAL { ?recipe schema:url ?url . }",
            "OPTIONAL { ?recipe rec:hasRating ?rating . }",
            "OPTIONAL { ?recipe rec:hasTotalTime ?totalTime . }",
            "OPTIONAL { ?recipe rec:hasCuisine ?cuisine . ?cuisine rdfs:label ?cuisineLabel . }",
            "OPTIONAL { ?recipe rec:hasDiet ?diet . ?diet rdfs:label ?dietLabel . }",
        ]

        filter_parts = []
        
        if ingredient:
            where_parts.append("?recipe rec:hasIngredient ?ingredient .")
            where_parts.append("?ingredient rdfs:label ?ingredientLabel .")
            filter_parts.append(f'FILTER(CONTAINS(LCASE(?ingredientLabel), LCASE("{ingredient}")))')
            
        if cuisine:
            where_parts.append("?recipe rec:hasCuisine ?cuisineFilterUri .")
            where_parts.append("?cuisineFilterUri rdfs:label ?cuisineLabelFilter .")
            filter_parts.append(f'FILTER(LCASE(?cuisineLabelFilter) = LCASE("{cuisine}"))')
            
        if diet:
            where_parts.append("?recipe rec:hasDiet ?dietFilterUri .")
            where_parts.append("?dietFilterUri rdfs:label ?dietLabelFilter .")
            filter_parts.append(f'FILTER(LCASE(?dietLabelFilter) = LCASE("{diet}"))')
            
        if max_total_time is not None:
            filter_parts.append(f'FILTER(xsd:integer(?totalTime) <= {max_total_time})')

        where_block = "\n".join(where_parts)
        filter_block = "\n".join(filter_parts)
        
        query = f"""
        PREFIX rec: <{REC_NS}>
        PREFIX schema: <{SCHEMA_NS}>
        PREFIX rdfs: <{RDFS_NS}>
        PREFIX xsd: <http://www.w3.org/2001/XMLSchema#>
        SELECT ?recipe ?label ?url ?rating ?totalTime ?cuisineLabel ?dietLabel
        WHERE {{
            {where_block}
            {filter_block}
        }}
        ORDER BY LCASE(?label)
        """

        rows = self.graph.query(query)
        summaries: List[RecipeSummary] = []
        
        # Group results by recipe URI to collect cuisines and diets
        recipe_data = {}
        for row in rows:
            recipe_uri = str(row["recipe"])
            if recipe_uri not in recipe_data:
                recipe_data[recipe_uri] = {
                    "uri": recipe_uri,
                    "label": str(row["label"]),
                    "url": str(row["url"]) if row["url"] else None,
                    "rating": row["rating"].toPython() if row["rating"] else None,
                    "total_time": row["totalTime"].toPython() if row["totalTime"] else None,
                    "cuisines": set(),
                    "diets": set()
                }
            
            # Add cuisine if present
            if row["cuisineLabel"]:
                recipe_data[recipe_uri]["cuisines"].add(str(row["cuisineLabel"]))
            
            # Add diet if present
            if row["dietLabel"]:
                recipe_data[recipe_uri]["diets"].add(str(row["dietLabel"]))
        
        # Convert to RecipeSummary objects
        for recipe_uri, data in recipe_data.items():
            summaries.append(
                RecipeSummary(
                    uri=data["uri"],
                    label=data["label"],
                    url=data["url"],
                    rating=data["rating"],
                    total_time=data["total_time"],
                    cuisines=list(data["cuisines"]),
                    diets=list(data["diets"]),
                )
            )
        
        return summaries

    def recipe_detail(self, recipe_uri: str) -> Optional[RecipeDetail]:
        query = f"""
        PREFIX rec: <{REC_NS}>
        PREFIX schema: <{SCHEMA_NS}>
        PREFIX rdfs: <{RDFS_NS}>
        SELECT ?label ?url ?rating ?totalTime ?ingredientLabel ?direction ?dietLabel ?cuisineLabel WHERE {{
            BIND(<{recipe_uri}> AS ?recipe)
            ?recipe rdfs:label ?label .
            OPTIONAL {{ ?recipe schema:url ?url . }}
            OPTIONAL {{ ?recipe rec:hasRating ?rating . }}
            OPTIONAL {{ ?recipe rec:hasTotalTime ?totalTime . }}
            OPTIONAL {{ ?recipe rec:hasIngredient ?ingredient . ?ingredient rdfs:label ?ingredientLabel . }}
            OPTIONAL {{ ?recipe schema:step ?step . ?step rdfs:label ?direction . }}
            OPTIONAL {{ ?recipe rec:hasDiet ?diet . ?diet rdfs:label ?dietLabel . }}
            OPTIONAL {{ ?recipe rec:hasCuisine ?cuisine . ?cuisine rdfs:label ?cuisineLabel . }}
        }}
        """
        rows = list(self.graph.query(query))
        if not rows:
            return None
        first = rows[0]
        rating = first["rating"].toPython() if first["rating"] else None
        total_time_val = first["totalTime"].toPython() if first["totalTime"] else None
        detail = RecipeDetail(
            uri=recipe_uri,
            label=str(first["label"]),
            url=str(first["url"]) if first["url"] else None,
            rating=rating,
            total_time=total_time_val,
            cuisines=[],
            diets=[],
            ingredients=[],
            directions=[],
        )
        for row in rows:
            if row["ingredientLabel"]:
                ingredient_label = str(row["ingredientLabel"])
                if ingredient_label not in detail.ingredients:
                    detail.ingredients.append(ingredient_label)
            if row["direction"]:
                direction = str(row["direction"])
                if direction not in detail.directions:
                    detail.directions.append(direction)
            if row["dietLabel"]:
                diet_label = str(row["dietLabel"])
                if diet_label not in detail.diets:
                    detail.diets.append(diet_label)
            if row["cuisineLabel"]:
                cuisine_label = str(row["cuisineLabel"])
                if cuisine_label not in detail.cuisines:
                    detail.cuisines.append(cuisine_label)
        return detail


@lru_cache(maxsize=1)
def load_graph(ttl_path: Path) -> RecipeGraph:
    return RecipeGraph(ttl_path)
