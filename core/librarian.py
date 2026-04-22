"""Librarian Module - intelligent context retrieval with lazy loading."""

import re
from pathlib import Path
from typing import Dict, List, Optional, Tuple


class Librarian:
    """
    Lightweight search engine over local markdown/txt knowledge files.

    Design goals:
    - Build an inverted keyword index once.
    - Keep runtime memory low by indexing chunk metadata, not full files.
    - Load per-file content lazily only when retrieving top-ranked chunks.
    """

    def __init__(self, knowledge_base_path: str = "knowledge_base"):
        self.kb_path = Path(knowledge_base_path)
        # word -> [(filename, chunk_idx)]
        self.index: Dict[str, List[Tuple[str, int]]] = {}
        # filename -> line offsets where chunk starts
        self.chunk_map: Dict[str, List[Tuple[int, int]]] = {}
        self.files: List[str] = []
        # lazy file cache: filename -> full content
        self.file_cache: Dict[str, str] = {}
        self._build_index()

    def _build_index(self):
        """Build inverted index from knowledge base files."""
        if not self.kb_path.exists():
            print(f"[Librarian] Knowledge base not found at {self.kb_path}")
            return

        for file_path in sorted(self.kb_path.glob("*.txt")):
            self._index_file(file_path)
        for file_path in sorted(self.kb_path.glob("*.md")):
            self._index_file(file_path)

        print(
            f"[Librarian] Indexed {len(self.chunk_map)} files, "
            f"{sum(len(v) for v in self.chunk_map.values())} chunks, "
            f"{len(self.index)} topics"
        )

    def _index_file(self, file_path: Path):
        """Index a single file by keyword using chunk spans."""
        try:
            content = file_path.read_text(encoding="utf-8")
            chunks = re.split(r"\n\s*\n", content)
            starts: List[Tuple[int, int]] = []
            cursor = 0

            kept_idx = 0
            for chunk in chunks:
                if len(chunk.strip()) < 20:  # Skip tiny chunks
                    cursor += len(chunk) + 2
                    continue
                start = content.find(chunk, cursor)
                end = start + len(chunk)
                starts.append((start, end))
                cursor = end

                words = set(re.findall(r"\b[a-zA-Z_][a-zA-Z0-9_]{2,}\b", chunk.lower()))
                for word in words:
                    if word not in self.index:
                        self.index[word] = []
                    self.index[word].append((file_path.name, kept_idx))
                kept_idx += 1
            self.chunk_map[file_path.name] = starts
            self.files.append(file_path.name)

        except Exception as e:
            print(f"[Librarian] Error indexing {file_path}: {e}")

    def retrieve(self, query: str, mode: str = "mixed", max_chunks: int = 3) -> str:
        """
        Retrieve relevant context based on query and mode.

        Args:
            query: User's question/query
            mode: 'coding', 'general', or 'mixed'
            max_chunks: Maximum number of chunks to return

        Returns:
            Concatenated relevant context string
        """
        # Extract keywords from query
        keywords = set(re.findall(r"\b[a-zA-Z_][a-zA-Z0-9_]{2,}\b", query.lower()))
        expanded_keywords = set(keywords)
        for kw in keywords:
            if kw.endswith("s") and len(kw) > 4:
                expanded_keywords.add(kw[:-1])
            if kw.endswith("ing") and len(kw) > 6:
                expanded_keywords.add(kw[:-3])
        keywords = expanded_keywords

        # Mode-based file filtering
        relevant_files = self._get_mode_files(mode)

        # Score and collect chunks
        chunk_scores: Dict[Tuple[str, int], int] = {}

        for keyword in keywords:
            if keyword in self.index:
                for filename, chunk_idx in self.index[keyword]:
                    if relevant_files and filename not in relevant_files:
                        continue

                    key = (filename, chunk_idx)
                    chunk_scores[key] = chunk_scores.get(key, 0) + 1

        # Sort by score and take top chunks
        sorted_chunks = sorted(chunk_scores.items(), key=lambda x: x[1], reverse=True)

        context_parts = []
        for (filename, chunk_idx), score in sorted_chunks[:max_chunks]:
            chunk = self._get_chunk(filename, chunk_idx)
            if chunk:
                context_parts.append(f"### From {filename} (score: {score}):\n{chunk}")

        if not context_parts:
            return ""

        return "\n\n".join(context_parts)

    def _get_mode_files(self, mode: str) -> Optional[List[str]]:
        """Get list of files relevant to the current mode."""
        if mode == "coding":
            return [
                f
                for f in self.files
                if any(kw in f.lower() for kw in ["code", "lang", "engine", "pattern", "godot", "cpp", "js"])
            ]
        if mode == "general":
            return [
                f
                for f in self.files
                if any(kw in f.lower() for kw in ["fact", "life", "recipe", "history", "science"])
            ]
        # mixed mode returns all files
        return None

    def _get_chunk(self, filename: str, chunk_idx: int) -> Optional[str]:
        """Retrieve a specific chunk from a file."""
        if filename not in self.file_cache:
            file_path = self.kb_path / filename
            if not file_path.exists():
                return None
            self.file_cache[filename] = file_path.read_text(encoding="utf-8")

        chunk_spans = self.chunk_map.get(filename, [])
        if chunk_idx < len(chunk_spans):
            start, end = chunk_spans[chunk_idx]
            return self.file_cache[filename][start:end].strip()

        return None

    def get_all_topics(self) -> List[str]:
        """Return list of all indexed topics/keywords."""
        return sorted(list(self.index.keys()))

    def refresh(self):
        """Rebuild the index (call after courier updates files)."""
        self.index.clear()
        self.file_cache.clear()
        self.files.clear()
        self._build_index()


# Singleton instance
_librarian_instance: Optional[Librarian] = None


def get_librarian() -> Librarian:
    global _librarian_instance
    if _librarian_instance is None:
        _librarian_instance = Librarian()
    return _librarian_instance
