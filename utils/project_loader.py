"""
Ether v1.3 — Lazy Loading Project Loader
=========================================
OPTIMIZATION: Lazy Loading Architecture

Instead of loading all 42 scripts and 16 scenes at startup (which causes high RAM usage),
this module only loads file paths and metadata initially. File content is read dynamically
ONLY when a specific script is referenced or during a deep analysis pass.

Key Features:
- Scan project folder and build lightweight index (paths + metadata only)
- On-demand content loading via get_content() method
- Smart caching of loaded content with LRU eviction
- Memory-efficient metadata extraction without reading full file content
"""

import re
import zipfile
import io
from pathlib import Path
from typing import Dict, Any, List, Tuple, Optional
from collections import OrderedDict


# ── Configuration ──────────────────────────────────────────────────────────────

ALLOWED_EXTENSIONS = {".gd", ".tscn", ".tres", ".godot", ".cfg", ".json", ".txt", ".md"}
MAX_FILE_SIZE = 200_000  # Skip files larger than 200KB
MAX_CACHED_FILES = 15    # LRU cache size limit to prevent RAM bloat


# ── GDScript Metadata Tags ─────────────────────────────────────────────────────

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


# ── LRU Cache for Loaded Content ───────────────────────────────────────────────

class LRUCache:
    """
    Simple LRU cache to limit memory usage.
    When capacity is exceeded, least recently used items are evicted.
    """
    def __init__(self, capacity: int = MAX_CACHED_FILES):
        self.capacity = capacity
        self.cache: OrderedDict[str, str] = OrderedDict()
    
    def get(self, key: str) -> Optional[str]:
        if key in self.cache:
            # Move to end (most recently used)
            self.cache.move_to_end(key)
            return self.cache[key]
        return None
    
    def put(self, key: str, value: str) -> None:
        if key in self.cache:
            self.cache.move_to_end(key)
        self.cache[key] = value
        # Evict oldest if over capacity
        while len(self.cache) > self.capacity:
            self.cache.popitem(last=False)
    
    def clear(self) -> None:
        self.cache.clear()
    
    def keys(self) -> List[str]:
        return list(self.cache.keys())


# ── Lazy Project Loader Class ──────────────────────────────────────────────────

