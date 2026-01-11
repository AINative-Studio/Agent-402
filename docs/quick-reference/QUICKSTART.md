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
# Required environment variables
export API_KEY="test_api_key_123"
export PROJECT_ID="proj_demo_001"
export BASE_URL="http://localhost:8000"

# Optional: For production deployment
# export BASE_URL="https://api.ainative.studio"
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
curl -X POST "$BASE_URL/v1/public/projects" \
  -H "X-API-Key: $API_KEY" \
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
curl -X GET "$BASE_URL/v1/public/projects" \
  -H "X-API-Key: $API_KEY"
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

---

## ⚠️ Important: Vector Operations Require /database/ Prefix

**If you're using vector operations** (not embeddings), remember:

```bash
# ✅ CORRECT - Vector operations need /database/ prefix
curl -X POST "$BASE_URL/v1/public/database/vectors/upsert" \
  -H "X-API-Key: $API_KEY" \
  -H "Content-Type: application/json" \
  -d '{"vectors": [...]}'

# ❌ INCORRECT - Missing /database/ (will return 404)
curl -X POST "$BASE_URL/v1/public/vectors/upsert" \
  -H "X-API-Key: $API_KEY" \
  -H "Content-Type: application/json" \
  -d '{"vectors": [...]}'
```

**Embeddings endpoints do NOT need /database/:**
- `/v1/public/{project_id}/embeddings/generate` ✅
- `/v1/public/{project_id}/embeddings/embed-and-store` ✅
- `/v1/public/{project_id}/embeddings/search` ✅

**Vector operations DO need /database/:**
- `/v1/public/database/vectors/upsert` ✅
- `/v1/public/database/vectors/search` ✅
- `/v1/public/database/tables/*` ✅

**See:** [DATABASE_PREFIX_WARNING.md](/docs/api/DATABASE_PREFIX_WARNING.md) for complete details.

---

For full documentation, see API_IMPLEMENTATION.md
