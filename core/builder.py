"""
Ether v2.0 — AI Pipeline (Merged with v1.8 optimizations)
==========================================================
Multi-model, role-based, lazy execution.
CPU-only. 2GB RAM safe. One model per request.

OPTIMIZATIONS FROM v1.8:
1. Response Cache with TTL and LRU eviction
2. Fast-path predefined explanations for Godot terms
3. Hybrid static analysis support
4. Enhanced intent detection patterns
"""

import json
import re
import time
import hashlib
import requests
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple


# ── Configuration ──────────────────────────────────────────────────────────────

OLLAMA_URL = "http://localhost:11434/api/chat"

# One model per role. Only ONE loaded per request — never simultaneously.
MODELS = {
    "generate": "qwen2:1.5b",
    "debug":    "gemma:2b",
    "explain":  "qwen2:1.5b",
    "chat":     "qwen2:0.5b",
}

MAX_CONTEXT_CHARS = 500  # Hard cap. Do not raise.

TIMEOUT = {
    "generate": 60,
    "debug":    60,
    "explain":  30,
    "chat":     20,
}

MAX_TOKENS = {
    "generate": 512,
    "debug":    512,
    "explain":  256,
    "chat":     192,
}

# Cache settings from v1.8
CACHE_TTL_SECONDS = 300  # 5 minutes cache validity
MAX_CACHE_ENTRIES = 50   # Limit cache size to prevent memory bloat


# ── Cached Intelligence Layer (from v1.8) ──────────────────────────────────────

class ResponseCache:
    """
    In-memory LRU cache with TTL (Time-To-Live).
    Eviction policy: least-recently-accessed entry is removed when capacity is full.
    Access time is updated on every successful get(), ensuring true LRU behaviour.
    """

    def __init__(self, ttl_seconds: int = CACHE_TTL_SECONDS, max_entries: int = MAX_CACHE_ENTRIES):
        self.ttl = ttl_seconds
        self.max_entries = max_entries
        self._cache: Dict[str, Any] = {}
        self._insert_time: Dict[str, float] = {}
        self._access_time: Dict[str, float] = {}

    def _make_key(self, query: str, intent: str, project_fingerprint: str) -> str:
        """Create a unique cache key."""
        normalized_query = ' '.join(query.lower().split())
        key_data = f"{normalized_query}|{intent}|{project_fingerprint}"
        return hashlib.md5(key_data.encode()).hexdigest()

    def get(self, query: str, intent: str, project_fingerprint: str) -> Optional[Any]:
        """Get cached response if still valid. Updates LRU access time."""
        key = self._make_key(query, intent, project_fingerprint)

        if key not in self._cache:
            return None

        # Check TTL against insert time
        if time.time() - self._insert_time.get(key, 0) > self.ttl:
            self._cache.pop(key, None)
            self._insert_time.pop(key, None)
            self._access_time.pop(key, None)
            return None

        # Update access time so this entry is treated as recently used
        self._access_time[key] = time.time()
        return self._cache[key]

    def set(self, query: str, intent: str, project_fingerprint: str, response: Any) -> None:
        """Store response. Evicts least-recently-accessed entry when at capacity."""
        key = self._make_key(query, intent, project_fingerprint)

        # Evict LRU entry if at capacity
        if len(self._cache) >= self.max_entries and key not in self._cache:
            lru_key = min(
                self._cache.keys(),
                key=lambda k: self._access_time.get(k, self._insert_time.get(k, 0))
            )
            self._cache.pop(lru_key, None)
            self._insert_time.pop(lru_key, None)
            self._access_time.pop(lru_key, None)

        now = time.time()
        self._cache[key] = response
        self._insert_time[key] = now
        self._access_time[key] = now

    def clear(self) -> None:
        """Clear all cached entries."""
        self._cache.clear()
        self._insert_time.clear()
        self._access_time.clear()

    def stats(self) -> Dict[str, int]:
        """Get cache statistics."""
        return {
            "entries": len(self._cache),
            "max_entries": self.max_entries,
        }


# Global cache instance
_response_cache = ResponseCache()


def get_project_fingerprint(file_index: Dict[str, Any]) -> str:
    """Generate a lightweight fingerprint of project state for cache invalidation."""
    if not file_index:
        return "empty"
    
    fingerprint_data = "|".join(
        f"{path}:{meta.get('size', 0)}" 
        for path, meta in sorted(file_index.items())
    )
    return hashlib.md5(fingerprint_data.encode()).hexdigest()[:16]


# ── Intent Detection (Fast Path) — ENHANCED from v1.8 ──────────────────────────

