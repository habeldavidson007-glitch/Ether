"""
Builder — The AI pipeline.
Patched:
  - _CHAT_SYSTEM now instructs model to use project context
  - analyze intent routes to dedicated analyze pipeline
  - chat_mode (coding/general/mixed) modifies system prompt
"""

import json
import re
import requests
from typing import Any, Dict, List, Optional, Tuple


OPENROUTER_URL = "https://openrouter.ai/api/v1/chat/completions"
DEFAULT_MODEL = "google/gemma-2-9b-it:free"
FALLBACK_MODELS = [
    "meta-llama/llama-3.1-8b-instruct:free",
    "mistralai/mistral-7b-instruct:free",
    "qwen/qwen-2.5-7b-instruct:free",
]


def _call(messages: List[Dict], api_key: str, max_tokens: int = 800) -> str:
    if not api_key or not api_key.startswith("sk-or-"):
        raise RuntimeError("Invalid OpenRouter API key. Get one at https://openrouter.ai/keys")

    max_tokens = min(max_tokens, 800)

    if not messages:
        return "⚠ No input provided."

    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json",
        "HTTP-Referer": "https://github.com/your-repo/ether",
        "X-Title": "Ether",
    }

    # Try primary model first, then fallbacks
    models_to_try = [DEFAULT_MODEL] + FALLBACK_MODELS
    
    for model in models_to_try:
        payload = {
            "model": model,
            "messages": messages,
            "max_tokens": max_tokens,
            "temperature": 0.3,
        }
        try:
            r = requests.post(OPENROUTER_URL, headers=headers, json=payload, timeout=30)
            if not r.ok:
                error_text = r.text[:300]
                # If authentication fails, stop trying other models
                if "Authentication failed" in error_text or "401" in error_text:
                    return f"❌ API ERROR ({model}): Authentication failed. Check your OpenRouter API key."
                # Continue to next model for other errors (rate limits, etc.)
                continue
                
            data = r.json()
            if "choices" not in data or len(data["choices"]) == 0:
                continue
                
            content = data["choices"][0]["message"]["content"]
            if not content:
                continue
                
            return content.strip()
            
        except requests.exceptions.Timeout:
            continue
        except requests.exceptions.RequestException:
            continue
        except Exception:
            continue
    
    # If all models failed, return last error
    return f"❌ API ERROR: All models failed. Check your API key and try again."


def _safe_json(text: str) -> Optional[Dict]:
    text = re.sub(r"```(?:json)?\s*", "", text)
    text = re.sub(r"```", "", text)
    try:
        return json.loads(text.strip())
    except json.JSONDecodeError:
        m = re.search(r"\{.*\}", text, re.DOTALL)
        if m:
            try:
                return json.loads(m.group())
            except Exception:
                pass
    return None


# ── System Prompts ──────────────────────────────────────────────────────────────

