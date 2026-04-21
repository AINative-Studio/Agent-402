#!/usr/bin/env bash
#
# Workshop Tutorial Walkthrough — narrative vibe-coder test harness
#
# Both:
#   1. A NARRATIVE — reads like a vibe coder going through the tutorials with
#      an AI assistant (natural-language prompts + API call + visible response)
#   2. A TEST — every step makes a REAL HTTP request and ASSERTS on the
#      response. Any failure increments a counter and prints FAIL; the script
#      exits non-zero if any checkpoint fails.
#
# Designed to be wrapped in asciinema for a human-watchable cast file:
#
#   asciinema rec docs/workshop/recordings/vibe-coder-walkthrough.cast \
#     --command scripts/workshop_tutorial_walkthrough.sh
#
# Built by AINative Dev Team
# Refs PRD §15.2 (Vibe Coder persona), §15.3 (acceptance criteria)

set -uo pipefail   # NOT set -e — we want to continue on failures to show all

BASE_URL="${WORKSHOP_BASE_URL:-http://localhost:8000}"
API_KEY="${WORKSHOP_API_KEY:-demo_key_user1_abc123}"
PROJECT_ID="${WORKSHOP_PROJECT_ID:-proj_demo_u1_001}"
PAUSE="${WORKSHOP_PAUSE:-1.0}"

BOLD="\033[1m"; DIM="\033[2m"; RESET="\033[0m"
CYAN="\033[36m"; GREEN="\033[32m"; RED="\033[31m"; YELLOW="\033[33m"; MAG="\033[35m"; BLUE="\033[34m"

PASS_COUNT=0
FAIL_COUNT=0
FAIL_DETAILS=()

banner() {
    printf "\n${BOLD}${BLUE}══════════════════════════════════════════════════════════════════════${RESET}\n"
    printf "${BOLD}${BLUE}  %s${RESET}\n" "$1"
    printf "${BOLD}${BLUE}══════════════════════════════════════════════════════════════════════${RESET}\n\n"
    sleep "$PAUSE"
}

step() {
    printf "\n${BOLD}${MAG}▸ Step %s — %s${RESET}\n" "$1" "$2"
    sleep "$PAUSE"
}

vibe_says() {
    printf "\n${CYAN}💬 You say to your AI:${RESET}\n"
    printf "${CYAN}   \"%s\"${RESET}\n\n" "$1"
    sleep "$PAUSE"
}

ai_runs() {
    printf "${DIM}   AI runs: %s${RESET}\n" "$1"
}

# assert_eq "label" "expected" "actual" — increments counters, prints PASS/FAIL
assert_eq() {
    local label="$1" expected="$2" actual="$3"
    if [[ "$actual" == "$expected" ]]; then
        printf "   ${GREEN}✅ PASS  %s${RESET}  (got %q)\n" "$label" "$actual"
        PASS_COUNT=$((PASS_COUNT + 1))
    else
        printf "   ${RED}❌ FAIL  %s${RESET}  (expected %q, got %q)\n" "$label" "$expected" "$actual"
        FAIL_COUNT=$((FAIL_COUNT + 1))
        FAIL_DETAILS+=("$label — expected $expected, got $actual")
    fi
}

# assert_nonempty "label" "value" — increments counters; PASS if non-empty/non-null
assert_nonempty() {
    local label="$1" value="$2"
    if [[ -n "$value" && "$value" != "null" && "$value" != "None" ]]; then
        printf "   ${GREEN}✅ PASS  %s${RESET}  (got %q)\n" "$label" "${value:0:60}"
        PASS_COUNT=$((PASS_COUNT + 1))
    else
        printf "   ${RED}❌ FAIL  %s${RESET}  (empty/null)\n" "$label"
        FAIL_COUNT=$((FAIL_COUNT + 1))
        FAIL_DETAILS+=("$label — got empty/null")
    fi
}