_GREETING_PATTERNS = [
    r'^\s*(hi|hello|hey|yo|hola|greetings)\b',
    r'^\s*(good\s+(morning|afternoon|evening|night))\b',
    r'^\s*(how\s+are\s+you|whats?\s*up|sup|yo)\b',
]
_STATUS_PATTERNS = [
    r'^\s*(status|stats)\b',
    r'\bhow\s+(many|much)\s+(scripts|scenes|files)\b',
    r'\bcount\s+(scripts|scenes|files)\b',
]
_QUICK_HELP_PATTERNS = [
    r'^(help|what\s+can\s+you\s+do|commands|features)\b',
    r'^\s*thanks?\b',
    r'^(bye|goodbye|see\s+you|later)\b',
]
_EXPLAIN_PATTERNS = [
    r'^(what\s+is|define|explain)\s+',
    r'\s+mean(ing)?\s*[?]?\s*$',
]

_GREETING_RE   = [re.compile(p, re.IGNORECASE) for p in _GREETING_PATTERNS]
_STATUS_RE     = [re.compile(p, re.IGNORECASE) for p in _STATUS_PATTERNS]
_QUICK_HELP_RE = [re.compile(p, re.IGNORECASE) for p in _QUICK_HELP_PATTERNS]
_EXPLAIN_RE    = [re.compile(p, re.IGNORECASE) for p in _EXPLAIN_PATTERNS]


def detect_intent_fast(query: str) -> str:
    """Regex-based fast intent. No LLM. Enhanced from v1.8."""
    q = query.strip()
    for p in _GREETING_RE:
        if p.match(q): return 'greeting'
    for p in _STATUS_RE:
        if p.search(q): return 'status'
    for p in _QUICK_HELP_RE:
        if p.match(q) or p.search(q): return 'quick_help'
    for p in _EXPLAIN_RE:
        if p.search(q) and len(q) < 60: return 'explain'
    return 'complex'


def get_fast_response(intent: str, query: str, project_stats: Dict = None) -> str:
    """
    Instant responses — no LLM. Enhanced from v1.8 with predefined Godot term explanations.
    """
    if intent == 'greeting':
        return "Hello! I'm Ether, your Godot development assistant. How can I help?"
    elif intent == 'status':
        if project_stats:
            return (f"Project Status:\n"
                    f"Scripts: {project_stats.get('script_count', 0)}\n"
                    f"Scenes: {project_stats.get('scene_count', 0)}\n"
                    f"Total Files: {project_stats.get('total_files', 0)}")
        return "No project loaded. Upload a ZIP to see project status."
    elif intent == 'quick_help':
        return "I can write GDScript, debug errors, or explain Godot concepts."
    elif intent == 'explain':
        # Fast path for simple definition/explanation questions (from v1.8)
        query_lower = query.lower().strip()
        
        # Common Godot/game dev terms
        explanations = {
            "signal": "In Godot, signals are a way for nodes to emit events that other nodes can connect to. They enable loose coupling between objects.",
            "node": "A Node is the basic building block in Godot. Everything in Godot is a Node - scenes, characters, UI elements, etc.",
            "scene": "A Scene is a collection of nodes saved as a file. You can instance (reuse) scenes multiple times in your project.",
            "export": "@export is a decorator in GDScript that exposes a variable to the Godot editor's Inspector panel.",
            "gdscript": "GDScript is Godot's built-in scripting language. It's Python-like, designed specifically for Godot's API.",
            "characterbody2d": "CharacterBody2D is a node type for 2D character movement with built-in collision detection.",
            "area2d": "Area2D is a 2D node for detecting overlaps, collisions, and monitoring other objects entering/exiting its hitbox.",
        }
        
        for term, definition in explanations.items():
            if term in query_lower:
                return f"**{term.title()}**: {definition}"
        
        return "I don't have a quick definition for that term. Try asking about specific Godot concepts."
    
    return ""


# ── Ollama Call — Role-Aware ───────────────────────────────────────────────────

