"""Writer Module - response polishing and template formatting."""

from pathlib import Path
from typing import Dict, Optional


class Writer:
    def __init__(self, templates_dir: str = "templates"):
        self.templates_dir = Path(templates_dir)
        self.templates: Dict[str, str] = {
            "explanation": "## {title}\n\n{content}\n\n### Key Points\n{bullet_points}\n\n### Examples\n{examples}\n\n{conversational}",
            "tutorial": "## {title}\n\n### Steps\n{bullet_points}\n\n### Details\n{content}\n\n### Examples\n{examples}\n\n{conversational}",
            "debug_report": "## {title}\n\n### Issue\n{content}\n\n### Findings\n{bullet_points}\n\n### Repro Tips\n{examples}\n\n{conversational}",
            "comparison": "## {title}\n\n{content}\n\n### Comparison Notes\n{bullet_points}\n\n### Practical Examples\n{examples}\n\n{conversational}",
            "casual_chat": "Hey! {content}\n\nQuick takeaways:\n{bullet_points}\n\nExamples:\n{examples}\n\n{conversational}",
            "code_review": "## {title}\n\n### Review\n{content}\n\n### Suggestions\n{bullet_points}\n\n### Example Refactors\n{examples}\n\n{conversational}",
        }

    def format_response(self, content: str, format_type: str = "explanation", title: str = "Response") -> str:
        expanded = self._expand_short_content(content.strip())
        template = self._get_template(format_type)
        bullet_points = self._to_bullets(expanded)
        examples = self._build_examples(expanded)
        conversational = self._conversational_line(format_type)
        return template.format(
            title=title,
            content=expanded,
            bullet_points=bullet_points,
            examples=examples,
            conversational=conversational,
        )

    def enhance_chat_response(self, content: str, context: Optional[str] = None) -> str:
        prefix = ""
        if context:
            prefix = "I found helpful context and used it. "
        expanded = self._expand_short_content(content.strip())
        bullets = self._to_bullets(expanded)
        examples = self._build_examples(expanded)
        return f"{prefix}{expanded}\n\nWant a deeper walkthrough?\n{bullets}\n\nExample:\n{examples}"

    def _expand_short_content(self, content: str) -> str:
        """Turn very short LLM replies into richer, user-friendly text."""
        if len(content) >= 180:
            return content
        bullets = self._to_bullets(content)
        return (
            f"{content}\n\n"
            "Why this works:\n"
            f"{bullets}\n\n"
            "Next action: apply the change incrementally and re-test after each step."
        )

    def _to_bullets(self, content: str) -> str:
        parts = [p.strip() for p in content.replace("\n", ". ").split(".") if p.strip()]
        if not parts:
            return "- No key points extracted"
        top = parts[:4]
        return "\n".join(f"- {line}" for line in top)

    def _build_examples(self, content: str) -> str:
        first = content.splitlines()[0].strip() if content.strip() else "Use a small reproducible snippet."
        return f"- Example 1: {first[:100]}\n- Example 2: Validate behavior with a focused test case."

    def _conversational_line(self, format_type: str) -> str:
        if format_type == "casual_chat":
            return "If you want, I can make this even more practical for your exact file."
        return "If helpful, I can also provide a concise version."

    def _get_template(self, format_type: str) -> str:
        custom = self.templates_dir / f"{format_type}.txt"
        if custom.exists():
            return custom.read_text(encoding="utf-8")
        return self.templates.get(format_type, self.templates["explanation"])


_writer_instance: Optional[Writer] = None


def get_writer() -> Writer:
    global _writer_instance
    if _writer_instance is None:
        _writer_instance = Writer()
    return _writer_instance
