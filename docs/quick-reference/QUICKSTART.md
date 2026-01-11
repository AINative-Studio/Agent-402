# Quick Start Guide - POST /v1/public/projects

Get the project creation API up and running in 5 minutes.

## Prerequisites

- Python 3.11+ installed
- Terminal access

## Step 1: Install Dependencies (30 seconds)

```bash
cd /Users/aideveloper/Agent-402
pip install -r requirements.txt
```

## Step 2: Set Environment Variables (30 seconds)

```bash
# Required for API authentication
export ZERODB_API_KEY="test_api_key_123"

# Optional: For ZeroDB persistence (future feature)
# export ZERODB_PROJECT_ID="your_project_id_here"
```

## Step 3: Start the API Server (10 seconds)

```bash
# Option 1: Quick start
python3 -m uvicorn api.main:app --reload

# Option 2: Custom host/port
uvicorn api.main:app --reload --host 0.0.0.0 --port 8000
```

You should see:
```
INFO:     Uvicorn running on http://127.0.0.1:8000 (Press CTRL+C to quit)
INFO:     Started reloader process
🚀 ZeroDB API Server starting up...
```

## Step 4: Test the API (2 minutes)

### Option A: Using curl

**Create a project:**
```bash
curl -X POST http://localhost:8000/v1/public/projects \
  -H "X-API-Key: test_api_key_123" \
  -H "Content-Type: application/json" \
  -d '{
    "name": "My First Project",
    "description": "Testing the API",
    "tier": "free",
    "database_enabled": true
  }'
```

**List projects:**
```bash
curl -H "X-API-Key: test_api_key_123" \
  http://localhost:8000/v1/public/projects
```

## Step 5: Run Tests (30 seconds)

```bash
# Run all tests
python3 -m pytest tests/test_projects_api.py -v
```

**Expected output:**
```
======================== 25 passed, 30 warnings in 0.16s ========================
```

For full documentation, see API_IMPLEMENTATION.md
