# Workshop Troubleshooting Guide

## Quick Fix Pattern

For ANY error, paste it to your AI assistant:

> "I'm working on Agent-402 and got this error: [paste error]. The server is at localhost:8000. Help me fix it."

Your AI handles 90% of issues. Below are the top 10 for the remaining 10%.

---

## 1. "command not found: python3"

**Problem:** Python isn't installed or isn't in PATH.

**Fix (macOS):**
```bash
brew install python@3.9
```

**Fix (Windows WSL):**
```bash
sudo apt update && sudo apt install python3 python3-pip
```

---

## 2. "ModuleNotFoundError: No module named 'fastapi'"

**Problem:** Dependencies not installed.

**Fix:**
```bash
cd Agent-402
pip3 install -r requirements.txt
```

If that fails, try:
```bash
pip3 install -r backend/requirements.txt
```

---

## 3. "Address already in use: port 8000"

**Problem:** Something else is running on port 8000.

**Fix:**
```bash
# Find what's using port 8000
lsof -i :8000
# Kill it
kill -9 <PID>
# Or use a different port
uvicorn app.main:app --reload --port 8001
```

---

## 4. "HEDERA_OPERATOR_ID not set" or "Invalid operator ID"

**Problem:** Hedera credentials missing from `.env`.

**Fix:**
1. Open `.env` in your editor
2. Replace placeholder values with your real Hedera testnet credentials:
   ```
   HEDERA_OPERATOR_ID=0.0.12345
   HEDERA_OPERATOR_KEY=302e020100300506032b657004220420...
   HEDERA_NETWORK=testnet
   ```
3. Restart the server

**Don't have credentials?** Go to https://portal.hedera.com and create a free account.

---

## 5. "TypeError: unsupported operand type(s) for |: 'type' and 'NoneType'"

**Problem:** Python 3.9 vs 3.10+ type syntax.

**Fix:** This was fixed in Sprint 3 (`config.py` has `from __future__ import annotations`). If you still see it:
```bash
python3 --version
```
If < 3.9, upgrade. If 3.9, make sure you pulled latest code: `git pull origin main`.

---

## 6. "Connection refused" when calling API

**Problem:** Server isn't running.

**Fix:**
```bash
cd backend
uvicorn app.main:app --reload --port 8000
```

Keep this terminal open. Open a NEW terminal for API calls.

---

## 7. API returns 401 Unauthorized

**Problem:** Missing API key header.

**Fix:** Add the `X-API-Key` header to your requests:
```bash
curl -H "X-API-Key: demo_key_user1_abc123" \
  http://localhost:8000/api/v1/agents
```

For workshop/development, the default test key works.

---

## 7a. "ZeroDB connection failed" / 500 errors on agent or memory endpoints

**Problem:** Missing or wrong `ZERODB_API_KEY` / `ZERODB_PROJECT_ID`. Any call that touches agent CRUD, agent memory, or cognitive memory will 500 without them.

**Fix:**

1. Visit [https://www.ainative.studio/developer-settings](https://www.ainative.studio/developer-settings), sign in, and generate an API key tied to a project.
2. Add both values to `backend/.env` (see Vibe Coder Guide Step 4.5):
   ```bash
   ZERODB_API_KEY=ZDB_XXXXXXXXXXXX
   ZERODB_PROJECT_ID=proj_YYYYYYYY
   ```
3. Restart the server so the new env vars are picked up.

**Verify:**
```bash
curl -H "X-API-Key: demo_key_user1_abc123" http://localhost:8000/v1/public/projects
```
A 200 response with a JSON list confirms ZeroDB is reachable. A 500 with `ZERODB_ERROR` or `ZeroDBClient running in mock mode` log message means credentials are still missing.

---

## 8. "No module named 'app.core.config'"

**Problem:** Running from wrong directory.

**Fix:** Make sure you're in the `backend/` directory:
```bash
cd Agent-402/backend
uvicorn app.main:app --reload
```

---

## 9. Hedera testnet transactions failing

**Problem:** Testnet account has no HBAR or USDC.

**Fix:**
1. Go to https://portal.hedera.com
2. Select your testnet account
3. Use the faucet to get free testnet HBAR
4. For USDC testing: the workshop uses mock amounts by default

---

## 10. "git: command not found" or "npm: command not found"

**Problem:** Developer tools not installed.

**Fix (macOS):**
```bash
xcode-select --install  # git
brew install node        # npm
```

**Fix (Windows):** Use WSL (Windows Subsystem for Linux), then follow Linux instructions.

---

## Still Stuck?

1. **Paste the full error** to your AI assistant — it can usually diagnose and fix
2. **Ask the instructor** — raise your hand, that's what we're here for
3. **Check the docs:** http://localhost:8000/docs shows all available endpoints
4. **Restart clean:**
   ```bash
   # Stop server (Ctrl+C), then:
   cd Agent-402/backend
   uvicorn app.main:app --reload --port 8000
   ```