def _call(role: str, messages: List[Dict]) -> str:
    """
    Call Ollama with the model assigned to this role.
    Stateless — no shared model state. Ollama handles load/unload.
    We never preload or cache models in memory.
    """
    model   = MODELS.get(role, MODELS["chat"])
    tokens  = MAX_TOKENS.get(role, 192)
    timeout = TIMEOUT.get(role, 30)

    # Keep only system + last user msg to minimize token pressure
    system_msg = next((m for m in messages if m["role"] == "system"), None)
    user_msg   = next((m for m in reversed(messages) if m["role"] == "user"), None)

    payload_msgs = []
    if system_msg: payload_msgs.append(system_msg)
    if user_msg:   payload_msgs.append(user_msg)

    if not payload_msgs:
        return "No input provided."

    payload = {
        "model": model,
        "messages": payload_msgs,
        "stream": False,
        "options": {
            "num_predict": tokens,
            "temperature": 0.4,
            "top_p": 0.9,
            "repeat_penalty": 1.05,
            "stop": ["User:", "Assistant:", "###"],
        },
    }

    try:
        r = requests.post(OLLAMA_URL, json=payload, timeout=timeout)
        if r.status_code != 200:
            return f"Ollama error {r.status_code}: {r.text[:200]}"
        content = r.json().get("message", {}).get("content", "").strip()
        for tag in ["User:", "Assistant:", "Chatbot:"]:
            if tag in content:
                content = content.split(tag)[0].strip()
        return content or "Empty response. Try again."
    except requests.exceptions.Timeout:
        return f"Timeout ({timeout}s). Input too long or Ollama slow."
    except requests.exceptions.ConnectionError:
        return "Ollama not running. Start with: ollama serve"
    except Exception as e:
        return f"Error: {str(e)}"


# ── JSON Parsing ───────────────────────────────────────────────────────────────

def _safe_json(raw: str) -> Optional[Dict]:
    """Parse JSON from model output. Handles fences and trailing commas."""
    if not raw or not raw.strip():
        return None
    text = raw.strip()
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        m = re.search(r'```(?:json)?\s*(\{.*?\})\s*```', text, re.S | re.I)
        candidate = m.group(1) if m else None
        if not candidate:
            for i, ch in enumerate(text):
                if ch != '{': continue
                depth = 0
                for j in range(i, len(text)):
                    if text[j] == '{': depth += 1
                    elif text[j] == '}':
                        depth -= 1
                        if depth == 0:
                            candidate = text[i:j+1]
                            break
                if candidate: break
        if not candidate:
            return None
        candidate = re.sub(r',\s*([}\]])', r'\1', candidate)
        candidate = re.sub(r'\bNone\b', 'null', candidate)
        candidate = re.sub(r'\bTrue\b', 'true', candidate)
        candidate = re.sub(r'\bFalse\b', 'false', candidate)
        try:
            return json.loads(candidate)
        except json.JSONDecodeError:
            return None


def _format_llm_result(result: Any) -> str:
    """Format non-chat result dicts into readable text. PRESERVED."""
    if not isinstance(result, dict):
        return str(result)
    if result.get("text"):        return str(result["text"])
    if result.get("summary"):     return str(result["summary"])
    if result.get("root_cause"):
        out = str(result["root_cause"])
        if result.get("explanation"):
            out += "\n\n" + str(result["explanation"])
        return out.strip()
    if isinstance(result.get("changes"), list):
        changes = result["changes"]
        if not changes: return "No changes generated."
        lines = ["Generated changes:"]
        for c in changes[:5]:
            lines.append(f"- {c.get('file','?')} ({c.get('action','')})")
        return "\n".join(lines)
    return "No response generated."


# ── Context Trimmer — Lightweight ─────────────────────────────────────────────

def _trim_context(context: str, task: str) -> str:
    """
    Hard cap: MAX_CONTEXT_CHARS.
    Prioritizes lines with task keywords — no RAG, no embeddings.
    """
    if not context:
        return ""
    keywords = set(re.findall(r'\w+', task.lower()))
    lines = context.splitlines()
    scored = sorted(
        [(len(keywords & set(re.findall(r'\w+', l.lower()))), l) for l in lines],
        reverse=True
    )
    result, total = [], 0
    for _, line in scored:
        if total + len(line) + 1 > MAX_CONTEXT_CHARS:
            break
        result.append(line)
        total += len(line) + 1
    return "\n".join(result)


# ── GDScript Validator — Pure Python ──────────────────────────────────────────

