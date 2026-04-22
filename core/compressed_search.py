"""
Local LEANN Adapter - Compressed Search
--------------------------------------------
Prototype for GPU-free, privacy-first local search using compression techniques.
Inspired by LEANN: Compresses text chunks for massive AI searches on standard laptops.

Key Features:
- Zero Cloud: All processing happens locally.
- Zero GPU: Runs on CPU with optimized data structures.
- Privacy First: No data leaves the machine.
- Compression: Uses efficient indexing to fit large codebases in RAM.

Note: This is a lightweight prototype implementing core LEANN concepts 
using Python built-ins and efficient data structures.
"""

import os
import json
import hashlib
import pickle
from typing import Dict, List, Tuple, Optional, Set
from pathlib import Path
from collections import defaultdict
import re


class CompressedChunk:
    """
    Represents a compressed text chunk with metadata.
    Uses simple tokenization and frequency-based compression hints.
    """
    
    def __init__(self, chunk_id: str, content: str, file_path: str, 
                 start_line: int, end_line: int):
        self.chunk_id = chunk_id
        self.content = content
        self.file_path = file_path
        self.start_line = start_line
        self.end_line = end_line
        
        # Compression metadata
        self.tokens = self._tokenize(content)
        self.token_freq = self._compute_frequency()
        self.signature = self._generate_signature()
        
    def _tokenize(self, text: str) -> List[str]:
        """Simple tokenizer for code (splits on whitespace and symbols)."""
        # Keep identifiers intact, split on operators/whitespace
        tokens = re.findall(r'[a-zA-Z_][a-zA-Z0-9_]*|[0-9]+|[^\s\w]', text)
        return [t.lower() for t in tokens if len(t) > 1]
    
    def _compute_frequency(self) -> Dict[str, int]:
        """Compute token frequency for this chunk."""
        freq = defaultdict(int)
        for token in self.tokens:
            freq[token] += 1
        return dict(freq)
    
    def _generate_signature(self) -> str:
        """Generate a compact signature for quick comparison."""
        # Use top 10 most frequent tokens as signature
        sorted_tokens = sorted(self.token_freq.items(), key=lambda x: x[1], reverse=True)
        sig_tokens = [t[0] for t in sorted_tokens[:10]]
        return ":".join(sig_tokens)
    
    def get_size_estimate(self) -> int:
        """Estimate compressed size (bytes)."""
        # Rough estimate: store only unique tokens + frequencies
        return len(self.token_freq) * 20  # ~20 bytes per token entry
    
    def to_dict(self) -> Dict:
        return {
            "id": self.chunk_id,
            "file": self.file_path,
            "lines": f"{self.start_line}-{self.end_line}",
            "token_count": len(self.tokens),
            "unique_tokens": len(self.token_freq),
            "signature": self.signature[:50]  # Truncate for display
        }


