"""
Ether v1.9.2 — AI Pipeline (Windows-Safe Execution)
====================================================
Multi-model, role-based, lazy execution.
CPU-only. 2GB RAM safe. One model per request.

CRITICAL FIXES IN v1.9.2:
1. Temp file injection for reliable prompt delivery (bypasses Windows CLI limits)
2. Stderr capture for debugging silent failures
3. Increased buffer limit (12000 chars) to prevent mid-generation cutoff
4. Aggressive "never fail" code extraction
5. Proper temp file cleanup

OPTIMIZATIONS FROM v1.8:
- Response Cache with TTL and LRU eviction
- Fast-path predefined explanations for Godot terms
- Hybrid static analysis support
- Enhanced intent detection patterns
"""

import json
import re
import time
import hashlib
import requests
import threading
import subprocess
import tempfile
import os
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple
from concurrent.futures import ThreadPoolExecutor, TimeoutError as FuturesTimeoutError


# ── THINKING ENGINE (Deterministic Cognitive Layer) ─────────────────────────
# Converts vague user requests into atomic, bounded instructions for LLM
# This removes "thinking" burden from the model and puts it in Python

def _extract_filename(query: str) -> str:
    """Extract .gd filename from query."""
    import re
    match = re.search(r'([\w\-]+\.gd)', query.lower())
    return match.group(1) if match else ""


def _decompose_task(query: str) -> dict:
    """
    Decompose user query into action and target.
    Returns: {"action": str, "target": str}
    """
    q = query.lower()

    action = "unknown"
    if "optimize" in q or "improve" in q or "refactor" in q:
        action = "optimize"
    elif "fix" in q or "error" in q or "bug" in q or "broken" in q:
        action = "debug"
    elif "explain" in q or "what" in q or "how" in q:
        action = "explain"
    elif "create" in q or "make" in q or "add" in q:
        action = "build"
    elif "analyze" in q or "check" in q or "review" in q:
        action = "analyze"
    else:
        action = "chat"

    return {
        "action": action,
        "target": _extract_filename(q)
    }


def _reduce_task(task: dict, analysis: dict) -> dict:
    """
    Convert vague task into atomic instruction based on static analysis.
    This is the CORE of the Thinking Engine - reduces LLM cognitive load.
    
    Returns: {"focus": str, "instruction": str, "limit": str}
    """
    issues = analysis.get("issues", []) if analysis else []
    issue_str = ", ".join(issues).lower() if issues else ""

    # Priority-based reduction: specific issues get specific fixes
    if "velocity" in issue_str or "movement" in issue_str:
        return {
            "focus": "movement logic",
            "instruction": "normalize velocity handling and ensure delta is applied correctly",
            "limit": "max 30 lines"
        }

    if "delta" in issue_str or "_process" in issue_str:
        return {
            "focus": "_process function",
            "instruction": "add delta parameter and use it for frame-independent movement",
            "limit": "max 20 lines"
        }

    if "signal" in issue_str or "connect" in issue_str:
        return {
            "focus": "signal connections",
            "instruction": "ensure signals are properly connected and disconnected",
            "limit": "max 25 lines"
        }

    if "variable" in issue_str or "unused" in issue_str:
        return {
            "focus": "code cleanup",
            "instruction": "remove unused variables and improve code organization",
            "limit": "max 20 lines"
        }

    # Fallback based on action type
    if task["action"] == "optimize":
        return {
            "focus": "code structure",
            "instruction": "reduce redundancy, improve readability, and apply Godot best practices",
            "limit": "max 25 lines"
        }

    if task["action"] == "debug":
        return {
            "focus": "bug fix",
            "instruction": "identify and fix the root cause of the reported issue",
            "limit": "max 30 lines"
        }

    if task["action"] == "build":
        return {
            "focus": "new feature",
            "instruction": "implement the requested functionality following Godot conventions",
            "limit": "max 30 lines"
        }

    # Default fallback
    return {
        "focus": "general improvement",
        "instruction": "make minimal necessary improvements for clarity and efficiency",
        "limit": "max 20 lines"
    }


