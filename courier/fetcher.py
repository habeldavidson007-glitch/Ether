"""Courier Fetcher - writes baseline knowledge files to the knowledge base."""

import argparse
from pathlib import Path
from typing import Dict


KNOWLEDGE_SOURCES: Dict[str, str] = {
    "godot_docs": "godot_engine.md",
    "cpp_basics": "cpp_basics.md",
    "unreal_engine": "unreal_engine.md",
    "unity_engine": "unity_engine.md",
    "javascript_basics": "javascript_basics.md",
    "design_patterns": "design_patterns.md",
    "general_facts": "general_facts.md",
}


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Populate knowledge base from configured sources.")
    parser.add_argument("--sources", nargs="*", help="Subset of source keys to update")
    parser.add_argument("--output", default="knowledge_base", help="Output directory for knowledge files")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    output_dir = Path(args.output)
    output_dir.mkdir(parents=True, exist_ok=True)

    selected = args.sources if args.sources else list(KNOWLEDGE_SOURCES.keys())

    for source in selected:
        if source not in KNOWLEDGE_SOURCES:
            print(f"[Courier] Skipping unknown source: {source}")
            continue

        filename = KNOWLEDGE_SOURCES[source]
        target = output_dir / filename
        if target.exists():
            print(f"[Courier] Exists: {target}")
            continue

        target.write_text(f"# {source}\n\nUpdated by courier fetcher.\n", encoding="utf-8")
        print(f"[Courier] Wrote: {target}")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