# assert_http_2xx "label" "http_code"
assert_http_2xx() {
    local label="$1" code="$2"
    if [[ "$code" =~ ^2[0-9][0-9]$ ]]; then
        printf "   ${GREEN}✅ PASS  %s${RESET}  (HTTP %s)\n" "$label" "$code"
        PASS_COUNT=$((PASS_COUNT + 1))
    else
        printf "   ${RED}❌ FAIL  %s${RESET}  (HTTP %s — expected 2xx)\n" "$label" "$code"
        FAIL_COUNT=$((FAIL_COUNT + 1))
        FAIL_DETAILS+=("$label — HTTP $code not 2xx")
    fi
}

pretty() { echo "$1" | python3 -m json.tool 2>/dev/null || echo "$1"; }

# HTTP helper — prints body, captures status code into $HTTP_CODE
http_post() {
    local path="$1" body="$2"
    local tmp; tmp=$(mktemp)
    HTTP_CODE=$(curl -sS -o "$tmp" -w "%{http_code}" -X POST "$BASE_URL$path" \
        -H "Content-Type: application/json" -H "X-API-Key: $API_KEY" \
        -d "$body")
    HTTP_BODY=$(cat "$tmp"); rm -f "$tmp"
    pretty "$HTTP_BODY"
}

http_get() {
    local path="$1"
    local tmp; tmp=$(mktemp)
    HTTP_CODE=$(curl -sS -o "$tmp" -w "%{http_code}" "$BASE_URL$path" \
        -H "X-API-Key: $API_KEY")
    HTTP_BODY=$(cat "$tmp"); rm -f "$tmp"
    pretty "$HTTP_BODY"
}

json_field() { echo "$1" | python3 -c "import sys,json;print(json.load(sys.stdin).get('$2',''))" 2>/dev/null; }

# --- Prerequisite: server running -----------------------------------------
if ! curl -sf -o /dev/null "$BASE_URL/health"; then
    printf "${RED}⚠  Server not running at %s${RESET}\n" "$BASE_URL"
    printf "${YELLOW}   Start with: cd backend && uvicorn app.main:app --port 8000${RESET}\n"
    exit 2
fi

# ===========================================================================
banner "Tutorial 01 — Identity & Memory"
# ===========================================================================

# Step 1 ---------------------------------------------------------------------
step "1" "Create your agent"
vibe_says "Create an autonomous finance agent for me called 'my-consensus-agent'. It's an analyst and my first autonomous fintech agent on Hedera."
ai_runs "POST /v1/public/$PROJECT_ID/agents"
http_post "/v1/public/$PROJECT_ID/agents" \
  '{"did":"did:key:z6MkhaXgBZDvotDkL5257faiztiGiC2QtKLGpbnnEGta2doK","name":"my-consensus-agent","role":"analyst","scope":"PROJECT","description":"My first autonomous fintech agent on Hedera"}'
assert_http_2xx "create agent" "$HTTP_CODE"
AGENT_ID=$(json_field "$HTTP_BODY" "agent_id")
assert_nonempty "agent_id returned" "$AGENT_ID"
assert_eq "agent name matches" "my-consensus-agent" "$(json_field "$HTTP_BODY" name)"
assert_eq "agent role matches" "analyst" "$(json_field "$HTTP_BODY" role)"

# Step 2 ---------------------------------------------------------------------
step "2" "Verify the agent exists"
vibe_says "Show me my agent's details."
ai_runs "GET /v1/public/$PROJECT_ID/agents/$AGENT_ID"
http_get "/v1/public/$PROJECT_ID/agents/$AGENT_ID"
assert_http_2xx "retrieve agent" "$HTTP_CODE"
assert_eq "same agent_id on retrieve" "$AGENT_ID" "$(json_field "$HTTP_BODY" agent_id)"

# Step 4 ---------------------------------------------------------------------
step "4" "Register your agent on Hedera (linked to Step 1)"
vibe_says "Register my agent on Hedera — it should have finance, compliance, and payments capabilities."
ai_runs "POST /api/v1/hedera/identity/$AGENT_ID/register"
http_post "/api/v1/hedera/identity/$AGENT_ID/register" \
  '{"capabilities":["finance","compliance","payments"]}'
