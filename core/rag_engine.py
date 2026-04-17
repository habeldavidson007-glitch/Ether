"""
Ether v1.4 — RAG (Retrieval-Augmented Generation) Context Engine
=================================================================
Semantic search and intelligent context retrieval for better AI responses.

This module implements:
1. Lightweight TF-IDF based semantic search (no external dependencies)
2. Chunked document indexing for precise context retrieval
3. Relevance scoring with query-term matching
4. Smart context window building with deduplication

Key Benefits:
- Loads ONLY the most relevant code snippets for each query
- Dramatically improves analysis quality without increasing token count
- Maintains fast response times by avoiding full-file loading
"""

import re
import math
from pathlib import Path
from typing import Dict, List, Tuple, Any, Optional
from collections import defaultdict


# ── Configuration ──────────────────────────────────────────────────────────────

MAX_CHUNK_SIZE = 800       # Characters per chunk
CHUNK_OVERLAP = 150        # Overlap between chunks for context continuity
MAX_RETRIEVED_CHUNKS = 8   # Number of chunks to retrieve
MIN_RELEVANCE_SCORE = 0.15 # Minimum score threshold


# ── TF-IDF Vectorizer (Lightweight, No Dependencies) ───────────────────────────

class SimpleTFIDFVectorizer:
    """
    Simple TF-IDF implementation without sklearn dependency.
    Converts text into weighted term vectors for similarity comparison.
    """
    
    def __init__(self):
        self.vocabulary: Dict[str, int] = {}
        self.idf: Dict[str, float] = {}
        self.documents: List[List[str]] = []
    
    def _tokenize(self, text: str) -> List[str]:
        """Tokenize text into lowercase words, filtering stopwords."""
        stopwords = {
            'the', 'a', 'an', 'and', 'or', 'but', 'in', 'on', 'at', 'to', 'for',
            'of', 'with', 'by', 'from', 'is', 'are', 'was', 'were', 'be', 'been',
            'being', 'have', 'has', 'had', 'do', 'does', 'did', 'will', 'would',
            'could', 'should', 'may', 'might', 'must', 'shall', 'can', 'need',
            'it', 'its', 'this', 'that', 'these', 'those', 'i', 'you', 'he', 'she',
            'we', 'they', 'what', 'which', 'who', 'whom', 'whose', 'where', 'when',
            'why', 'how', 'all', 'each', 'every', 'both', 'few', 'more', 'most',
            'other', 'some', 'such', 'no', 'nor', 'not', 'only', 'own', 'same', 'so',
            'than', 'too', 'very', 'just', 'also', 'now', 'here', 'there', 'then',
            'once', 'if', 'func', 'var', 'const', 'extends', 'class', 'return',
            'pass', 'break', 'continue', 'elif', 'else', 'while', 'for', 'import',
            'as', 'signal', 'export', 'onready', 'enum', 'match', 'case', 'static',
        }
        
        # Extract words (alphanumeric sequences)
        tokens = re.findall(r'\b[a-zA-Z_][a-zA-Z0-9_]*\b', text.lower())
        # Filter stopwords and short tokens
        return [t for t in tokens if t not in stopwords and len(t) > 2]
    
    def fit(self, documents: List[str]) -> None:
        """Build vocabulary and compute IDF scores from documents."""
        self.documents = [self._tokenize(doc) for doc in documents]
        
        # Build vocabulary
        vocab_set = set()
        for tokens in self.documents:
            vocab_set.update(tokens)
        self.vocabulary = {word: idx for idx, word in enumerate(sorted(vocab_set))}
        
        # Compute IDF: log(N / df) where N=total docs, df=docs containing term
        N = len(self.documents)
        doc_freq = defaultdict(int)
        for tokens in self.documents:
            unique_tokens = set(tokens)
            for token in unique_tokens:
                doc_freq[token] += 1
        
        self.idf = {
            word: math.log((N + 1) / (freq + 1)) + 1
            for word, freq in doc_freq.items()
        }
    
    def transform(self, documents: List[str]) -> List[Dict[str, float]]:
        """Transform documents into TF-IDF vectors (sparse representation)."""
        vectors = []
        for doc in documents:
            tokens = self._tokenize(doc)
            vector = defaultdict(float)
            
            # Compute term frequency
            tf = defaultdict(int)
            for token in tokens:
                tf[token] += 1
            
            # Normalize TF (log-normalized)
            for token, count in tf.items():
                tf[token] = 1 + math.log(count) if count > 0 else 0
            
            # Compute TF-IDF
            for token, tf_val in tf.items():
                if token in self.idf:
                    vector[token] = tf_val * self.idf[token]
            
            vectors.append(dict(vector))
        
        return vectors
    
    def cosine_similarity(self, vec1: Dict[str, float], vec2: Dict[str, float]) -> float:
        """Compute cosine similarity between two sparse vectors."""
        # Find common terms
        common_terms = set(vec1.keys()) & set(vec2.keys())
        
        if not common_terms:
            return 0.0
        
        # Compute dot product
        dot_product = sum(vec1[term] * vec2[term] for term in common_terms)
        
        # Compute magnitudes
        mag1 = math.sqrt(sum(v ** 2 for v in vec1.values()))
        mag2 = math.sqrt(sum(v ** 2 for v in vec2.values()))
        
        if mag1 == 0 or mag2 == 0:
            return 0.0
        
        return dot_product / (mag1 * mag2)