class CompressedSearch:
    """
    Main LEANN-style index for local, compressed search.
    
    Instead of vector embeddings, uses:
    1. Inverted Index: Token -> Chunk IDs
    2. Signature Matching: Quick filtering via token signatures
    3. Overlap Detection: Finds related chunks via token overlap
    """
    
    def __init__(self, project_root: str, chunk_size: int = 200):
        self.project_root = Path(project_root)
        self.chunk_size = chunk_size  # Lines per chunk
        self.chunks: Dict[str, CompressedChunk] = {}
        
        # Inverted index: token -> set of chunk_ids
        self.inverted_index: Dict[str, Set[str]] = defaultdict(set)
        
        # File index: file_path -> list of chunk_ids
        self.file_index: Dict[str, List[str]] = defaultdict(list)
        
        # Statistics
        self.total_tokens = 0
        self.vocabulary_size = 0
        
    def build_index(self):
        """Build the compressed index from project files."""
        print(f"[CompressedSearch] Building compressed index for {self.project_root}...")
        self.chunks.clear()
        self.inverted_index.clear()
        self.file_index.clear()
        
        all_tokens = set()
        
        # Scan all relevant files
        extensions = ['*.gd', '*.tscn', '*.cs', '*.py', '*.json', '*.md']
        files_processed = 0
        
        for ext in extensions:
            for file_path in self.project_root.rglob(ext):
                self._index_file(file_path, all_tokens)
                files_processed += 1
                
        self.vocabulary_size = len(all_tokens)
        self.total_tokens = sum(len(c.tokens) for c in self.chunks.values())
        
        print(f"[CompressedSearch] Indexed {files_processed} files, {len(self.chunks)} chunks")
        print(f"[CompressedSearch] Vocabulary: {self.vocabulary_size} unique tokens")
        print(f"[CompressedSearch] Total tokens: {self.total_tokens}")
        
    def _index_file(self, file_path: Path, all_tokens: Set[str]):
        """Index a single file by splitting into chunks."""
        try:
            content = file_path.read_text(encoding='utf-8', errors='ignore')
        except Exception as e:
            print(f"[CompressedSearch] Skip {file_path}: {e}")
            return
            
        lines = content.split('\n')
        relative_path = str(file_path.relative_to(self.project_root))
        
        # Split into overlapping chunks
        chunk_start = 0
        while chunk_start < len(lines):
            chunk_end = min(chunk_start + self.chunk_size, len(lines))
            chunk_lines = lines[chunk_start:chunk_end]
            
            # Skip empty chunks
            if not any(line.strip() for line in chunk_lines):
                chunk_start = chunk_end
                continue
                
            chunk_content = '\n'.join(chunk_lines)
            chunk_id = hashlib.md5(f"{relative_path}:{chunk_start}".encode()).hexdigest()[:12]
            
            chunk = CompressedChunk(
                chunk_id=chunk_id,
                content=chunk_content,
                file_path=relative_path,
                start_line=chunk_start + 1,
                end_line=chunk_end
            )
            
            self.chunks[chunk_id] = chunk
            self.file_index[relative_path].append(chunk_id)
            
            # Update inverted index
            for token in chunk.tokens:
                self.inverted_index[token].add(chunk_id)
                all_tokens.add(token)
                
            chunk_start += self.chunk_size // 2  # 50% overlap
            
    def search(self, query: str, top_k: int = 10) -> List[Dict]:
        """
        Search for query terms using token matching (no embeddings).
        
        Args:
            query: Search query string
            top_k: Number of results to return
            
        Returns:
            List of matching chunks with relevance scores
        """
        # Tokenize query
        query_tokens = re.findall(r'[a-zA-Z_][a-zA-Z0-9_]*|[0-9]+', query.lower())
        query_tokens = [t for t in query_tokens if len(t) > 1]
        
        if not query_tokens:
            return []
            
        # Score chunks by token overlap
        chunk_scores: Dict[str, int] = defaultdict(int)
        
        for token in query_tokens:
            if token in self.inverted_index:
                for chunk_id in self.inverted_index[token]:
                    # Weight by exact match bonus
                    chunk_scores[chunk_id] += 1
                    if token == query.lower():
                        chunk_scores[chunk_id] += 2  # Exact match bonus
                        
        # Sort by score
        sorted_chunks = sorted(chunk_scores.items(), key=lambda x: x[1], reverse=True)
        
        # Build results
        results = []
        for chunk_id, score in sorted_chunks[:top_k]:
            chunk = self.chunks[chunk_id]
            results.append({
                "chunk_id": chunk_id,
                "file": chunk.file_path,
                "lines": f"{chunk.start_line}-{chunk.end_line}",
                "score": score,
                "content": chunk.content[:500] + "..." if len(chunk.content) > 500 else chunk.content,
                "matched_tokens": [t for t in query_tokens if t in chunk.token_freq]
            })
            
        return results
        
    def find_related(self, chunk_id: str, top_k: int = 5) -> List[Dict]:
        """Find chunks related to a given chunk via token overlap."""
        if chunk_id not in self.chunks:
            return []
            
        source_chunk = self.chunks[chunk_id]
        chunk_scores: Dict[str, float] = {}
        
        # Calculate Jaccard similarity with other chunks
        source_tokens = set(source_chunk.tokens)
        
        for other_id, other_chunk in self.chunks.items():
            if other_id == chunk_id:
                continue
                
            other_tokens = set(other_chunk.tokens)
            
            if not source_tokens or not other_tokens:
                continue
                
            intersection = len(source_tokens & other_tokens)
            union = len(source_tokens | other_tokens)
            
            if union > 0:
                similarity = intersection / union
                if similarity > 0.1:  # Threshold
                    chunk_scores[other_id] = similarity
                    
        # Sort by similarity
        sorted_chunks = sorted(chunk_scores.items(), key=lambda x: x[1], reverse=True)
        
        results = []
        for other_id, sim in sorted_chunks[:top_k]:
            chunk = self.chunks[other_id]
            results.append({
                "chunk_id": other_id,
                "file": chunk.file_path,
                "similarity": round(sim, 3),
                "lines": f"{chunk.start_line}-{chunk.end_line}"
            })
            
        return results
        
    def get_stats(self) -> Dict:
        """Get index statistics."""
        total_size_estimate = sum(c.get_size_estimate() for c in self.chunks.values())
        return {
            "chunks": len(self.chunks),
            "files": len(self.file_index),
            "vocabulary": self.vocabulary_size,
            "total_tokens": self.total_tokens,
            "estimated_memory_kb": total_size_estimate // 1024,
            "inverted_index_entries": len(self.inverted_index)
        }
        
    def save_index(self, path: str):
        """Save index to disk for persistence."""
        data = {
            "chunks": {k: vars(v) for k, v in self.chunks.items()},
            "inverted_index": {k: list(v) for k, v in self.inverted_index.items()},
            "file_index": dict(self.file_index),
            "stats": self.get_stats()
        }
        with open(path, 'wb') as f:
            pickle.dump(data, f)
        print(f"[CompressedSearch] Index saved to {path}")
        
    def load_index(self, path: str) -> bool:
        """Load index from disk."""
        if not os.path.exists(path):
            return False
            
        with open(path, 'rb') as f:
            data = pickle.load(f)
            
        # Reconstruct chunks
        self.chunks = {}
        for chunk_id, chunk_data in data["chunks"].items():
            chunk = CompressedChunk(
                chunk_id=chunk_data["chunk_id"],
                content=chunk_data["content"],
                file_path=chunk_data["file_path"],
                start_line=chunk_data["start_line"],
                end_line=chunk_data["end_line"]
            )
            # Restore computed fields
            chunk.tokens = chunk_data.get("tokens", [])
            chunk.token_freq = chunk_data.get("token_freq", {})
            chunk.signature = chunk_data.get("signature", "")
            self.chunks[chunk_id] = chunk
            
        # Restore inverted index
        self.inverted_index = defaultdict(set)
        for token, chunk_ids in data["inverted_index"].items():
            self.inverted_index[token] = set(chunk_ids)
            
        # Restore file index
        self.file_index = defaultdict(list)
        for file_path, chunk_ids in data["file_index"].items():
            self.file_index[file_path] = chunk_ids
            
        print(f"[CompressedSearch] Index loaded from {path}")
        return True


