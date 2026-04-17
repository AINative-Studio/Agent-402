# Claude Desktop Prompt: Developer Test Run

**Paste this entire prompt into Claude Desktop after opening the Agent-402 folder.**

---

You are an experienced developer testing the Agent-402 workshop curriculum. You can use all your normal developer abilities: run commands, inspect code, debug issues, read source files.

Your task: **Verify that every tutorial in `docs/workshop/tutorials/` works end-to-end against a running backend**, and record the session with asciinema for sharing.

## Execution Steps

1. **Install asciinema:**
   ```
   brew install asciinema
   brew install agg   # for GIF export
   ```

2. **Verify prerequisites:**
   - Python 3.9+ installed
   - `httpx` package available: `pip3 install httpx`
   - `.env` file exists (copy from `.env.example` if missing — the defaults work for testing)

3. **Run the smoke test first** to confirm everything imports:
   ```
   python3 scripts/workshop_smoke_test.py
   ```
   Expect 45/45 passing. If any fail, fix them before continuing.

4. **Record the end-to-end test run:**
   ```
   asciinema rec docs/workshop/recordings/developer-run.cast \
     --title "Developer Workshop Test Run" \
     --command "python3 scripts/workshop_e2e_test.py --persona developer --tutorial all"
   ```

   The orchestrator will:
   - Check if server is running; start it if not (on port 8000)
   - Execute all 3 tutorials step-by-step
   - Verify each API response against expected checkpoints
   - Write a markdown report per tutorial
   - Stop the server on exit

5. **Read the test reports:**
   ```
   ls docs/workshop/test-results/developer-*.md
   cat docs/workshop/test-results/developer-*.md
   ```

6. **Upload the recording:**
   ```
   asciinema upload docs/workshop/recordings/developer-run.cast
   ```
   Save the asciinema.org URL.

7. **Generate GIF for Luma embed:**
   ```
   agg --speed 2 docs/workshop/recordings/developer-run.cast docs/workshop/recordings/developer-run.gif
   ```

8. **If any checkpoints failed**, investigate:
   - Check the specific API endpoint in `backend/app/api/`
   - Check service logic in `backend/app/services/`
   - Is the failure a tutorial documentation bug, or a code bug?
   - File an issue or fix if it's blocking.

## Developer Analysis Deliverables

Write a report at `docs/workshop/test-results/DEVELOPER_ANALYSIS.md` covering:

1. **API path accuracy** — do the tutorial paths match actual routes? (Known: tutorials use `/api/v1/` but most actual routes are under `/v1/public/{project_id}/`)
2. **Response shape accuracy** — do documented response fields match actual responses?
3. **Error handling** — what happens when a user hits an edge case the tutorial doesn't cover?
4. **Performance** — how long does each tutorial hour actually take?
5. **Recommended tutorial fixes** with priority (P0 blocks workshop, P1 causes confusion, P2 nice-to-have)

## What to Report Back

When finished, tell Karsten:
1. The asciinema.org URL
2. X/Y checkpoints passed across all 3 tutorials
3. List of API path mismatches that need tutorial corrections
4. Any actual code bugs discovered (separate from tutorial docs)
5. Whether the workshop is ready to ship or needs fixes before May 5

Go.
