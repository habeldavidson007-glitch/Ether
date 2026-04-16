"""
Ether v1.3 — AI Pipeline with Intent-Aware Routing, Lazy Loading & Cached Intelligence
=======================================================================================
Model: qwen2.5:0.5b (fits 4GB RAM)
No API key. No internet required.

OPTIMIZATIONS IMPLEMENTED:
1. INTENT-AWARE ROUTING: Detect simple intents (greetings, status) via regex and route
   to fast path with low token limits (64-192 tokens) and short timeouts (10s).
2. LAZY LOADING: File content loaded only when needed (handled by project_loader.py).
3. CACHED INTELLIGENCE: In-memory cache with TTL for repeated queries.

Performance Targets:
- Greetings respond in <2 seconds
- RAM usage kept under 1.5GB
- Cache hits return instantly (<100ms)
"""

import json
import re
import time
import hashlib
import requests
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple
from functools import lru_cache


# ── Configuration ──────────────────────────────────────────────────────────────

OLLAMA_URL = "http://localhost:11434/api/chat"
DEFAULT_MODEL = "qwen2.5:0.5b"

# Timeout settings based on intent
TIMEOUT_FAST = 10    # For greetings, simple chat
TIMEOUT_NORMAL = 30  # For analysis
TIMEOUT_SLOW = 90    # For code generation, debugging

# Token limits based on intent
MAX_TOKENS_FAST = 64     # Greetings, simple responses
MAX_TOKENS_CHAT = 192    # General conversation
MAX_TOKENS_ANALYZE = 384 # Analysis tasks
MAX_TOKENS_BUILD = 1024  # Code generation

# Cache settings
CACHE_TTL_SECONDS = 300  # 5 minutes cache validity
MAX_CACHE_ENTRIES = 50   # Limit cache size to prevent memory bloat


# ── Cached Intelligence Layer ──────────────────────────────────────────────────

class ResponseCache:
    """
    OPTIMIZATION #3: Cached Intelligence Layer
    
    Simple in-memory cache with TTL (Time-To-Live).
    If the user asks the same question about the same project state,
    return the cached answer instantly without calling Ollama.
    
    Cache key includes:
    - Query text (normalized)
    - Intent type
    - Project fingerprint (based on file count and sizes)
    """
    
    def __init__(self, ttl_seconds: int = CACHE_TTL_SECONDS, max_entries: int = MAX_CACHE_ENTRIES):
        self.ttl = ttl_seconds
        self.max_entries = max_entries
        self._cache: Dict[str, Dict[str, Any]] = {}
        self._timestamps: Dict[str, float] = {}
    
    def _make_key(self, query: str, intent: str, project_fingerprint: str) -> str:
        """Create a unique cache key."""
        normalized_query = ' '.join(query.lower().split())  # Normalize whitespace
        key_data = f"{normalized_query}|{intent}|{project_fingerprint}"
        return hashlib.md5(key_data.encode()).hexdigest()
    
    def get(self, query: str, intent: str, project_fingerprint: str) -> Optional[Any]:
        """Get cached response if valid."""
        key = self._make_key(query, intent, project_fingerprint)
        
        if key not in self._cache:
            return None
        
        # Check TTL
        if time.time() - self._timestamps.get(key, 0) > self.ttl:
            # Expired, remove it
            self._cache.pop(key, None)
            self._timestamps.pop(key, None)
            return None
        
        return self._cache[key]
    
    def set(self, query: str, intent: str, project_fingerprint: str, response: Any) -> None:
        """Store response in cache."""
        key = self._make_key(query, intent, project_fingerprint)
        
        # Evict oldest if at capacity
        if len(self._cache) >= self.max_entries:
            oldest_key = min(self._timestamps.keys(), key=lambda k: self._timestamps[k])
            self._cache.pop(oldest_key, None)
            self._timestamps.pop(oldest_key, None)
        
        self._cache[key] = response
        self._timestamps[key] = time.time()
    
    def clear(self) -> None:
        """Clear all cached entries."""
        self._cache.clear()
        self._timestamps.clear()
    
    def stats(self) -> Dict[str, int]:
        """Get cache statistics."""
        return {
            "entries": len(self._cache),
            "max_entries": self.max_entries,
        }


# Global cache instance
_response_cache = ResponseCache()


