# Project Lifecycle Documentation

**Version:** 1.0
**Last Updated:** 2026-01-10
**Applies To:** ZeroDB Projects API v1

---

## Overview

This document defines the complete lifecycle of a ZeroDB project, from creation through deletion. Understanding the project lifecycle is essential for building reliable agent-native systems that depend on ZeroDB for persistent memory, compliance auditing, and request ledgers.

---

## Project States

A ZeroDB project can exist in one of three states:

| State      | Description                                           | Can Perform Operations? | Billing Active? |
| ---------- | ----------------------------------------------------- | ----------------------- | --------------- |
| `ACTIVE`   | Project is fully operational and accepting all requests | Yes                     | Yes             |
| `SUSPENDED`| Project is temporarily disabled (admin or billing action) | No (read-only)          | Varies          |
| `DELETED`  | Project is marked for permanent deletion (soft delete) | No                      | No              |

---

## Lifecycle Diagram

```
┌─────────────┐
│   CREATE    │
│   PROJECT   │
└──────┬──────┘
       │
       v
┌─────────────────┐
│     ACTIVE      │◄──────┐
│   (default)     │       │
└────┬────────┬───┘       │
     │        │           │
     │        └───────────┼─────┐
     │                    │     │
     v                    │     v
┌────────────┐       ┌────────────────┐
│  DELETED   │       │   SUSPENDED    │
│ (terminal) │       │  (reversible)  │
└────────────┘       └────────────────┘
```

---

## State Transitions

### 1. Creation → ACTIVE

**Trigger:** `POST /v1/public/projects`

**Behavior:**
- All newly created projects start in `ACTIVE` state
- The project is immediately available for database operations
- The `status` field in the response is guaranteed to be `"ACTIVE"`

**Example:**
```bash
curl -X POST "https://api.ainative.studio/v1/public/projects" \
  -H "X-API-Key: your_api_key" \
  -H "Content-Type: application/json" \
  -d '{
    "name": "My New Project",
    "tier": "free"
  }'

# Response:
{
  "id": "proj_xyz789",
  "name": "My New Project",
  "status": "ACTIVE",  # ← Guaranteed on creation
  "tier": "free",
  "created_at": "2026-01-10T12:00:00Z"
}
```

---

### 2. ACTIVE → SUSPENDED

**Triggers:**
- Administrative action (policy violation)
- Billing failure (payment method declined)
- Manual suspension via admin API
- Account tier limits exceeded

**Behavior:**
- Project becomes read-only
- Write operations return `403 Forbidden`
- Existing data remains intact
- Can be reversed by resolving the underlying issue

**Error Response (when suspended):**
```json
{
  "detail": "Project is suspended. Reason: Billing payment failed.",
  "error_code": "PROJECT_SUSPENDED"
}
```

---

### 3. SUSPENDED → ACTIVE

**Triggers:**
- Payment method updated and validated
- Policy violation resolved
- Admin manual reactivation

**Behavior:**
- Project returns to full operational status
- All write operations resume
- No data loss during suspension period

---

### 4. ACTIVE → DELETED (Soft Delete)

**Triggers:**
- User-initiated deletion via API or dashboard
- Account closure
- Extended suspension period (30+ days default)

**Behavior:**
- Project is marked for deletion but not immediately purged
- All operations return `404 Not Found` or `403 Forbidden`
- Data enters grace period (typically 30 days)
- Can be recovered during grace period (contact support)

**Grace Period Recovery:**
- Contact support with project ID
- Data restored to `ACTIVE` state if within grace period
- After grace period, deletion becomes permanent

---

### 5. SUSPENDED → DELETED

**Triggers:**
- Suspended project not reactivated within grace period
- User-initiated deletion while in suspended state

**Behavior:**
- Same as ACTIVE → DELETED
- Grace period applies

---

### 6. DELETED → Permanent Deletion

**Triggers:**
- Grace period expires (30 days default)
- Explicit permanent deletion request (immediate)

**Behavior:**
- All project data permanently removed:
  - Vector embeddings
  - Database tables and rows
  - Events and audit logs
  - X402 request ledger
