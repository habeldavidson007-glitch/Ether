"""
Ether v2.1 — Constrained Intelligence Core
==========================================
Optimized for low-end hardware (2GB RAM, Windows).
Philosophy: "Python THINKS (Analysis), LLM EXECUTES (Hands), System CONTROLS (Time)."

Architecture:
- Smart Context Builder: ~150-char structured summaries (not raw code)
- Micro-Reasoning Prompts: Execution-only, no personas, no internal reasoning
- Adaptive Execution: 45s primary, 20s fallback, hard timeouts
- Single-call pipeline: No multi-stage chains
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

# V2.1 CONFIG FOR 2GB RAM - STRICT LIMITS
PRIMARY_MODEL = "qwen2.5-coder:1.5b-instruct-q4_k_m"
FALLBACK_MODEL = "gemma:2b"

MODELS = {
    "generate": PRIMARY_MODEL,
    "debug":    PRIMARY_MODEL,
    "explain":  PRIMARY_MODEL,
    "chat":     PRIMARY_MODEL,
}

# STRICT CONTEXT LIMITS - Structured summaries only
MAX_CONTEXT_CHARS = 200
MAX_CONTEXT_ANALYZE = 400  # Analysis benefits from more context
MAX_CONTEXT_BUILD = 300    # Build needs focused context
TIMEOUT_PRIMARY = 45
TIMEOUT_FALLBACK = 20
MAX_TOKENS_RESPONSE = 256

MAX_TOKENS = {
    "generate": MAX_TOKENS_RESPONSE,
    "debug":    MAX_TOKENS_RESPONSE,
    "explain":  MAX_TOKENS_RESPONSE,
    "chat":     128,
}

# Cache settings
CACHE_TTL_SECONDS = 300
MAX_CACHE_ENTRIES = 50


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


# ── Ollama Call — Adaptive Execution Engine ─────────────────────────────────────

def _extract_code_from_tags(content: str) -> str:
    """Extract content between <code> tags only."""
    match = re.search(r'<code>(.*?)</code>', content, re.DOTALL)
    if match:
        return match.group(1).strip()
    return content.strip()


def _call_with_retry(role: str, messages: List[Dict], structured_context: str = "") -> str:
    """
    ADAPTIVE EXECUTION ENGINE (v2.1):
    1. Try Primary Model (45s timeout)
    2. If Timeout/Error → Switch to Fallback (20s) with simplified prompt
    3. If Fail → Return partial result with warning
    
    Enforces output guard: Extract content between <code> tags only.
    """
    model = MODELS.get(role, MODELS["chat"])
    tokens = MAX_TOKENS.get(role, MAX_TOKENS_RESPONSE)
    
    system_msg = next((m for m in messages if m["role"] == "system"), None)
    user_msg = next((m for m in reversed(messages) if m["role"] == "user"), None)
    
    payload_msgs = []
    if system_msg:
        payload_msgs.append(system_msg)
    if user_msg:
        payload_msgs.append(user_msg)
    
    if not payload_msgs:
        return "No input provided."
    
    # PRIMARY MODEL ATTEMPT (45s)
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
        r = requests.post(OLLAMA_URL, json=payload, timeout=TIMEOUT_PRIMARY)
        if r.status_code == 200:
            content = r.json().get("message", {}).get("content", "").strip()
            return _extract_code_from_tags(content)
    except requests.exceptions.Timeout:
        pass
    except Exception:
        pass
    
    # FALLBACK MODEL ATTEMPT (20s) - Simplified prompt
    fallback_payload = {
        "model": FALLBACK_MODEL,
        "messages": [
            {"role": "system", "content": "Fix issue. Output code only between <code> tags."},
            {"role": "user", "content": user_msg["content"] if user_msg else ""},
        ],
        "stream": False,
        "options": {
            "num_predict": tokens,
            "temperature": 0.3,
            "top_p": 0.9,
            "repeat_penalty": 1.1,
            "stop": ["User:", "Assistant:", "###"],
        },
    }
    
    try:
        r = requests.post(OLLAMA_URL, json=fallback_payload, timeout=TIMEOUT_FALLBACK)
        if r.status_code == 200:
            content = r.json().get("message", {}).get("content", "").strip()
            return _extract_code_from_tags(content)
    except requests.exceptions.Timeout:
        return f"Warning: Both models timed out. Primary: {TIMEOUT_PRIMARY}s, Fallback: {TIMEOUT_FALLBACK}s."
    except Exception as e:
        return f"Warning: Fallback failed: {str(e)}"
    
    return "Warning: All execution attempts failed."


def _call(role: str, messages: List[Dict]) -> str:
    """Legacy wrapper for backward compatibility. Use _call_with_retry for v2.1."""
    return _call_with_retry(role, messages)


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

def _trim_context(context: str, task: str, task_type: str = "default") -> str:
    """
    Smart context trimmer - adaptive limits based on task type.
    Prioritizes lines with task keywords — no RAG, no embeddings.
    """
    if not context:
        return ""
    
    max_chars = MAX_CONTEXT_CHARS
    
    keywords = set(re.findall(r'\w+', task.lower()))
    lines = context.splitlines()
    scored = sorted(
        [(len(keywords & set(re.findall(r'\w+', l.lower()))), l) for l in lines],
        reverse=True
    )
    result, total = [], 0
    for _, line in scored:
        if total + len(line) + 1 > max_chars:
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


# ── System Prompts (v2.1 Micro-Reasoning) ─────────────────────────────────────

_GENERATE_PROMPT = "Fix the issue using the strategy. Context: {structured_context}. Output: <code>FULL_SCRIPT</code>"
_DEBUG_PROMPT = "Identify root cause. Context: {structured_context}. Output: <code>FIXED_SCRIPT</code>"


def _generate(task: str, structured_context: str) -> Dict:
    """GENERATE role - ultra-light for 1.5B models with micro-reasoning prompts."""
    user_content = _GENERATE_PROMPT.format(structured_context=structured_context) if structured_context else f"Task:{task}"
    
    raw = _call("generate", [
        {"role": "system", "content": "Godot 4 GDScript. Output code between <code> tags."},
        {"role": "user",   "content": user_content},
    ])
    result = _safe_json(raw)
    if not result:
        result = {"changes": [{"file": "output.gd", "action": "create_or_modify", "content": raw}], "summary": "Generated"}
    return result


def _debug(task: str, structured_context: str) -> Dict:
    """DEBUG role - ultra-light for 1.5B models with micro-reasoning prompts."""
    user_content = _DEBUG_PROMPT.format(structured_context=structured_context) if structured_context else f"Error:{task}"
    
    raw = _call("debug", [
        {"role": "system", "content": "Godot 4 GDScript. Output JSON with root_cause and changes."},
        {"role": "user",   "content": user_content},
    ])
    result = _safe_json(raw)
    if not result:
        result = {"root_cause": "See output", "changes": [], "explanation": raw.strip() or "No output"}
    return result


def _explain(task: str, structured_context: str) -> str:
    """EXPLAIN role - ultra-light for 1.5B models."""
    user_content = f"{task}\nContext:{structured_context}" if structured_context else task
    
    return _call("explain", [
        {"role": "system", "content": "Godot 4 expert. Be specific. 3 bullet points max."},
        {"role": "user",   "content": user_content},
    ])


def _chat(task: str) -> str:
    """CHAT role — fastest path, no context"""
    return _call("chat", [
        {"role": "system", "content": "Be direct and concise. Plain text only."},
        {"role": "user",   "content": task},
    ])


# ── Public API — v2.1 PIPELINE REFACTOR ───────────────────────────────────────

def run_pipeline(
    task: str,
    intent: str,
    context: str,
    history: List[Dict],
    api_key: str = None,
    yield_steps=None,
    chat_mode: str = "mixed",
) -> Tuple[Dict, List[str]]:
    """
    V2.1 PIPELINE REFACTOR - Single call only. No multi-stage chains.
    
    Routing:
        Simple (greeting/status/quick_help) → Fast Path (0s, no LLM)
        Complex → build_structured_context() → _call_with_retry()
    
    ONE LLM call per request. Python THINKS, LLM EXECUTES.
    """
    from utils.project_loader import build_structured_context
    
    log: List[str] = []

    def step(name: str):
        log.append(name)
        if yield_steps:
            yield_steps(name)

    # FAST PATH for simple intents (no LLM)
    if intent in ('greeting', 'status', 'quick_help'):
        return {"type": "chat", "text": get_fast_response(intent, task)}, log

    # COMPLEX PATH: Build structured context and execute single LLM call
    step("Building context...")
    structured_ctx = build_structured_context(context, intent)
    
    if intent in ("build", "generate"):
        step("Generating...")
        try:
            result = _generate(task, structured_ctx)
            return {"type": "build", **result}, log
        except Exception as e:
            return {"type": "chat", "text": f"Build error: {e}"}, log

    elif intent == "debug":
        step("Debugging...")
        try:
            result = _debug(task, structured_ctx)
            return {"type": "debug", **result}, log
        except Exception as e:
            return {"type": "chat", "text": f"Debug error: {e}"}, log

    elif intent in ("explain", "analyze"):
        step("Explaining...")
        try:
            text = _explain(task, structured_ctx)
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


# ── System Prompts (from v1.8) ──────────────────────────────────────────────────

_GODOT_SYSTEM = """You are Ether — a Godot 4 development assistant with deep GDScript expertise.

