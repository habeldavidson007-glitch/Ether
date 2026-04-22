"""
Unified Search Engine - The "Cortex"
=====================================
Replaces: rag_index.py, compressed_search.py, structural_rag.py, librarian.py (search portion)

A hybrid search engine that combines:
1. Keyword-based inverted index (fast, exact matches)
2. Compressed token search (GPU-free semantic-like retrieval)
3. Structural awareness (Godot scene trees, GDScript AST)
4. External knowledge retrieval (from librarian's knowledge base)

Smart routing automatically selects the best strategy based on query type.
"""

import os
import re
import json
import hashlib
from typing import Dict, List, Optional, Tuple, Any, Set
from pathlib import Path
from collections import defaultdict
from datetime import datetime


class SearchChunk:
    """Unified chunk representation for all search strategies."""
    
    def __init__(self, chunk_id: str, content: str, source_type: str,
                 source_path: str, start_line: int = 0, end_line: int = 0,
                 metadata: Optional[Dict] = None):
        self.chunk_id = chunk_id
        self.content = content
        self.source_type = source_type  # 'gdscript', 'scene', 'knowledge', 'code'
        self.source_path = source_path
        self.start_line = start_line
        self.end_line = end_line
        self.metadata = metadata or {}
        
        # Pre-computed features
        self.tokens = self._tokenize()
        self.token_freq = self._compute_frequency()
        self.signature = self._generate_signature()
        
    def _tokenize(self) -> List[str]:
        """Tokenize content for search."""
        tokens = re.findall(r'[a-zA-Z_][a-zA-Z0-9_]*|[0-9]+', self.content.lower())
        return [t for t in tokens if len(t) > 2]
    
    def _compute_frequency(self) -> Dict[str, int]:
        """Compute token frequency."""
        freq = defaultdict(int)
        for token in self.tokens:
            freq[token] += 1
        return dict(freq)
    
    def _generate_signature(self) -> str:
        """Generate compact signature for quick matching."""
        sorted_tokens = sorted(self.token_freq.items(), key=lambda x: x[1], reverse=True)
        sig_tokens = [t[0] for t in sorted_tokens[:10]]
        return ":".join(sig_tokens)
    
    def get_context(self, include_structure: bool = True) -> str:
        """Get formatted context for LLM prompts."""
        lines = []
        lines.append(f"# Source: {self.source_path} ({self.source_type})")
        
        if self.start_line > 0:
            lines.append(f"# Lines: {self.start_line}-{self.end_line}")
            
        if include_structure and self.metadata:
            if 'node_type' in self.metadata:
                lines.append(f"# Type: {self.metadata['node_type']}")
            if 'parent' in self.metadata:
                lines.append(f"# Parent: {self.metadata['parent']}")
                
        lines.append("")
        lines.append(self.content)
        
        return "\n".join(lines)
    
    def to_dict(self) -> Dict:
        return {
            "id": self.chunk_id,
            "source": self.source_path,
            "type": self.source_type,
            "lines": f"{self.start_line}-{self.end_line}",
            "tokens": len(self.tokens),
            "signature": self.signature[:50]
        }