def get_project_fingerprint(file_index: Dict[str, Any]) -> str:
    """
    Generate a lightweight fingerprint of project state for cache invalidation.
    Based on file paths and sizes, not content (to avoid hashing large files).
    """
    if not file_index:
        return "empty"
    
    # Create a simple hash from file metadata
    fingerprint_data = "|".join(
        f"{path}:{meta.get('size', 0)}" 
        for path, meta in sorted(file_index.items())
    )
    return hashlib.md5(fingerprint_data.encode()).hexdigest()[:16]


# ── Intent Detection (Fast Path) ───────────────────────────────────────────────

# Regex patterns for fast intent detection (no LLM needed)
_GREETING_PATTERNS = [
    r'^\s*(hi|hello|hey|yo|hola|greetings)\b',
    r'^\s*(good\s+(morning|afternoon|evening|night))\b',
    r'^\s*(how\s+are\s+you|whats?\s*up|sup|yo)\b',
]

_STATUS_PATTERNS = [
    r'\b(status|stats|how\s+(many|much)|count)\b',
    r'\bwhat\s+(do|i have|files|scripts)|list\s+(files|scripts|scenes)\b',
]

_QUICK_HELP_PATTERNS = [
    r'^(help|what\s+can\s+you\s+do|commands|features)\b',
    r'^\s*thanks?\b',
    r'^(bye|goodbye|see\s+you|later)\b',
]

# Pre-compiled regexes for speed
_GREETING_RE = [re.compile(p, re.IGNORECASE) for p in _GREETING_PATTERNS]
_STATUS_RE = [re.compile(p, re.IGNORECASE) for p in _STATUS_PATTERNS]
_QUICK_HELP_RE = [re.compile(p, re.IGNORECASE) for p in _QUICK_HELP_PATTERNS]


def detect_intent_fast(query: str) -> str:
    """
    OPTIMIZATION #1: Intent-Aware Routing (Fast Detection)
    
    Detect simple intents using regex patterns WITHOUT calling LLM.
    Returns: 'greeting', 'status', 'quick_help', or 'complex'
    """
    query_stripped = query.strip()
    
    # Check greetings first (most common fast path)
    for pattern in _GREETING_RE:
        if pattern.match(query_stripped):
            return 'greeting'
    
    # Check status queries
    for pattern in _STATUS_RE:
        if pattern.search(query_stripped):
            return 'status'
    
    # Check quick help
    for pattern in _QUICK_HELP_RE:
        if pattern.match(query_stripped) or pattern.search(query_stripped):
            return 'quick_help'
    
    return 'complex'


def get_fast_response(intent: str, query: str, project_stats: Dict[str, int] = None) -> str:
    """
    Generate instant responses for simple intents without calling LLM.
    This ensures greetings respond in <2 seconds.
    """
    if intent == 'greeting':
        return "Hello! I'm Ether, your Godot development assistant. How can I help with your project today?"
    
    elif intent == 'status':
        if project_stats:
            return (f"📊 Project Status:\n"
                    f"• Scripts: {project_stats.get('script_count', 0)}\n"
                    f"• Scenes: {project_stats.get('scene_count', 0)}\n"
                    f"• Total Files: {project_stats.get('total_files', 0)}\n"
                    f"• Loaded in Memory: {project_stats.get('loaded_files', 0)}")
        return "No project loaded. Upload a ZIP to see project status."
    
    elif intent == 'quick_help':
        return ("I can help you with:\n"
                "• 📝 Writing GDScript code\n"
                "• 🐛 Debugging errors\n"
                "• 🔍 Analyzing your project\n"
                "• 💡 Game design advice\n\n"
                "Just ask me anything about your Godot project!")
    
    return ""


# ── Ollama Call Function ───────────────────────────────────────────────────────

