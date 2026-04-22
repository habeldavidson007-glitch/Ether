"""Writer Module - Response polishing and template formatting."""

from pathlib import Path
from typing import Dict, Optional


class Writer:
    def __init__(self, templates_dir: str = "templates"):
        self.templates_dir = Path(templates_dir)
        self.templates: Dict[str, str] = {
            "explanation": "## {title}\n\n{content}\n\n### Key Points\n{bullet_points}",
            "tutorial": "## {title}\n\n### Steps\n{bullet_points}\n\n### Details\n{content}",
            "debug_report": "## {title}\n\n### Issue\n{content}\n\n### Findings\n{bullet_points}",
            "comparison": "## {title}\n\n{content}\n\n### Comparison Notes\n{bullet_points}",
            "casual_chat": "Hey! {content}\n\nQuick takeaways:\n{bullet_points}",
            "code_review": "## {title}\n\n### Review\n{content}\n\n### Suggestions\n{bullet_points}",
        }

    def format_response(self, content: str, format_type: str = "explanation", title: str = "Response") -> str:
        template = self._get_template(format_type)
        bullet_points = self._to_bullets(content)
        return template.format(title=title, content=content.strip(), bullet_points=bullet_points)

    def enhance_chat_response(self, content: str, context: Optional[str] = None) -> str:
        prefix = ""
        if context:
            prefix = "I found helpful context and used it. "
        bullets = self._to_bullets(content)
        return f"{prefix}{content.strip()}\n\nWant a deeper walkthrough?\n{bullets}"

    def _to_bullets(self, content: str) -> str:
        parts = [p.strip() for p in content.replace("\n", ". ").split(".") if p.strip()]
        if not parts:
            return "- No key points extracted"
        top = parts[:4]
        return "\n".join(f"- {line}" for line in top)

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