assert_http_2xx "register Hedera identity" "$HTTP_CODE"
HEDERA_DID=$(json_field "$HTTP_BODY" "did")
assert_nonempty "agent_did returned" "$HEDERA_DID"
assert_eq "SAME agent_id reused (PRD §15.3)" "$AGENT_ID" "$(json_field "$HTTP_BODY" agent_id)"
assert_eq "registration status" "SUCCESS" "$(json_field "$HTTP_BODY" status)"

# Step 7 ---------------------------------------------------------------------
step "7" "Store a memory"
vibe_says "Store a memory for my agent: 'Evaluated market conditions — HBAR/USD stable at 0.08.'"
ai_runs "POST /v1/public/$PROJECT_ID/memory/remember"
http_post "/v1/public/$PROJECT_ID/memory/remember" \
  "{\"agent_id\":\"$AGENT_ID\",\"content\":\"Evaluated market conditions: HBAR/USD stable at 0.08\",\"namespace\":\"default\"}"
assert_http_2xx "store memory" "$HTTP_CODE"
MEM_ID=$(json_field "$HTTP_BODY" memory_id)
assert_nonempty "memory_id returned" "$MEM_ID"
assert_eq "same agent owns memory" "$AGENT_ID" "$(json_field "$HTTP_BODY" agent_id)"

# Step 8 ---------------------------------------------------------------------
step "8" "Recall memories with relevance + recency"
vibe_says "What did my agent learn about market conditions?"
ai_runs "POST /v1/public/$PROJECT_ID/memory/recall"
http_post "/v1/public/$PROJECT_ID/memory/recall" \
  "{\"agent_id\":\"$AGENT_ID\",\"query\":\"market conditions\"}"
assert_http_2xx "recall memories" "$HTTP_CODE"
MEM_COUNT=$(echo "$HTTP_BODY" | python3 -c 'import sys,json;print(len(json.load(sys.stdin).get("memories",[])))')
if [[ "$MEM_COUNT" -ge 1 ]]; then
    printf "   ${GREEN}✅ PASS  at least one memory returned${RESET}  (count=%s)\n" "$MEM_COUNT"; PASS_COUNT=$((PASS_COUNT + 1))
else
    printf "   ${RED}❌ FAIL  expected ≥1 memory, got %s${RESET}\n" "$MEM_COUNT"; FAIL_COUNT=$((FAIL_COUNT + 1))
    FAIL_DETAILS+=("recall: expected ≥1 memory, got $MEM_COUNT")
fi

# ===========================================================================
banner "Tutorial 02 — Payments & Trust"
# ===========================================================================

# Step 1 ---------------------------------------------------------------------
step "1" "Create a Hedera wallet for your agent"
vibe_says "Create a Hedera wallet for my agent so it can hold HBAR and USDC."
ai_runs "POST /v1/public/$PROJECT_ID/hedera/wallets"
http_post "/v1/public/$PROJECT_ID/hedera/wallets" "{\"agent_id\":\"$AGENT_ID\",\"initial_balance_hbar\":0}"
assert_http_2xx "create Hedera wallet" "$HTTP_CODE"
ACCOUNT_ID=$(json_field "$HTTP_BODY" account_id)
assert_nonempty "account_id returned" "$ACCOUNT_ID"

# Step 2 ---------------------------------------------------------------------
step "2" "Enable USDC on the wallet"
vibe_says "Enable USDC on my agent's wallet so it can send and receive USDC payments."
ai_runs "POST /v1/public/$PROJECT_ID/hedera/wallets/$ACCOUNT_ID/associate-usdc"
http_post "/v1/public/$PROJECT_ID/hedera/wallets/$ACCOUNT_ID/associate-usdc" '{}'
assert_http_2xx "associate USDC" "$HTTP_CODE"
assert_eq "association status" "SUCCESS" "$(json_field "$HTTP_BODY" status)"

# Step 3 ---------------------------------------------------------------------
step "3" "Check the wallet balance"
vibe_says "What's in my agent's wallet?"
ai_runs "GET /v1/public/$PROJECT_ID/hedera/wallets/$ACCOUNT_ID/balance"
http_get "/v1/public/$PROJECT_ID/hedera/wallets/$ACCOUNT_ID/balance"
assert_http_2xx "check balance" "$HTTP_CODE"
assert_nonempty "hbar balance present" "$(json_field "$HTTP_BODY" hbar)"

