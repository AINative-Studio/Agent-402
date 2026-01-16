# GitHub Issues Created - Frontend-Backend Gap Closure
**Date:** 2026-01-11
**Status:** All issues successfully created

---

## Summary

Created **7 GitHub issues** across both repositories to address all identified frontend-backend integration gaps.

- **Backend Issues:** 5 issues in Agent-402 repository
- **Frontend Issues:** 2 issues in Agent-402-frontend repository
- **Epic Tracking:** 1 master tracking issue

---

## Backend Issues (Agent-402 Repository)

### Issue #80: Add PATCH endpoint for agent updates
**URL:** https://github.com/AINative-Studio/Agent-402/issues/80
**Priority:** Critical (P0)
**Component:** Backend API
**Type:** Enhancement

**Description:** Frontend expects `PATCH /v1/public/{project_id}/agents/{agent_id}` to update agent properties, but this endpoint is currently missing.

**Impact:** UpdateAgentModal component completely fails without this endpoint.

**Estimated Work:** 2 hours

---

### Issue #81: Add DELETE endpoint for agent deletion
**URL:** https://github.com/AINative-Studio/Agent-402/issues/81
**Priority:** High (P0)
**Component:** Backend API
**Type:** Enhancement

**Description:** Frontend expects `DELETE /v1/public/{project_id}/agents/{agent_id}` to permanently remove agents, but this endpoint is currently missing.

**Impact:** Agent deletion feature completely fails.

**Estimated Work:** 1.5 hours

---

### Issue #82: Add DELETE endpoint for vector deletion
**URL:** https://github.com/AINative-Studio/Agent-402/issues/82
**Priority:** High (P0)
**Component:** Backend API
**Type:** Enhancement

**Description:** Frontend expects `DELETE /v1/public/{project_id}/database/vectors/{vector_id}` to remove vectors from the database.

**Impact:** Document deletion feature completely fails.

**Estimated Work:** 1.5 hours

---

### Issue #83: Add POST /embeddings/compare endpoint
**URL:** https://github.com/AINative-Studio/Agent-402/issues/83
**Priority:** Medium (P1)
**Component:** Backend API
**Type:** Enhancement

**Description:** Frontend has a comparison feature for analyzing semantic similarity between two text inputs, but the backend endpoint is missing.

**Impact:** Embedding comparison feature unavailable.

**Estimated Work:** 2 hours

---

### Issue #84: Use agent_id as primary field in Agent responses
**URL:** https://github.com/AINative-Studio/Agent-402/issues/84
**Priority:** Medium (P1)
**Component:** Backend API
**Type:** Enhancement, Breaking Change (minor)

**Description:** Backend currently returns `id` as the primary identifier, but should use `agent_id` for consistency with other models (run_id, project_id, event_id, etc.).

**Impact:** Field naming is inconsistent across the API.

**Estimated Work:** 2 hours

---

## Frontend Issues (Agent-402-frontend Repository)

### Issue #35: Update useAgents hook to match backend path structure
**URL:** https://github.com/AINative-Studio/Agent-402-frontend/issues/35
**Priority:** Critical (P0)
**Component:** Frontend Hooks
**Type:** Bug

**Description:** The useAgents hook is calling incorrect endpoint paths that don't match the backend implementation. Frontend expects project_id as query parameter, but backend requires it as path parameter.

**Current (Wrong):** `GET /v1/public/agents?project_id={id}`
**Expected (Correct):** `GET /v1/public/{projectId}/agents`

**Impact:** Agent management page completely fails. All agent CRUD operations broken.

**Estimated Work:** 1 hour

---

### Issue #36: Fix inconsistent embeddings search endpoint paths
**URL:** https://github.com/AINative-Studio/Agent-402-frontend/issues/36
**Priority:** Medium (P1)
**Component:** Frontend Hooks
**Type:** Bug

**Description:** Multiple frontend hooks are using inconsistent endpoint paths for embeddings search. The `useEmbeddings.ts` hook is missing the project_id path parameter.

**Impact:** Embedding search functionality in useEmbeddings hook fails.

**Estimated Work:** 0.5 hours

---

## Epic Tracking Issue

