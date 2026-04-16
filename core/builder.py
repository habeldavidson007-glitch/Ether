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
            "num_predict": 384,        # 🔥 Optimized for speed/quality balance
            "temperature": 0.4,        # 🔥 Better creativity for small model
            "top_p": 0.9,
            "repeat_penalty": 1.05,    # 🔥 Less restrictive
            "stop": ["User:", "Chatbot:", "Assistant:", "###", "\n\n"],
        },
    }

    try:
        response = requests.post(
            OLLAMA_URL,
            json=payload,
            timeout=90   # 🔥 Optimized timeout
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
        return "❌ Timeout (model too slow). Try shorter input or restart Ollama."

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
