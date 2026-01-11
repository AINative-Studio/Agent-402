# Issues Created from Gap Analysis
**Date:** 2025-01-11
**Source:** GAP_ANALYSIS.md (530 lines)

All issues created from comprehensive PRD gap analysis comparing requirements vs actual implementation.

---

## Backend Issues (Agent-402 Repository)

### Critical Priority Issues

| Issue # | Title | Priority | Effort | Dependencies |
|---------|-------|----------|--------|--------------|
| [#72](https://github.com/AINative-Studio/Agent-402/issues/72) | Implement CrewAI Runtime with 3 Agent Personas | CRITICAL | 3 days | None |
| [#73](https://github.com/AINative-Studio/Agent-402/issues/73) | Add /.well-known/x402 Discovery Endpoint | CRITICAL | 4 hours | None |
| [#74](https://github.com/AINative-Studio/Agent-402/issues/74) | Implement AIKit x402.request Tool Wrapper | CRITICAL | 1 day | #72 |
| [#75](https://github.com/AINative-Studio/Agent-402/issues/75) | Implement DID-based ECDSA Signing and Verification | CRITICAL | 2 days | None |
| [#76](https://github.com/AINative-Studio/Agent-402/issues/76) | Create One-Command Demo Execution Script | CRITICAL | 1 day | #72, #73, #74, #75 |

### High Priority Issues

| Issue # | Title | Priority | Effort | Dependencies |
|---------|-------|----------|--------|--------------|
| [#77](https://github.com/AINative-Studio/Agent-402/issues/77) | Add /x402 Root Signed POST Endpoint | HIGH | 4 hours | #75 |
| [#78](https://github.com/AINative-Studio/Agent-402/issues/78) | Fix Service Dependency Injection for ZeroDB Client | HIGH | 1 day | None |
| [#79](https://github.com/AINative-Studio/Agent-402/issues/79) | Fix Embedding Dimension Validation and Test Failures | HIGH | 4 hours | None |

**Total Backend Issues:** 8
**Estimated Total Effort:** 9.5 days

---

## Frontend Issues (Agent-402-frontend Repository)

### High Priority Issues

| Issue # | Title | Priority | Effort | Dependencies |
|---------|-------|----------|--------|--------------|
| [#29](https://github.com/AINative-Studio/Agent-402-frontend/issues/29) | Add Real-Time CrewAI Workflow Visualization | HIGH | 2 days | Backend #72, #76 |
| [#33](https://github.com/AINative-Studio/Agent-402-frontend/issues/33) | Add Demo Dashboard with One-Click Launch | HIGH | 2 days | Backend #76 |

### Medium Priority Issues

| Issue # | Title | Priority | Effort | Dependencies |
|---------|-------|----------|--------|--------------|
| [#30](https://github.com/AINative-Studio/Agent-402-frontend/issues/30) | Add X402 Discovery Endpoint UI | MEDIUM | 1 day | Backend #73, #77 |
| [#31](https://github.com/AINative-Studio/Agent-402-frontend/issues/31) | Add DID Signature Verification Debugger | MEDIUM | 1.5 days | Backend #75 |
| [#32](https://github.com/AINative-Studio/Agent-402-frontend/issues/32) | Add Agent Tool Call Visualization and Tracing | MEDIUM | 2 days | Backend #74 |
| [#34](https://github.com/AINative-Studio/Agent-402-frontend/issues/34) | Enhance Run Replay with Workflow Step Navigation | MEDIUM | 1.5 days | None |

**Total Frontend Issues:** 6
**Estimated Total Effort:** 10 days

---

## Implementation Roadmap

### Phase 1: Core Backend (5 days)
**Goal:** Implement core PRD requirements

1. **Day 1-3:** Issue #72 - CrewAI Runtime
   - Create crew.py with 3 agent definitions
   - Define tasks for each agent
   - Implement crew orchestration

2. **Day 3-5:** Issue #75 - DID Signing/Verification
   - Implement ECDSA signing logic
   - Add signature verification
   - Create DID resolver

3. **Day 5 (4h):** Issue #73 - /.well-known/x402 endpoint
   - Add discovery endpoint
   - Update smoke_test.py

4. **Day 5 (4h):** Issue #77 - /x402 root endpoint
   - Add signed POST endpoint
   - Integrate signature verification

### Phase 2: Tool Abstraction (1 day)
**Goal:** Implement AIKit tool wrapper

5. **Day 6:** Issue #74 - AIKit x402.request Tool
   - Create tool wrapper
   - Register with CrewAI agents
   - Add tool tracing

### Phase 3: Demo Orchestration (1 day)
**Goal:** Create one-command demo

6. **Day 7:** Issue #76 - One-Command Demo
   - Create run_demo.sh
   - Create run_crew.py
   - Update README

### Phase 4: Test Fixes (1.5 days)
**Goal:** Fix failing tests

7. **Day 8:** Issue #78 - Service Dependency Injection
   - Create ZeroDB mock client
   - Fix service constructors
   - Update conftest.py

8. **Day 8.5:** Issue #79 - Embedding Dimension Fix
   - Standardize on 384-dim default
   - Fix dimension validator
   - Update test fixtures

### Phase 5: Frontend (10 days - Can run in parallel)
**Goal:** Build visualization and tooling

9. **Days 1-2:** Issue #33 - Demo Dashboard
   - Create demo launcher
   - Add progress tracking
   - Display results

10. **Days 3-4:** Issue #29 - Workflow Visualization
    - Create workflow viewer
    - Add real-time updates
    - Display agent states

11. **Days 5-6:** Issue #32 - Tool Call Tracer
    - Create tool tracer page
    - Add performance metrics
    - Build timeline view

12. **Day 7:** Issue #30 - X402 Discovery UI
    - Add discovery tab
    - Create protocol tester

13. **Days 8-9:** Issue #31 - Signature Debugger
    - Create signature debugger
    - Add DID resolver
    - Build verification UI

14. **Days 9-10:** Issue #34 - Run Replay Enhancement
    - Add step navigation
    - Create workflow diagram
    - Add playback controls

---

## Success Criteria (From PRD)

When all issues are complete, the system should:

- ✅ Run 3 CrewAI agents locally (Analyst, Compliance, Transaction)
- ✅ Execute one-command demo in < 5 minutes
- ✅ Support X402 protocol discovery (/.well-known/x402)
- ✅ Sign and verify requests with DID + ECDSA
- ✅ Provide AIKit tool abstraction (x402.request)
- ✅ Store all decisions in agent_memory
- ✅ Enable workflow replay from ZeroDB records
- ✅ Display real-time agent execution in UI
- ✅ Pass all tests (1,426 total)

---

## Test Impact

### Current Test Status
- 915 passing (64.2%)
- 495 failing (34.7%)
- 81 errors (5.7%)

### Expected After Issues Complete
- **Issue #78** → Fixes 495 failing tests (service injection)
- **Issue #79** → Fixes 155 embedding tests
- **Other fixes** → Address remaining errors

**Target:** 95%+ test pass rate (1,355+ passing tests)

---

## PRD Compliance Progress

### Before Issues
- **55% PRD Compliant** (6/11 core requirements)

### After Issues Complete
- **100% PRD Compliant** (11/11 core requirements)

| Requirement | Before | After |
|-------------|--------|-------|
| ZeroDB Collections | ✅ | ✅ |
| CrewAI Runtime | ❌ | ✅ (#72) |
| AIKit Tool | ❌ | ✅ (#74) |
| /.well-known/x402 | ❌ | ✅ (#73) |
| /x402 Endpoint | ❌ | ✅ (#77) |
| DID Signing | ⚠️ | ✅ (#75) |
| One-Command Demo | ⚠️ | ✅ (#76) |
| Frontend Viz | ✅ | ✅ |
| API Endpoints | ✅ | ✅ |
| Tests Passing | ⚠️ | ✅ (#78, #79) |

---

## Notes

1. **Critical Path:** Issues #72, #75, #73, #74 must complete before #76 (demo)
2. **Parallel Work:** Frontend issues can be developed alongside backend issues
3. **Test Dependencies:** Issues #78 and #79 unblock test reliability
4. **Documentation:** Each issue includes detailed acceptance criteria and implementation examples

---

## References

- **Gap Analysis:** `/Users/aideveloper/Agent-402/GAP_ANALYSIS.md`
- **PRD:** `/Users/aideveloper/Agent-402/docs/product/PRD.md`
- **Backend Repo:** https://github.com/AINative-Studio/Agent-402
- **Frontend Repo:** https://github.com/AINative-Studio/Agent-402-frontend

---

**Created:** 2025-01-11
**Total Issues:** 14 (8 backend, 6 frontend)
**Total Estimated Effort:** 19.5 days (9.5 backend + 10 frontend, can overlap)