Core rules:
- Always use Godot 4 syntax (@export, @onready, func _ready, etc.)
- Prefer signals over direct node coupling
- snake_case for all names
- Include type hints where helpful
- Never hallucinate Unity, Unreal, or C# patterns
- Generate COMPLETE files, never partial snippets"""

_EXPERT_PERSONAS = {
    "coding": """

**Expert Persona: Coding Expert**
You are a senior Godot developer with 10+ years of experience.
- Write production-ready, optimized GDScript code
- Follow best practices: SOLID principles, design patterns
- Use strong typing, proper error handling
- Code is clean, modular, and well-documented
- Focus on implementation details and technical precision""",
    "general": """

**Expert Persona: General Expert**
You are a game design and architecture consultant.
- Explain concepts clearly with practical examples
- Focus on game design patterns, architecture decisions
- Provide high-level guidance and trade-offs
- Help with project planning and organization
- Balance theory with actionable advice""",
    "mixed": """

**Expert Persona: Mixed Mode**
You adapt your response based on what the question needs.
- For technical questions: provide code + explanation
- For conceptual questions: explain then show examples
- Balance depth with clarity
- Match the user's level of expertise"""
}

_MODE_SUFFIX = {
    "coding": "\n\nMode: CODING. Focus on code, scripts, and technical implementation. Be precise and direct.",
    "general": "\n\nMode: GENERAL. Focus on concepts, design patterns, and high-level guidance. Explain clearly.",
    "mixed": "\n\nMode: MIXED. Balance code and explanation based on what the question needs.",
}

