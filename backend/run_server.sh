#!/bin/bash
# Run the FastAPI server for development

set -e

echo "Starting ZeroDB Agent Finance API..."
echo "Server will be available at http://localhost:8000"
echo "API docs at http://localhost:8000/docs"
echo ""
echo "Demo API Keys:"
echo "  User 1: demo_key_user1_abc123"
echo "  User 2: demo_key_user2_xyz789"
echo ""

cd "$(dirname "$0")"

# Check if virtual environment exists
if [ ! -d "venv" ]; then
    echo "Creating virtual environment..."
    python3 -m venv venv
fi

# Activate virtual environment
source venv/bin/activate

# Install dependencies if needed
if [ ! -f "venv/.installed" ]; then
    echo "Installing dependencies..."
    pip install -r requirements.txt
    touch venv/.installed
fi

# Run the server
python -m app.main