- **This operation is irreversible**
- Project ID is retired and cannot be reused

---

## Status Field Guarantees (DX Contract)

Per GitHub Issue #60 and PRD Section 9, the following guarantees apply:

### 1. Presence Guarantee

The `status` field **MUST** be present in all project-related API responses:

✅ **Guaranteed Endpoints:**
- `POST /v1/public/projects` (create)
- `GET /v1/public/projects` (list)
- `GET /v1/public/projects/{id}` (get details)

❌ **Invalid Responses:**
```json
// NEVER allowed - missing status field
{
  "id": "proj_abc",
  "name": "My Project"
  // ❌ status field is missing
}

// NEVER allowed - null status
{
  "id": "proj_abc",
  "name": "My Project",
  "status": null  // ❌ null is not allowed
}

// NEVER allowed - empty string
{
  "id": "proj_abc",
  "name": "My Project",
  "status": ""  // ❌ empty string is not allowed
}
```

### 2. Creation Default Guarantee

```json
// Always true for newly created projects
{
  "status": "ACTIVE"  // ✅ Guaranteed default
}
```

### 3. Valid Values Guarantee

The `status` field must be one of:
- `"ACTIVE"` (operational)
- `"SUSPENDED"` (read-only)
- `"DELETED"` (soft deleted)

Any other value violates the contract.

### 4. List Response Guarantee

When listing projects, **every** project object in the response array must include `status`:

```json
{
  "items": [
    {
      "id": "proj_001",
      "name": "Project 1",
      "status": "ACTIVE"  // ✅ Required
    },
    {
      "id": "proj_002",
      "name": "Project 2",
      "status": "SUSPENDED"  // ✅ Required
    }
  ],
  "total": 2
}
```

---

## Agent Integration Patterns

### Pattern 1: Pre-Flight Status Check

Before performing critical operations, agents should verify project status:

```python
def ensure_project_active(project_id: str) -> None:
    """Verify project is in ACTIVE state before proceeding."""
    project = zerodb_client.get_project(project_id)

    # Contract guarantee: status field is always present
    assert "status" in project, "Status field missing (contract violation)"

    if project["status"] != "ACTIVE":
        raise ProjectNotActiveError(
            f"Project {project_id} is {project['status']}, expected ACTIVE"
        )

# Usage in agent workflow
ensure_project_active(env.project_id)
# Now safe to proceed with operations
```

### Pattern 2: Graceful Degradation

Handle non-ACTIVE states gracefully:

```python
def write_to_ledger(project_id: str, entry: dict) -> bool:
    """Attempt to write to X402 ledger, handle suspended projects."""
    try:
        project = zerodb_client.get_project(project_id)

        if project["status"] == "ACTIVE":
            # Normal write path
            return zerodb_client.create_event(entry)

        elif project["status"] == "SUSPENDED":
            # Log to local cache for later replay
            local_cache.append(entry)
            logger.warning(f"Project {project_id} suspended, caching locally")
            return False

        elif project["status"] == "DELETED":
            # Cannot proceed
            raise ProjectDeletedError(f"Project {project_id} is deleted")

    except Exception as e:
        logger.error(f"Ledger write failed: {e}")
        return False
```

### Pattern 3: Status Monitoring

Log status changes for audit trail:

```python
def monitor_project_status(project_id: str) -> None:
    """Periodically check and log project status changes."""
    current = zerodb_client.get_project(project_id)
    previous_status = cache.get(f"status:{project_id}")

    if current["status"] != previous_status:
        # Status changed - log to events
        zerodb_client.create_event({
            "event_type": "project_status_changed",
            "data": {
                "project_id": project_id,
                "old_status": previous_status,
                "new_status": current["status"],
                "detected_at": datetime.utcnow().isoformat()
            }
        })

        cache.set(f"status:{project_id}", current["status"])
```

---

## Best Practices

### 1. Always Check Status Before Critical Operations

```python
# ✅ Good - verify status first
project = get_project(project_id)
if project["status"] == "ACTIVE":
    perform_critical_operation()

# ❌ Bad - assume project is active
perform_critical_operation()  # May fail if suspended
```