_THINK_SYSTEM = _GODOT_SYSTEM + """

Your job: analyze the request and project context.
Output a JSON object:
{
  "understanding": "what the user actually wants",
  "existing_relevant": ["list of relevant existing files"],
  "missing": ["what needs to be created"],
  "approach": "one sentence: the cleanest way to build this"
}"""

_PLAN_SYSTEM = _GODOT_SYSTEM + """

Your job: produce a concrete file plan.
Output a JSON object:
{
  "files": [
    {
      "path": "scripts/player.gd",
      "action": "create or modify",
      "purpose": "one sentence"
    }
  ],
  "connections": ["signal x connects to y", "scene A instanced in B"],
  "notes": "anything the user should know"
}"""

_BUILD_SYSTEM = _GODOT_SYSTEM + """

Your job: generate complete, working file contents.
Output ONLY a JSON object:
{
  "changes": [
    {
      "file": "scripts/player.gd",
      "action": "create_or_modify",
      "content": "# full file content here\\nextends CharacterBody2D\\n..."
    }
  ],
  "summary": "what was built and how to use it"
}

Rules for content:
- COMPLETE files only. Never use placeholders.
- If modifying, include the full file with changes applied.
- GDScript only."""

_DEBUG_SYSTEM = _GODOT_SYSTEM + """

Your job: diagnose and fix the error using the ACTUAL CODE provided.
Reference specific file names, line patterns, and variable names from context.

Output a JSON object:
{
  "root_cause": "specific issue found in the actual code",
  "changes": [
    {
      "file": "path/to/file.gd",
      "action": "create_or_modify",
      "content": "complete fixed file content"
    }
  ],
  "explanation": "why this specific fix works",
  "prevention": "how to avoid this in future"
}"""

