"""
Ether State — Single source of truth for session identity.
Patched: classify() now returns 'analyze' for analysis queries.
"""

import json
import math
import re
import time
from collections import Counter
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional

MEMORY_CAP = 150
MEMORY_TOP_K = 3
SIM_THRESHOLD = 0.15

WORKSPACE = Path("workspace")
MEMORY_FILE = WORKSPACE / "memory.json"


# ── Intent Classification (PATCHED) ───────────────────────────────────────────

_CASUAL = {"hi", "hey", "hello", "thanks", "ok", "okay", "cool", "great", "lol", "nice"}
_DEBUG  = {"error", "crash", "fix", "bug", "broken", "fail", "exception", "traceback"}
_BUILD  = {"create", "generate", "build", "make", "add", "write", "implement", "new"}
_ANALYZE= {"analyze", "explain", "what", "how", "why", "understand", "review", "check",
           "list", "find", "show", "tell", "describe", "issues", "problems", "look"}


def is_casual(text: str) -> bool:
    text = text.lower().strip()
    
    # Very short greetings are always casual
    if len(text) <= 4:
        return True

    # "whatsup" variants MUST be checked first - they are ALWAYS casual
    if "whatsup" in text or "whats up" in text or "what's up" in text:
        return True
    
    # Explicit non-casual keywords (check second) - these override everything else
    non_casual_keywords = [
        "fix", "bug", "error", "debug", "crash",
        "explain", "analyze", "review", "check",
        "list", "find", "show me", "tell me", "describe",
        "issues", "problems", "implement", "create",
        "build", "generate", "write code", "add feature",
        "think of", "opinion on", "feedback on"
    ]
    
    if any(k in text for k in non_casual_keywords):
        return False
    
    # Casual patterns - expanded
    casual_patterns = [
        "hi", "hello", "hey", "yo", "sup", 
        "thanks", "thank you", "thx",
        "congrats", "congratulations",
        "lol", "lmao", "haha", "rofl",
        "how are you", "how's it going",
        "good morning", "good night", "good day",
        "nice", "cool", "great", "awesome",
        "ok", "okay", "sure", "yeah", "yep",
        "bye", "see you", "later",
        "whatcha", "greetings", "g'day"
    ]
    
    # Check for exact casual patterns
    if any(p in text for p in casual_patterns):
        return True
    
    # Short conversational phrases (2-3 words) without technical/game keywords
    words = text.split()
    if len(words) <= 3:
        technical_words = ["game", "code", "script", "project", "player", "enemy", "level"]
        if not any(k in text for k in technical_words):
            return True

    return False


def classify(text: str) -> str:
    """Classify user intent. Returns: casual, debug, build, analyze, or task."""
    text_lower = text.lower()

    if any(k in text_lower for k in ["fix", "bug", "error", "debug", "crash", "broken", "fail"]):
        return "debug"

    if any(k in text_lower for k in ["build", "create", "make", "implement", "generate", "write", "add"]):
        return "build"

    # PATCH: catch analysis/review queries — these need real file context
    if any(k in text_lower for k in ["analyze", "explain", "list", "find", "show", "what",
                                      "how", "why", "review", "check", "issues", "problems",
                                      "tell me", "describe", "look at", "read"]):
        return "analyze"

    return "casual"


# ── Memory ─────────────────────────────────────────────────────────────────────

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
    mode: str = "task"
    history: List[Dict[str, str]] = field(default_factory=list)
    project_loaded: bool = False
    project_files: List[str] = field(default_factory=list)
    file_contents: Dict[str, str] = field(default_factory=dict)
    project_map: Dict[str, Any] = field(default_factory=dict)
    active_file: Optional[str] = None
    chat_mode: str = "mixed"  # coding | general | mixed
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
