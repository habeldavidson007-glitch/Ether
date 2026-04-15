"""
Scanner — Builds a lightweight Project Map from .gd and .tscn files.
Patched: select_context now always returns files even on generic queries.
"""

import re
import zipfile
import io
from pathlib import Path
from typing import Dict, Any, List, Tuple


# ── GDScript Parser ────────────────────────────────────────────────────────────

_GD_TAGS = {
    "movement": ["velocity", "move_and_slide", "CharacterBody"],
    "input":    ["Input.", "action_pressed", "get_axis"],
    "combat":   ["damage", "health", "attack", "hit"],
    "ui":       ["Label", "Button", "Panel", "CanvasLayer"],
    "ai":       ["NavigationAgent", "pathfind", "chase", "patrol"],
    "physics":  ["RigidBody", "Area2D", "collision"],
    "audio":    ["AudioStreamPlayer", "play(", "stream"],
    "animation":["AnimationPlayer", "AnimatedSprite", "anim"],
    "camera":   ["Camera2D", "Camera3D", "follow"],
    "signal":   ["emit_signal", "connect(", "signal "],
}

# ── Issue Detector ─────────────────────────────────────────────────────────────

_ISSUE_PATTERNS = [
    (r'\bnull\b.*\.\w+',          "null dereference risk"),
    (r'while\s+true',             "infinite loop risk"),
    (r'get_node\(',               "get_node without @onready"),
    (r'print\(',                  "debug print left in code"),
    (r'_process\(.*\):[\s\S]{0,200}get_node\(', "get_node in _process (expensive)"),
    (r'for .+ in .+:\s*\n\s+for', "nested loop (O(n²) risk)"),
    (r'yield\(',                  "deprecated yield (use await)"),
    (r'\.connect\(.*,\s*["\']',   "old signal connect syntax"),
    (r'setget\s',                 "deprecated setget (use property)"),
]

_IMPROVEMENT_PATTERNS = [
    (r'var\s+\w+\s*=',            "consider @export or @onready for node refs"),
    (r'func _process',            "check if _physics_process is more appropriate"),
    (r'if\s+\w+\s*!=\s*null',     "consider is_instance_valid() for safety"),
    (r'#\s*TODO',                 "unresolved TODO comment"),
    (r'#\s*FIXME',                "unresolved FIXME comment"),
    (r'magic_number\s*=\s*\d+',  "magic number — consider const"),
    (r'^\s{8,}',                  "deep nesting — refactor candidate"),
]


def analyze_file_issues(content: str) -> Tuple[List[str], List[str]]:
    """Returns (issues, improvements) for a GDScript file."""
    issues = []
    improvements = []
    for pattern, label in _ISSUE_PATTERNS:
        if re.search(pattern, content):
            issues.append(label)
    for pattern, label in _IMPROVEMENT_PATTERNS:
        if re.search(pattern, content, re.MULTILINE):
            improvements.append(label)
    return issues, improvements


def _parse_gd(content: str) -> Dict[str, Any]:
    extends = ""
    functions, signals, variables, tags = [], [], [], []

    for line in content.splitlines():
        s = line.strip()
        if s.startswith("extends "):
            extends = s.split(None, 1)[1].strip()
        elif s.startswith("func "):
            m = re.match(r"func\s+(\w+)\s*\(", s)
            if m:
                functions.append(m.group(1))
        elif s.startswith("signal "):
            m = re.match(r"signal\s+(\w+)", s)
            if m:
                signals.append(m.group(1))
        elif re.match(r"^(var|const|@export|@onready)\s+(\w+)", s):
            m = re.match(r"^(?:var|const|@export|@onready)\s+(\w+)", s)
            if m:
                variables.append(m.group(1))

    for tag, keywords in _GD_TAGS.items():
        if any(kw in content for kw in keywords):
            tags.append(tag)

    issues, improvements = analyze_file_issues(content)

    return {
        "extends": extends,
        "functions": functions[:20],
        "signals": signals,
        "variables": variables[:15],
        "tags": list(set(tags)),
        "issues": issues,
        "improvements": improvements,
    }


# ── Scene Parser ───────────────────────────────────────────────────────────────

def _parse_tscn(content: str) -> Dict[str, Any]:
    nodes, scripts = [], []

    for line in content.splitlines():
        m = re.match(r'\[node name="([^"]+)"(?:\s+type="([^"]+)")?', line)
        if m:
            nodes.append({"name": m.group(1), "type": m.group(2) or "Node"})
        m = re.search(r'script\s*=\s*ExtResource\(.*?path="([^"]+\.gd)"', line)
        if not m:
            m = re.search(r'"([^"]+\.gd)"', line)
        if m:
            path = m.group(1).replace("res://", "")
            if path not in scripts:
                scripts.append(path)

    return {
        "nodes": [f"{n['name']} ({n['type']})" for n in nodes[:15]],
        "scripts": scripts,
    }


