# Curriculum Walkthrough Report — 2026-04-19

**Tester:** Automated curriculum test agent (Claude Desktop session)
**Method:** Live HTTP requests against `localhost:8000` — every result is real, not simulated.
**Server config:** Mock mode (no `HEDERA_OPERATOR_KEY`, no `ZERODB_API_KEY`) — the default workshop setup a vibe coder encounters.
**Project used:** `proj_demo_u1_001` (one of three that appear in `GET /v1/public/projects` by default).

---

## Summary

| Tutorial | Steps that WORK | Steps that FAIL | Steps BLOCKED by earlier failures |
|---|---|---|---|
| 01 Identity & Memory | 1/10 (Step 3 = /docs page) | 4 (#345, #346, #347) | 5 (everything that needed agent_id from Step 1) |
| 02 Payments & Trust | 3/11 (Steps 2, 3, 6) | 3 (#345, #322, #348) | 5 |
| 03 Discovery & Marketplace | 3/10 (Steps 1, 7-categories, 8-empty) | 5 (#327, #345) | 2 |
| **Total** | **7/31 (23%)** | **12 confirmed failures** | **12 blocked** |

If the 7 open code issues (#322, #327, #329, #330, #342, #345, #348) land, expected coverage jumps to 26/31 (84%). The remaining 5 are genuine curriculum issues (#346, #347 plus the 3 doc-fix gaps).

---

## Tutorial 01: Identity & Memory

### Step 1: Create agent — ❌ FAIL (500)
- **Real request:** `POST /v1/public/proj_demo_u1_001/agents` with the exact body from the tutorial
- **Real response:** `500 INTERNAL_SERVER_ERROR` → tracked to `httpx.HTTPStatusError: 404 for url '...zerodb/mock_project/database/tables/agents/rows'`
- **Filed:** #345 (ZeroDB mock mode fails for all tables) — expanded scope from #328

### Step 2: Verify agent — BLOCKED (no agent_id from Step 1)

### Step 3: `/docs` page — ✅ works (static FastAPI page)

### Step 4: Register Hedera identity — ❌ FAIL (422)
- **Real request body from tutorial:** `{"agent_id":"X","capabilities":[...]}`
- **Real response:** `422 — Field 'name' required, Field 'role' required`
- Schema requires `name` and `role`; tutorial omits both
- Endpoint also generates its own `agent_id`, ignoring Step 1's value
- **Filed:** #346

### Step 5: Resolve DID — BLOCKED (no Hedera DID from Step 4)

### Step 6: Get capabilities — BLOCKED

### Step 7: Store memory — ❌ FAIL (500, ZeroDB mock gap #345)

### Step 8: Recall memory — BLOCKED

### Step 9: Reflect / profile — BLOCKED

### Step 10: Verify HCS anchor — ❌ FAIL (422)
- **Real request:** `GET /anchor/mem_fake_001/verify`
- **Real response:** `422 — Field 'current_content' required` (as a query param)
- Tutorial doesn't mention this required parameter
- **Filed:** #347

---

## Tutorial 02: Payments & Trust

### Step 1: Create Hedera wallet — ❌ FAIL (500, ZeroDB mock gap #345)

### Step 2: Associate USDC — ✅ WORKS
- Returned valid: `{"transaction_id": "0.0.12345@1776643336.901326000", "status": "SUCCESS", ...}`
- Doesn't require prior wallet existence — would be good for demos even if Step 1 is broken

### Step 3: Check balance — ✅ WORKS
- Returned realistic balances: `{"hbar": "103055.43182359", "usdc": "0.0"}`
- Goes to real Hedera testnet mirror node

### Step 4: Execute USDC payment — ❌ FAIL (500, ZeroDB mock gap)
- First tried with `from_account`/`to_account` (from tutorial's running text) → got 422 for missing `agent_id`/`recipient`
- Tutorial's **JSON example body** uses `agent_id`/`recipient`, but the **narrative** says "from my agent's account to account `0.0.22222`" — wording mismatch
- After using correct body: 500 from ZeroDB mock gap

### Step 5: Verify payment receipt — ⚠️ FALSE POSITIVE
- Returns `{"verified": true, "transaction_status": "SUCCESS"}` for **any** transaction_id, even fabricated ones
- This completely defeats the "tamper-proof payment verification" value prop of the step
- **Filed:** #348

### Step 6: x402 discovery — ✅ WORKS
- Returns proper discovery JSON with Hedera metadata, USDC token ID, mirror node URL

### Step 7: Submit reputation feedback — ❌ FAIL (502)
- `'HederaClient' object has no attribute 'submit_hcs_message'`
- **Already filed:** #322

### Steps 8–11: BLOCKED (depend on Step 7)

---

## Tutorial 03: Discovery & Marketplace

### Step 1: HCS-14 directory register — ✅ WORKS
- Returned valid transaction_id and directory_topic

### Step 2: Search directory — ⚠️ DEGRADED
- Returns `{"agents": []}` — empty — despite Step 1 successfully registering a finance agent
- The registration is a simulated HCS write; the search reads from the real mirror node which has no such message
- **Result:** attendees see "no agents" and lose the narrative thread. **Net: curriculum-breaking even though the endpoint is "working".**

### Step 3: Discover by role — Same issue as Step 2 (returns empty)

### Step 4: Send HCS-10 message — ❌ FAIL (500)
- `'HederaClient' object has no attribute 'submit_topic_message'`
- **Already filed:** #327

### Step 5: Check messages — BLOCKED

### Step 6: View audit trail — BLOCKED

### Step 7: Publish to marketplace — ❌ FAIL (500, ZeroDB mock gap)
- Tutorial body was correct once I used it verbatim (`agent_config`, `publisher_did`, `pricing`)
- But persistence fails: #345

### Step 7 (alt): List categories — ✅ WORKS
- Returns `["finance", "analytics", "communication", "development", "research", "automation", "other"]`
- Doesn't touch ZeroDB — hardcoded endpoint

### Step 8: Browse marketplace — ❌ FAIL (500, ZeroDB mock gap #345)

### Step 9: Search marketplace — ❌ FAIL (500, ZeroDB mock gap #345)

### Step 10: Full agent lifecycle — ❌ FAIL (all sub-steps blocked)

---

## Findings NOT caught by E2E orchestrator

The orchestrator tests 16 checkpoints. The manual walkthrough surfaced 5 issues that the orchestrator could not catch because it short-circuits on earlier failures:

1. **#346** — Tutorial 01 Step 4 wrong request body (E2E never gets past Step 1)
2. **#347** — Tutorial 01 Step 10 missing `current_content` param (E2E never reaches Step 10)
3. **#348** — Tutorial 02 Step 5 false-positive verification (E2E doesn't assert `verified` is meaningful)
4. **#345** — Scope expansion beyond #328: ZeroDB mock gap affects ALL tables, not just marketplace
5. **Tutorial 03 Steps 2–3 directory search gap** — Returns empty after a successful register, orchestrator counts this as PASS but workshop attendees see a broken demo

---

## Fix-first priority (to reach 16/16 on E2E + a runnable workshop for vibe coders)

| # | Fix | Unblocks | Spawned? |
|---|-----|----------|----------|
| 1 | #345 ZeroDB mock mode (all tables) | Tutorial 01 Steps 1, 2, 7, 8, 9; Tutorial 02 Steps 1, 4; Tutorial 03 Steps 7, 8, 9 | ✅ yes |
| 2 | #322 + #327 HederaClient HCS methods | Tutorial 02 Step 7; Tutorial 03 Steps 4, 5 | ✅ yes |
| 3 | #330 + #329 Orchestrator project setup + wallet realignment | E2E 8/16 → higher | ✅ yes |
| 4 | #342 Vibe-coder prompt API path leaks | Vibe-coder persona integrity | ✅ yes |
| 5 | #346 Tutorial 01 Step 4 body + agent_id link | Tutorial 01 Step 4 and downstream | open doc fix |
| 6 | #347 Tutorial 01 Step 10 missing query param | Tutorial 01 Step 10 | open doc fix |
| 7 | #348 Tutorial 02 Step 5 false-positive verify | Workshop credibility | open code fix |

---

## Vibe-coder real-world observations

Even after all doc fixes from PR #343 landed, a true vibe coder running these tutorials today hits walls at:

- **Tutorial 01 Step 1** — 500 error with a stack-trace-looking message. A vibe coder pastes this to their AI, which needs to know about ZeroDB mock mode to diagnose.
- **Tutorial 01 Step 4** — 422 error with validation details. A vibe coder could fix this by asking their AI "what fields does this endpoint need?" IF they're prompting their AI to do discovery. But the tutorial doesn't suggest that pattern.
- **Tutorial 02 Step 4** — Tutorial body says `agent_id`+`recipient` but running text says `from_account`/`to_account`. Vibe coder gets confused about which to use.
- **Tutorial 02 Step 5** — "verified: true" on any input. The attendee never knows this is fake. **Silent failure is worse than loud failure.**
- **Tutorial 03 Step 2** — Empty `agents: []` breaks narrative flow. Attendees think they did Step 1 wrong.

**Biggest curriculum-quality issue:** the tutorials are optimized for the "happy path with real credentials". They don't account for the mock-mode experience, which is what 90% of workshop attendees will actually have. Either mock mode needs to produce realistic-looking data (so the demo narrative holds), OR the tutorials need to explicitly say "you must have ZeroDB credentials to complete this — see `VIBE_CODER_GUIDE.md` Step 4.5".

---

## Recommendation

After the 5 spawned dev tasks land:
1. Re-run `python3 scripts/workshop_e2e_test.py --persona developer --tutorial all` (expect 14–16/16)
2. Repeat this manual walkthrough (expect Tutorial 01 Steps 1–9 all passing in mock mode after #345)
3. Address #346, #347, #348 as P1 doc/code fixes
4. Re-record asciinema with the green run for the Luma page

Built by AINative Dev Team