def _call(messages: List[Dict], max_tokens: int = 200, timeout: int = TIMEOUT_NORMAL) -> str:
    """
    Call Ollama API with configurable token limit and timeout.
    Optimized for qwen2.5:0.5b model.
    """
    if not messages:
        return "⚠ No input provided."

    # 🔥 ONLY system + last user (to save context window)
    system_msg = None
    user_msg = None

    for m in messages:
        if m["role"] == "system":
            system_msg = m
        elif m["role"] == "user":
            user_msg = m

    messages = []
    if system_msg:
        messages.append(system_msg)
    if user_msg:
        messages.append(user_msg)

    payload = {
        "model": DEFAULT_MODEL,
        "messages": messages,
        "stream": False,
        "options": {
            "num_predict": max_tokens,
            "temperature": 0.4,
            "top_p": 0.9,
            "repeat_penalty": 1.05,
            "stop": ["User:", "Chatbot:", "Assistant:", "###", "\n\n"],
        },
    }

    try:
        response = requests.post(
            OLLAMA_URL,
            json=payload,
            timeout=timeout  # Configurable timeout based on intent
        )

        if response.status_code != 200:
            return f"❌ Ollama error {response.status_code}: {response.text[:200]}"

        data = response.json()
        content = data.get("message", {}).get("content", "").strip()

        # 🔥 CLEAN LOOP / WEIRD OUTPUT
        for bad in ["User:", "Chatbot:", "Assistant:"]:
            if bad in content:
                content = content.split(bad)[0].strip()

        if not content:
            return "⚠ Empty response. Try again."

        return content

    except requests.exceptions.Timeout:
        return f"❌ Timeout (model too slow, waited {timeout}s). Try shorter input or restart Ollama."

    except requests.exceptions.ConnectionError:
        return "❌ Ollama not running. Start with: ollama serve"

    except Exception as e:
        return f"❌ Error: {str(e)}"


# ── System Prompts ──────────────────────────────────────────────────────────────

_GODOT_SYSTEM = """You are Ether — a Godot 4 development assistant with deep GDScript expertise.

Core rules:
- Always use Godot 4 syntax (@export, @onready, func _ready, etc.)
- Prefer signals over direct node coupling
- snake_case for all names
- Include type hints where helpful
- Never hallucinate Unity, Unreal, or C# patterns
- Generate COMPLETE files, never partial snippets"""

# Expert personas for different modes
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


# ── Pipeline Steps ──────────────────────────────────────────────────────────────

def think(task: str, context: str) -> Dict:
    # Truncate context for thinking step
    context_truncated = context[:1000] if len(context) > 1000 else context
    
    messages = [
        {"role": "system", "content": _THINK_SYSTEM},
        {"role": "user", "content": f"Task: {task}\n\nProject context:\n{context_truncated}"}
    ]
    raw = _call(messages, max_tokens=400)  # Reduced for speed
    result = _safe_json(raw)
    if not result:
        result = {"understanding": raw[:300], "existing_relevant": [], "missing": [], "approach": ""}
    return result


def plan(task: str, thought: Dict, context: str) -> Dict:
    # Truncate inputs for planning
    context_truncated = context[:1000] if len(context) > 1000 else context
    thought_str = json.dumps(thought, indent=2)[:400]
    
    messages = [
        {"role": "system", "content": _PLAN_SYSTEM},
        {"role": "user", "content": (
            f"Task: {task}\n\n"
            f"Analysis: {thought_str}\n\n"
            f"Project context:\n{context_truncated}"
        )}
    ]
    raw = _call(messages, max_tokens=600)  # Reduced for speed
    result = _safe_json(raw)
    if not result:
        result = {"files": [], "connections": [], "notes": raw[:200]}
    return result


def build(task: str, thought: Dict, blueprint: Dict, context: str) -> Dict:
    # Truncate context heavily for build step
    context_truncated = context[:1500] if len(context) > 1500 else context
    
    messages = [
        {"role": "system", "content": _BUILD_SYSTEM},
        {"role": "user", "content": (
            f"Task: {task}\n\n"
            f"Analysis: {json.dumps(thought, indent=2)[:500]}\n\n"  # Truncate thought
            f"Plan: {json.dumps(blueprint, indent=2)[:500]}\n\n"   # Truncate plan
            f"Existing code:\n{context_truncated}"
        )}
    ]
    raw = _call(messages, max_tokens=1024)  # Reduced for speed
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
        {"role": "user", "content": f"Error/task:\n{error_log}\n\nACTUAL PROJECT CODE:\n{context[:1500]}"}  # Truncate context
    ]
    raw = _call(messages, max_tokens=1024)  # Reduced for speed
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
        max_context_len = 1200
        if len(context) > max_context_len:
            context = context[:max_context_len] + "\n...(truncated)"
        messages.append({"role": "user", "content": f"Task: {task}\n\nPROJECT CODE:\n{context}"})
    else:
        messages.append({"role": "user", "content": task})
    
    return _call(messages, max_tokens=384)


