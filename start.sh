#!/bin/bash

# Vornics Weather AI - Backend Startup Script
# This script activates the virtual environment and starts the backend server

set -e  # Exit on error

echo "🚀 Starting Vornics Weather AI Backend..."

# Navigate to backend directory
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

# Check if virtual environment exists
if [ ! -d "venv" ]; then
    echo "❌ Virtual environment not found!"
    echo "Creating virtual environment..."
    python3 -m venv venv
fi

# Activate virtual environment
echo "📦 Activating virtual environment..."
source venv/bin/activate

# Install/upgrade dependencies
echo "📥 Installing dependencies..."
pip install --upgrade pip --quiet
pip install -r requirements.txt --quiet

# Check if .env exists
if [ ! -f ".env" ]; then
    echo "⚠️  Warning: .env file not found!"
    echo "Copying from .env.example..."
    cp .env.example .env
    echo "⚠️  Please configure .env with your Firebase credentials!"
fi

# Start the server
echo "✅ Starting FastAPI server on port 8000..."
echo "📡 API will be available at: http://localhost:8000"
echo "📚 API docs available at: http://localhost:8000/docs"
echo ""
echo "Press CTRL+C to stop the server"
echo ""

python -m uvicorn app:app --host 0.0.0.0 --port 8000 --reload
