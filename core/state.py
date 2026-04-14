"""
Ether State - Single source of truth for session identity.

Replaces: identity_engine, cognitive_controller, memory_system, todo_manager,
          strategy_engine, intent_engine (all collapsed into one lean module).

Design: flat, readable, no inheritance chains.
"""

import json
import math
import re
import time
from collections import Counter
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional

# ── Constants ──────────────────────────────────────────────────────────────────

MEMORY_CAP = 150
MEMORY_TOP_K = 3
SIM_THRESHOLD = 0.15

WORKSPACE = Path("workspace")
MEMORY_FILE = WORKSPACE / "memory.json"


# ── Intent Classification ──────────────────────────────────────────────────────

_CASUAL = {"hi", "hey", "hello", "thanks", "ok", "okay", "cool", "great", "lol", "nice"}
_DEBUG  = {"error", "crash", "fix", "bug", "broken", "fail", "exception", "traceback"}
_BUILD  = {"create", "generate", "build", "make", "add", "write", "implement", "new"}
_ANALYZE= {"analyze", "explain", "what", "how", "why", "understand", "review", "check"}


def is_casual(text: str) -> bool:
    """Detect casual/conversational input that should NOT trigger build pipeline."""
    text = text.lower().strip()

    if len(text) < 6:
        if any(k in text for k in ["fix", "bug", "error"]):
            return False
        if any(k in text for k in ["explain", "what", "how"]):
            return False
        return True

    casual_patterns = [
        "hi", "hello", "hey", "yo",
        "thanks", "thank you",
        "congrats", "congratulations",
        "lol", "lmao", "haha",
        "how are you",
        "good morning", "good night",
        "nice", "cool"
    ]

    if any(k in text for k in ["fix", "bug", "error", "debug"]):
        return False

    if any(k in text for k in ["explain", "what", "how", "analyze", "why"]):
        return False

    return any(p in text for p in casual_patterns)


def classify(text: str) -> str:
    """Classify user intent. Returns: casual, debug, build, analyze, or task."""
    text = text.lower()

    if any(k in text for k in ["fix", "bug", "error", "debug"]):
        return "debug"

    if any(k in text for k in ["build", "create", "make", "implement"]):
        return "build"

    return "casual"


# ── Memory (TF-IDF cosine, no external libs) ───────────────────────────────────

def _tokenize(text: str) -> List[str]:
    return [w for w in re.findall(r"[a-zA-Z_]\w*", text.lower()) if len(w) >= 3]


def _tfidf(tokens: List[str], idf: Dict[str, float]) -> Dict[str, float]:
    tf = Counter(tokens)
    total = max(len(tokens), 1)
    return {t: (c / total) * idf.get(t, 1.0) for t, c in tf.items()}


def _cosine(a: Dict[str, float], b: Dict[str, float]) -> float:
    common = set(a) & set(b)
    if not common:
        return 0.0
    dot = sum(a[k] * b[k] for k in common)
    mag_a = math.sqrt(sum(v * v for v in a.values()))
    mag_b = math.sqrt(sum(v * v for v in b.values()))
    return dot / (mag_a * mag_b) if mag_a and mag_b else 0.0


def _build_idf(entries: List[Dict]) -> Dict[str, float]:
    N = max(len(entries), 1)
    df: Counter = Counter()
    for e in entries:
        tokens = set(_tokenize(e.get("task", "") + " " + " ".join(e.get("tags", []))))
        df.update(tokens)
    return {t: math.log(N / (c + 1)) + 1.0 for t, c in df.items()}


def load_memory() -> List[Dict]:
    try:
        if MEMORY_FILE.exists():
            return json.loads(MEMORY_FILE.read_text(encoding="utf-8"))
    except Exception:
        pass
    return []


def save_memory(entries: List[Dict]) -> None:
    try:
        MEMORY_FILE.parent.mkdir(parents=True, exist_ok=True)
        MEMORY_FILE.write_text(
            json.dumps(entries[-MEMORY_CAP:], indent=2, ensure_ascii=False),
            encoding="utf-8",
        )
    except Exception:
        pass


def recall(query: str, top_k: int = MEMORY_TOP_K) -> List[Dict]:
    entries = load_memory()
    if not entries:
        return []
    idf = _build_idf(entries)
    qv = _tfidf(_tokenize(query), idf)
    scored = []
    for e in entries:
        ev = _tfidf(_tokenize(e.get("task", "") + " " + " ".join(e.get("tags", []))), idf)
        score = _cosine(qv, ev)
        if score >= SIM_THRESHOLD:
            scored.append((score, e))
    scored.sort(key=lambda x: x[0], reverse=True)
    return [e for _, e in scored[:top_k]]


def remember(task: str, intent: str, success: bool, tags: List[str] = None) -> None:
    entries = load_memory()
    entries.append({
        "task": task[:200],
        "intent": intent,
        "success": success,
        "tags": tags or [],
        "ts": time.strftime("%Y-%m-%d %H:%M"),
    })
    save_memory(entries)


# ── Session State ──────────────────────────────────────────────────────────────

@dataclass
class EtherSession:
    """
    The identity layer. One instance per conversation.
    Holds everything the pipeline needs to make decisions.
    """
    mode: str = "task"                          # current mode: task | casual | debug
    history: List[Dict[str, str]] = field(default_factory=list)
    project_loaded: bool = False
    project_files: List[str] = field(default_factory=list)
    file_contents: Dict[str, str] = field(default_factory=dict)
    project_map: Dict[str, Any] = field(default_factory=dict)
    active_file: Optional[str] = None
    constraints: Dict[str, Any] = field(default_factory=lambda: {
        "max_history_turns": 20,
        "max_file_chars": 8000,
        "allow_memory": True,
    })

    def update_mode(self, intent: str) -> None:
        if intent == "casual":
            self.mode = "casual"
        else:
            self.mode = "task"

    def add_turn(self, role: str, content: str) -> None:
        self.history.append({"role": role, "content": content})
        cap = self.constraints["max_history_turns"] * 2
        if len(self.history) > cap:
            self.history = self.history[-cap:]

    def get_history(self) -> List[Dict[str, str]]:
        return self.history

    def get_memory_context(self, query: str) -> str:
        hits = recall(query)
        if not hits:
            return ""
        lines = ["Relevant past work:"]
        for h in hits:
            status = "✓" if h.get("success") else "✗"
            lines.append(f"  {status} {h['task'][:100]} [{h.get('intent', '')}]")
        return "\n".join(lines)

    def get_file_context(self, max_chars: int = None) -> str:
        cap = max_chars or self.constraints["max_file_chars"]
        if not self.file_contents:
            return ""
        parts = []
        used = 0
        # Active file first
        priority = []
        if self.active_file and self.active_file in self.file_contents:
            priority.append(self.active_file)
        for f in self.project_files:
            if f not in priority:
                priority.append(f)
        for f in priority:
            content = self.file_contents.get(f, "")
            if used + len(content) > cap:
                break
            parts.append(f"# {f}\n{content}")
            used += len(content)
        return "\n\n".join(parts)
