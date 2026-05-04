# Workshop Setup Guide

Complete this guide before starting any tutorial. Every tutorial assumes a running server with workshop mode enabled.

**Time:** ~15 minutes

---

## Step 1: Clone and Install

```bash
git clone https://github.com/AINative-Studio/Agent-402.git
cd Agent-402
cp .env.example .env
pip3 install -r requirements.txt
```

---

## Step 2: Add Your Credentials to `.env`

Open `.env` and fill in the following values.

### Hedera Testnet Account

Get a free testnet account at https://portal.hedera.com (takes ~2 minutes).

```bash
HEDERA_OPERATOR_ID=0.0.XXXXX
HEDERA_OPERATOR_KEY=your_private_key_here
HEDERA_NETWORK=testnet
```

### ZeroDB API Key

Sign in at https://ainative.studio/developer-settings, create a project, and generate an API key.

```bash
ZERODB_API_KEY=ZDB_XXXXXXXXXXXX
ZERODB_PROJECT_ID=proj_YYYYYYYY
```

### Workshop Mode

These two lines activate the URL rewriting middleware that maps the tutorial-style paths
(`/api/v1/...`) to the real API routes (`/v1/public/{project_id}/...`). Without them,
every tutorial API call returns a 404.

```bash
WORKSHOP_MODE=true
WORKSHOP_DEFAULT_PROJECT_ID=proj_workshop
```

Set `WORKSHOP_DEFAULT_PROJECT_ID` to the same value as your `ZERODB_PROJECT_ID` so that
requests are routed to your actual project.

---

## Step 3: Start the Server

```bash
cd backend
uvicorn app.main:app --reload --port 8000
```

**Verify it's running:**

```bash
curl http://localhost:8000/health
# → {"status": "healthy"}
```

You can also open http://localhost:8000/docs in your browser to see the full API reference.

If you see an error, paste it to your AI assistant:

> "I got this error starting the Agent-402 server: [paste error]. Help me fix it."

---

## Step 4: Confirm Workshop Mode Is Active

```bash
curl -H "X-API-Key: demo_key_user1_abc123" \
     http://localhost:8000/api/v1/agents
```

You should receive a `200` with a JSON list (empty is fine). A `404` means
`WORKSHOP_MODE=true` is not set — check your `.env` and restart the server.

---

## Step 5: Run the Smoke Test

```bash
python scripts/workshop_smoke_test.py
```

All checks should pass. If any fail, paste the output to your AI assistant.

---

## You're Ready

Start with Tutorial 1 and work through them in order:

1. [Tutorial 1: Identity & Memory](tutorials/01-identity-and-memory.md)
2. [Tutorial 2: Payments & Trust](tutorials/02-payments-and-trust.md)
3. [Tutorial 3: Discovery & Marketplace](tutorials/03-discovery-and-marketplace.md)

---

## Troubleshooting

| Symptom | Likely cause | Fix |
|---------|--------------|-----|
| `Connection refused` on any API call | Server not running | Run `uvicorn app.main:app --reload --port 8000` from `backend/` |
| `404` on `/api/v1/...` paths | `WORKSHOP_MODE` not set | Add `WORKSHOP_MODE=true` to `.env`, restart server |
| `500` on memory/vector calls | Bad ZeroDB credentials | Check `ZERODB_API_KEY` and `ZERODB_PROJECT_ID` in `.env` |
| `PROJECT_NOT_FOUND` | `WORKSHOP_DEFAULT_PROJECT_ID` mismatch | Set it to the same value as `ZERODB_PROJECT_ID` |

For more help, see [TROUBLESHOOTING.md](TROUBLESHOOTING.md).