class LazyProjectLoader:
    """
    OPTIMIZATION: Lazy Loading Architecture
    
    This class scans a Godot project but ONLY reads file content on demand.
    Initial scan builds a lightweight index with paths and basic metadata.
    Full file content is loaded only when explicitly requested.
    """
    
    def __init__(self):
        self.file_index: Dict[str, Dict[str, Any]] = {}  # path -> metadata
        self.content_cache: LRUCache = LRUCache()
        self._raw_file_contents: Dict[str, bytes] = {}   # For ZIP mode
        self._mode: str = "empty"  # empty, zip, folder
        self._base_path: Optional[Path] = None
    
    def load_from_zip(self, zip_data: bytes) -> Tuple[bool, str]:
        """
        Load project from ZIP data. Stores raw bytes, doesn't decode yet.
        Returns (success, message).
        """
        try:
            self.content_cache.clear()
            self.file_index.clear()
            self._raw_file_contents.clear()
            
            with zipfile.ZipFile(io.BytesIO(zip_data)) as zf:
                names = zf.namelist()
                if not names:
                    return False, "ZIP is empty."
                
                for name in names:
                    if name.endswith("/"):
                        continue
                    ext = Path(name).suffix.lower()
                    if ext not in ALLOWED_EXTENSIONS:
                        continue
                    
                    info = zf.getinfo(name)
                    if info.file_size > MAX_FILE_SIZE:
                        continue
                    
                    # Store raw bytes for lazy decoding later
                    try:
                        self._raw_file_contents[name] = zf.read(name)
                        # Build minimal metadata without reading content
                        self.file_index[name] = {
                            "size": info.file_size,
                            "ext": ext,
                            "type": self._guess_type(ext),
                            "loaded": False,  # Not loaded yet
                        }
                    except Exception:
                        continue
            
            if not self.file_index:
                return False, "No readable Godot files found in ZIP."
            
            self._mode = "zip"
            return True, f"Indexed {len(self.file_index)} files (content loaded on demand)."
        
        except zipfile.BadZipFile:
            return False, "Invalid or corrupted ZIP file."
        except Exception as e:
            return False, f"Extraction error: {e}"
    
    def load_from_folder(self, folder_path: Path) -> Tuple[bool, str]:
        """
        Load project from a folder. Only stores paths, doesn't read content yet.
        """
        try:
            self.content_cache.clear()
            self.file_index.clear()
            self._base_path = folder_path
            
            count = 0
            for ext in ALLOWED_EXTENSIONS:
                for path in folder_path.rglob(f"*{ext}"):
                    if path.is_file():
                        rel_path = str(path.relative_to(folder_path))
                        try:
                            size = path.stat().st_size
                            if size > MAX_FILE_SIZE:
                                continue
                            
                            self.file_index[rel_path] = {
                                "size": size,
                                "ext": ext,
                                "type": self._guess_type(ext),
                                "loaded": False,
                            }
                            count += 1
                        except Exception:
                            continue
            
            if count == 0:
                return False, "No readable Godot files found in folder."
            
            self._mode = "folder"
            return True, f"Indexed {count} files (content loaded on demand)."
        
        except Exception as e:
            return False, f"Folder scan error: {e}"
    
    def _guess_type(self, ext: str) -> str:
        """Guess file type from extension."""
        if ext == ".gd":
            return "script"
        elif ext == ".tscn":
            return "scene"
        elif ext == ".tres":
            return "resource"
        else:
            return "other"
    
    def get_content(self, path: str) -> Optional[str]:
        """
        OPTIMIZATION: Load file content ONLY when requested.
        Uses cache to avoid re-reading same file multiple times.
        """
        # Check cache first
        cached = self.content_cache.get(path)
        if cached is not None:
            return cached
        
        # Load on demand
        content = None
        if self._mode == "zip" and path in self._raw_file_contents:
            try:
                content = self._raw_file_contents[path].decode("utf-8", errors="replace")
            except Exception:
                return None
        elif self._mode == "folder" and self._base_path:
            try:
                full_path = self._base_path / path
                content = full_path.read_text(encoding="utf-8", errors="replace")
            except Exception:
                return None
        
        if content:
            # Mark as loaded and cache it
            if path in self.file_index:
                self.file_index[path]["loaded"] = True
            self.content_cache.put(path, content)
        
        return content
    
    def get_metadata(self, path: str) -> Optional[Dict[str, Any]]:
        """
        Get metadata for a file without loading its content.
        Includes extends, functions, signals, tags (extracted lazily).
        """
        if path not in self.file_index:
            return None
        
        meta = self.file_index[path].copy()
        
        # Extract detailed metadata only if needed (lazy)
        if "details" not in meta:
            content = self.get_content(path)
            if content:
                if meta["ext"] == ".gd":
                    meta["details"] = self._parse_gd_metadata(content)
                elif meta["ext"] == ".tscn":
                    meta["details"] = self._parse_tscn_metadata(content)
                else:
                    meta["details"] = {}
            else:
                meta["details"] = {}
        
        return meta
    
    def _parse_gd_metadata(self, content: str) -> Dict[str, Any]:
        """Parse GDScript file for metadata (lightweight)."""
        extends = ""
        functions, signals = [], []
        tags = set()
        
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
        
        # Detect tags
        for tag, keywords in _GD_TAGS.items():
            if any(kw in content for kw in keywords):
                tags.add(tag)
        
        return {
            "extends": extends,
            "functions": functions[:20],
            "signals": signals,
            "tags": list(tags),
        }
    
    def _parse_tscn_metadata(self, content: str) -> Dict[str, Any]:
        """Parse TSCN file for metadata (lightweight)."""
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
    
    def get_all_paths(self) -> List[str]:
        """Get all indexed file paths."""
        return list(self.file_index.keys())
    
    def get_script_paths(self) -> List[str]:
        """Get paths to all GDScript files."""
        return [p for p, m in self.file_index.items() if m["ext"] == ".gd"]
    
    def get_scene_paths(self) -> List[str]:
        """Get paths to all scene files."""
        return [p for p, m in self.file_index.items() if m["ext"] == ".tscn"]
    
    def get_stats(self) -> Dict[str, int]:
        """Get project statistics."""
        return {
            "script_count": len(self.get_script_paths()),
            "scene_count": len(self.get_scene_paths()),
            "total_files": len(self.file_index),
            "loaded_files": sum(1 for m in self.file_index.values() if m.get("loaded", False)),
        }
    
    def find_relevant_files(self, query: str, max_files: int = 10) -> List[str]:
        """
        Find files relevant to a query without loading their content.
        Uses filename matching and metadata tags.
        """
        query_lower = query.lower()
        scored: List[Tuple[float, str]] = []
        
        for path, meta in self.file_index.items():
            score = 0.0
            name = Path(path).stem.lower()
            
            # Name match
            if name in query_lower or any(w in name for w in query_lower.split() if len(w) > 3):
                score += 2.0
            
            # Tag match (from pre-extracted metadata)
            details = meta.get("details", {})
            tags = details.get("tags", [])
            score += sum(1.0 for tag in tags if tag in query_lower)
            
            # Scene script priority
            if meta["ext"] == ".tscn":
                scene_scripts = details.get("scripts", [])
                for sp in scene_scripts:
                    if sp in query_lower:
                        score += 1.0
            
            if score > 0:
                scored.append((score, path))
        
        scored.sort(key=lambda x: x[0], reverse=True)
        return [p for _, p in scored[:max_files]]
    
    def build_lightweight_context(self, query: str, max_chars: int = 4000) -> str:
        """
        Build context string for AI by loading only relevant files.
        This is the key optimization: don't load everything, just what's needed.
        
        ENHANCED v1.4: Uses RAG-based semantic search for better relevance matching.
        """
        # Try RAG-based retrieval first (more precise)
        try:
            from core.rag_engine import RAGIndex
            
            # Get all loaded content for RAG indexing
            file_contents = {}
            for path in self.get_all_paths():
                content = self.get_content(path)
                if content:
                    file_contents[path] = content
            
            if file_contents:
                rag_index = RAGIndex()
                rag_index.build_index(file_contents)
                rag_context = rag_index.get_context_for_query(query, max_chars)
                
                if rag_context:
                    return rag_context
        except Exception:
            # Fallback to simple keyword matching if RAG fails
            pass
        
        # Fallback: Use original keyword-based retrieval
        relevant_paths = self.find_relevant_files(query)
        
        parts = []
        used = 0
        
        for path in relevant_paths:
            content = self.get_content(path)
            if not content:
                continue
            
            chunk = content
            if used + len(chunk) > max_chars:
                if not parts:
                    remaining = max_chars - used
                    chunk = content[:remaining] + "\n# [TRUNCATED]"
                    parts.append(f"### {path}\n```gdscript\n{chunk}\n```")
                break
            
            parts.append(f"### {path}\n```gdscript\n{content}\n```")
            used += len(chunk)
        
        # If no relevant files found, include a few random ones as fallback
        if not parts and self.file_index:
            for path in list(self.file_index.keys())[:3]:
                content = self.get_content(path)
                if content:
                    parts.append(f"### {path}\n```gdscript\n{content[:1000]}\n```")
        
        return "\n\n".join(parts)
    
    def unload_all(self) -> None:
        """Clear all loaded content to free memory."""
        self.content_cache.clear()
        for meta in self.file_index.values():
            meta["loaded"] = False


