# Semantic Food Recipe Finder

Semantic Food Recipe Finder is a full-stack semantic web project that builds a
recipe ontology, generates an RDF knowledge graph from structured datasets, and
exposes a queryable API with a lightweight front-end. Users can explore the
knowledge graph with semantic filters such as “vegan lentil recipes under 45
minutes.”

## Features

- **Ontology-driven graph** – Scripts for transforming the Kaggle “Better
  Recipes for a Better Life” dataset into a Turtle knowledge graph using
  `rdflib` with inferred diet categories.
- **Semantic search API** – A Flask backend that performs SPARQL queries over
  the graph, supporting ingredient keyword searches, cuisine filtering, diet
  constraints, and total-time limits.
- **Interactive front-end** – A responsive interface that consumes the API,
  visualises recipe metadata, and displays full directions straight from the
  graph.
- **Extensible ontology** – Classes for recipes, ingredients, cuisines, and
  dietary types that can be customised for coursework or further research.

## Project Structure

```
.
├── app/                  # Flask application and graph helpers
├── data/                 # Sample data and RDF graph
├── frontend/             # Static front-end assets
├── scripts/              # Utilities for building the graph
├── requirements.txt      # Python dependencies
└── README.md
```

### Key Files

- `scripts/build_graph.py` – Convert the Kaggle dataset (CSV or JSON) into an
  RDF Turtle file with inferred dietary categories.
- `data/recipes_sample.ttl` – A small demonstration graph generated from the
  sample JSON dataset.
- `app/main.py` – Flask entry-point that exposes the API and serves the static
  site.
- `app/graph_loader.py` – High-level search helpers that wrap SPARQL queries and
  assemble JSON-friendly objects.
- `frontend/index.html`, `styles.css`, `app.js` – Search UI that calls the API
  and renders recipe details.

## Quick Start (Recommended)

**The easiest way to get started:**

### **Option 1: Automatic Startup (Recommended)**
```bash
# 1. Install dependencies
pip install -r requirements.txt

# 2. Run the automatic startup script
./start.sh    # On Mac/Linux
# OR
start.bat     # On Windows
```

### **Option 2: Manual Startup**
```bash
# 1. Install dependencies
pip install -r requirements.txt

# 2. Run the application (automatically finds free port)
python run.py
```

The application will automatically:
- Find a free port (8000, 8001, 8002, etc.)
- Load your recipe database
- Show the URL to open in your browser
- Display recipes immediately when you open the page

## Detailed Setup

### 1. Set up Python dependencies

Create a virtual environment and install requirements (Python 3.10+ recommended):

```bash
python -m venv .venv
source .venv/bin/activate  # On Windows: .venv\Scripts\activate
pip install -r requirements.txt
```

### 2. Run with sample data (easiest)

The project includes sample data that works out of the box:

```bash
python run.py
```

This will:
- Automatically build the sample knowledge graph if needed
- Start the Flask server on http://localhost:5000
- Show you helpful startup information

### 3. Run with your own dataset (optional)

If you want to use your own recipe data:

1. **Download the Kaggle dataset:**
   - Visit: <https://www.kaggle.com/datasets/thedevastator/better-recipes-for-a-better-life>
   - Download the CSV file and save it as `data/recipes.csv`

2. **Build your knowledge graph:**
   ```bash
   python scripts/build_graph.py data/recipes.csv data/recipes.ttl
   ```

3. **Set the environment variable:**
   ```bash
   export RECIPE_GRAPH_PATH=$(pwd)/data/recipes.ttl
   ```

4. **Run the application:**
   ```bash
   python run.py
   ```

### 4. Alternative: Manual Flask startup

If you prefer to use Flask directly:

```bash
export FLASK_APP=app.main:create_app
flask run
```

## API Endpoints

- `GET /api/search` – Query recipes with optional `ingredient`, `cuisine`, `diet`, and `maxTime` parameters
- `GET /api/recipes?uri=<URI>` – Retrieve full details for a recipe resource  
- `GET /api/cuisines` and `GET /api/diets` – Retrieve available filter values
- `GET /api/health` – Health check endpoint

Visit <http://localhost:5000> to load the front-end UI.

## Front-end Overview

The single-page interface provides:

- A search form with ingredient keyword, cuisine dropdown, diet dropdown, and
  total time filter.
- Live query results that display ratings, cuisine, diets, and cook time badges.
- A details panel that renders the recipe’s ingredients and directions fetched
  directly from the knowledge graph.

## Extending the Ontology

The default ontology defines the following key classes and properties:

- `rec:Recipe`, `rec:Ingredient`, `rec:Cuisine`, `rec:DietType`
- Properties: `rec:hasIngredient`, `rec:hasCuisine`, `rec:hasDiet`,
  `rec:hasTotalTime`, `rec:hasRating`, and more
- Ingredient subclasses for `rec:AnimalProduct` and `rec:GlutenIngredient`

To extend the ontology, edit `scripts/build_graph.py` to add new classes or
properties, then regenerate the TTL file. The Flask API automatically reflects
additional data properties because SPARQL queries use labels and groups.

## Sample Data

`data/sample_recipes.json` and `data/recipes_sample.ttl` demonstrate the expected
input schema and the generated RDF output. Use them to validate your pipeline
before operating on the full Kaggle dataset.

## License

This project is provided for educational purposes. Verify the licensing terms of
any external datasets before redistribution.