### Issue #85: [Epic] Frontend-Backend Integration Gap Closure
**URL:** https://github.com/AINative-Studio/Agent-402/issues/85
**Repository:** Agent-402 (Backend)
**Type:** Epic

**Description:** Master tracking issue for closing all identified integration gaps between frontend and backend.

**Tracks:**
- 5 backend issues (#80, #81, #82, #83, #84)
- 2 frontend issues (#35, #36)

**Total Estimated Work:** ~13.5 hours (approximately 2 development days)

**Success Criteria:**
- All 7 identified gaps resolved
- Integration test suite passing
- No errors in browser console
- All frontend features working end-to-end
- API documentation updated

---

## Implementation Timeline

### Phase 1: Backend Endpoints (Day 1 Morning)
- Implement missing PATCH, DELETE endpoints for agents
- Implement DELETE endpoint for vectors
- Deploy to staging environment

### Phase 2: Frontend Path Fixes (Day 1 Afternoon)
- Update useAgents hook with correct paths
- Fix embeddings search path consistency
- Test against staging backend

### Phase 3: Field Standardization (Day 2 Morning)
- Update backend to return agent_id as primary field
- Update frontend types if needed
- Add embeddings compare endpoint

### Phase 4: Testing & Validation (Day 2 Afternoon)
- Run integration test suite
- Manual QA testing
- Deploy to production

---

## Gap Priority Breakdown

### Critical (P0) - 4 Issues
1. Backend: Add PATCH /agents endpoint (#80)
2. Backend: Add DELETE /agents endpoint (#81)
3. Backend: Add DELETE /vectors endpoint (#82)
4. Frontend: Fix useAgents path structure (#35)

**Impact:** Core agent management completely broken without these fixes.

### High Priority (P1) - 3 Issues
1. Backend: Add POST /embeddings/compare (#83)
2. Backend: Standardize agent_id field (#84)
3. Frontend: Fix embeddings search paths (#36)

**Impact:** Important features unavailable but core functionality works.

---

## Files Requiring Modification

### Backend Files
- `/Users/aideveloper/Agent-402/backend/app/api/agents.py` - Add PATCH, DELETE endpoints
- `/Users/aideveloper/Agent-402/backend/app/api/vectors.py` - Add DELETE endpoint
- `/Users/aideveloper/Agent-402/backend/app/api/embeddings.py` - Add POST /compare endpoint
- `/Users/aideveloper/Agent-402/backend/app/schemas/agent.py` - Add UpdateAgentRequest, update AgentResponse
- `/Users/aideveloper/Agent-402/backend/app/schemas/embedding.py` - Add CompareEmbeddingsRequest/Response
- `/Users/aideveloper/Agent-402/backend/tests/api/test_agents.py` - Add tests
- `/Users/aideveloper/Agent-402/backend/tests/api/test_vectors.py` - Add tests
- `/Users/aideveloper/Agent-402/backend/tests/api/test_embeddings.py` - Add tests

### Frontend Files
- `/Users/aideveloper/Agent-402-frontend/src/hooks/useAgents.ts` - Fix endpoint paths
- `/Users/aideveloper/Agent-402-frontend/src/hooks/useEmbeddings.ts` - Fix search path

---

## Related Documentation

- **Gap Analysis:** `/Users/aideveloper/Agent-402/FRONTEND_BACKEND_GAP_ANALYSIS.md`
- **Frontend Repository:** https://github.com/AINative-Studio/Agent-402-frontend
- **Backend Repository:** https://github.com/AINative-Studio/Agent-402

---

## Issue Links Quick Reference

### Backend Issues
- #80: https://github.com/AINative-Studio/Agent-402/issues/80
- #81: https://github.com/AINative-Studio/Agent-402/issues/81
- #82: https://github.com/AINative-Studio/Agent-402/issues/82
- #83: https://github.com/AINative-Studio/Agent-402/issues/83
- #84: https://github.com/AINative-Studio/Agent-402/issues/84
- #85: https://github.com/AINative-Studio/Agent-402/issues/85 (Epic)

### Frontend Issues
- #35: https://github.com/AINative-Studio/Agent-402-frontend/issues/35
- #36: https://github.com/AINative-Studio/Agent-402-frontend/issues/36

---

**Status:** All issues created successfully
**Next Steps:** Begin implementation starting with Phase 1 (Backend Endpoints)