def _validate_gdscript(code: str) -> List[str]:
    """
    Static analysis. No LLM. Returns issues list.
    Expanded rules for Godot 4 compliance.
    """
    issues = []
    lines  = code.splitlines()

    if not any(l.strip().startswith("extends ") for l in lines):
        issues.append("Missing 'extends' declaration")

    indent_err = []
    func_name, func_lines, func_has_return_type = "", [], False

    for i, line in enumerate(lines, 1):
        stripped = line.rstrip()
        if not stripped or stripped.lstrip().startswith("#"):
            continue

        # Godot 4 syntax
        if re.search(r'\bonready\b', stripped) and "@onready" not in stripped:
            issues.append(f"Line {i}: use '@onready' (Godot 4)")
        if re.search(r'^\s*export\s+var\b', stripped) and "@export" not in stripped:
            issues.append(f"Line {i}: use '@export var' (Godot 4)")
        if "emit_signal(" in stripped:
            issues.append(f"Line {i}: use signal.emit() not emit_signal() (Godot 4)")
        if re.search(r'\bsetget\b', stripped):
            issues.append(f"Line {i}: use 'set/get:' blocks not 'setget' (Godot 4)")

        # Indentation: tabs only
        if line and line[0] == ' ' and stripped.lstrip():
            indent_err.append(i)

        # Function return type check
        fm = re.match(r'^func\s+(\w+)\s*\(.*\)\s*(->\s*\S+)?\s*:', stripped)
        if fm:
            if func_name and func_has_return_type:
                if not any("return" in fl for fl in func_lines):
                    issues.append(f"Function '{func_name}': has return type but no return statement")
            func_name = fm.group(1)
            func_lines = []
            ret_type = fm.group(2)
            func_has_return_type = bool(ret_type and "void" not in ret_type)
        else:
            func_lines.append(stripped)

    if indent_err:
        issues.append(f"Lines {indent_err[:3]}: spaces found — GDScript requires tabs")

    return issues


# ── System Prompts ─────────────────────────────────────────────────────────────

_GODOT_BASE = (
    "You are Ether — a Godot 4 GDScript assistant. "
    "Godot 4 syntax only (@export, @onready). snake_case. Type hints. "
    "No Unity/C#/Godot 3 patterns."
)

_BUILD_SYSTEM = _GODOT_BASE + """
Output ONLY valid JSON — no preamble, no markdown outside the JSON block:
{
  "changes": [{"file": "path.gd", "action": "create_or_modify", "content": "full file content"}],
  "summary": "what was built"
}
Complete files only. No placeholders."""

_DEBUG_SYSTEM = _GODOT_BASE + """
Diagnose and fix the provided code.
Output ONLY valid JSON:
{
  "root_cause": "specific issue found",
  "changes": [{"file": "path.gd", "action": "create_or_modify", "content": "fixed file"}],
  "explanation": "why this fix works"
}"""

_EXPLAIN_SYSTEM = _GODOT_BASE + " Answer clearly. Reference Godot 4 API. Plain text only."
_CHAT_SYSTEM    = _GODOT_BASE + " Conversational mode. Direct and concise. Plain text only."


# ── Pipeline Steps ─────────────────────────────────────────────────────────────

def _generate(task: str, context: str) -> Dict:
    """GENERATE role → qwen2:1.5b"""
    ctx = _trim_context(context, task)
    user_content = f"Task: {task}\n\nContext:\n{ctx}" if ctx else f"Task: {task}"
    raw = _call("generate", [
        {"role": "system", "content": _BUILD_SYSTEM},
        {"role": "user",   "content": user_content},
    ])
    result = _safe_json(raw)
    if not result:
        result = {
            "changes": [{"file": "output.gd", "action": "create_or_modify", "content": raw}],
            "summary": "Generated (raw fallback — JSON parse failed)"
        }
    return result


def _debug(task: str, context: str) -> Dict:
    """DEBUG role → gemma:2b. Only called when needed."""
    ctx = _trim_context(context, task)
    user_content = f"Error/task:\n{task}\n\nCode:\n{ctx}" if ctx else f"Error/task:\n{task}"
    raw = _call("debug", [
        {"role": "system", "content": _DEBUG_SYSTEM},
        {"role": "user",   "content": user_content},
    ])
    result = _safe_json(raw)
    if not result:
        result = {
            "root_cause": "Parse failed — see raw output",
            "changes": [],
            "explanation": raw.strip() or "No debug output."
        }
    return result


def _explain(task: str, context: str) -> str:
    """EXPLAIN role → qwen2:1.5b. Plain text."""
    ctx = _trim_context(context, task)
    user_content = f"{task}\n\nContext:\n{ctx}" if ctx else task
    return _call("explain", [
        {"role": "system", "content": _EXPLAIN_SYSTEM},
        {"role": "user",   "content": user_content},
    ])


def _chat(task: str) -> str:
    """CHAT role → qwen2:0.5b. No context — fastest path."""
    return _call("chat", [
        {"role": "system", "content": _CHAT_SYSTEM},
        {"role": "user",   "content": task},
    ])


# ── Public API — PRESERVED SIGNATURE ──────────────────────────────────────────