def _build_execution_prompt(file: str, reduction: dict, context: str) -> str:
    """
    Build a constrained execution prompt that tells LLM exactly what to do.
    No analysis, no thinking - just execution.
    """
    return f"""File: {file}

Focus: {reduction['focus']}

Instruction:
{reduction['instruction']}

Constraints:
- Modify only necessary parts
- Do not rewrite entire file
- {reduction['limit']}
- Output code only, no explanations

Context:
{context}

Output:
Code only."""


# ── Configuration ──────────────────────────────────────────────────────────────

OLLAMA_URL = "http://localhost:11434/api/chat"

# OPTIMIZED CONFIG FOR 2GB RAM - STRICT LIMITS TO PREVENT TIMEOUTS
PRIMARY_MODEL = "qwen2.5-coder:1.5b-instruct-q4_k_m"
FALLBACK_MODEL = "gemma:2b"

MODELS = {
    "generate": PRIMARY_MODEL,
    "debug":    PRIMARY_MODEL,
    "explain":  PRIMARY_MODEL,
    "chat":     PRIMARY_MODEL,
}

# STRICT CONTEXT LIMITS - Prevents timeout on 1.5B models
MAX_CONTEXT_CHARS = 200      # Hard cap for most tasks
MAX_CONTEXT_ANALYZE = 250    # Slightly more for analysis (max safe limit)
MAX_CONTEXT_BUILD = 150      # Minimal context for generation

TIMEOUT = {
    "generate": 60,   # File-specific tasks need more time
    "debug":    60,
    "explain":  30,
    "chat":     25,
    "analyze":  75,   # Project-wide analysis needs maximum time
}

