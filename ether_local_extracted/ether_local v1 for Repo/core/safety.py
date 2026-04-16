"""
Safety — Diff preview and safe file writing.

Rules enforced here:
- Never write outside workspace/project/
- Never delete files
- Always show diff before applying
- Validate paths are clean

Replaces: execution_safety.py (412 lines → ~80 lines)
"""

import difflib
from pathlib import Path
from typing import Dict, List, Optional, Tuple


WORKSPACE = Path("workspace") / "project"


def safe_path(relative: str) -> Optional[Path]:
    """
    Resolve a relative path inside workspace/project/.
    Returns None if path escapes the workspace.
    """
    try:
        base = WORKSPACE.resolve()
        full = (base / relative).resolve()
        if not str(full).startswith(str(base)):
            return None
        return full
    except Exception:
        return None


def make_diff(old: str, new: str, filename: str) -> str:
    """Generate a unified diff string between old and new content."""
    old_lines = old.splitlines(keepends=True)
    new_lines = new.splitlines(keepends=True)
    diff = difflib.unified_diff(
        old_lines, new_lines,
        fromfile=f"a/{filename}",
        tofile=f"b/{filename}",
        lineterm=""
    )
    return "\n".join(diff)


def apply_changes(changes: List[Dict], file_contents: Dict[str, str]) -> Tuple[bool, str, Dict[str, str]]:
    """
    Write changes to workspace/project/.
    Returns (success, message, updated_file_contents).
    
    changes: list of {"file": str, "action": str, "content": str}
    """
    updated = dict(file_contents)
    written = []

    for change in changes:
        rel = change.get("file", "").lstrip("/")
        content = change.get("content", "")

        if not rel:
            continue

        target = safe_path(rel)
        if target is None:
            return False, f"Unsafe path rejected: {rel}", file_contents

        try:
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_text(content, encoding="utf-8")
            updated[rel] = content
            written.append(rel)
        except Exception as e:
            return False, f"Write failed for {rel}: {e}", file_contents

    return True, f"Applied {len(written)} file(s): {', '.join(written)}", updated


def preview_changes(changes: List[Dict], file_contents: Dict[str, str]) -> List[Dict]:
    """
    Generate diff previews for all changes without writing.
    Returns list of {file, action, diff, is_new} dicts.
    """
    previews = []
    for change in changes:
        rel = change.get("file", "").lstrip("/")
        new_content = change.get("content", "")
        old_content = file_contents.get(rel, "")
        is_new = rel not in file_contents

        diff = make_diff(old_content, new_content, rel) if not is_new else (
            f"NEW FILE: {rel}\n" + "\n".join(f"+ {line}" for line in new_content.splitlines()[:30])
        )

        previews.append({
            "file": rel,
            "action": change.get("action", "create_or_modify"),
            "diff": diff or "(no changes detected)",
            "is_new": is_new,
            "line_count": len(new_content.splitlines()),
        })
    return previews