def run_pipeline(
    task: str,
    intent: str,
    context: str,
    history: List[Dict],
    api_key: str = None,       # unused (Ollama local) — kept for app.py compat
    yield_steps=None,
    chat_mode: str = "mixed",  # unused — kept for app.py compat
) -> Tuple[Dict, List[str]]:
    """
    Main pipeline. Signature unchanged from v1.9.

    Routing:
        build/generate → _generate()        → qwen2:1.5b
        debug          → _validate() first  → _debug() if issues → gemma:2b
        explain/analyze→ _explain()         → qwen2:1.5b
        casual/chat    → _chat()            → qwen2:0.5b

    ONE model active per call. No parallel execution. No preloading.
    """
    log: List[str] = []

    def step(name: str):
        log.append(name)
        if yield_steps:
            yield_steps(name)

    if intent in ("build", "generate"):
        step("Building...")
        try:
            result = _generate(task, context)
            return {"type": "build", "thought": {}, **result}, log
        except Exception as e:
            return {"type": "chat", "text": f"Build error: {e}"}, log

    elif intent == "debug":
        step("Validating...")
        issues = _validate_gdscript(context) if context else []
        if issues:
            step(f"{len(issues)} issue(s) found — debugging...")
            augmented = task + "\n\nStatic issues:\n" + "\n".join(f"- {i}" for i in issues)
        else:
            step("Debugging...")
            augmented = task
        try:
            result = _debug(augmented, context)
            return {"type": "debug", **result}, log
        except Exception as e:
            return {"type": "chat", "text": f"Debug error: {e}"}, log

    elif intent in ("explain", "analyze"):
        step("Explaining...")
        try:
            text = _explain(task, context)
            return {"type": "chat", "text": text}, log
        except Exception as e:
            return {"type": "chat", "text": f"Explain error: {e}"}, log

    else:
        step("Responding...")
        try:
            text = _chat(task)
            return {"type": "chat", "text": text}, log
        except Exception as e:
            return {"type": "chat", "text": f"Error: {e}"}, log


# ── Code Style Memory (ultra lightweight) ─────────────────────────────────────

def get_code_style() -> str:
    """
    Lightweight code style memory.
    No database. No embeddings. Under 5 lines.
    """
    return """
- naming: snake_case
- prefers_signals: true
- node_type: CharacterBody2D
"""


# ── Project Pattern Awareness (ultra lightweight) ──────────────────────────────

def get_pattern() -> str:
    """
    Ultra-lightweight project pattern hints.
    Max 3-5 lines. No dynamic heavy analysis.
    """
    return """
- modular scripts
- signal-based communication
"""


# ── Role Mapping (Python-side only) ────────────────────────────────────────────

def map_intent_to_role(intent: str) -> str:
    """
    Map intent to role. LLM must NOT perform classification.
    Python controls routing.
    """
    if intent in ("build", "generate"):
        return "GENERATE"
    elif intent == "debug":
        return "DEBUG"
    elif intent in ("analyze", "explain"):
        return "EXPLAIN"
    else:
        return "CHAT"


# ── Refactored chat() Function — Execution Mode ────────────────────────────────

def chat(message: str, history: List[Dict], context: str, role: str = "CHAT") -> str:
    """
    Refactored chat function — LLM as executor only.
    
    Constraints:
    - LLM must NOT decide intent
    - LLM must NOT simulate personality
    - Single LLM call per request
    """
    # Truncate context to fit low-end hardware
    context = context[:300] if len(context) > 300 else context
    
    # Select prompt based on role
    from core.prompts import select_prompt, build_style_hints, build_pattern_hints
    
    # Get lightweight hints
    style_hints = build_style_hints(None)  # Can be extended to use get_code_style()
    pattern_hints = build_pattern_hints(None)  # Can be extended to use get_pattern()
    
    system, user = select_prompt(
        role=role.lower(),
        task=message,
        context=context,
        style_memory=None,
        project_patterns=None
    )
    
    messages = [
        {"role": "system", "content": system},
        {"role": "user", "content": user}
    ]
    
    # Use appropriate token limit
    max_tokens = MAX_TOKENS.get(role.lower(), MAX_TOKENS["chat"])
    
    return _call(role.lower(), messages)


# ── Smart Retry with Fallback Model (optional improvement) ─────────────────────

def _call_with_retry(role: str, messages: List[Dict], fallback_model: str = "gemma:2b") -> str:
    """
    Smart retry: switch to smaller model on timeout.
    """
    result = _call(role, messages)
    
    if "Timeout" in result:
        # Switch to fallback model
        global MODELS
        original_model = MODELS.get(role, MODELS["chat"])
        MODELS[role] = fallback_model
        result = _call(role, messages)
        MODELS[role] = original_model  # Restore
    
    return result