_GODOT_SYSTEM = """You are Ether — a Godot 4 development assistant with deep GDScript expertise.

Core rules:
- Always use Godot 4 syntax (@export, @onready, func _ready, etc.)
- Prefer signals over direct node coupling
- snake_case for all names
- Include type hints where helpful
- Never hallucinate Unity, Unreal, or C# patterns
- Generate COMPLETE files, never partial snippets"""

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
      "action": "create" | "modify",
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
- COMPLETE files only. Never use "# ... rest of code ..." or placeholders.
- If modifying, include the full file with changes applied.
- GDScript only (no C#, no pseudo-code)."""

_DEBUG_SYSTEM = _GODOT_SYSTEM + """

Your job: diagnose and fix the error using the ACTUAL CODE provided.
You MUST reference specific file names, line patterns, and variable names from the code context.
Do NOT give generic advice — analyze the real code.

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
  "explanation": "why this specific fix works for this specific code",
  "prevention": "how to avoid this in future"
}"""

_ANALYZE_SYSTEM = _GODOT_SYSTEM + """

Your job: analyze the ACTUAL PROJECT CODE provided and give specific findings.
You MUST reference specific file names, function names, and line patterns found in the code.
Do NOT give generic Godot advice — analyze what is actually in the files.

Format your response as clear text with sections:
- Reference specific files and functions you found
- List concrete issues with file+function references
- List improvements with specific suggestions
- Prioritize by impact"""

# PATCHED: explicitly instructs use of project context
_CHAT_SYSTEM = _GODOT_SYSTEM + """

You are in conversational mode. Be direct, helpful, and specific to Godot.
CRITICAL: If project context is provided below, you MUST reference the actual files,
functions, and code patterns found in that context. Never give generic advice when
real code is available. Quote specific function names, variable names, and file paths.
No JSON output — just clear, useful text."""


# ── Pipeline Steps ──────────────────────────────────────────────────────────────

def think(task: str, context: str, api_key: str) -> Dict:
    messages = [
        {"role": "system", "content": _THINK_SYSTEM},
        {"role": "user", "content": f"Task: {task}\n\nProject context:\n{context}"}
    ]
    raw = _call(messages, api_key, max_tokens=600)
    result = _safe_json(raw)
    if not result:
        result = {"understanding": raw[:300], "existing_relevant": [], "missing": [], "approach": ""}
    return result


def plan(task: str, thought: Dict, context: str, api_key: str) -> Dict:
    messages = [
        {"role": "system", "content": _PLAN_SYSTEM},
        {"role": "user", "content": (
            f"Task: {task}\n\n"
            f"Analysis: {json.dumps(thought, indent=2)}\n\n"
            f"Project context:\n{context}"
        )}
    ]
    raw = _call(messages, api_key, max_tokens=800)
    result = _safe_json(raw)
    if not result:
        result = {"files": [], "connections": [], "notes": raw[:200]}
    return result


def build(task: str, thought: Dict, blueprint: Dict, context: str, api_key: str) -> Dict:
    messages = [
        {"role": "system", "content": _BUILD_SYSTEM},
        {"role": "user", "content": (
            f"Task: {task}\n\n"
            f"Analysis: {json.dumps(thought, indent=2)}\n\n"
            f"Plan: {json.dumps(blueprint, indent=2)}\n\n"
            f"Existing code:\n{context}"
        )}
    ]
    raw = _call(messages, api_key, max_tokens=3000)
    result = _safe_json(raw)
    if not result:
        result = {
            "changes": [{"file": "output.gd", "action": "create_or_modify", "content": raw}],
            "summary": "Generated (raw fallback — JSON parse failed)"
        }
    return result


def debug(error_log: str, context: str, api_key: str) -> Dict:
    messages = [
        {"role": "system", "content": _DEBUG_SYSTEM},
        {"role": "user", "content": f"Error/task:\n{error_log}\n\nACTUAL PROJECT CODE:\n{context}"}
    ]
    raw = _call(messages, api_key, max_tokens=2500)
    result = _safe_json(raw)
    if not result:
        result = {
            "root_cause": "Parse failed — see raw output",
            "changes": [],
            "explanation": raw[:400],
            "prevention": ""
        }
    return result


def analyze(task: str, context: str, history: List[Dict], api_key: str,
            chat_mode: str = "mixed") -> str:
    """PATCHED: dedicated analyze path — always injects full context."""
    mode_suffix = _MODE_SUFFIX.get(chat_mode, _MODE_SUFFIX["mixed"])
    system = _ANALYZE_SYSTEM + mode_suffix
    messages = [{"role": "system", "content": system}]
    for turn in history[-6:]:
        messages.append(turn)
    if context:
        messages.append({"role": "user", "content": f"Task: {task}\n\nACTUAL PROJECT CODE:\n{context}"})
    else:
        messages.append({"role": "user", "content": task})
    return _call(messages, api_key, max_tokens=800)


def chat(message: str, history: List[Dict], context: str, api_key: str,
         chat_mode: str = "mixed") -> str:
    mode_suffix = _MODE_SUFFIX.get(chat_mode, _MODE_SUFFIX["mixed"])
    system = _CHAT_SYSTEM + mode_suffix
    messages = [{"role": "system", "content": system}]
    for turn in history[-8:]:
        messages.append(turn)
    if context:
        messages.append({"role": "user", "content": f"[Project context]\n{context}\n\n{message}"})
    else:
        messages.append({"role": "user", "content": message})
    return _call(messages, api_key, max_tokens=800)


# ── Full Pipeline Entry Point ───────────────────────────────────────────────────

def run_pipeline(task: str, intent: str, context: str,
                 history: List[Dict], api_key: str,
                 yield_steps=None,
                 chat_mode: str = "mixed") -> Tuple[Dict, List[str]]:
    log = []

    def step(name: str):
        log.append(name)
        if yield_steps:
            yield_steps(name)

    if intent not in ["build", "debug", "casual", "analyze", "task"]:
        intent = "casual"

    if intent == "casual":
        step("💬 Thinking...")
        text = chat(task, history, context, api_key, chat_mode=chat_mode)
        return {"type": "chat", "text": text}, log

    # PATCHED: analyze has dedicated path
    if intent == "analyze":
        step("🔬 Analyzing project...")
        text = analyze(task, context, history, api_key, chat_mode=chat_mode)
        return {"type": "chat", "text": text}, log

    if intent == "debug":
        step("🔍 Diagnosing...")
        result = debug(task, context, api_key)
        result["type"] = "debug"
        return result, log

    # Build pipeline
    step("🧠 Understanding...")
    thought = think(task, context, api_key)

    step("📋 Planning...")
    blueprint = plan(task, thought, context, api_key)

    step("⚙️ Building...")
    result = build(task, thought, blueprint, context, api_key)
    result["type"] = "build"
    result["thought"] = thought
    result["blueprint"] = blueprint

    return result, log