# ── Document Chunker ───────────────────────────────────────────────────────────

class DocumentChunker:
    """
    Split documents into overlapping chunks for fine-grained retrieval.
    Preserves code structure by splitting at natural boundaries.
    """
    
    def __init__(self, chunk_size: int = MAX_CHUNK_SIZE, overlap: int = CHUNK_OVERLAP):
        self.chunk_size = chunk_size
        self.overlap = overlap
    
    def chunk_code(self, content: str, file_path: str) -> List[Dict[str, Any]]:
        """
        Split code into chunks at natural boundaries (functions, classes, etc.).
        Returns list of chunks with metadata.
        """
        chunks = []
        lines = content.splitlines()
        
        # Try to split at function/class boundaries
        boundaries = [0]
        for i, line in enumerate(lines):
            stripped = line.strip()
            if (stripped.startswith('func ') or 
                stripped.startswith('class ') or 
                stripped.startswith('extends ') or
                stripped.startswith('@') or
                (stripped.startswith('#') and '---' in stripped)):
                boundaries.append(i)
        
        # Create chunks from boundaries
        for i, start in enumerate(boundaries):
            end = boundaries[i + 1] if i + 1 < len(boundaries) else len(lines)
            
            # Merge small chunks with neighbors
            chunk_lines = lines[start:end]
            chunk_text = '\n'.join(chunk_lines)
            
            if len(chunk_text) < self.chunk_size // 2:
                continue  # Skip very small chunks
            
            # If chunk is too large, split it further
            if len(chunk_text) > self.chunk_size:
                sub_chunks = self._split_large_chunk(chunk_text, file_path, start)
                chunks.extend(sub_chunks)
            else:
                chunks.append({
                    'text': chunk_text,
                    'file': file_path,
                    'start_line': start + 1,
                    'end_line': end,
                    'metadata': {
                        'type': self._detect_chunk_type(chunk_text),
                        'keywords': self._extract_keywords(chunk_text),
                    }
                })
        
        # If no natural boundaries found, use fixed-size chunks
        if not chunks:
            chunks = self._fixed_size_chunk(content, file_path)
        
        return chunks
    
    def _split_large_chunk(self, text: str, file_path: str, base_line: int) -> List[Dict[str, Any]]:
        """Split a large chunk into smaller pieces."""
        chunks = []
        lines = text.splitlines()
        
        i = 0
        while i < len(lines):
            chunk_end = min(i + 30, len(lines))  # ~30 lines per sub-chunk
            
            # Try to end at a blank line or comment
            for j in range(chunk_end - 1, max(i, chunk_end - 10), -1):
                if not lines[j].strip() or lines[j].strip().startswith('#'):
                    chunk_end = j + 1
                    break
            
            chunk_lines = lines[i:chunk_end]
            chunk_text = '\n'.join(chunk_lines)
            
            if chunk_text.strip():
                chunks.append({
                    'text': chunk_text,
                    'file': file_path,
                    'start_line': base_line + i + 1,
                    'end_line': base_line + chunk_end,
                    'metadata': {
                        'type': 'code_block',
                        'keywords': self._extract_keywords(chunk_text),
                    }
                })
            
            i = chunk_end
        
        return chunks
    
    def _fixed_size_chunk(self, content: str, file_path: str) -> List[Dict[str, Any]]:
        """Create fixed-size chunks with overlap."""
        chunks = []
        chars = len(content)
        
        if chars <= self.chunk_size:
            return [{
                'text': content,
                'file': file_path,
                'start_line': 1,
                'end_line': content.count('\n') + 1,
                'metadata': {
                    'type': 'full_file',
                    'keywords': self._extract_keywords(content),
                }
            }]
        
        start = 0
        chunk_num = 0
        while start < chars:
            end = min(start + self.chunk_size, chars)
            
            # Try to break at a newline
            if end < chars:
                last_newline = content.rfind('\n', start, end)
                if last_newline > start:
                    end = last_newline + 1
            
            chunk_text = content[start:end]
            
            # Calculate line numbers
            start_line = content[:start].count('\n') + 1
            end_line = content[:end].count('\n') + 1
            
            chunks.append({
                'text': chunk_text,
                'file': file_path,
                'start_line': start_line,
                'end_line': end_line,
                'metadata': {
                    'type': 'continuation',
                    'keywords': self._extract_keywords(chunk_text),
                }
            })
            
            start = end - self.overlap
            chunk_num += 1
        
        return chunks
    
    def _detect_chunk_type(self, text: str) -> str:
        """Detect the type of code chunk."""
        if 'func ' in text:
            return 'function'
        elif 'class ' in text or 'extends ' in text:
            return 'class'
        elif 'signal ' in text:
            return 'signal'
        elif '@export' in text or '@onready' in text:
            return 'variables'
        else:
            return 'code_block'
    
    def _extract_keywords(self, text: str) -> List[str]:
        """Extract important keywords from chunk."""
        # Function names
        funcs = re.findall(r'func\s+(\w+)', text)
        # Class names
        classes = re.findall(r'class\s+(\w+)|extends\s+(\w+)', text)
        # Variable names (@export, @onready)
        vars_ = re.findall(r'@(?:export|onready)\s+(?:\([^)]*\))?\s*(?:var)?\s*(\w+)', text)
        
        keywords = funcs + [c for group in classes for c in group if c] + vars_
        return list(set(keywords))[:10]  # Limit to top 10


