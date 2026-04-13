"""
Scanner — Builds a lightweight Project Map from .gd and .tscn files.

Replaces: cognitive_map.py (890 lines → ~120 lines)
Output: dict used as Ether's "memory" of the project structure.
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

    return {
        "extends": extends,
        "functions": functions[:20],
        "signals": signals,
        "variables": variables[:15],
        "tags": list(set(tags)),
    }


# ── Scene Parser ───────────────────────────────────────────────────────────────

def _parse_tscn(content: str) -> Dict[str, Any]:
    nodes, scripts = [], []

    for line in content.splitlines():
        # Node name + type
        m = re.match(r'\[node name="([^"]+)"(?:\s+type="([^"]+)")?', line)
        if m:
            nodes.append({"name": m.group(1), "type": m.group(2) or "Node"})
        # Attached script
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
    """
    Takes {filename: content} dict, returns Project Map JSON.
    This IS the system's understanding of the project.
    """
    pm: Dict[str, Any] = {"scripts": {}, "scenes": {}, "stats": {}}

    for path, content in file_contents.items():
        if path.endswith(".gd"):
            pm["scripts"][path] = _parse_gd(content)
        elif path.endswith(".tscn"):
            pm["scenes"][path] = _parse_tscn(content)

    pm["stats"] = {
        "script_count": len(pm["scripts"]),
        "scene_count": len(pm["scenes"]),
        "total_files": len(file_contents),
    }
    return pm


# ── ZIP Extraction ─────────────────────────────────────────────────────────────

ALLOWED_EXTENSIONS = {".gd", ".tscn", ".tres", ".godot", ".cfg", ".json", ".txt", ".md"}
MAX_FILE_SIZE = 200_000  # 200KB per file


def extract_zip(data: bytes) -> Tuple[bool, str, Dict[str, str]]:
    """
    Extract a ZIP into {relative_path: content}.
    Returns (success, message, file_contents).
    """
    try:
        file_contents: Dict[str, str] = {}
        with zipfile.ZipFile(io.BytesIO(data)) as zf:
            names = zf.namelist()
            if not names:
                return False, "ZIP is empty.", {}

            # Strip common top-level folder prefix
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


# ── Context Selector ───────────────────────────────────────────────────────────

def select_context(query: str, pm: Dict[str, Any], file_contents: Dict[str, str],
                   max_chars: int = 6000) -> str:
    """
    Smart context: pick files most relevant to the query.
    Returns concatenated file content string for the AI prompt.
    """
    query_lower = query.lower()
    scored: List[Tuple[float, str]] = []

    for path in file_contents:
        score = 0.0
        name = Path(path).stem.lower()
        # Name match
        if name in query_lower or any(w in name for w in query_lower.split() if len(w) > 3):
            score += 2.0
        # Tag match (scripts only)
        if path in pm.get("scripts", {}):
            tags = pm["scripts"][path].get("tags", [])
            score += sum(1.0 for tag in tags if tag in query_lower)
        # Active scene scripts get priority
        for scene_path, scene_data in pm.get("scenes", {}).items():
            if path in scene_data.get("scripts", []):
                score += 0.5
        scored.append((score, path))

    scored.sort(key=lambda x: x[0], reverse=True)

    parts = []
    used = 0
    for _, path in scored:
        content = file_contents.get(path, "")
        if used + len(content) > max_chars:
            break
        parts.append(f"### {path}\n```gdscript\n{content}\n```")
        used += len(content)

    return "\n\n".join(parts) if parts else ""