# Singleton instance
_instance: Optional[CompressedSearch] = None

def get_compressed_search(project_root: str, chunk_size: int = 200) -> CompressedSearch:
    """Get or create the singleton CompressedSearch instance."""
    global _instance
    if _instance is None or str(_instance.project_root) != project_root:
        _instance = CompressedSearch(project_root, chunk_size)
    return _instance


if __name__ == "__main__":
    # Test the CompressedSearch
    print("=== Testing CompressedSearch ===\n")
    
    # Create a test directory with sample files
    import tempfile
    import shutil
    
    test_dir = Path(tempfile.mkdtemp())
    try:
        # Create test GDScript file
        test_file = test_dir / "player.gd"
        test_file.write_text("""extends Node2D

var health: int = 100
var speed: float = 200.0

func _ready():
    print("Player ready")
    
func _process(delta):
    move_player(delta)
    
func move_player(delta):
    var direction = Input.get_action_direction("ui_right")
    position.x += direction * speed * delta
    
func take_damage(amount):
    health -= amount
    if health <= 0:
        die()
        
func die():
    queue_free()
""")
        
        # Create another test file
        test_file2 = test_dir / "enemy.gd"
        test_file2.write_text("""extends Node2D

var health: int = 50
var damage: int = 10

func _ready():
    print("Enemy ready")
    
func attack(player):
    if player:
        player.take_damage(damage)
        
func take_damage(amount):
    health -= amount
    if health <= 0:
        die()
        
func die():
    queue_free()
""")
        
        # Build index
        search = get_compressed_search(str(test_dir))
        search.build_index()
        
        # Test search
        print("\n=== Search for 'take_damage' ===")
        results = search.search("take_damage function", top_k=3)
        for i, result in enumerate(results, 1):
            print(f"\n{i}. {result['file']}:{result['lines']} (score: {result['score']})")
            print(f"   Matched: {result['matched_tokens']}")
            print(f"   Preview: {result['content'][:100]}...")
        
        # Test related chunks
        if results:
            print("\n=== Find Related Chunks ===")
            related = search.find_related(results[0]['chunk_id'], top_k=2)
            for i, rel in enumerate(related, 1):
                print(f"\n{i}. {rel['file']} (similarity: {rel['similarity']})")
        
        # Get stats
        print("\n=== Statistics ===")
        stats = search.get_stats()
        for key, value in stats.items():
            print(f"{key}: {value}")
        
        # Test save/load
        index_path = test_dir / "search_index.pkl"
        search.save_index(str(index_path))
        
        # Load into new instance
        search2 = CompressedSearch(str(test_dir))
        search2.load_index(str(index_path))
        print(f"\n✅ Loaded index with {len(search2.chunks)} chunks")
        
        print("\n✅ CompressedSearch test complete!")
        
    finally:
        # Cleanup
        shutil.rmtree(test_dir)
