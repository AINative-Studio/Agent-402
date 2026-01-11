# Autonomous Fintech Agent Crew

**AINative Edition: CrewAI × X402 × ZeroDB × AIKit**

> **Status:** MVP / Hackathon-ready
> **Goal:** Demonstrate an auditable, replayable, agent-native fintech workflow

---

## 🧠 What This Is

This project is a **minimal but real** implementation of an **agent-native fintech system**.

It proves that autonomous AI agents can:

* Discover and call financial services
* Cryptographically sign requests (X402)
* Persist decisions and memory
* Produce audit-ready ledgers
* Replay workflows deterministically

This is **not a toy demo**.
It is the smallest possible foundation for **regulated, agent-driven finance**.

---

## 🎯 Why This Exists

Most AI agent demos today are:

* Stateless
* Non-verifiable
* Impossible to audit or replay
* Unsafe for regulated domains

This project shows what changes when you add:

* **Signed requests**
* **Persistent agent memory**
* **Immutable ledgers**
* **Deterministic replay**

---

## 🏗️ Architecture Overview

```
+------------------------------+
|        CrewAI Agents         |
|------------------------------|
| analyst                      |
| compliance_agent             |
| transaction_agent            |
|------------------------------|
| Tools                        |
| - AIKit x402.request         |
| - Market Data (mock)         |
+--------------+---------------+
               |
               v
+------------------------------+
|      X402 FastAPI Server     |
|------------------------------|
| /.well-known/x402            |
| /x402 (signed POST)          |
| Signature verification      |
| Payload validation           |
+--------------+---------------+
               |
               v
+------------------------------+
|           ZeroDB             |
|------------------------------|
| agents                       |
| agent_memory                 |
| compliance_events            |
| x402_requests (ledger)       |
| events                       |
+------------------------------+
```

---

## 🤖 Agent Roles (MVP)

| Agent                 | Responsibility                   |
| --------------------- | -------------------------------- |
| **Analyst Agent**     | Evaluates mock market data       |
| **Compliance Agent**  | Simulates KYC/KYT + risk scoring |
| **Transaction Agent** | Signs and submits X402 requests  |

Each agent has:

* A DID
* A defined scope
* Access to shared AIKit tools
* Persistent memory in ZeroDB

---

## 🔐 Core Technologies

* **CrewAI** — Multi-agent orchestration
* **FastAPI** — X402 protocol server
* **X402** — Cryptographically signed request protocol
* **ZeroDB** — Persistent memory, vectors, ledgers, audit
* **AIKit** — Tool abstraction + execution tracing

---

## 📦 Repo Structure

```
.
├── agents/
│   ├── analyst.py
│   ├── compliance.py
│   └── transaction.py
│
├── server/
│   ├── main.py              # FastAPI X402 server
│   ├── x402.py              # Signing + verification
│   └── routes.py
│
├── tools/
│   └── x402_request.py      # AIKit tool wrapper
│
├── zerodb/
│   ├── client.py
│   └── schemas.py
│
├── tests/
│   └── smoke_test.py        # End-to-end validation
│
├── scripts/
│   └── run_demo.py          # One-command demo
│
├── docs/
│   ├── api-spec.md          # Full API specification
│   ├── datamodel.md         # Developer guide
│   ├── DX-Contract.md       # Guaranteed behaviors
│   ├── project-lifecycle.md # Project status lifecycle
│   ├── prd.md               # Product requirements
│   └── backlog.md           # User stories
│
├── .env.example
├── README.md
└── pyproject.toml
```

---

## 🚀 Quick Start (5 Minutes)

### 1. Clone & install

```bash
git clone https://github.com/ainative/autonomous-fintech-agent-crew.git
cd autonomous-fintech-agent-crew
pip install -r requirements.txt
```

---

### 2. Configure environment

Create `.env`:

```bash
API_KEY=your_zerodb_api_key
BASE_URL=https://api.ainative.studio/v1/public
PROJECT_ID=your_project_id
```

> **⚠️ SECURITY WARNING:** This `.env` file contains your API key. **NEVER commit this file to version control** or expose it in client-side code. Always add `.env` to your `.gitignore` file. See [SECURITY.md](/SECURITY.md) for best practices.