# ── RAG Index ──────────────────────────────────────────────────────────────────

class RAGIndex:
    """
    Semantic search index for project files using TF-IDF.
    Enables intelligent retrieval of relevant code snippets.
    """
    
    def __init__(self):
        self.vectorizer = SimpleTFIDFVectorizer()
        self.chunker = DocumentChunker()
        self.chunks: List[Dict[str, Any]] = []
        self.chunk_vectors: List[Dict[str, float]] = []
        self.is_indexed = False
    
    def build_index(self, file_contents: Dict[str, str]) -> None:
        """
        Build index from file contents.
        Chunks all files and computes TF-IDF vectors.
        """
        self.chunks = []
        
        # Chunk all files
        for file_path, content in file_contents.items():
            file_chunks = self.chunker.chunk_code(content, file_path)
            self.chunks.extend(file_chunks)
        
        if not self.chunks:
            self.is_indexed = False
            return
        
        # Build TF-IDF vectors
        chunk_texts = [chunk['text'] for chunk in self.chunks]
        self.vectorizer.fit(chunk_texts)
        self.chunk_vectors = self.vectorizer.transform(chunk_texts)
        
        self.is_indexed = True
    
    def search(self, query: str, top_k: int = MAX_RETRIEVED_CHUNKS) -> List[Tuple[Dict[str, Any], float]]:
        """
        Search for chunks relevant to query.
        Returns list of (chunk, relevance_score) tuples.
        """
        if not self.is_indexed or not self.chunks:
            return []
        
        # Transform query to vector
        query_vector = self.vectorizer.transform([query])[0]
        
        # Compute similarity with all chunks
        scores = []
        for i, chunk_vec in enumerate(self.chunk_vectors):
            similarity = self.vectorizer.cosine_similarity(query_vector, chunk_vec)
            
            # Boost score if query terms appear in chunk keywords
            chunk_keywords = self.chunks[i]['metadata'].get('keywords', [])
            query_terms = set(query.lower().split())
            keyword_boost = sum(1 for kw in chunk_keywords if kw.lower() in query_terms) * 0.1
            final_score = similarity + keyword_boost
            
            if final_score >= MIN_RELEVANCE_SCORE:
                scores.append((i, final_score))
        
        # Sort by score descending
        scores.sort(key=lambda x: x[1], reverse=True)
        
        # Return top-k results
        results = []
        for idx, score in scores[:top_k]:
            results.append((self.chunks[idx], score))
        
        return results
    
    def get_context_for_query(self, query: str, max_chars: int = 3000) -> str:
        """
        Build optimized context string for AI from retrieved chunks.
        Includes file paths and line numbers for reference.
        """
        results = self.search(query)
        
        if not results:
            return ""
        
        parts = []
        total_chars = 0
        seen_files = set()
        
        for chunk, score in results:
            file_path = chunk['file']
            chunk_type = chunk['metadata']['type']
            
            # Format chunk header
            header = f"\n\n### {file_path} (lines {chunk['start_line']}-{chunk['end_line']}) [{chunk_type}, score: {score:.2f}]\n"
            
            # Add chunk content
            content = f"```gdscript\n{chunk['text']}\n```"
            
            chunk_total = len(header) + len(content)
            
            if total_chars + chunk_total > max_chars:
                # Truncate if needed
                remaining = max_chars - total_chars - len(header)
                if remaining > 100:
                    content = f"```gdscript\n{chunk['text'][:remaining]}\n# [TRUNCATED]\n```"
                    parts.append(header + content)
                break
            
            # Avoid duplicate file contexts
            if file_path not in seen_files or chunk_type in ['function', 'class']:
                parts.append(header + content)
                seen_files.add(file_path)
                total_chars += chunk_total
        
        return "\n".join(parts)
    
    def clear(self) -> None:
        """Clear the index."""
        self.chunks = []
        self.chunk_vectors = []
        self.is_indexed = False


# ── Integration Helper ─────────────────────────────────────────────────────────

def build_rag_context(file_contents: Dict[str, str], query: str, max_chars: int = 3000) -> str:
    """
    Main entry point: Build RAG-enhanced context for a query.
    
    Usage in builder.py:
        context = build_rag_context(loader.get_all_contents(), query)
    """
    index = RAGIndex()
    index.build_index(file_contents)
    return index.get_context_for_query(query, max_chars)
