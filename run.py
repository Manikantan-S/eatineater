#!/usr/bin/env python3
"""
Simple startup script for the Semantic Food Recipe Finder.
This script ensures the data is built and starts the Flask application.
"""

import os
import sys
from pathlib import Path

def main():
    """Start the Semantic Food Recipe Finder application."""
    
    # Get the project root directory
    project_root = Path(__file__).parent
    os.chdir(project_root)
    
    # Check if we have the main recipes data
    recipes_ttl = project_root / "data" / "recipes.ttl"
    recipes_csv = project_root / "data" / "recipes.csv"
    sample_ttl = project_root / "data" / "recipes_sample.ttl"
    sample_json = project_root / "data" / "sample_recipes.json"
    
    # Use main recipes.ttl if it exists, otherwise fall back to sample
    if recipes_ttl.exists():
        print(f"Using main recipes graph: {recipes_ttl}")
    elif recipes_csv.exists():
        print("Building main knowledge graph from recipes.csv...")
        import subprocess
        result = subprocess.run([
            sys.executable, "scripts/build_graph.py", 
            str(recipes_csv), str(recipes_ttl)
        ], capture_output=True, text=True)
        
        if result.returncode != 0:
            print(f"Error building main graph: {result.stderr}")
            print("Falling back to sample data...")
        else:
            print("Main knowledge graph built successfully!")
    elif sample_ttl.exists():
        print(f"Using sample recipes graph: {sample_ttl}")
    elif sample_json.exists():
        print("Building sample knowledge graph...")
        import subprocess
        result = subprocess.run([
            sys.executable, "scripts/build_graph.py", 
            str(sample_json), str(sample_ttl)
        ], capture_output=True, text=True)
        
        if result.returncode != 0:
            print(f"Error building sample graph: {result.stderr}")
            sys.exit(1)
        print("Sample knowledge graph built successfully!")
    else:
        print("❌ No recipe data found!")
        print("Please ensure you have either:")
        print("  - data/recipes.csv (main dataset)")
        print("  - data/recipes.ttl (pre-built graph)")
        print("  - data/sample_recipes.json (sample data)")
        sys.exit(1)
    
    # Import and start the Flask app
    try:
        from app.main import create_app
        app = create_app()
        
        print("=" * 60)
        print("🍽️  Semantic Food Recipe Finder")
        print("=" * 60)
        print("🌐 Starting web server...")
        print("📍 Open your browser to: http://localhost:8000")
        print("🔍 Try searching for 'vegan recipes with lentils'")
        print("=" * 60)
        print("Press Ctrl+C to stop the server")
        print("=" * 60)
        
        # Try different ports if 8000 is occupied
        import socket
        
        def find_free_port(start_port=8000):
            for port in range(start_port, start_port + 10):
                try:
                    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
                        s.bind(('localhost', port))
                        return port
                except OSError:
                    continue
            return 8000
        
        port = find_free_port()
        print(f"🌐 Server starting on port {port}")
        print(f"📍 Open your browser to: http://localhost:{port}")
        
        app.run(host="0.0.0.0", port=port, debug=False)
        
    except ImportError as e:
        print(f"❌ Error importing application: {e}")
        print("💡 Make sure you've installed the requirements:")
        print("   pip install -r requirements.txt")
        sys.exit(1)
    except Exception as e:
        print(f"❌ Error starting application: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()
