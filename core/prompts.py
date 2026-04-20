"""
Ether — Prompt Architecture v2.0
=================================
Split prompt system: GENERATE | DEBUG | EXPLAIN
Optimized for small local models (qwen2.5-coder, gemma 2b).

Design rules:
- LLM NEVER classifies intent. Python routes. LLM executes.
- Each prompt is role-specific, no routing logic inside.
- Minimal tokens. Deterministic output format.
- Code style memory + project pattern hints injected by Python.
"""

from typing import Optional


# ── Base identity (shared, tiny) ───────────────────────────────────────────────

_BASE = """You are a Godot 4 GDScript code assistant.
Rules: Godot 4 syntax only. snake_case. No Unity/Unreal patterns. No extra commentary."""


# ══════════════════════════════════════════════════════════════════════════════
# GENERATE_PROMPT
# Role: Create or modify GDScript files from a task description.
# Input vars: {task}, {context}, {style_hints}, {pattern_hints}
# ══════════════════════════════════════════════════════════════════════════════

GENERATE_PROMPT = _BASE + """

Task: generate complete GDScript file(s).

Output ONLY this JSON — no other text:
{{
  "changes": [
    {{
      "file": "scripts/example.gd",
      "action": "create_or_modify",
      "content": "# full file content\\nextends Node\\n..."
    }}
  ],
  "summary": "one sentence: what was built"
}}

Constraints:
- Complete files only. No placeholders. No snippets.
- Use signals over direct node refs where possible.
- Include @export and type hints where useful.
{style_hints}{pattern_hints}"""


# ══════════════════════════════════════════════════════════════════════════════
# DEBUG_PROMPT
# Role: Find root cause and fix from error + code context.
# Input vars: {error}, {context}, {style_hints}, {pattern_hints}
# ══════════════════════════════════════════════════════════════════════════════

DEBUG_PROMPT = _BASE + """

Task: diagnose the error and output a fix.

Output ONLY this JSON — no other text:
{{
  "root_cause": "specific cause in the provided code",
  "changes": [
    {{
      "file": "path/to/file.gd",
      "action": "create_or_modify",
      "content": "complete fixed file content"
    }}
  ],
  "explanation": "why this fix works",
  "prevention": "one line: how to avoid this"
}}

Constraints:
- Reference actual file names and variable names from context.
- changes[] must contain the full corrected file, not a patch.
- If no code context is available, set changes to [].
{style_hints}{pattern_hints}"""


# ══════════════════════════════════════════════════════════════════════════════
# EXPLAIN_PROMPT
# Role: Explain a Godot concept, signal, API, or pattern in plain text.
# Input vars: {topic}, {context}, {pattern_hints}
# ══════════════════════════════════════════════════════════════════════════════

EXPLAIN_PROMPT = _BASE + """

Task: explain the topic clearly and concisely.

Output plain text only — no JSON, no markdown headers.
- 2–4 sentences max for concepts.
- Include a short GDScript example if it aids understanding.
- Use Godot 4 API only.
{pattern_hints}"""


# ── Hint builders ──────────────────────────────────────────────────────────────

def build_style_hints(style_memory: Optional[dict]) -> str:
    """
    Convert code style memory dict into a compact hint line.
    style_memory example:
      {"indent": "tabs", "typing": "strict", "signals": "preferred"}
    """
    if not style_memory:
        return ""
    parts = []
    if style_memory.get("indent"):
        parts.append(f"indent:{style_memory['indent']}")
    if style_memory.get("typing"):
        parts.append(f"typing:{style_memory['typing']}")
    if style_memory.get("signals"):
        parts.append(f"signals:{style_memory['signals']}")
    if not parts:
        return ""
    return f"\nStyle: {', '.join(parts)}."


def build_pattern_hints(project_patterns: Optional[list]) -> str:
    """
    Convert project pattern list into a compact hint block.
    project_patterns example:
      ["uses StateMachine autoload", "CharacterBody2D for player"]
    Max 3 hints, 60 chars each, to keep tokens low.
    """
    if not project_patterns:
        return ""
    trimmed = [str(p)[:60] for p in project_patterns[:3]]
    return "\nProject patterns: " + "; ".join(trimmed) + "."


# ── Prompt selector (called by Python pipeline, NOT by LLM) ───────────────────

def select_prompt(
    role: str,
    task: str = "",
    context: str = "",
    style_memory: Optional[dict] = None,
    project_patterns: Optional[list] = None,
) -> tuple[str, str]:
    """
    Select and render the correct system + user prompt pair.

    Args:
        role:             "generate" | "debug" | "explain"
        task:             User task / error description
        context:          Relevant project code (pre-truncated by caller)
        style_memory:     Optional dict of code style hints
        project_patterns: Optional list of short project pattern strings

    Returns:
        (system_prompt, user_message) tuple ready to pass to _call()

    Python controls routing. LLM never sees the role decision.
    """
    sh = build_style_hints(style_memory)
    ph = build_pattern_hints(project_patterns)

    if role == "generate":
        system = GENERATE_PROMPT.format(style_hints=sh, pattern_hints=ph)
        user = f"Task: {task}"
        if context:
            user += f"\n\nExisting code:\n{context}"

    elif role == "debug":
        system = DEBUG_PROMPT.format(style_hints=sh, pattern_hints=ph)
        user = f"Error/task:\n{task}"
        if context:
            user += f"\n\nACTUAL CODE:\n{context}"

    elif role == "explain":
        system = EXPLAIN_PROMPT.format(pattern_hints=ph)
        user = f"Topic: {task}"
        if context:
            user += f"\n\nRelated code:\n{context}"

    else:
        # Fallback: plain chat, no routing metadata exposed to LLM
        system = _BASE + "\nAnswer helpfully and concisely. Plain text only."
        user = task

    return system, user
