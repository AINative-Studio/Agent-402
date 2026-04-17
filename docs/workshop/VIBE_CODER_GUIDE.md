# Vibe Coder Getting Started Guide

## You Don't Need to Know How to Code

You need three things:
1. **A laptop** with a terminal (every computer has one)
2. **An AI coding assistant** (Claude Code, Cursor, or GitHub Copilot)
3. **The ability to describe what you want** in plain English

Your AI assistant writes the code. You describe the goal. Agent-402's test suite catches mistakes. That's vibe coding.

---

## Step 1: Get Your AI Assistant Ready

**Option A: Claude Code** (recommended)
```
Open your terminal and type:
npx @anthropic-ai/claude-code
```

**Option B: Cursor**
Download from cursor.com, open the Agent-402 folder.

**Option C: GitHub Copilot**
Install the VS Code extension, open the Agent-402 folder.

---

## Step 2: Clone the Project

Tell your AI assistant:

> "Help me clone the Agent-402 repository and set it up. The repo is at github.com/AINative-Studio/Agent-402. I need to clone it, install Python dependencies, and copy the environment file."

Your AI will run something like:
```bash
git clone https://github.com/AINative-Studio/Agent-402.git
cd Agent-402
pip3 install -r requirements.txt
cp .env.example .env
```

**Verification:** You should see a folder called `Agent-402` with a `backend/` directory inside.

---

## Step 3: Get Your Hedera Testnet Account

Tell your AI:

> "I need a Hedera testnet account. Walk me through creating one at portal.hedera.com"

Or do it yourself:
1. Go to https://portal.hedera.com
2. Create an account (free)
3. You'll get an **Account ID** (like `0.0.12345`) and a **Private Key**
4. The portal gives you free testnet HBAR

**Verification:** You have an account ID and private key. Keep the private key safe.

---

## Step 4: Configure Your Environment

Tell your AI:

> "Help me edit the .env file in the Agent-402 project. I need to add my Hedera testnet account ID and private key. My account ID is 0.0.XXXXX and my private key is YYYYY."

Your AI will edit `.env` to include:
```bash
HEDERA_OPERATOR_ID=0.0.XXXXX
HEDERA_OPERATOR_KEY=YYYYY
HEDERA_NETWORK=testnet
```

**Verification:** Your `.env` file has real Hedera credentials (not the placeholder text).

---

## Step 4.5: Get Your ZeroDB API Key

Agent-402 uses ZeroDB for agent memory and vector search. Without a ZeroDB key, any memory-related call (and Tutorial 01 Steps 7+) will fail with 500 errors.

1. Open [https://www.ainative.studio/developer-settings](https://www.ainative.studio/developer-settings) and sign in.
2. Create a project (or use an existing one) and generate an API key.
3. Copy both the **API key** and the **project ID**.

Tell your AI:

> "Add my ZeroDB credentials to the .env file. API key is ZDB_XXXXXXXXXXXX and project ID is proj_YYYYYYYY."

Your AI will add these lines:
```bash
ZERODB_API_KEY=ZDB_XXXXXXXXXXXX
ZERODB_PROJECT_ID=proj_YYYYYYYY
```

**Verification:** After starting the server in Step 5, run:
```bash
curl -H "X-API-Key: demo_key_user1_abc123" http://localhost:8000/v1/public/projects
```
A 200 response with a JSON list means ZeroDB is connected. A 500 error means the key or project ID is wrong — double-check and restart the server.

---

## Step 5: Start the Server

Tell your AI:

> "Start the Agent-402 backend server"

Your AI will run:
```bash
cd backend
uvicorn app.main:app --reload --port 8000
```

**Verification:** Open http://localhost:8000/docs in your browser. You should see the FastAPI interactive documentation page with a list of all API endpoints.

If you see an error instead, paste it to your AI:

> "I got this error when starting the server: [paste error]. Help me fix it."

---

## Step 6: Verify Everything Works

Tell your AI:

> "Run the workshop smoke test to make sure everything is working"

Your AI will run:
```bash
python scripts/workshop_smoke_test.py
```

You should see all checks pass. If any fail, your AI can help debug.

---

## You're Ready!

Now follow the tutorials in order:
1. **[Tutorial 1: Identity & Memory](tutorials/01-identity-and-memory.md)** — Create your agent, give it a Hedera identity and persistent memory
2. **[Tutorial 2: Payments & Trust](tutorials/02-payments-and-trust.md)** — Wire USDC payments and build reputation
3. **[Tutorial 3: Discovery & Marketplace](tutorials/03-discovery-and-marketplace.md)** — Publish your agent and interact with others

---

## The Vibe Coding Pattern

For every step in the tutorials, the pattern is the same:

1. **Read the goal** — what are we building?
2. **Tell your AI** — describe what you want in plain English
3. **Your AI writes code** — it sends API requests or creates files
4. **Check the result** — does the response match what we expected?
5. **If something breaks** — paste the error to your AI, it'll fix it

You are the architect. Your AI is the builder. The test suite is the safety net.

---

## Quick Reference: Talking to Your AI

**Starting a task:**
> "I'm working on Agent-402, a fintech agent system on Hedera. Help me [specific goal]."

**When something breaks:**
> "I got this error: [paste error]. The server is running at localhost:8000. Help me fix it."

**When you're stuck:**
> "I'm trying to [goal] using the Agent-402 API. Show me the curl command or Python code to do this."

**When you want to understand:**
> "Explain what just happened. What did that API call do and why does it matter for a fintech agent?"