_ANALYZE_SYSTEM = _GODOT_SYSTEM + """

Your job: analyze the ACTUAL PROJECT CODE provided and give specific findings.
Reference specific file names, function names, and line patterns found in the code.

Format your response as clear text:
- Reference specific files and functions you found
- List concrete issues with file+function references
- List improvements with specific suggestions
- Prioritize by impact"""

_CHAT_SYSTEM = _GODOT_SYSTEM + """

You are in conversational mode. Be direct, helpful, and specific to Godot.
If project context is provided, reference the actual files and code patterns.
No JSON output — just clear, useful text."""


# ── Pipeline Steps (from v1.8) ──────────────────────────────────────────────────

def think(task: str, context: str) -> Dict:
    # Truncate context for thinking step
    context_truncated = context[:600] if len(context) > 600 else context
    
    messages = [
        {"role": "system", "content": _THINK_SYSTEM},
        {"role": "user", "content": f"Task: {task}\n\nProject context:\n{context_truncated}"}
    ]
    raw = _call("chat", messages)
    result = _safe_json(raw)
    if not result:
        result = {"understanding": raw[:300], "existing_relevant": [], "missing": [], "approach": ""}
    return result


def plan(task: str, thought: Dict, context: str) -> Dict:
    # Truncate inputs for planning
    context_truncated = context[:600] if len(context) > 600 else context
    thought_str = json.dumps(thought, indent=2)[:300]
    
    messages = [
        {"role": "system", "content": _PLAN_SYSTEM},
        {"role": "user", "content": (
            f"Task: {task}\n\n"
            f"Analysis: {thought_str}\n\n"
            f"Project context:\n{context_truncated}"
        )}
    ]
    raw = _call("chat", messages)
    result = _safe_json(raw)
    if not result:
        result = {"files": [], "connections": [], "notes": raw[:200]}
    return result


def build(task: str, thought: Dict, blueprint: Dict, context: str) -> Dict:
    # Truncate context heavily for build step
    context_truncated = context[:1000] if len(context) > 1000 else context
    
    messages = [
        {"role": "system", "content": _BUILD_SYSTEM},
        {"role": "user", "content": (
            f"Task: {task}\n\n"
            f"Analysis: {json.dumps(thought, indent=2)[:400]}\n\n"  # Truncate thought
            f"Plan: {json.dumps(blueprint, indent=2)[:400]}\n\n"   # Truncate plan
            f"Existing code:\n{context_truncated}"
        )}
    ]
    raw = _call("generate", messages)
    result = _safe_json(raw)
    if not result:
        result = {
            "changes": [{"file": "output.gd", "action": "create_or_modify", "content": raw}],
            "summary": "Generated (raw fallback)"
        }
    return result


def debug(error_log: str, context: str) -> Dict:
    messages = [
        {"role": "system", "content": _DEBUG_SYSTEM},
        {"role": "user", "content": f"Error/task:\n{error_log}\n\nACTUAL PROJECT CODE:\n{context[:1000]}"}
    ]
    raw = _call("debug", messages)
    result = _safe_json(raw)
    if not result:
        result = {
            "root_cause": "Parse failed — see raw output",
            "changes": [],
            "explanation": raw[:400],
            "prevention": ""
        }
    return result