MAX_TOKENS = {
    "generate": 150,  # Short, focused responses
    "debug":    150,
    "explain":  100,
    "chat":     80,
    "analyze":  200,  # Analysis can be slightly longer
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


# ── WINDOWS-SAFE SUBPROCESS EXECUTION WRAPPER (v1.9) ─────────────────────────────
# Replaces blocking HTTP calls with subprocess.Popen for hard kill capability


def _run_ollama_subprocess(prompt: str, model: str, timeout: int = 60, max_chars: int = 12000) -> Dict[str, Any]:
    """
    Run ollama via subprocess with HARD timeout enforcement.
    
    This is CRITICAL for Windows 2GB RAM systems - prevents indefinite hangs.
    Uses Popen with non-blocking read to enforce exact timeout with process.kill().
    
    FIX v1.9.2: Use temp file injection for reliable prompt delivery on Windows.
    This bypasses CLI argument length limits and encoding issues.
    
    Args:
        prompt: The prompt to send to ollama
        model: Model name to use
        timeout: Hard timeout in seconds
        max_chars: Maximum characters to buffer (early stop) - increased to 12000
    
    Returns:
        Dict with success, output, time, and model info
    """
    # Create temp file for prompt injection (Windows-safe, no length limits)
    temp_file = None
    try:
        # Write prompt to temp file
        fd, temp_path = tempfile.mkstemp(suffix=".txt", text=True)
        temp_file = temp_path
        with os.fdopen(fd, 'w', encoding='utf-8') as f:
            f.write(prompt)
        
        # Use pipe to feed temp file content to ollama
        # cmd /c type file | ollama run model
        cmd = ["cmd", "/c", f"type \"{temp_path}\" | ollama run {model}"]
        
        process = subprocess.Popen(
            cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            encoding="utf-8",
            errors="ignore",
            bufsize=1
        )
        
        buffer = []
        stderr_buffer = []
        start_time = time.time()
        
        # Non-blocking read loop with timeout
        while True:
            # Check if process finished naturally
            if process.poll() is not None:
                # Drain any remaining output
                try:
                    remaining = process.stdout.read()
                    if remaining:
                        buffer.append(remaining)
                except Exception:
                    pass
                break
            
            # Check timeout BEFORE reading (critical!)
            elapsed = time.time() - start_time
            if elapsed > timeout:
                break
            
            # Try to read with small timeout to avoid blocking forever
            # Use select on Unix for non-blocking I/O
            try:
                import select
                # Wait up to 0.5 seconds for data
                ready, _, _ = select.select([process.stdout], [], [], 0.5)
                if ready:
                    line = process.stdout.readline()
                    if line:
                        buffer.append(line)
                        # Early stop if buffer exceeds max_chars
                        if sum(len(l) for l in buffer) > max_chars:
                            break
            except (ImportError, ValueError):
                # Windows fallback: use readline with timeout check
                # On Windows, select() doesn't work on pipes, so we use a different approach
                # Read with a short sleep to prevent CPU spinning
                try:
                    # Try to read available data
                    line = process.stdout.readline()
                    if line:
                        buffer.append(line)
                        if sum(len(l) for l in buffer) > max_chars:
                            break
                    else:
                        # No data available, sleep briefly to avoid blocking
                        time.sleep(0.1)
                except Exception:
                    time.sleep(0.1)
            
            # Also capture stderr for debugging
            try:
                err_line = process.stderr.readline()
                if err_line:
                    stderr_buffer.append(err_line)
            except Exception:
                pass
            
            # Final timeout check after read attempt
            if time.time() - start_time > timeout:
                break
        
        # HARD KILL - ensures process doesn't linger
        try:
            process.kill()
        except Exception:
            pass
        
        elapsed = round(time.time() - start_time, 2)
        output = "".join(buffer).strip()
        stderr_output = "".join(stderr_buffer).strip()
        
        return {
            "success": True if buffer else False,
            "output": output,
            "stderr": stderr_output,
            "time": elapsed,
            "model": model
        }
    except Exception as e:
        return {"success": False, "output": "", "stderr": "", "error": str(e), "time": 0, "model": model}
    finally:
        # Cleanup temp file
        if temp_file and os.path.exists(temp_file):
            try:
                os.unlink(temp_file)
            except Exception:
                pass


def _extract_code_safe(text: str) -> str:
    """
    Aggressive Code Extractor - NEVER fails.
    
    Priority-based extraction:
    1. Try ```gdscript ... ``` blocks
    2. Try generic ``` ... ``` blocks  
    3. Fallback: scan for code keywords (func, var, if, =)
    4. Last resort: return truncated raw text
    
    Never returns empty string unless input is empty.
    """
    if not text or not text.strip():
        return ""
    
    # Priority 1: Try gdscript block
    match = re.search(r"```gdscript(.*?)```", text, re.DOTALL | re.IGNORECASE)
    if match:
        return match.group(1).strip()
    
    # Priority 2: Try generic block
    match = re.search(r"```(.*?)```", text, re.DOTALL)
    if match:
        return match.group(1).strip()
    
    # Priority 3: Fallback heuristic - scan for code keywords
    lines = text.splitlines()
    code_keywords = ["func", "var", "if", "for", "class", "@export", "@onready"]
    code_lines = [
        l for l in lines 
        if any(l.strip().startswith(k) for k in code_keywords) or "=" in l.strip()
    ]
    
    if code_lines:
        return "\n".join(code_lines[:40]).strip()
    
    # Priority 4: Return raw text truncated (never fail)
    return text[:500]


def _call_llm_with_retry(prompt: str, primary_model: str, fallback_model: str, timeout: int = 60) -> Tuple[str, str, str, float]:
    """
    Call LLM with retry downgrade logic.
    
    If primary model produces too short/messy output (< 3 lines of code),
    retry with simplified prompt and fallback model.
    
    Args:
        prompt: Original user prompt
        primary_model: Primary model to try first
        fallback_model: Fallback model for retry
        timeout: Timeout for primary call (fallback uses 40s)
    
    Returns:
        Tuple of (raw_output, extracted_code, model_used, time_taken)
    """
    # First attempt with primary model
    result = _run_ollama_subprocess(prompt, primary_model, timeout=timeout)
    raw_output = result.get("output", "")
    extracted = _extract_code_safe(raw_output)
    time_taken = result.get("time", 0)
    
    # Check if output is too short/messy (less than 3 lines)
    extracted_lines = extracted.splitlines() if extracted else []
    
    if len(extracted_lines) < 3 and fallback_model != primary_model:
        # Retry with simplified prompt and fallback model
        simplified_prompt = f"Fix this briefly: {prompt[:200]}"
        fallback_result = _run_ollama_subprocess(simplified_prompt, fallback_model, timeout=40)
        fallback_raw = fallback_result.get("output", "")
        fallback_extracted = _extract_code_safe(fallback_raw)
        fallback_lines = fallback_extracted.splitlines() if fallback_extracted else []
        
        # Use fallback result if it's better (more lines)
        if len(fallback_lines) >= len(extracted_lines):
            return (
                fallback_raw,
                fallback_extracted,
                fallback_model,
                fallback_result.get("time", 0)
            )
    
    return (raw_output, extracted, primary_model, time_taken)


# ── Ollama Call — Role-Aware with HARD TIMEOUT ENFORCEMENT ─────────────────────

def _call_with_enforced_timeout(model: str, payload: dict, timeout: int) -> Optional[str]:
    """
    Execute Ollama call with HARD timeout enforcement using threading.
    Returns response string or None if timeout/error.
    
    This is CRITICAL for 2GB RAM systems - prevents hanging forever.
    """
    result = {"response": None, "error": None}
    
    def make_request():
        try:
            r = requests.post(OLLAMA_URL, json=payload, timeout=timeout)
            if r.status_code != 200:
                result["error"] = f"Ollama error {r.status_code}: {r.text[:200]}"
                return
            
            content = r.json().get("message", {}).get("content", "").strip()
            # Clean up common artifacts
            for tag in ["User:", "Assistant:", "Chatbot:"]:
                if tag in content:
                    content = content.split(tag)[0].strip()
            result["response"] = content if content else "Empty response. Try again."
            
        except requests.exceptions.Timeout:
            result["error"] = "TIMEOUT"
        except requests.exceptions.ConnectionError:
            result["error"] = "CONNECTION_ERROR"
        except Exception as e:
            result["error"] = str(e)
    
    # Execute in thread with hard timeout
    thread = threading.Thread(target=make_request)
    thread.daemon = True
    thread.start()
    thread.join(timeout + 2)  # Small buffer
    
    if thread.is_alive():
        # Thread still running = timeout enforced
        return None
    
    if result["error"]:
        raise Exception(result["error"])
    
    return result["response"]


def _call(role: str, messages: List[Dict]) -> str:
    """
    Call Ollama with the model assigned to this role.
    Uses Windows-safe subprocess execution with HARD kill capability.
    
    CRITICAL FIX for v1.9: Replaces blocking HTTP calls with subprocess.Popen
    that can be killed exactly at timeout limit.
    """
    model = MODELS.get(role, MODELS["chat"])
    timeout = TIMEOUT.get(role, 30)

    # Keep only system + last user msg to minimize token pressure
    system_msg = next((m for m in messages if m["role"] == "system"), None)
    user_msg = next((m for m in reversed(messages) if m["role"] == "user"), None)

    # Build prompt from messages
    prompt_parts = []
    if system_msg and "content" in system_msg:
        prompt_parts.append(f"System: {system_msg['content']}")
    if user_msg and "content" in user_msg:
        prompt_parts.append(f"User: {user_msg['content']}")
    
    if not prompt_parts:
        return "No input provided."
    
    prompt = "\n".join(prompt_parts) + "\n\nAssistant:"

    try:
        # Use new subprocess wrapper with retry logic
        raw_output, extracted_code, model_used, time_taken = _call_llm_with_retry(
            prompt=prompt,
            primary_model=model,
            fallback_model=FALLBACK_MODEL,
            timeout=timeout
        )
        
        # CRITICAL: Never return empty - always have something to show user
        if not extracted_code and not raw_output:
            return f"No response from {model_used}. Try again."
        
        # Return extracted code if available, otherwise raw output
        result = extracted_code if extracted_code else raw_output
        
        # If result is still very short, add context note
        if len(result.splitlines()) < 2 and raw_output:
            # Include stderr info if available for debugging
            return result
        
        return result
        
    except Exception as e:
        error_msg = str(e)
        if "TIMEOUT" in error_msg or "killed" in error_msg.lower():
            if FALLBACK_MODEL and FALLBACK_MODEL != model:
                # Try one more time with fallback
                try:
                    raw_output, extracted_code, _, time_taken = _call_llm_with_retry(
                        prompt=prompt[:200],  # Simplified prompt
                        primary_model=FALLBACK_MODEL,
                        fallback_model=FALLBACK_MODEL,  # No further fallback
                        timeout=40
                    )
                    return extracted_code if extracted_code else raw_output
                except Exception:
                    pass
            return f"Timeout ({timeout}s). Both models timed out."
        elif "CONNECTION_ERROR" in error_msg or "not found" in error_msg.lower():
            return "Ollama not running. Start with: ollama serve"
        else:
            return f"Error: {error_msg}"


def _call_with_fallback(role: str, messages: List[Dict], timeout: int, tokens: int) -> str:
    """
    Retry with fallback model when primary fails.
    Uses HARD timeout enforcement for reliability.
    """
    fallback_model = FALLBACK_MODEL
    payload_msgs = [m for m in messages if m["role"] in ("system", "user")]
    
    payload = {
        "model": fallback_model,
        "messages": payload_msgs,
        "stream": False,
        "options": {
            "num_predict": tokens,
            "temperature": 0.3,  # Slightly lower for stability
            "top_p": 0.9,
            "repeat_penalty": 1.1,
            "stop": ["User:", "Assistant:", "###"],
        },
    }
    
    try:
        # Use hard timeout enforcement for fallback too
        extended_timeout = int(timeout * 1.2)  # Give fallback slightly more time
        content = _call_with_enforced_timeout(fallback_model, payload, extended_timeout)
        
        if content is None:
            return f"Timeout ({extended_timeout}s). Both models timed out."
        
        return content
        
    except Exception as e:
        error_msg = str(e)
        if "TIMEOUT" in error_msg:
            return f"Timeout ({int(timeout * 1.2)}s). Both models timed out."
        elif "CONNECTION_ERROR" in error_msg:
            return "Ollama not running. Start with: ollama serve"
        else:
            return f"Fallback error: {error_msg}"


# ── JSON Parsing & RESILIENT CODE EXTRACTION ───────────────────────────────────

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


def _extract_code_block(raw: str) -> Optional[str]:
    """
    RESILIENT CODE EXTRACTOR - Never fails.
    Extracts code from various formats:
    - ```gdscript ... ```
    - ```python ... ```
    - ``` ... ```
    - Plain text (returns as-is)
    
    This is CRITICAL - prevents "Parse failed" errors.
    """
    if not raw or not raw.strip():
        return raw
    
    text = raw.strip()
    
    # Try to extract fenced code blocks
    patterns = [
        r'```(?:gdscript|python|GDScript)?\s*(.*?)\s*```',
        r'```\s*(.*?)\s*```',
    ]
    
    for pattern in patterns:
        m = re.search(pattern, text, re.S | re.I)
        if m:
            code = m.group(1).strip()
            if code:
                return code
    
    # If no fenced block found, check if entire response looks like code
    # (starts with common GDScript keywords)
    code_indicators = ['extends ', 'func ', 'var ', '@export', '@onready', 'class_name']
    if any(text.lower().startswith(ind) or f'\n{ind}' in text.lower() for ind in code_indicators):
        return text
    
    # Last resort: return raw output (don't fail)
    return text


def _parse_gd_output(raw: str, expected_format: str = "json") -> Dict:
    """
    RESILIENT PARSER - Combines JSON parsing with code extraction.
    NEVER returns failure - always produces usable output.
    
    Args:
        raw: Raw LLM output
        expected_format: "json" or "code"
    
    Returns:
        Dict with parsed content or fallback
    """
    if not raw or not raw.strip():
        return {"error": "Empty output", "raw": ""}
    
    # First try JSON parsing (for structured responses)
    if expected_format == "json":
        result = _safe_json(raw)
        if result:
            return result
        
        # JSON failed - try to extract code and wrap it
        code = _extract_code_block(raw)
        if code and code != raw:
            # Found code in markdown block
            return {
                "changes": [{"file": "output.gd", "action": "create_or_modify", "content": code}],
                "summary": "Generated (extracted from markdown)",
                "raw_output": raw
            }
    
    # For code format or if JSON parsing failed
    code = _extract_code_block(raw)
    return {
        "changes": [{"file": "output.gd", "action": "create_or_modify", "content": code}],
        "summary": "Generated",
        "raw_output": raw
    }


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
    
    # Adaptive limits based on task type
    if task_type == "analyze":
        max_chars = MAX_CONTEXT_ANALYZE
    elif task_type in ("build", "generate"):
        max_chars = MAX_CONTEXT_BUILD
    else:
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


# ── Hard Output Constraint System (CRITICAL SAFETY LAYER) ──────────────────────

def enforce_max_lines(code: str, max_lines: int = 30) -> str:
    """
    HARD CAP: Enforce maximum line count on generated code.
    This is the primary defense against RAM spikes and infinite generation.
    
    Why this matters:
    - Token limits are soft (model may try to use all tokens)
    - Line limits are hard (immediate truncation)
    - Prevents decoding pressure on low-RAM systems
    """
    if not code:
        return code
    
    lines = code.splitlines()
    if len(lines) <= max_lines:
        return code
    
    # Truncate with clear indicator
    truncated = "\n".join(lines[:max_lines])
    return truncated + "\n# [OUTPUT TRUNCATED: max lines reached]"


def validate_code_safety(code: str) -> Tuple[bool, str]:
    """
    SECURITY GATE: Block dangerous patterns AFTER generation.
    Returns (is_safe, reason_if_unsafe)
    
    Banned patterns:
    - File system access outside workspace
    - Dynamic code loading
    - Infinite loops / recursion without guards
    - External network calls
    """
    if not code:
        return False, "Empty code"
    
    banned_patterns = [
        ("extends Node3D", "Node3D requires 3D resources"),
        ("class_name ", "Global class registration not allowed"),
        ("load(\"res://", "Dynamic resource loading blocked"),
        ("preload(\"res://", "Preload blocked in generated code"),
        ("OS.execute(", "System command execution blocked"),
        ("DirAccess.", "Direct filesystem access blocked"),
        ("FileAccess.", "Direct file access blocked"),
        ("HTTPRequest", "Network requests blocked"),
        ("while true:", "Infinite loop detected"),
        ("while True:", "Infinite loop detected"),
    ]
    
    for pattern, reason in banned_patterns:
        if pattern in code:
            return False, reason
    
    # Check for excessive recursion
    func_calls = re.findall(r'(\w+)\s*\([^)]*\)', code)
    func_defs = set(re.findall(r'^func\s+(\w+)\s*\(', code, re.MULTILINE))
    
    for func_name in func_defs:
        call_count = func_calls.count(func_name)
        if call_count > 3:  # Potential recursive loop
            # Allow if there's a base case check
            if f"if not {func_name}" not in code and f"if !{func_name}" not in code:
                return False, f"Potential unsafe recursion in '{func_name}'"
    
    return True, "OK"


# ── System Prompts ─────────────────────────────────────────────────────────────

_GODOT_BASE = (
    "Godot 4 GDScript assistant. @export, @onready, snake_case. COMPLETE files only."
)

_BUILD_SYSTEM = _GODOT_BASE + """
Output ONLY valid JSON:
{"changes":[{"file":"path.gd","action":"create_or_modify","content":"full file"}],"summary":"what"}"""

_DEBUG_SYSTEM = _GODOT_BASE + """
Diagnose and fix. Output ONLY valid JSON:
{"root_cause":"issue","changes":[{"file":"path.gd","action":"create_or_modify","content":"fixed"}],"explanation":"why"}"""

_EXPLAIN_SYSTEM = _GODOT_BASE + " Answer clearly in 2-3 sentences max. Godot 4 API only."
_CHAT_SYSTEM    = _GODOT_BASE + " Be direct and concise. No JSON — plain text only."


# ── Pipeline Steps ─────────────────────────────────────────────────────────────

def _generate(task: str, context: str) -> Dict:
    """GENERATE role - ultra-light for 1.5B models with HARD OUTPUT CONSTRAINTS"""
    ctx = _trim_context(context, task, task_type="build")[:150]  # Hard cap
    user_content = f"Task:{task}\nCode:{ctx}" if ctx else f"Task:{task}"
    
    # Simplified prompt for speed
    system_prompt = "Godot 4 GDScript. Output JSON:{\"changes\":[{\"file\":\"path.gd\",\"action\":\"create_or_modify\",\"content\":\"full file\"}],\"summary\":\"what changed\"}"
    
    raw = _call("generate", [
        {"role": "system", "content": system_prompt},
        {"role": "user",   "content": user_content},
    ])
    result = _safe_json(raw)
    if not result:
        result = {"changes": [{"file": "output.gd", "action": "create_or_modify", "content": raw}], "summary": "Generated"}

    # CRITICAL: Apply hard output constraints AFTER generation (seatbelt system)
    if "changes" in result and isinstance(result["changes"], list):
        for change in result["changes"]:
            if "content" in change:
                # Enforce line limit
                change["content"] = enforce_max_lines(change["content"], max_lines=30)
                # Validate safety
                is_safe, reason = validate_code_safety(change["content"])
                if not is_safe:
                    change["content"] = f"# INVALID PATCH REJECTED: {reason}\n" + change["content"][:200]

    return result


def _debug(task: str, context: str) -> Dict:
    """DEBUG role - ultra-light for 1.5B models with HARD OUTPUT CONSTRAINTS"""
    ctx = _trim_context(context, task, task_type="default")[:150]  # Hard cap
    user_content = f"Error:{task}\nCode:{ctx}" if ctx else f"Error:{task}"
    
    # Simplified prompt for speed
    system_prompt = "Godot 4 GDScript. Output JSON:{\"root_cause\":\"issue\",\"changes\":[{\"file\":\"path.gd\",\"content\":\"fixed\"}],\"explanation\":\"why\"}"
    
    raw = _call("debug", [
        {"role": "system", "content": system_prompt},
        {"role": "user",   "content": user_content},
    ])
    result = _safe_json(raw)
    if not result:
        result = {"root_cause": "See output", "changes": [], "explanation": raw.strip() or "No output"}

    # CRITICAL: Apply hard output constraints AFTER generation (seatbelt system)
    if "changes" in result and isinstance(result["changes"], list):
        for change in result["changes"]:
            if "content" in change:
                # Enforce line limit
                change["content"] = enforce_max_lines(change["content"], max_lines=30)
                # Validate safety
                is_safe, reason = validate_code_safety(change["content"])
                if not is_safe:
                    change["content"] = f"# INVALID PATCH REJECTED: {reason}\n" + change["content"][:200]

    return result


def _explain(task: str, context: str) -> str:
    """EXPLAIN role - ultra-light for 1.5B models"""
    ctx = _trim_context(context, task, task_type="analyze")[:200]  # Slightly more for analysis
    user_content = f"{task}\n{ctx}" if ctx else task
    
    # Simplified prompt for speed
    system_prompt = "Godot 4 expert. Analyze and optimize. Be specific about file names and line changes. 3 bullet points max."
    
    return _call("explain", [
        {"role": "system", "content": system_prompt},
        {"role": "user",   "content": user_content},
    ])


def _chat(task: str) -> str:
    """CHAT role — fastest path, no context"""
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
        build/generate → _generate()        → qwen2.5-coder:1.5b-instruct-q4_k_m
        debug          → _validate() first  → _debug() if issues → gemma:2b
        explain/analyze→ _explain()         → qwen2.5-coder:1.5b-instruct-q4_k_m
        casual/chat    → _chat()            → qwen2.5-coder:1.5b-instruct-q4_k_m

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
        # CRITICAL FIX: Never show "Parse failed" - always return something useful
        result = {
            "root_cause": raw[:200] if raw else "Unable to parse response",
            "changes": [],
            "explanation": raw[:400] if raw else "No explanation available",
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
    
    return _call("analyze", messages)


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
            
            # Run appropriate pipeline with PIPELINE REORDERING (v1.9 FIX)
            # KEY: File-specific tasks use scoped_loader, NOT global analyzer
            
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
            
            elif complex_intent in ('generate', 'build', 'debug'):
                # FILE-SPECIFIC PIPELINE: Use scoped_loader + THINKING ENGINE
                # This is the CRITICAL FIX - prevents timeout on single-file tasks
                
                # STEP 1: Thinking Engine - decompose task and reduce cognitive load
                task = _decompose_task(query)
                step(f"🧠 Thinking Engine: {task['action']} → {task['target'] or 'general'}")
                
                # STEP 2: Run micro static analysis on target file only (if exists)
                analysis = None
                if task['target'] and self.project_loader:
                    try:
                        from core.static_analyzer import StaticAnalyzer
                        analyzer = StaticAnalyzer()
                        # Analyze ONLY the target file, not entire project
                        analysis = analyzer.analyze_file(task['target'])
                        step(f"⚡ Micro analysis complete: {len(analysis.get('issues', []))} issues found")
                    except Exception as e:
                        step(f"⚠️ Micro analysis skipped: {str(e)}")
                        analysis = None
                
                # STEP 3: Reduce vague task to atomic instruction
                reduction = _reduce_task(task, analysis)
                step(f"🎯 Focus: {reduction['focus']} (limit: {reduction['limit']})")
                
                # STEP 4: Build execution prompt with Thinking Engine output
                target_file = task['target'] or "unknown"
                final_prompt = _build_execution_prompt(target_file, reduction, context)
                
                # STEP 5: Execute with appropriate function
                if complex_intent == 'debug':
                    step("🔧 Debugging...")
                    try:
                        result = debug(final_prompt, context)
                        return {"type": "debug", **result}, log
                    except Exception as e:
                        return {"type": "chat", "text": f"❌ Debug error: {str(e)}"}, log
                
                elif complex_intent == 'build':
                    step("🏗 Building...")
                    try:
                        result = build(final_prompt, context)
                        return {"type": "build", **result}, log
                    except Exception as e:
                        return {"type": "chat", "text": f"❌ Build error: {str(e)}"}, log
                
                else:  # generate
                    step("✨ Generating optimization...")
                    try:
                        result = debug(final_prompt, context)  # Reuse debug pipeline for generate
                        return {"type": "debug", **result}, log
                    except Exception as e:
                        return {"type": "chat", "text": f"❌ Generation error: {str(e)}"}, log
            
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
    
    def _extract_target_file(self, query: str) -> str:
        """
        Extract target .gd filename from query if present.
        Returns filename or None.
        """
        import re
        match = re.search(r'(\w+\.gd)', query.lower())
        return match.group(1) if match else None
    
    def _classify_complex_intent(self, query: str) -> str:
        """
        Classify complex intents (after fast path filtering).
        Returns: analyze, debug, build, generate, or chat
        
        KEY FIX: File-specific requests (e.g., "optimize game.gd") are routed to GENERATE,
        not ANALYZE. This prevents global scans for single-file tasks.
        """
        query_lower = query.lower()
        
        # CRITICAL: Check if query targets a specific file
        has_target_file = self._extract_target_file(query) is not None
        
        # Debug keywords (always debug mode)
        if any(k in query_lower for k in ["fix", "bug", "error", "debug", "crash", "broken", "fail", "exception"]):
            return "debug"
        
        # Build keywords (creating new code)
        if any(k in query_lower for k in ["create", "make", "implement", "generate", "write", "add", "build", "new"]):
            return "build"
        
        # OPTIMIZE/REFACTOR with target file = GENERATE (modification request)
        if has_target_file and any(k in query_lower for k in ["optimize", "improve", "refactor", "clean", "simplify"]):
            return "generate"
        
        # Analyze keywords - ONLY for project-wide or non-file-specific requests
        if any(k in query_lower for k in ["analyze", "list", "find", "show", "review", "check", 
                                           "issues", "problems", "describe", "what do you think", 
                                           "how is my", "rate my", "feedback on"]):
            # If targeting a specific file, treat as generate (local modification)
            if has_target_file:
                return "generate"
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
