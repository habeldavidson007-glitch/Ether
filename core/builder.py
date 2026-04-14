"""
Builder — The AI pipeline. Three steps, no ceremony.

  think  → understand the problem, identify what's needed
  plan   → decide what files to touch and why
  build  → generate complete working output

Replaces: blackboard pipeline, parallel planners/executors/critics,
          strategy_engine, router, evaluate_hypotheses, refine loop
          (all 2000+ lines → ~200 lines here)

Model: OpenRouter free tier (minimax-m2.5:free default, hermes fallback)
"""

import json
import re
import requests
from typing import Any, Dict, List, Optional, Tuple


# ── API ─────────────────────────────────────────────────────────────────────────

OPENROUTER_URL = "https://openrouter.ai/api/v1/chat/completions"
MODEL_PRIMARY  = "minimax/minimax-m2.5:free"
MODEL_FALLBACK = "nousresearch/hermes-3-llama-3.1-405b:free"


def _call(messages: List[Dict], api_key: str, max_tokens: int = 800) -> str:
    """Single API call with fallback. Returns response text or safe fallback."""
    
    # Validate API key
    if not api_key or not api_key.startswith("sk-"):
        raise RuntimeError("Invalid OpenRouter API key.")
    
    # Cap tokens to prevent issues
    max_tokens = min(max_tokens, 800)
    
    # Ensure messages not empty
    if not messages:
        return "⚠ No input provided."
    
    # Model fallback system (free tier only) - HARD CODED, NO EXTERNAL OVERRIDE
    models = [
        "nousresearch/hermes-3-llama-3.1-405b:free",
        "minimax/minimax-m2.5:free"
    ]
    
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json",
        "HTTP-Referer": "http://localhost:8501",
        "X-Title": "Ether"
    }
    
    for model_name in models:
        # Hard guard: skip any disallowed models (should never happen now)
        if "nemotron" in model_name.lower() or "nvidia" in model_name.lower():
            print(f"[MODEL BLOCKED] {model_name}: Not allowed")
            continue
        
        print(f"[MODEL USED] {model_name}")
        
        payload = {
            "model": model_name,
            "messages": messages,
            "max_tokens": max_tokens,
            "temperature": 0.3,
        }
        
        try:
            r2 = requests.post(OPENROUTER_URL, headers=headers, json=payload, timeout=30)
            
            if not r2.ok:
                print(f"[MODEL FAIL] {model_name}: {r2.text[:300]}")
                continue
            
            data = r2.json()
            
            # Validate response structure
            if "choices" not in data or len(data["choices"]) == 0:
                print(f"[MODEL FAIL] {model_name}: No choices in response")
                continue
            
            content = data["choices"][0]["message"]["content"]
            if not content:
                print(f"[MODEL FAIL] {model_name}: Empty content")
                continue
                
            return content.strip()
            
        except requests.exceptions.Timeout:
            print(f"[MODEL FAIL] {model_name}: Timeout")
            continue
        except requests.exceptions.RequestException as e:
            print(f"[MODEL FAIL] {model_name}: {e}")
            continue
        except Exception as e:
            print(f"[MODEL FAIL] {model_name}: {e}")
            continue
    
    # Final fallback if ALL models fail
    return "⚠ Model unavailable. Check API or try again."


def _safe_json(text: str) -> Optional[Dict]:
    """Extract first JSON object from text, tolerantly."""
    # Strip markdown fences
    text = re.sub(r"```(?:json)?\s*", "", text)
    text = re.sub(r"```", "", text)
    try:
        return json.loads(text.strip())
    except json.JSONDecodeError:
        # Try to find first {...}
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

Your job: diagnose and fix the error.
Output a JSON object:
{
  "root_cause": "what's actually wrong",
  "changes": [
    {
      "file": "path/to/file.gd",
      "action": "create_or_modify",
      "content": "complete fixed file content"
    }
  ],
  "explanation": "why this fix works",
  "prevention": "how to avoid this in future"
}"""

_CHAT_SYSTEM = _GODOT_SYSTEM + """

You are in conversational mode. Be direct, helpful, and specific to Godot.
No JSON output — just clear, useful text."""


# ── Pipeline ────────────────────────────────────────────────────────────────────

def think(task: str, context: str, api_key: str) -> Dict:
    """Step 1: Understand the problem."""
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
    """Step 2: Decide what to build."""
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
    """Step 3: Generate complete working code."""
    messages = [
        {"role": "system", "content": _BUILD_SYSTEM},
        {"role": "user", "content": (
            f"Task: {task}\n\n"
            f"Analysis: {json.dumps(thought, indent=2)}\n\n"
            f"Plan: {json.dumps(blueprint, indent=2)}\n\n"
            f"Existing code:\n{context}"
        )}
    ]
    raw = _call(messages, api_key, max_tokens=1500)
    result = _safe_json(raw)
    if not result:
        # Wrap raw response as a single file change
        result = {
            "changes": [{"file": "output.gd", "action": "create_or_modify", "content": raw}],
            "summary": "Generated (raw fallback — JSON parse failed)"
        }
    return result


def debug(error_log: str, context: str, api_key: str) -> Dict:
    """Single-step debug: diagnose + fix in one call."""
    messages = [
        {"role": "system", "content": _DEBUG_SYSTEM},
        {"role": "user", "content": f"Error log:\n{error_log}\n\nCode context:\n{context}"}
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


def chat(message: str, history: List[Dict], context: str, api_key: str) -> str:
    """Conversational response — no JSON, just text."""
    messages = [{"role": "system", "content": _CHAT_SYSTEM}]
    # Inject limited history
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
                 yield_steps=None) -> Tuple[Dict, List[str]]:
    """
    Routes to the right pipeline based on intent.
    
    Returns: (result_dict, log_lines)
    yield_steps: optional callable(step_name) for streaming UI updates
    """
    log = []

    def step(name: str):
        log.append(name)
        if yield_steps:
            yield_steps(name)

    # Safety fallback - ensure unknown intents default to casual
    if intent not in ["build", "debug", "casual", "analyze", "task"]:
        intent = "casual"

    if intent == "casual":
        step("💬 Thinking...")
        text = chat(task, history, context, api_key)
        return {"type": "chat", "text": text}, log

    if intent == "debug":
        step("🔍 Diagnosing...")
        result = debug(task, context, api_key)
        result["type"] = "debug"
        return result, log

    # Build pipeline (build + analyze both use full 3-step)
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
