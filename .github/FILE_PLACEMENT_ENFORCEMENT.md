# File Placement Enforcement

This directory contains enforcement mechanisms for `.claude/skills/file-placement` rules.

## Current Status

✅ **File placement rules APPLIED** - All documentation organized (Commit: 26197ed)
⚠️ **GitHub Actions workflow created** - Needs manual push with `workflow` scope
✅ **Pre-commit hook ready** - Available in `.github/hooks/pre-commit`

## Enforcement Mechanisms

### 1. GitHub Actions Workflow (Automated CI/CD)

**File:** `.github/workflows/file-placement-check.yml`

**Status:** Created but not pushed (requires `workflow` scope OAuth token)

**To Enable:**
```bash
# Push with a token that has workflow scope, or
# Manually create this workflow in GitHub UI
```

**What it checks:**
- ❌ No .md files in root (except README.md, CLAUDE.md)
- ❌ No .sh files in root
- ❌ No .sh files in backend/ (except start.sh)
- ❌ No .md files in src/backend/

**When it runs:**
- On pull requests that modify .md or .sh files
- On push to main branch

### 2. Pre-commit Hook (Local Enforcement)

**File:** `.github/hooks/pre-commit`

**Status:** ✅ Ready to use

**To Install:**
```bash
# From project root
cp .github/hooks/pre-commit .git/hooks/pre-commit
chmod +x .git/hooks/pre-commit
```

**What it checks:**
- Blocks commits with .md files in root (except README.md, CLAUDE.md)
- Blocks commits with .sh files in root
- Blocks commits with .sh files in backend/ (except start.sh)
- Blocks commits with .md files in src/backend/

### 3. Manual Review Checklist

Before creating/moving files, verify:

- [ ] Is this a .md file? → Must go in `docs/{category}/`
- [ ] Is this a .sh file? → Must go in `scripts/` (except `backend/start.sh`)
- [ ] Am I creating in root? → STOP, use subdirectory
- [ ] Did I check the file-placement skill? → `/file-placement`

## File Placement Rules

| File Type | ❌ Forbidden Location | ✅ Required Location |
|-----------|----------------------|---------------------|
| Documentation (.md) | `/` (root) | `docs/{category}/` |
| Documentation (.md) | `src/backend/` | `docs/{category}/` |
| Scripts (.sh) | `/` (root) | `scripts/` |
| Scripts (.sh) | `backend/` | `scripts/` (except `start.sh`) |

**Exceptions:**
- ✅ `README.md` (root)
- ✅ `CLAUDE.md` (root)
- ✅ `backend/start.sh` (only this one)

## Documentation Categories

| Category | Location | Use For |
|----------|----------|---------|
| Product | `docs/product/` | PRDs, requirements |
| Planning | `docs/planning/` | Backlog, sprint plans |
| Backend | `docs/backend/` | Backend architecture, data models |
| API | `docs/api/` | API specs, examples |
| Issues | `docs/issues/` | Issue tracking, summaries |
| Reports | `docs/reports/` | Implementation reports |
| Quick Reference | `docs/quick-reference/` | Quick start guides |

## Enforcement History

**2026-01-11:** File placement rules applied
- Moved 9 .md files from root to appropriate docs/ subdirectories
- Created enforcement mechanisms (GitHub Actions + pre-commit hook)
- All existing files now compliant

**Commits:**
- `26197ed` - Apply file-placement rules - Organize documentation files
- `ad5a717` - Add file-placement enforcement via GitHub Actions and hooks

## How to Use the Pre-commit Hook

### Install for This Repository

```bash
# From project root
cp .github/hooks/pre-commit .git/hooks/pre-commit
chmod +x .git/hooks/pre-commit
```

### Test It

```bash
# Try to create a violation
touch test.md
git add test.md
git commit -m "test"

# Expected: Hook blocks the commit with helpful error message
```

### Bypass (Not Recommended)

```bash
# Only if you have a legitimate reason
git commit --no-verify -m "message"
```

## Troubleshooting

### "Workflow scope" Error When Pushing

**Error:**
```
refusing to allow an OAuth App to create or update workflow
```

**Solution:**
1. Create the workflow manually in GitHub UI
2. OR use a token with `workflow` scope
3. OR ask team member with admin access to push it

### Hook Not Running

**Check:**
```bash
ls -la .git/hooks/pre-commit
# Should show executable permissions (-rwxr-xr-x)
```

**Fix:**
```bash
chmod +x .git/hooks/pre-commit
```

## Related

- `.claude/skills/file-placement` - File placement rules skill
- `.claude/RULES.MD` - Deprecated, migrated to skills
- `docs/` - All documentation lives here
- `scripts/` - All utility scripts live here