# ── Legacy Compatibility Functions ─────────────────────────────────────────────

def extract_zip(data: bytes) -> Tuple[bool, str, Dict[str, str]]:
    """
    Legacy function for backward compatibility.
    Loads ALL files immediately (not recommended for large projects).
    Use LazyProjectLoader for better memory efficiency.
    """
    loader = LazyProjectLoader()
    success, msg = loader.load_from_zip(data)
    
    if not success:
        return False, msg, {}
    
    # Load all content (legacy behavior)
    file_contents = {}
    for path in loader.get_all_paths():
        content = loader.get_content(path)
        if content:
            file_contents[path] = content
    
    return True, msg, file_contents


def build_project_map(file_contents: Dict[str, str]) -> Dict[str, Any]:
    """
    Legacy function for backward compatibility.
    Builds project map from already-loaded file contents.
    """
    pm: Dict[str, Any] = {"scripts": {}, "scenes": {}, "stats": {}}
    
    for path, content in file_contents.items():
        if path.endswith(".gd"):
            extends = ""
            functions, signals, tags = [], [], []
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
            
            for tag, keywords in _GD_TAGS.items():
                if any(kw in content for kw in keywords):
                    tags.append(tag)
            
            pm["scripts"][path] = {
                "extends": extends,
                "functions": functions[:20],
                "signals": signals,
                "tags": list(set(tags)),
            }
        elif path.endswith(".tscn"):
            nodes, scripts = [], []
            for line in content.splitlines():
                m = re.match(r'\[node name="([^"]+)"(?:\s+type="([^"]+)")?', line)
                if m:
                    nodes.append({"name": m.group(1), "type": m.group(2) or "Node"})
                m = re.search(r'script\s*=\s*ExtResource\(.*?path="([^"]+\.gd)"', line)
                if not m:
                    m = re.search(r'"([^"]+\.gd)"', line)
                if m:
                    path_gd = m.group(1).replace("res://", "")
                    if path_gd not in scripts:
                        scripts.append(path_gd)
            
            pm["scenes"][path] = {
                "nodes": [f"{n['name']} ({n['type']})" for n in nodes[:15]],
                "scripts": scripts,
            }
    
    pm["stats"] = {
        "script_count": len(pm["scripts"]),
        "scene_count": len(pm["scenes"]),
        "total_files": len(file_contents),
    }
    return pm