def analyze(task: str, context: str, history: List[Dict], chat_mode: str = "mixed") -> str:
    """Analyze project with context - optimized for local models."""
    mode_suffix = _MODE_SUFFIX.get(chat_mode, _MODE_SUFFIX["mixed"])
    system = _ANALYZE_SYSTEM + mode_suffix
    messages = [{"role": "system", "content": system}]
    
    # Add user message with context (if available)
    if context and len(context) > 0:
        # Truncate context aggressively for small model
        max_context_len = 800
        if len(context) > max_context_len:
            context = context[:max_context_len] + "\n...(truncated)"
        messages.append({"role": "user", "content": f"Task: {task}\n\nPROJECT CODE:\n{context}"})
    else:
        messages.append({"role": "user", "content": task})
    
    return _call("explain", messages)


def chat(message: str, history: List[Dict], context: str, chat_mode: str = "mixed") -> str:
    # Expert persona system prompt - LIGHTWEIGHT version
    persona = _EXPERT_PERSONAS.get(chat_mode, _EXPERT_PERSONAS["mixed"])
    mode_suffix = _MODE_SUFFIX.get(chat_mode, _MODE_SUFFIX["mixed"])

    # Simplified system prompt for faster response
    system = _GODOT_SYSTEM + persona + mode_suffix + """

You are helpful and conversational. Be friendly but concise."""

    # Build messages with ONLY current message (no context to save tokens & speed)
    messages = [{"role": "system", "content": system}]
    messages.append({"role": "user", "content": message})

    return _call("chat", messages)


# ── EtherBrain: Main Engine Class (from v1.8) ──────────────────────────────────────

