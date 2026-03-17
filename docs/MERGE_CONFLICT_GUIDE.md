# Merge Conflict Resolution Guide

This guide helps you resolve common merge conflicts in the xCode repository.

---

## Quick Resolution

### Automated Tool

Use the automated conflict resolver:

```bash
python scripts/resolve_conflicts.py
```

This handles the most common conflict patterns automatically.

---

## Common Conflict Patterns

### 1. `xcode/__init__.py` - Import Conflicts

**Problem:** Old branches may have imports for modules that no longer exist (`utils`, `validation`).

**Conflict looks like:**
```python
<<<<<<< HEAD
# Empty or minimal imports
=======
from .utils import something
from .validation import something_else
>>>>>>> feature/branch
```

**Resolution:**
```python
# Keep it simple - remove old imports
# The file should be minimal or empty
```

**Manual fix:**
```bash
# Edit the file to remove old imports
vim xcode/__init__.py
# Remove lines with: from .utils import, from .validation import
git add xcode/__init__.py
```

---

### 2. `tests/test_agent_runner.py` - Stub Test Conflicts

**Problem:** Old branches have stub tests that were removed after la-factoria integration.

**Conflict looks like:**
```python
<<<<<<< HEAD
# No stub tests (or commented out)
=======
def test_run_stub_returns_success():
    # Old stub test
>>>>>>> feature/branch
```

**Resolution:**
Keep the HEAD version (without stub tests or with them commented out).

**Manual fix:**
```bash
git checkout --ours tests/test_agent_runner.py
git add tests/test_agent_runner.py
```

---

### 3. Import Section Conflicts

**Problem:** Multiple branches add different imports to the same file.

**Conflict looks like:**
```python
<<<<<<< HEAD
from xcode.task_classifier import TaskClassifier
=======
from xcode.file_cache import get_cache_manager
>>>>>>> feature/branch
```

**Resolution:**
Merge both imports together:
```python
from xcode.task_classifier import TaskClassifier
from xcode.file_cache import get_cache_manager
```

**Manual fix:**
```bash
# Edit the file to include both imports
vim xcode/agent_runner.py
# Combine imports from both sections
git add xcode/agent_runner.py
```

---

## Step-by-Step Resolution Process

### When Push Fails with Conflicts

1. **Fetch latest changes**
   ```bash
   git fetch origin
   ```

2. **Try to rebase (recommended)**
   ```bash
   git rebase origin/main
   ```
   
   Or merge:
   ```bash
   git merge origin/main
   ```

3. **Check for conflicts**
   ```bash
   git status
   ```
   
   Look for "Unmerged paths" or "both modified" files.

4. **Use automated resolver**
   ```bash
   python scripts/resolve_conflicts.py
   ```

5. **If auto-resolution worked:**
   ```bash
   git rebase --continue  # or git commit if merging
   ```

6. **If manual resolution needed:**
   - Edit each conflicted file
   - Remove conflict markers (`<<<<<<<`, `=======`, `>>>>>>>`)
   - Keep the correct version or merge both
   - Stage the file: `git add <file>`
   - Continue: `git rebase --continue` or `git commit`

7. **Push again**
   ```bash
   git push origin main
   ```

---

## Prevention Strategies

### 1. Pull Before Starting Work

Always sync with origin before creating a branch:

```bash
git checkout main
git pull origin main
git checkout -b feature/my-feature
```

### 2. Keep Branches Short-Lived

Merge feature branches quickly to avoid drift:
- Work on one feature at a time
- Merge within 1-2 days
- Delete merged branches immediately

### 3. Rebase Regularly

Keep your feature branch up to date:

```bash
git checkout feature/my-feature
git fetch origin
git rebase origin/main
```

### 4. Use Merge Strategy

For complex features, use merge instead of rebase:

```bash
git checkout main
git merge --no-ff feature/my-feature
```

This preserves the feature branch history and makes conflicts easier to resolve.

---

## Specific File Guidelines

### `xcode/__init__.py`

**Keep it minimal:**
```python
"""xCode - AI-powered coding assistant with knowledge graphs."""

__version__ = "0.1.0"
```

**Never add imports for:**
- `utils` module (doesn't exist)
- `validation` module (doesn't exist)
- Any other non-existent modules

### `xcode/agent_runner.py`

**Import order:**
1. Standard library
2. Third-party (httpx, rich)
3. Local imports (config, result, schema, task_classifier, file_cache)

**When adding new imports:**
- Add them in the correct section
- Keep alphabetical order within sections
- Check if the module exists before importing

### `tests/test_agent_runner.py`

**Current state:**
- Stub tests are commented out (obsolete after la-factoria)
- Only integration tests remain
- If conflicts arise, prefer the version without stub tests

---

## Troubleshooting

### "fatal: no rebase in progress"

You're not in a rebase. Check `git status` to see actual state.

### "error: Your local changes would be overwritten"

You have uncommitted changes:
```bash
git status
git stash  # Save changes
# Or commit them
git add -A
git commit -m "WIP: save changes"
```

### "both modified" files persist

Conflict markers still exist in files:
```bash
# Check for markers
grep -r "<<<<<<< HEAD" .
# Edit files to remove markers
# Stage resolved files
git add <file>
```

### Push rejected (non-fast-forward)

Origin has commits you don't have:
```bash
git fetch origin
git rebase origin/main  # Recommended
# Or
git merge origin/main   # Alternative
```

---

## Emergency Recovery

### Abort Everything and Start Fresh

If conflicts are too complex:

```bash
# Abort rebase
git rebase --abort

# Or abort merge
git merge --abort

# Reset to origin
git fetch origin
git reset --hard origin/main

# Re-apply your changes
git cherry-pick <your-commit-sha>
```

### Lost Commits

If you accidentally lost commits:

```bash
# Find lost commits
git reflog

# Recover a commit
git cherry-pick <commit-sha>
```

---

## Best Practices

1. **Always test after resolving conflicts**
   ```bash
   python -m pytest tests/ -v
   ```

2. **Review resolved files**
   ```bash
   git diff --staged
   ```

3. **Use descriptive commit messages**
   ```bash
   git commit -m "fix: Resolve merge conflicts in __init__.py and test_agent_runner.py"
   ```

4. **Push immediately after resolving**
   ```bash
   git push origin main
   ```

5. **Communicate with team**
   - Let others know about major merges
   - Coordinate on shared files
   - Use feature flags for incomplete work

---

## Automated Workflow

Create an alias for the full workflow:

```bash
# Add to ~/.gitconfig or ~/.zshrc
alias xcode-push='git fetch origin && git rebase origin/main && python scripts/resolve_conflicts.py && git push origin main'
```

Usage:
```bash
xcode-push
```

This will:
1. Fetch latest changes
2. Rebase on origin/main
3. Auto-resolve conflicts
4. Push to origin

---

## Getting Help

If you encounter a conflict pattern not covered here:

1. **Check the conflict**
   ```bash
   git diff <conflicted-file>
   ```

2. **Understand both versions**
   - `<<<<<<< HEAD` = Your current branch
   - `=======` = Separator
   - `>>>>>>> branch` = Incoming changes

3. **Ask for help**
   - Document the conflict pattern
   - Update this guide
   - Add to automated resolver

---

## Related Files

- **Conflict Resolver:** `scripts/resolve_conflicts.py`
- **Git Workflow:** See README.md
- **Testing:** `tests/` directory

---

## Maintenance

This guide should be updated when:
- New conflict patterns emerge
- File structure changes
- New modules are added
- Import patterns change

Last updated: 2026-03-17