# Step 7 ---------------------------------------------------------------------
step "7" "Submit reputation feedback for another agent"
vibe_says "Give agent did:hedera:testnet:0.0.99999 a 5-star rating — excellent analysis work."
ai_runs "POST /api/v1/hedera/reputation/{did}/feedback"
http_post "/api/v1/hedera/reputation/did:hedera:testnet:0.0.99999/feedback" \
  "{\"rating\":5,\"comment\":\"excellent analysis work\",\"payment_proof_tx\":\"0.0.12345@1234567890.000000001\",\"task_id\":\"walkthrough-task-1\",\"submitter_did\":\"$HEDERA_DID\"}"
assert_http_2xx "submit feedback" "$HTTP_CODE"
assert_nonempty "feedback anchored to HCS (sequence_number)" "$(json_field "$HTTP_BODY" sequence_number)"
assert_nonempty "consensus timestamp present" "$(json_field "$HTTP_BODY" consensus_timestamp)"

# ===========================================================================
banner "Tutorial 03 — Discovery & Marketplace"
# ===========================================================================

# Step 1 ---------------------------------------------------------------------
step "1" "Register your agent in the HCS-14 directory"
vibe_says "Add my agent to the public agent directory so other agents can find me."
ai_runs "POST /api/v1/hedera/identity/directory/register"
http_post "/api/v1/hedera/identity/directory/register" \
  "{\"agent_did\":\"$HEDERA_DID\",\"capabilities\":[\"finance\",\"analysis\"],\"role\":\"analyst\",\"reputation_score\":0}"
assert_http_2xx "directory register" "$HTTP_CODE"
assert_nonempty "directory transaction_id" "$(json_field "$HTTP_BODY" transaction_id)"

# Step 4 ---------------------------------------------------------------------
step "4" "Send an HCS-10 message to another agent"
vibe_says "Send a task request to agent 0.0.88888 — ask them to analyze HBAR market conditions."
ai_runs "POST /hcs10/send"
http_post "/hcs10/send" \
  "{\"sender_did\":\"$HEDERA_DID\",\"recipient_did\":\"did:hedera:testnet:0.0.88888\",\"conversation_id\":\"walkthrough-conv-1\",\"message_type\":\"task_request\",\"payload\":{\"task\":\"analyze HBAR market conditions\"}}"
assert_http_2xx "HCS-10 send" "$HTTP_CODE"
assert_eq "HCS-10 status SUCCESS" "SUCCESS" "$(json_field "$HTTP_BODY" status)"
assert_nonempty "consensus timestamp on HCS-10" "$(json_field "$HTTP_BODY" consensus_timestamp)"

# Step 8 ---------------------------------------------------------------------
step "8" "Browse the agent marketplace"
vibe_says "Show me what agents are available in the marketplace."
ai_runs "GET /marketplace/browse"
http_get "/marketplace/browse"
assert_http_2xx "marketplace browse" "$HTTP_CODE"

# ===========================================================================
# Result summary
# ===========================================================================

TOTAL=$((PASS_COUNT + FAIL_COUNT))

printf "\n${BOLD}${BLUE}══════════════════════════════════════════════════════════════════════${RESET}\n"
if [[ $FAIL_COUNT -eq 0 ]]; then
    printf "${BOLD}${GREEN}  WALKTHROUGH PASSED — %d/%d assertions green${RESET}\n" "$PASS_COUNT" "$TOTAL"
    printf "${BOLD}${BLUE}══════════════════════════════════════════════════════════════════════${RESET}\n"
    exit 0
else
    printf "${BOLD}${RED}  WALKTHROUGH FAILED — %d/%d assertions green, %d failed${RESET}\n" "$PASS_COUNT" "$TOTAL" "$FAIL_COUNT"
    printf "${BOLD}${BLUE}══════════════════════════════════════════════════════════════════════${RESET}\n"
    printf "\n${RED}Failures:${RESET}\n"
    for f in "${FAIL_DETAILS[@]}"; do
        printf "  - %s\n" "$f"
    done
    exit 1
fi