# ── Project Map Builder ────────────────────────────────────────────────────────

def build_project_map(file_contents: Dict[str, str]) -> Dict[str, Any]:
    pm: Dict[str, Any] = {"scripts": {}, "scenes": {}, "stats": {}}

    for path, content in file_contents.items():
        if path.endswith(".gd"):
            pm["scripts"][path] = _parse_gd(content)
        elif path.endswith(".tscn"):
            pm["scenes"][path] = _parse_tscn(content)

    # Global issue summary
    total_issues = sum(len(v.get("issues", [])) for v in pm["scripts"].values())
    total_improvements = sum(len(v.get("improvements", [])) for v in pm["scripts"].values())

    pm["stats"] = {
        "script_count": len(pm["scripts"]),
        "scene_count": len(pm["scenes"]),
        "total_files": len(file_contents),
        "total_issues": total_issues,
        "total_improvements": total_improvements,
    }
    return pm


# ── ZIP Extraction ─────────────────────────────────────────────────────────────

ALLOWED_EXTENSIONS = {".gd", ".tscn", ".tres", ".godot", ".cfg", ".json", ".txt", ".md"}
MAX_FILE_SIZE = 200_000


def extract_zip(data: bytes) -> Tuple[bool, str, Dict[str, str]]:
    try:
        file_contents: Dict[str, str] = {}
        with zipfile.ZipFile(io.BytesIO(data)) as zf:
            names = zf.namelist()
            if not names:
                return False, "ZIP is empty.", {}

            prefix = ""
            if all(n.startswith(names[0].split("/")[0] + "/") for n in names if "/" in n):
                prefix = names[0].split("/")[0] + "/"

            for name in names:
                if name.endswith("/"):
                    continue
                ext = Path(name).suffix.lower()
                if ext not in ALLOWED_EXTENSIONS:
                    continue
                info = zf.getinfo(name)
                if info.file_size > MAX_FILE_SIZE:
                    continue
                rel = name[len(prefix):] if prefix and name.startswith(prefix) else name
                try:
                    file_contents[rel] = zf.read(name).decode("utf-8", errors="replace")
                except Exception:
                    continue

        if not file_contents:
            return False, "No readable Godot files found in ZIP.", {}

        return True, f"Loaded {len(file_contents)} files.", file_contents

    except zipfile.BadZipFile:
        return False, "Invalid or corrupted ZIP file.", {}
    except Exception as e:
        return False, f"Extraction error: {e}", {}


# ── Context Selector (PATCHED) ─────────────────────────────────────────────────

def select_context(query: str, pm: Dict[str, Any], file_contents: Dict[str, str],
                   max_chars: int = 8000) -> str:
    """
    Smart context: pick files most relevant to query.
    PATCH: when no strong match, falls back to returning ALL files up to char limit.
    """
    query_lower = query.lower()
    scored: List[Tuple[float, str]] = []

    for path in file_contents:
        score = 0.0
        name = Path(path).stem.lower()
        # Name match
        if name in query_lower or any(w in name for w in query_lower.split() if len(w) > 3):
            score += 2.0
        # Tag match
        if path in pm.get("scripts", {}):
            tags = pm["scripts"][path].get("tags", [])
            score += sum(1.0 for tag in tags if tag in query_lower)
            # Boost files with issues if query is debug/analyze
            debug_words = {"fix", "issue", "bug", "crash", "error", "problem", "wrong", "broken", "list"}
            if any(w in query_lower for w in debug_words):
                issue_count = len(pm["scripts"][path].get("issues", []))
                score += issue_count * 0.5
        # Scene script priority
        for scene_data in pm.get("scenes", {}).values():
            if path in scene_data.get("scripts", []):
                score += 0.5
        scored.append((score, path))

    scored.sort(key=lambda x: x[0], reverse=True)

    # PATCH: always include files — no zero-score gating
    parts = []
    used = 0
    for _, path in scored:
        content = file_contents.get(path, "")
        if not content:
            continue
        chunk = content
        if used + len(chunk) > max_chars:
            # Include truncated version if nothing yet
            if not parts:
                remaining = max_chars - used
                chunk = content[:remaining] + "\n# [TRUNCATED]"
                parts.append(f"### {path}\n```gdscript\n{chunk}\n```")
            break
        parts.append(f"### {path}\n```gdscript\n{chunk}\n```")
        used += len(chunk)

    return "\n\n".join(parts) if parts else ""