---

### 3. Start the X402 server

```bash
uvicorn server.main:app --reload
```

---

### 4. Run the full agent workflow

```bash
python scripts/run_demo.py
```

✅ In under 5 minutes you should see:

* Signed X402 request verified
* Agent memory written to ZeroDB
* Compliance event stored
* Ledger entry created
* Replayable workflow completed

---

## 🧪 Smoke Test

Run the full system validation:

```bash
python tests/smoke_test.py
```

The smoke test verifies:

1. Project exists
2. Embeddings work
3. Agent memory persists
4. X402 requests are signed + verified
5. Ledger entries are immutable
6. Workflow is replayable

If this passes, **the system is real**.

---

## 🔁 Deterministic Replay

Every agent action writes to ZeroDB with:

* `agent_id`
* `run_id`
* `inputs`
* `outputs`
* `timestamp`

You can replay a run **without re-executing agents**, proving:

* Auditability
* Non-repudiation
* Compliance traceability

---

## 📜 ZeroDB DX Contract

This project follows the **ZeroDB DX Contract**, which guarantees:

* Stable endpoints
* Default 384-dim embeddings
* Deterministic errors
* Immutable ledgers
* Copy-paste-safe docs
* **Project status field consistency** (Issue #60)

All project responses (create, list, get) include `status: "ACTIVE"` by default.

See [DX-Contract.md](/DX-Contract.md) and [project-lifecycle.md](/project-lifecycle.md) for details.

---

## 🧠 What This Project Is *Not*

* ❌ A production fintech system
* ❌ A full compliance implementation
* ❌ A UI product

This is **infrastructure**, not an app.

---

## 🏆 Hackathon Framing

> “We didn’t build a demo.
> We built the minimum viable foundation for agent-native finance.”

Judges should focus on:

* Auditability
* Determinism
* Real cryptography
* Replayability
* Clear extensibility

---

## 🔮 What Comes Next

* Replace mock fintech endpoints with real APIs
* Expand compliance logic
* Add multi-party signing
* Introduce agent marketplaces
* Enforce regulatory workflows

---

## 🔒 Security Best Practices

### ⚠️ CRITICAL: API Key Safety

**NEVER expose your ZeroDB API key in:**
- Frontend JavaScript code (React, Vue, Angular, etc.)
- Mobile apps (iOS, Android)
- Browser DevTools
- Public repositories
- Client-side environment variables

**Why this matters:**
- Anyone can extract your API key from client-side code
- Full access to your project data, vectors, and agent memory
- Violates SOC 2, GDPR, PCI DSS compliance requirements
- Creates liability for fintech applications

### ✅ Correct Pattern: Backend Proxy

```
[Client App] → [Your Backend API] → [ZeroDB API]
     ↓              ↓                    ↓
  JWT Token    API Key (secure)    Validated Request
```

**Your frontend should:**
- Authenticate users with JWT tokens or OAuth
- Call YOUR backend API endpoints
- Never access ZeroDB API directly

**Your backend should:**
- Store API key in environment variables
- Validate user authentication
- Proxy requests to ZeroDB API
- Implement rate limiting

**Example:**

```python
# ✅ SECURE - Backend endpoint
@app.post('/api/search')
async def search(query: str, user: User = Depends(get_current_user)):
    response = await httpx.post(
        'https://api.ainative.studio/v1/public/embeddings/search',
        headers={'X-API-Key': os.getenv('ZERODB_API_KEY')},
        json={'query': query}
    )
    return response.json()
```

```javascript
// ✅ SECURE - Frontend code
const results = await fetch('/api/search', {
  headers: { 'Authorization': `Bearer ${userToken}` },
  body: JSON.stringify({ query: 'fintech agents' })
});
```

**📚 Complete Guide:** See [SECURITY.md](/SECURITY.md) for detailed patterns, examples, and mobile app guidance.

---

## 📫 Support & Contact

* **AINative Studio** — [https://ainative.studio](https://ainative.studio)
* **Issues / PRs** — welcome
* **Hackathon questions** — find us onsite

---