### 2. Handle All States Explicitly

```python
# ✅ Good - handle all states
status = project["status"]
if status == "ACTIVE":
    proceed_normally()
elif status == "SUSPENDED":
    handle_suspension()
elif status == "DELETED":
    handle_deletion()
else:
    raise ValueError(f"Unknown status: {status}")

# ❌ Bad - only handle happy path
if project["status"] == "ACTIVE":
    proceed_normally()
# What happens if suspended or deleted?
```

### 3. Log Status Transitions

```python
# ✅ Good - audit trail
def log_status_transition(project_id: str, old: str, new: str):
    zerodb_client.create_event({
        "event_type": "project_status_transition",
        "data": {
            "project_id": project_id,
            "from_status": old,
            "to_status": new,
            "timestamp": datetime.utcnow().isoformat()
        }
    })
```

### 4. Implement Retry Logic for Transient Failures

```python
# ✅ Good - retry with backoff
def get_project_with_retry(project_id: str, max_retries: int = 3) -> dict:
    for attempt in range(max_retries):
        try:
            project = zerodb_client.get_project(project_id)
            assert "status" in project  # Verify contract
            return project
        except (NetworkError, TimeoutError) as e:
            if attempt == max_retries - 1:
                raise
            time.sleep(2 ** attempt)  # Exponential backoff
```

---

## Testing Requirements

All implementations must validate project status behavior:

### Test Case 1: Creation Default

```python
def test_new_project_has_active_status():
    project = create_project(name="Test Project")
    assert "status" in project
    assert project["status"] == "ACTIVE"
```

### Test Case 2: Status Presence in List

```python
def test_list_projects_includes_status():
    projects = list_projects()
    for project in projects["items"]:
        assert "status" in project
        assert project["status"] in ["ACTIVE", "SUSPENDED", "DELETED"]
```

### Test Case 3: Status Never Null

```python
def test_status_never_null():
    project = get_project(project_id)
    assert project["status"] is not None
    assert project["status"] != ""
```

### Test Case 4: Suspended Project Rejects Writes

```python
def test_suspended_project_rejects_writes():
    # Assume project is suspended
    with pytest.raises(ProjectSuspendedError):
        zerodb_client.create_table(
            project_id=suspended_project_id,
            name="test_table",
            schema={}
        )
```

---

## Related Documentation

- [API Specification](/api-spec.md) - Detailed API endpoints
- [DX Contract](/DX-Contract.md) - Guaranteed behaviors
- [Developer Guide](/datamodel.md) - Integration patterns
- [PRD Section 9](/prd.md#9-system-architecture-mvp) - Stable demo expectations
- [Backlog Epic 1](/backlog.md#epic-1--public-projects-api-create--list) - User stories

---

## Support & Troubleshooting

### Common Issues

**Q: Project status is missing from response**
- **This is a contract violation.** Report immediately.
- Check API version (must be v1)
- Verify using documented endpoints

**Q: Cannot write to project after creation**
- Check project status (may be suspended due to billing)
- Verify API key permissions
- Check tier limits

**Q: Project deleted but data still visible**
- Project is in grace period (soft delete)
- Data will be permanently removed after 30 days
- Contact support for immediate permanent deletion

**Q: Status changed unexpectedly**
- Check billing status
- Review account notifications
- Check tier limits (project count, storage, etc.)

---

## Changelog

| Version | Date       | Changes                                    |
| ------- | ---------- | ------------------------------------------ |
| 1.0     | 2026-01-10 | Initial release - Issue #60 implementation |

---

## Compliance & Audit Notes

For agent-native fintech systems (per PRD):

1. **All status transitions must be logged** to the events table
2. **Status changes are auditable** via event stream
3. **Deletion grace period enables compliance reviews** before data loss
4. **Suspended states prevent non-compliant operations** while preserving data
5. **Status field consistency enables deterministic replay** of agent workflows

This aligns with:
- PRD Section 6: ZeroDB Integration (Compliance Events)
- PRD Section 10: Success Criteria (Replayability)
- PRD Section 11: Strategic Positioning (Regulated AI Systems)

---
