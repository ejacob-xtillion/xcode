#!/usr/bin/env python3
"""
Automated conflict resolution helper for xCode repository.

Common conflict patterns and resolutions:
1. xcode/__init__.py - Remove old import statements
2. tests/test_agent_runner.py - Keep commented stub tests
3. Import sections - Merge both sets of imports
"""
import subprocess
import sys
from pathlib import Path


def run_command(cmd: str) -> tuple[int, str]:
    """Run a shell command and return exit code and output."""
    result = subprocess.run(cmd, shell=True, capture_output=True, text=True)
    return result.returncode, result.stdout + result.stderr


def check_conflicts() -> list[str]:
    """Check for files with merge conflicts."""
    code, output = run_command("git diff --name-only --diff-filter=U")
    if code != 0:
        return []
    return [f.strip() for f in output.split('\n') if f.strip()]


def resolve_init_py(file_path: Path) -> bool:
    """
    Resolve conflicts in xcode/__init__.py.
    
    Common issue: Old imports for utils/validation modules that don't exist.
    Resolution: Remove these imports, keep only valid ones.
    """
    if not file_path.exists():
        return False
    
    content = file_path.read_text()
    
    # Check if there are conflict markers
    if '<<<<<<< HEAD' not in content:
        return False
    
    print(f"Resolving conflicts in {file_path}...")
    
    # Remove old imports that cause issues
    lines = content.split('\n')
    resolved_lines = []
    in_conflict = False
    skip_section = False
    
    for line in lines:
        if '<<<<<<< HEAD' in line:
            in_conflict = True
            continue
        elif '=======' in line:
            skip_section = not skip_section
            continue
        elif '>>>>>>>' in line:
            in_conflict = False
            skip_section = False
            continue
        
        # Skip lines with problematic imports
        if 'from .utils import' in line or 'from .validation import' in line:
            continue
        
        if not in_conflict or not skip_section:
            resolved_lines.append(line)
    
    # Write resolved content
    file_path.write_text('\n'.join(resolved_lines))
    print(f"✓ Resolved {file_path}")
    return True


def resolve_test_agent_runner(file_path: Path) -> bool:
    """
    Resolve conflicts in tests/test_agent_runner.py.
    
    Common issue: Stub tests that were removed/commented.
    Resolution: Keep the version without stub tests (or with commented stubs).
    """
    if not file_path.exists():
        return False
    
    content = file_path.read_text()
    
    if '<<<<<<< HEAD' not in content:
        return False
    
    print(f"Resolving conflicts in {file_path}...")
    
    # For test_agent_runner, prefer the version without stub tests
    # (they're obsolete after la-factoria integration)
    lines = content.split('\n')
    resolved_lines = []
    in_conflict = False
    use_head = True  # Prefer HEAD version (usually has stub tests removed)
    
    for line in lines:
        if '<<<<<<< HEAD' in line:
            in_conflict = True
            continue
        elif '=======' in line:
            use_head = False
            continue
        elif '>>>>>>>' in line:
            in_conflict = False
            use_head = True
            continue
        
        if not in_conflict or use_head:
            resolved_lines.append(line)
    
    file_path.write_text('\n'.join(resolved_lines))
    print(f"✓ Resolved {file_path}")
    return True


def auto_resolve_conflicts() -> bool:
    """
    Automatically resolve common merge conflicts.
    
    Returns:
        True if all conflicts were resolved, False otherwise
    """
    conflicts = check_conflicts()
    
    if not conflicts:
        print("No merge conflicts found.")
        return True
    
    print(f"Found {len(conflicts)} file(s) with conflicts:")
    for f in conflicts:
        print(f"  - {f}")
    print()
    
    resolved = []
    unresolved = []
    
    for conflict_file in conflicts:
        file_path = Path(conflict_file)
        
        # Try specific resolvers
        if file_path.name == "__init__.py" and "xcode" in str(file_path):
            if resolve_init_py(file_path):
                resolved.append(conflict_file)
            else:
                unresolved.append(conflict_file)
        elif file_path.name == "test_agent_runner.py":
            if resolve_test_agent_runner(file_path):
                resolved.append(conflict_file)
            else:
                unresolved.append(conflict_file)
        else:
            unresolved.append(conflict_file)
    
    # Stage resolved files
    if resolved:
        print(f"\n✓ Auto-resolved {len(resolved)} file(s):")
        for f in resolved:
            print(f"  - {f}")
            run_command(f"git add {f}")
    
    if unresolved:
        print(f"\n⚠ Could not auto-resolve {len(unresolved)} file(s):")
        for f in unresolved:
            print(f"  - {f}")
        print("\nPlease resolve these manually.")
        return False
    
    return True


def main():
    """Main entry point."""
    print("xCode Merge Conflict Resolver\n")
    
    # Check if we're in a git repo
    code, _ = run_command("git rev-parse --git-dir")
    if code != 0:
        print("Error: Not in a git repository")
        sys.exit(1)
    
    # Check if there's a merge/rebase in progress
    code, output = run_command("git status")
    if "rebase in progress" not in output and "merge" not in output.lower():
        print("No merge or rebase in progress.")
        sys.exit(0)
    
    # Try to auto-resolve
    if auto_resolve_conflicts():
        print("\n✓ All conflicts resolved!")
        print("\nNext steps:")
        print("  1. Review the changes: git diff --staged")
        print("  2. Continue rebase: git rebase --continue")
        print("  3. Or continue merge: git commit")
    else:
        print("\n⚠ Some conflicts require manual resolution.")
        print("\nCommon patterns:")
        print("  - xcode/__init__.py: Remove 'from .utils import' and 'from .validation import'")
        print("  - tests/test_agent_runner.py: Keep version without stub tests")
        sys.exit(1)


if __name__ == "__main__":
    main()