class UnifiedSearchEngine:
    """
    Main unified search engine combining multiple strategies.
    
    Strategies:
    - keyword: Fast inverted index lookup
    - compressed: Token overlap with Jaccard similarity
    - structural: Godot-aware tree traversal
    - hybrid: Smart combination of all three (default)
    """
    
    def __init__(self, project_root: Optional[str] = None, 
                 knowledge_base_path: str = "knowledge_base"):
        self.project_root = Path(project_root) if project_root else None
        self.knowledge_base_path = Path(knowledge_base_path)
        
        # Chunk storage
        self.chunks: Dict[str, SearchChunk] = {}
        
        # Strategy-specific indexes
        self.keyword_index: Dict[str, Set[str]] = defaultdict(set)  # token -> chunk_ids
        self.file_index: Dict[str, List[str]] = defaultdict(list)  # file -> chunk_ids
        self.structural_index: Dict[str, SearchChunk] = {}  # path -> chunk (for Godot structures)
        
        # Knowledge base chunks (external docs)
        self.knowledge_chunks: Dict[str, SearchChunk] = {}
        self.knowledge_keyword_index: Dict[str, Set[str]] = defaultdict(set)
        
        # Statistics
        self.stats = {
            "total_chunks": 0,
            "project_chunks": 0,
            "knowledge_chunks": 0,
            "vocabulary_size": 0,
            "files_indexed": 0
        }
        
        # Build indexes
        if self.project_root:
            self._build_project_index()
        self._build_knowledge_index()
        
    def _build_project_index(self):
        """Build indexes for project files."""
        if not self.project_root or not self.project_root.exists():
            return
            
        print(f"[UnifiedSearch] Building index for {self.project_root}...")
        self.chunks.clear()
        self.keyword_index.clear()
        self.file_index.clear()
        self.structural_index.clear()
        
        all_tokens = set()
        files_count = 0
        
        # Index GDScript files with structural awareness
        for gd_file in self.project_root.rglob("*.gd"):
            self._index_gdscript(gd_file, all_tokens)
            files_count += 1
            
        # Index scene files
        for tscn_file in self.project_root.rglob("*.tscn"):
            self._index_scene(tscn_file, all_tokens)
            files_count += 1
            
        # Index other code files
        for ext in ["*.py", "*.cs", "*.cpp", "*.h", "*.json"]:
            for code_file in self.project_root.rglob(ext):
                self._index_code_file(code_file, all_tokens)
                files_count += 1
                
        self.stats["files_indexed"] = files_count
        self.stats["project_chunks"] = len(self.chunks)
        self.stats["vocabulary_size"] = len(all_tokens)
        self.stats["total_chunks"] = len(self.chunks) + len(self.knowledge_chunks)
        
        print(f"[UnifiedSearch] Indexed {files_count} files, {len(self.chunks)} chunks")
        
    def _index_gdscript(self, file_path: Path, all_tokens: Set[str]):
        """Index GDScript file with structural awareness."""
        try:
            content = file_path.read_text(encoding='utf-8', errors='ignore')
        except Exception as e:
            return
            
        relative_path = str(file_path.relative_to(self.project_root))
        lines = content.split('\n')
        
        # Parse structure (classes, functions, signals)
        current_class = None
        current_function = None
        chunk_start = 0
        
        for i, line in enumerate(lines):
            stripped = line.strip()
            
            # Detect class
            if stripped.startswith("class "):
                if current_class and chunk_start < i:
                    # Save previous class chunk
                    self._add_gdscript_chunk(
                        lines[chunk_start:i], relative_path, 
                        current_class, current_function, all_tokens
                    )
                current_class = stripped.split()[1].split(":")[0].strip()
                current_function = None
                chunk_start = i
                
            # Detect function
            elif stripped.startswith("func "):
                if current_function and chunk_start < i:
                    # Save previous function chunk
                    self._add_gdscript_chunk(
                        lines[chunk_start:i], relative_path,
                        current_class, current_function, all_tokens
                    )
                func_match = re.match(r'func\s+([a-zA-Z_][a-zA-Z0-9_]*)', stripped)
                current_function = func_match.group(1) if func_match else "unknown"
                chunk_start = i
                
        # Add final chunk
        if chunk_start < len(lines):
            self._add_gdscript_chunk(
                lines[chunk_start:], relative_path,
                current_class, current_function, all_tokens
            )
            
    def _add_gdscript_chunk(self, lines: List[str], file_path: str,
                           class_name: Optional[str], func_name: Optional[str],
                           all_tokens: Set[str]):
        """Add a GDScript chunk to indexes."""
        if not lines or all(line.strip() == "" for line in lines):
            return
            
        content = '\n'.join(lines)
        chunk_id = hashlib.md5(f"{file_path}:{len(content)}".encode()).hexdigest()[:12]
        
        metadata = {}
        if class_name:
            metadata['class'] = class_name
            metadata['node_type'] = 'Class'
        if func_name:
            metadata['function'] = func_name
            metadata['node_type'] = 'Function'
            
        chunk = SearchChunk(
            chunk_id=chunk_id,
            content=content,
            source_type='gdscript',
            source_path=file_path,
            start_line=1,  # Simplified
            end_line=len(lines),
            metadata=metadata
        )
        
        self.chunks[chunk_id] = chunk
        self.file_index[file_path].append(chunk_id)
        
        # Update keyword index
        for token in chunk.tokens:
            self.keyword_index[token].add(chunk_id)
            all_tokens.add(token)
            
        # Structural index
        struct_key = f"{file_path}"
        if class_name:
            struct_key += f"::{class_name}"
        if func_name:
            struct_key += f"::{func_name}"
        self.structural_index[struct_key] = chunk
        
    def _index_scene(self, file_path: Path, all_tokens: Set[str]):
        """Index Godot scene file."""
        try:
            content = file_path.read_text(encoding='utf-8', errors='ignore')
        except Exception:
            return
            
        relative_path = str(file_path.relative_to(self.project_root))
        
        # Create chunk for entire scene (scenes are usually small)
        chunk_id = hashlib.md5(f"{relative_path}:scene".encode()).hexdigest()[:12]
        
        chunk = SearchChunk(
            chunk_id=chunk_id,
            content=content[:2000],  # Limit size
            source_type='scene',
            source_path=relative_path,
            metadata={'node_type': 'Scene'}
        )
        
        self.chunks[chunk_id] = chunk
        self.file_index[relative_path].append(chunk_id)
        
        for token in chunk.tokens:
            self.keyword_index[token].add(chunk_id)
            all_tokens.add(token)
            
    def _index_code_file(self, file_path: Path, all_tokens: Set[str]):
        """Index generic code file."""
        try:
            content = file_path.read_text(encoding='utf-8', errors='ignore')
        except Exception:
            return
            
        relative_path = str(file_path.relative_to(self.project_root))
        ext = file_path.suffix
        
        # Split into chunks of ~50 lines
        lines = content.split('\n')
        chunk_size = 50
        
        for i in range(0, len(lines), chunk_size):
            chunk_lines = lines[i:i+chunk_size]
            if not any(line.strip() for line in chunk_lines):
                continue
                
            content_chunk = '\n'.join(chunk_lines)
            chunk_id = hashlib.md5(f"{relative_path}:{i}".encode()).hexdigest()[:12]
            
            chunk = SearchChunk(
                chunk_id=chunk_id,
                content=content_chunk,
                source_type='code',
                source_path=relative_path,
                start_line=i+1,
                end_line=min(i+chunk_size, len(lines))
            )
            
            self.chunks[chunk_id] = chunk
            self.file_index[relative_path].append(chunk_id)
            
            for token in chunk.tokens:
                self.keyword_index[token].add(chunk_id)
                all_tokens.add(token)
                
    def _build_knowledge_index(self):
        """Build index for external knowledge base."""
        if not self.knowledge_base_path.exists():
            return
            
        print(f"[UnifiedSearch] Loading knowledge base from {self.knowledge_base_path}...")
        self.knowledge_chunks.clear()
        self.knowledge_keyword_index.clear()
        
        all_tokens = set()
        
        for md_file in self.knowledge_base_path.glob("*.md"):
            try:
                content = md_file.read_text(encoding='utf-8', errors='ignore')
            except Exception:
                continue
                
            # Create chunk for entire knowledge file
            chunk_id = f"kb_{md_file.stem}"
            
            chunk = SearchChunk(
                chunk_id=chunk_id,
                content=content,
                source_type='knowledge',
                source_path=str(md_file),
                metadata={'topic': md_file.stem}
            )
            
            self.knowledge_chunks[chunk_id] = chunk
            
            for token in chunk.tokens:
                self.knowledge_keyword_index[token].add(chunk_id)
                all_tokens.add(token)
                
        self.stats["knowledge_chunks"] = len(self.knowledge_chunks)
        self.stats["total_chunks"] = len(self.chunks) + len(self.knowledge_chunks)
        
        print(f"[UnifiedSearch] Loaded {len(self.knowledge_chunks)} knowledge files")
        
    def search(self, query: str, mode: str = "hybrid", top_k: int = 5,
               filters: Optional[Dict] = None) -> List[Dict]:
        """
        Unified search interface.
        
        Args:
            query: Search query
            mode: 'keyword', 'compressed', 'structural', 'hybrid'
            top_k: Number of results
            filters: Optional filters {'source_type': 'gdscript', 'file': 'player.gd'}
            
        Returns:
            List of results with content and metadata
        """
        if mode == "hybrid":
            return self._hybrid_search(query, top_k, filters)
        elif mode == "keyword":
            return self._keyword_search(query, top_k, filters)
        elif mode == "compressed":
            return self._compressed_search(query, top_k, filters)
        elif mode == "structural":
            return self._structural_search(query, top_k, filters)
        else:
            return self._hybrid_search(query, top_k, filters)
            
    def _keyword_search(self, query: str, top_k: int, 
                       filters: Optional[Dict]) -> List[Dict]:
        """Fast keyword-based search."""
        query_tokens = set(re.findall(r'[a-zA-Z_][a-zA-Z0-9_]*', query.lower()))
        query_tokens = {t for t in query_tokens if len(t) > 2}
        
        if not query_tokens:
            return []
            
        # Score chunks by token matches
        chunk_scores: Dict[str, int] = defaultdict(int)
        
        # Search project chunks
        for token in query_tokens:
            if token in self.keyword_index:
                for chunk_id in self.keyword_index[token]:
                    chunk_scores[chunk_id] += 1
                    
        # Search knowledge chunks
        for token in query_tokens:
            if token in self.knowledge_keyword_index:
                for chunk_id in self.knowledge_keyword_index[token]:
                    chunk_scores[chunk_id] += 2  # Boost knowledge
                    
        return self._rank_and_format_results(chunk_scores, top_k, filters)
        
    def _compressed_search(self, query: str, top_k: int,
                          filters: Optional[Dict]) -> List[Dict]:
        """Token overlap search with Jaccard similarity."""
        query_tokens = set(re.findall(r'[a-zA-Z_][a-zA-Z0-9_]*', query.lower()))
        query_tokens = {t for t in query_tokens if len(t) > 2}
        
        if not query_tokens:
            return []
            
        chunk_scores: Dict[str, float] = {}
        
        # Calculate Jaccard similarity for each chunk
        for chunk_id, chunk in self.chunks.items():
            chunk_tokens = set(chunk.tokens)
            if not chunk_tokens:
                continue
                
            intersection = len(query_tokens & chunk_tokens)
            union = len(query_tokens | chunk_tokens)
            
            if union > 0:
                similarity = intersection / union
                if similarity > 0.1:
                    chunk_scores[chunk_id] = similarity
                    
        # Also check knowledge chunks
        for chunk_id, chunk in self.knowledge_chunks.items():
            chunk_tokens = set(chunk.tokens)
            if not chunk_tokens:
                continue
                
            intersection = len(query_tokens & chunk_tokens)
            union = len(query_tokens | chunk_tokens)
            
            if union > 0:
                similarity = intersection / union
                if similarity > 0.15:  # Higher threshold for knowledge
                    chunk_scores[chunk_id] = similarity + 0.1  # Small boost
                    
        return self._rank_and_format_results(chunk_scores, top_k, filters)
        
    def _structural_search(self, query: str, top_k: int,
                          filters: Optional[Dict]) -> List[Dict]:
        """Godot-aware structural search."""
        # Try to extract class/function names from query
        patterns = [
            r'(?:class|extends)\s+([a-zA-Z_][a-zA-Z0-9_]*)',
            r'func\s+([a-zA-Z_][a-zA-Z0-9_]*)',
            r'([a-zA-Z_][a-zA-Z0-9_]*)\.(?:gd|tscn)'
        ]
        
        targets = []
        for pattern in patterns:
            matches = re.findall(pattern, query, re.IGNORECASE)
            targets.extend(matches)
            
        if not targets:
            # Fallback to keyword search
            return self._keyword_search(query, top_k, filters)
            
        results = []
        for target in targets[:3]:
            # Look for exact structural matches
            for key, chunk in self.structural_index.items():
                if target.lower() in key.lower():
                    results.append({
                        "chunk_id": chunk.chunk_id,
                        "source": chunk.source_path,
                        "type": chunk.source_type,
                        "content": chunk.get_context(),
                        "score": 1.0,
                        "match_type": "structural"
                    })
                    
        return results[:top_k]
        
    def _hybrid_search(self, query: str, top_k: int,
                      filters: Optional[Dict]) -> List[Dict]:
        """Smart combination of all search strategies."""
        # Run all strategies
        keyword_results = self._keyword_search(query, top_k * 2, filters)
        compressed_results = self._compressed_search(query, top_k * 2, filters)
        structural_results = self._structural_search(query, top_k, filters)
        
        # Combine and deduplicate
        combined_scores: Dict[str, float] = defaultdict(float)
        all_results = {}
        
        for result in keyword_results:
            chunk_id = result['chunk_id']
            combined_scores[chunk_id] += result.get('score', 0) * 0.3
            all_results[chunk_id] = result
            
        for result in compressed_results:
            chunk_id = result['chunk_id']
            combined_scores[chunk_id] += result.get('score', 0) * 0.5
            all_results[chunk_id] = result
            
        for result in structural_results:
            chunk_id = result['chunk_id']
            combined_scores[chunk_id] += result.get('score', 0) * 0.8  # High weight
            all_results[chunk_id] = result
            
        # Sort by combined score
        sorted_ids = sorted(combined_scores.keys(), 
                          key=lambda x: combined_scores[x], 
                          reverse=True)
                          
        # Format top results
        results = []
        for chunk_id in sorted_ids[:top_k]:
            result = all_results[chunk_id]
            result['score'] = combined_scores[chunk_id]
            results.append(result)
            
        return results
        
    def _rank_and_format_results(self, scores: Dict[str, float], top_k: int,
                                filters: Optional[Dict]) -> List[Dict]:
        """Rank and format search results."""
        # Apply filters
        filtered_scores = {}
        for chunk_id, score in scores.items():
            chunk = self.chunks.get(chunk_id) or self.knowledge_chunks.get(chunk_id)
            if not chunk:
                continue
                
            # Check filters
            if filters:
                if 'source_type' in filters and chunk.source_type != filters['source_type']:
                    continue
                if 'file' in filters and filters['file'] not in chunk.source_path:
                    continue
                    
            filtered_scores[chunk_id] = score
            
        # Sort and format
        sorted_ids = sorted(filtered_scores.keys(), 
                          key=lambda x: filtered_scores[x], 
                          reverse=True)
                          
        results = []
        for chunk_id in sorted_ids[:top_k]:
            chunk = self.chunks.get(chunk_id) or self.knowledge_chunks.get(chunk_id)
            if chunk:
                results.append({
                    "chunk_id": chunk_id,
                    "source": chunk.source_path,
                    "type": chunk.source_type,
                    "content": chunk.get_context(),
                    "score": filtered_scores[chunk_id],
                    "match_type": "search"
                })
                
        return results
        
    def get_stats(self) -> Dict:
        """Get search engine statistics."""
        return {
            **self.stats,
            "keyword_index_size": len(self.keyword_index),
            "structural_index_size": len(self.structural_index),
            "memory_estimate_kb": (len(self.chunks) + len(self.knowledge_chunks)) * 2
        }


# Singleton instance
_search_engine_instance: Optional[UnifiedSearchEngine] = None

def get_unified_search(project_root: Optional[str] = None, 
                      knowledge_base_path: str = "knowledge_base") -> UnifiedSearchEngine:
    """Get or create unified search engine instance."""
    global _search_engine_instance
    
    if _search_engine_instance is None:
        _search_engine_instance = UnifiedSearchEngine(project_root, knowledge_base_path)
    elif project_root and project_root != str(_search_engine_instance.project_root):
        # Rebuild for new project
        _search_engine_instance = UnifiedSearchEngine(project_root, knowledge_base_path)
        
    return _search_engine_instance
