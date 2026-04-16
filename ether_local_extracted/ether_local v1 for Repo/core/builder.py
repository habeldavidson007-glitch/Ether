"""
Builder — AI pipeline using Ollama (local).
Model: qwen2.5:0.5b (fits 4GB RAM)
No API key. No internet required.
"""

import json
import re
import requests
from typing import Any, Dict, List, Optional, Tuple

OLLAMA_URL = "http://localhost:11434/api/chat"
DEFAULT_MODEL = "qwen2.5:0.5b"


def _call(messages: List[Dict], max_tokens: int = 200) -> str:
    if not messages:
        return "⚠ No input provided."

    # 🔥 ONLY system + last user
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
            "num_predict": 96,         # 🔥 FIX: ga kepotong lagi
            "temperature": 0.2,
            "top_p": 0.9,
            "repeat_penalty": 1.15,    # 🔥 smoother
            "stop": ["User:", "Chatbot:", "Assistant:", "###"],
        },
    }

    try:
        response = requests.post(
            OLLAMA_URL,
            json=payload,
            timeout=60   # 🔥 jangan terlalu lama
        )

        if response.status_code != 200:
            return f"❌ Ollama error {response.status_code}: {response.text}"

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
        return "❌ Timeout (model too slow). Try shorter input."

    except requests.exceptions.ConnectionError:
        return "❌ Ollama not running."

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
    messages = [
        {"role": "system", "content": _THINK_SYSTEM},
        {"role": "user", "content": f"Task: {task}\n\nProject context:\n{context}"}
    ]
    raw = _call(messages, max_tokens=600)
    result = _safe_json(raw)
    if not result:
        result = {"understanding": raw[:300], "existing_relevant": [], "missing": [], "approach": ""}
    return result


def plan(task: str, thought: Dict, context: str) -> Dict:
    messages = [
        {"role": "system", "content": _PLAN_SYSTEM},
        {"role": "user", "content": (
            f"Task: {task}\n\n"
            f"Analysis: {json.dumps(thought, indent=2)}\n\n"
            f"Project context:\n{context}"
        )}
    ]
    raw = _call(messages, max_tokens=800)
    result = _safe_json(raw)
    if not result:
        result = {"files": [], "connections": [], "notes": raw[:200]}
    return result


def build(task: str, thought: Dict, blueprint: Dict, context: str) -> Dict:
    messages = [
        {"role": "system", "content": _BUILD_SYSTEM},
        {"role": "user", "content": (
            f"Task: {task}\n\n"
            f"Analysis: {json.dumps(thought, indent=2)}\n\n"
            f"Plan: {json.dumps(blueprint, indent=2)}\n\n"
            f"Existing code:\n{context}"
        )}
    ]
    raw = _call(messages, max_tokens=2048)
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
        {"role": "user", "content": f"Error/task:\n{error_log}\n\nACTUAL PROJECT CODE:\n{context}"}
    ]
    raw = _call(messages, max_tokens=2048)
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
    mode_suffix = _MODE_SUFFIX.get(chat_mode, _MODE_SUFFIX["mixed"])
    system = _ANALYZE_SYSTEM + mode_suffix
    messages = [{"role": "system", "content": system}]
    for turn in history[-6:]:
        messages.append(turn)
    if context:
        messages.append({"role": "user", "content": f"Task: {task}\n\nACTUAL PROJECT CODE:\n{context}"})
    else:
        messages.append({"role": "user", "content": task})
    return _call(messages, max_tokens=800)


def chat(message: str, history: List[Dict], context: str, chat_mode: str = "mixed") -> str:
    # Expert persona system prompt
    persona = _EXPERT_PERSONAS.get(chat_mode, _EXPERT_PERSONAS["mixed"])
    mode_suffix = _MODE_SUFFIX.get(chat_mode, _MODE_SUFFIX["mixed"])
    
    system = _GODOT_SYSTEM + persona + mode_suffix + """

Rules:
- Only answer based on the user's LAST message.
- Do NOT assume any previous topic.
- Do NOT continue unrelated text.
- Keep answers short and relevant.
- If user says 'hi', just greet back normally.
- No rambling. No hallucination.
"""

    messages = [
        {"role": "system", "content": system},
        {"role": "user", "content": message}  # 🔥 ONLY LAST MESSAGE
    ]

    return _call(messages, max_tokens=200)

# ── Full Pipeline Entry Point ───────────────────────────────────────────────────

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

    # 🔥 SIMPLE MODE (SAFE)
    step("⚡ Quick response...")

    try:
        text = chat(task, history, context, chat_mode=chat_mode)
        return {"type": "chat", "text": text}, log

    except Exception as e:
        return {"type": "chat", "text": f"❌ Error: {str(e)}"}, log