def chat(message: str, history: List[Dict], context: str, chat_mode: str = "mixed") -> str:
    # Expert persona system prompt - LIGHTWEIGHT version for 0.5b
    persona = _EXPERT_PERSONAS.get(chat_mode, _EXPERT_PERSONAS["mixed"])
    mode_suffix = _MODE_SUFFIX.get(chat_mode, _MODE_SUFFIX["mixed"])

    # Simplified system prompt for faster response
    system = _GODOT_SYSTEM + persona + mode_suffix + """

You are helpful and conversational. Respond naturally to greetings like "hi", "hello", "whatsup".
Be friendly but concise. Keep answers under 3 sentences for casual chat."""

    # Build messages with ONLY current message (no history to save tokens & speed)
    messages = [{"role": "system", "content": system}]
    messages.append({"role": "user", "content": message})

    return _call(messages, max_tokens=256)

def run_pipeline(task: str, intent: str, context: str,
                 history: List[Dict],
                 api_key: str = None,
                 yield_steps=None,
                 chat_mode: str = "mixed") -> Tuple[Dict, List[str]]:

    log = []

    def step(name: str):
        log.append(name)
        if yield_steps:
            yield_steps(name)

    # Route based on intent
    if intent == "analyze":
        step("🔍 Analyzing project...")
        try:
            text = analyze(task, context, history, chat_mode=chat_mode)
            return {"type": "chat", "text": text}, log
        except Exception as e:
            return {"type": "chat", "text": f"❌ Analysis error: {str(e)}"}, log
    
    elif intent == "debug":
        step("🔧 Debugging...")
        try:
            result = debug(task, context)
            return {"type": "debug", **result}, log
        except Exception as e:
            return {"type": "chat", "text": f"❌ Debug error: {str(e)}"}, log
    
    elif intent == "build":
        step("🏗 Building...")
        try:
            thought = think(task, context)
            step("Thinking...")
            blueprint = plan(task, thought, context)
            step("Planning...")
            result = build(task, thought, blueprint, context)
            step("Building...")
            return {"type": "build", "thought": thought, **result}, log
        except Exception as e:
            return {"type": "chat", "text": f"❌ Build error: {str(e)}"}, log
    
    else:
        # casual or default -> chat
        step("⚡ Quick response...")
        try:
            # For chat, don't pass heavy context - just use history
            text = chat(task, history[-4:] if len(history) >= 4 else history, "", chat_mode=chat_mode)
            return {"type": "chat", "text": text}, log
        except Exception as e:
            return {"type": "chat", "text": f"❌ Error: {str(e)}"}, log


# ── EtherBrain: Main Engine Class ──────────────────────────────────────────────

class EtherBrain:
    """
    Ether v1.3 — Main Engine Class
    
    Integrates all three optimizations:
    1. Intent-Aware Routing (fast path for simple queries)
    2. Lazy Loading Architecture (via project_loader)
    3. Cached Intelligence Layer (TTL-based response cache)
    
    Usage:
        brain = EtherBrain()
        brain.load_project_from_zip(zip_data)
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
        
        else:
            # SLOW PATH: Complex intent requires LLM
            # Determine complex intent type (analyze, debug, build, chat)
            complex_intent = self._classify_complex_intent(query)
            
            # Get context lazily (only loads relevant files)
            context = ""
            if self.project_loader:
                step("📂 Loading relevant files...")
                if complex_intent == 'analyze':
                    # For analysis, load more context
                    context = self.project_loader.build_lightweight_context(query, max_chars=4000)
                else:
                    # For other tasks, load minimal context
                    context = self.project_loader.build_lightweight_context(query, max_chars=2000)
                
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
                # Default to chat
                step("💬 Chatting...")
                try:
                    text = chat(query, self.history[-4:] if len(self.history) >= 4 else self.history, 
                               context, chat_mode=self.chat_mode)
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
        
        # Analyze keywords
        if any(k in query_lower for k in ["analyze", "explain", "list", "find", "show", "what", "how", 
                                           "why", "review", "check", "issues", "problems", "describe"]):
            return "analyze"
        
        # Default to chat
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