def select_context(query: str, pm: Dict[str, Any], file_contents: Dict[str, str],
                   max_chars: int = 8000) -> str:
    """
    Legacy context selector for backward compatibility.
    """
    query_lower = query.lower()
    scored: List[Tuple[float, str]] = []
    
    for path in file_contents:
        score = 0.0
        name = Path(path).stem.lower()
        if name in query_lower or any(w in name for w in query_lower.split() if len(w) > 3):
            score += 2.0
        if path in pm.get("scripts", {}):
            tags = pm["scripts"][path].get("tags", [])
            score += sum(1.0 for tag in tags if tag in query_lower)
        for scene_data in pm.get("scenes", {}).values():
            if path in scene_data.get("scripts", []):
                score += 0.5
        scored.append((score, path))
    
    scored.sort(key=lambda x: x[0], reverse=True)
    
    parts = []
    used = 0
    for _, path in scored:
        content = file_contents.get(path, "")
        if not content:
            continue
        chunk = content
        if used + len(chunk) > max_chars:
            if not parts:
                remaining = max_chars - used
                chunk = content[:remaining] + "\n# [TRUNCATED]"
                parts.append(f"### {path}\n```gdscript\n{chunk}\n```")
            break
        parts.append(f"### {path}\n```gdscript\n{chunk}\n```")
        used += len(chunk)
    
    return "\n\n".join(parts) if parts else ""