class EtherBrain:
    """
    Ether v1.9 — Main Engine Class (Merged with v2.0 optimizations)
    
    Integrates:
    1. Intent-Aware Routing (fast path for simple queries)
    2. Lazy Loading Architecture (via project_loader)
    3. Cached Intelligence Layer (TTL-based response cache)
    4. v2.0 Role-based execution model
    
    Usage:
        brain = EtherBrain()
        brain.load_project_from_folder(path)
        result = brain.process_query("Hello!", project_stats={})
    """
    
    def __init__(self):
        self.project_loader = None  # LazyProjectLoader instance
        self.project_stats = {"script_count": 0, "scene_count": 0, "total_files": 0, "loaded_files": 0}
        self.project_fingerprint = "empty"
        self.history: List[Dict[str, str]] = []
        self.chat_mode = "mixed"
    
    def load_project_from_zip(self, zip_data: bytes) -> Tuple[bool, str]:
        """
        Load project from ZIP using lazy loading.
        Only indexes files, doesn't read content yet.
        """
        try:
            from utils.project_loader import LazyProjectLoader
            
            self.project_loader = LazyProjectLoader()
            success, msg = self.project_loader.load_from_zip(zip_data)
            
            if success:
                self.project_stats = self.project_loader.get_stats()
                self.project_fingerprint = get_project_fingerprint(self.project_loader.file_index)
            
            return success, msg
        
        except ImportError:
            return False, "project_loader module not found"
        except Exception as e:
            return False, f"Load error: {str(e)}"
    
    def load_project_from_folder(self, folder_path: Path) -> Tuple[bool, str]:
        """
        Load project from a folder using lazy loading.
        """
        try:
            from utils.project_loader import LazyProjectLoader
            
            self.project_loader = LazyProjectLoader()
            success, msg = self.project_loader.load_from_folder(folder_path)
            
            if success:
                self.project_stats = self.project_loader.get_stats()
                self.project_fingerprint = get_project_fingerprint(self.project_loader.file_index)
            
            return success, msg
        
        except ImportError:
            return False, "project_loader module not found"
        except Exception as e:
            return False, f"Load error: {str(e)}"
    
    def unload_project(self) -> None:
        """Unload project and clear cache."""
        if self.project_loader:
            self.project_loader.unload_all()
        self.project_loader = None
        self.project_stats = {"script_count": 0, "scene_count": 0, "total_files": 0, "loaded_files": 0}
        self.project_fingerprint = "empty"
        _response_cache.clear()
    
    def process_query(self, query: str, yield_steps=None) -> Tuple[Dict, List[str]]:
        """
        Process a user query with intent-aware routing.
        
        Fast Path: Greetings, status, quick help → instant response (<2s)
        Slow Path: Analysis, coding, debugging → full LLM pipeline
        
        Returns: (result_dict, log_list)
        """
        log = []
        
        def step(name: str):
            log.append(name)
            if yield_steps:
                yield_steps(name)
        
        # STEP 1: Detect intent using fast regex patterns
        fast_intent = detect_intent_fast(query)
        
        # STEP 2: Check cache for repeated queries (only for non-greeting intents)
        if fast_intent != 'greeting':
            cached = _response_cache.get(query, fast_intent, self.project_fingerprint)
            if cached is not None:
                step("⚡ Cache hit!")
                return {"type": "chat", "text": cached, "cached": True}, log
        
        # STEP 3: Route based on intent
        if fast_intent == 'greeting':
            # FAST PATH: Instant greeting response
            step("⚡ Fast path (greeting)")
            response = get_fast_response(fast_intent, query, self.project_stats)
            return {"type": "chat", "text": response, "fast_path": True}, log
        
        elif fast_intent == 'status':
            # FAST PATH: Status from cached stats (no LLM needed)
            step("⚡ Fast path (status)")
            response = get_fast_response(fast_intent, query, self.project_stats)
            return {"type": "chat", "text": response, "fast_path": True}, log
        
        elif fast_intent == 'quick_help':
            # FAST PATH: Pre-defined help response
            step("⚡ Fast path (help)")
            response = get_fast_response(fast_intent, query, self.project_stats)
            return {"type": "chat", "text": response, "fast_path": True}, log
        
        elif fast_intent == 'explain':
            # FAST PATH: Quick definition/explanation without LLM
            step("⚡ Fast path (explain)")
            response = get_fast_response(fast_intent, query, self.project_stats)
            return {"type": "chat", "text": response, "fast_path": True}, log
        
        else:
            # SLOW PATH: Complex intent requires LLM
            # Determine complex intent type (analyze, debug, build, chat)
            complex_intent = self._classify_complex_intent(query)
            
            # Get context lazily (only loads relevant files)
            context = ""
            if self.project_loader:
                step("📂 Loading relevant files...")
                # SMART CONTEXT LOADING - Adaptive based on intent type
                if complex_intent == 'analyze':
                    # Analysis benefits from more context
                    context = self.project_loader.build_lightweight_context(query, max_chars=MAX_CONTEXT_ANALYZE)
                elif complex_intent == 'build':
                    # Build needs focused context
                    context = self.project_loader.build_lightweight_context(query, max_chars=MAX_CONTEXT_BUILD)
                else:
                    # Default balanced context
                    context = self.project_loader.build_lightweight_context(query, max_chars=MAX_CONTEXT_CHARS)
                
                self.project_stats = self.project_loader.get_stats()
                self.project_fingerprint = get_project_fingerprint(self.project_loader.file_index)
            
            # Add memory context if available
            memory_context = self._get_memory_context(query)
            if memory_context:
                context = memory_context + "\n\n" + context
            
            # Run appropriate pipeline
            if complex_intent == 'analyze':
                step("🔍 Analyzing project...")
                try:
                    # HYBRID STATIC ANALYSIS PIPELINE (v1.8)
                    # Step 1: Run static analyzer first (instant, no LLM)
                    static_report = ""
                    if self.project_loader and hasattr(self.project_loader, '_base_path') and self.project_loader._base_path:
                        from core.static_analyzer import StaticAnalyzer
                        analyzer = StaticAnalyzer()
                        static_report = analyzer.analyze(str(self.project_loader._base_path))
                        step(f"⚡ Static analysis complete ({analyzer.files_scanned} files)")
                    
                    # Step 2: Send ONLY the findings to LLM for friendly summary
                    if static_report:
                        llm_prompt = f"Here are the technical findings: {static_report}\n\nPlease summarize these for the user in 2-3 friendly sentences."
                        text = analyze(llm_prompt, "", self.history, chat_mode=self.chat_mode)
                    else:
                        # Fallback if static analysis couldn't run
                        text = analyze(query, context, self.history, chat_mode=self.chat_mode)
                    
                    # Cache the result
                    _response_cache.set(query, complex_intent, self.project_fingerprint, text)
                    return {"type": "chat", "text": text}, log
                except Exception as e:
                    return {"type": "chat", "text": f"❌ Analysis error: {str(e)}"}, log
            
            elif complex_intent == 'debug':
                step("🔧 Debugging...")
                try:
                    result = debug(query, context)
                    return {"type": "debug", **result}, log
                except Exception as e:
                    return {"type": "chat", "text": f"❌ Debug error: {str(e)}"}, log
            
            elif complex_intent == 'build':
                step("🏗 Building...")
                try:
                    thought = think(query, context)
                    step("Thinking...")
                    blueprint = plan(query, thought, context)
                    step("Planning...")
                    result = build(query, thought, blueprint, context)
                    step("Building...")
                    return {"type": "build", "thought": thought, **result}, log
                except Exception as e:
                    return {"type": "chat", "text": f"❌ Build error: {str(e)}"}, log
            
            else:
                # Default to chat - don't pass heavy context for casual chat
                step("💬 Chatting...")
                try:
                    text = chat(query, self.history[-4:] if len(self.history) >= 4 else self.history, 
                               "", chat_mode=self.chat_mode)
                    # Cache chat responses too
                    _response_cache.set(query, complex_intent, self.project_fingerprint, text)
                    return {"type": "chat", "text": text}, log
                except Exception as e:
                    return {"type": "chat", "text": f"❌ Error: {str(e)}"}, log
    
    def _classify_complex_intent(self, query: str) -> str:
        """
        Classify complex intents (after fast path filtering).
        Returns: analyze, debug, build, or chat
        """
        query_lower = query.lower()
        
        # Debug keywords
        if any(k in query_lower for k in ["fix", "bug", "error", "debug", "crash", "broken", "fail", "exception"]):
            return "debug"
        
        # Build keywords
        if any(k in query_lower for k in ["create", "make", "implement", "generate", "write", "add", "build", "new"]):
            return "build"
        
        # Analyze keywords - be more specific to avoid catching casual questions
        if any(k in query_lower for k in ["analyze", "list", "find", "show", "review", "check", 
                                           "issues", "problems", "describe", "what do you think", 
                                           "how is my", "rate my", "feedback on"]):
            return "analyze"
        
        # Default to chat for general questions
        return "chat"
    
    def _get_memory_context(self, query: str) -> str:
        """Get relevant past interactions from memory."""
        try:
            from core.state import recall
            hits = recall(query)
            if not hits:
                return ""
            lines = ["Relevant past work:"]
            for h in hits:
                status = "✓" if h.get("success") else "✗"
                lines.append(f"  {status} {h['task'][:100]} [{h.get('intent', '')}]")
            return "\n".join(lines)
        except Exception:
            return ""
    
    def add_to_history(self, role: str, content: str) -> None:
        """Add a turn to conversation history."""
        self.history.append({"role": role, "content": content})
        # Cap history to prevent memory bloat
        if len(self.history) > 40:  # Keep last 20 turns (user + assistant)
            self.history = self.history[-40:]
    
    def set_chat_mode(self, mode: str) -> None:
        """Set chat mode: coding, general, or mixed."""
        if mode in ("coding", "general", "mixed"):
            self.chat_mode = mode
    
    def get_cache_stats(self) -> Dict[str, int]:
        """Get cache statistics."""
        return _response_cache.stats()
    
    def clear_cache(self) -> None:
        """Clear the response cache."""
        _response_cache.clear()
