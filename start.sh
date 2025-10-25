#!/bin/bash

# Semantic Food Recipe Finder - Startup Script
# This script handles everything automatically

echo "🍽️  Starting Semantic Food Recipe Finder..."

# Navigate to the project directory
cd "$(dirname "$0")"

# Kill any existing processes on common ports
echo "🧹 Cleaning up any existing processes..."
lsof -ti :8000 | xargs kill -9 2>/dev/null || true
lsof -ti :8001 | xargs kill -9 2>/dev/null || true
lsof -ti :8002 | xargs kill -9 2>/dev/null || true

# Start the application
echo "🚀 Starting the application..."
python run.py
