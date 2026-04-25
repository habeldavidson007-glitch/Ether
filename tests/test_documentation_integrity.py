"""
Hardcoded documentation integrity rules to prevent doc/runtime drift.
"""

from pathlib import Path
import re


REPO_ROOT = Path(__file__).resolve().parent.parent

# Hardcoded scope: user-facing docs that must stay accurate.
DOC_FILES = [
    REPO_ROOT / "README.md",
    REPO_ROOT / "README_CLI.md",
]


def _is_local_link(link: str) -> bool:
    return not (
        link.startswith(("http://", "https://", "mailto:"))
        or link.startswith("#")
    )


def _extract_candidate_paths(text: str) -> set[str]:
    candidates: set[str] = set()

    # Markdown links: [label](path)
    for match in re.findall(r"\[[^\]]+\]\(([^)]+)\)", text):
        link = match.strip()
        if _is_local_link(link):
            candidates.add(link.split("#", 1)[0])

    # Inline code references: `path/to/file.ext`
    for match in re.findall(r"`([^`\n]+\.(?:py|md|toml|json|yaml|yml|txt))`", text):
        ref = match.strip()
        if _is_local_link(ref) and "/" in ref:
            candidates.add(ref)

    return candidates


def test_doc_references_resolve_to_real_files():
    """All local file references in top-level markdown docs must exist."""
    missing: list[str] = []

    for doc_file in DOC_FILES:
        content = doc_file.read_text(encoding="utf-8", errors="ignore")
        for candidate in sorted(_extract_candidate_paths(content)):
            resolved = (REPO_ROOT / candidate).resolve()
            if not resolved.exists():
                missing.append(f"{doc_file.name} -> {candidate}")

    assert not missing, "Broken doc file references:\n" + "\n".join(missing)
