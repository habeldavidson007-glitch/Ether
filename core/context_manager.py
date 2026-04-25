"""
Ether Context Manager - Smart Context Chunking System
=====================================================
Handles large files intelligently by chunking based on:
- Function/class boundaries
- Logical code sections
- User query relevance
- Memory constraints (2GB safe)

Features:
- Semantic chunking (not arbitrary character limits)
- Relevance scoring for query-focused context
- Sliding window for large refactoring tasks
- Backup original before modifications
"""

import re
from pathlib import Path
from typing import List, Dict, Tuple, Optional


class ContextChunker:
    """Smart context chunking for GDScript files."""
    
    # GDScript-specific patterns for intelligent chunking
    FUNCTION_PATTERN = r'^\s*(func|static func)\s+\w+'
    CLASS_PATTERN = r'^\s*(class|extends)\s+'
    SIGNAL_PATTERN = r'^\s*signal\s+'
    VARIABLE_PATTERN = r'^\s*(var|const|enum)\s+'
    REGION_PATTERN = r'^\s*#\s*─+|#\s*=+'  # Visual region markers
    
    def __init__(self, max_chunk_size: int = 600, overlap: int = 50):
        """
        Initialize chunker.
        
        Args:
            max_chunk_size: Maximum characters per chunk (default 600 for small models)
            overlap: Characters to overlap between chunks for context continuity
        """
        self.max_chunk_size = max_chunk_size
        self.overlap = overlap
        self.chunks = []
        self.metadata = []
    
    def chunk_file(self, file_path: str, user_query: str = "") -> List[Dict]:
        """
        Chunk a GDScript file intelligently.
        
        Args:
            file_path: Path to .gd file
            user_query: User's query for relevance scoring
            
        Returns:
            List of chunk dicts with {code, start_line, end_line, relevance, type}
        """
        if not Path(file_path).exists():
            return []
        
        with open(file_path, 'r', encoding='utf-8') as f:
            lines = f.readlines()
        
        return self.chunk_lines(lines, user_query)
    
    def chunk_lines(self, lines: List[str], user_query: str = "") -> List[Dict]:
        """
        Chunk lines intelligently based on GDScript structure.
        
        Strategy:
        1. Identify logical blocks (functions, classes, regions)
        2. Group related blocks
        3. Score relevance to user query
        4. Return prioritized chunks
        """
        self.chunks = []
        self.metadata = []
        
        # Step 1: Identify block boundaries
        blocks = self._identify_blocks(lines)
        
        # Step 2: Group blocks into chunks within size limit
        chunks = self._group_blocks(blocks)
        
        # Step 3: Score relevance if query provided
        if user_query:
            chunks = self._score_relevance(chunks, user_query)
            # Sort by relevance (most relevant first)
            chunks.sort(key=lambda c: c.get('relevance', 0), reverse=True)
        
        return chunks
    
    def _identify_blocks(self, lines: List[str]) -> List[Dict]:
        """Identify logical code blocks based on GDScript structure."""
        blocks = []
        current_block = {
            'lines': [],
            'type': 'unknown',
            'start_line': 0,
            'name': ''
        }
        
        indent_stack = []  # Track indentation levels
        
        for i, line in enumerate(lines):
            stripped = line.strip()
            
            # Skip empty lines and comments for block detection
            if not stripped or stripped.startswith('#'):
                current_block['lines'].append(line)
                continue
            
            # Detect block type
            block_type = self._detect_block_type(stripped)
            
            # New block detected
            if block_type and block_type != current_block['type']:
                # Save previous block if it has content
                if current_block['lines']:
                    current_block['end_line'] = i
                    blocks.append(current_block.copy())
                
                # Start new block
                current_block = {
                    'lines': [line],
                    'type': block_type,
                    'start_line': i,
                    'end_line': i,
                    'name': self._extract_name(stripped, block_type)
                }
            else:
                current_block['lines'].append(line)
                current_block['end_line'] = i
        
        # Add final block
        if current_block['lines']:
            current_block['end_line'] = len(lines)
            blocks.append(current_block)
        
        return blocks
    
    def _detect_block_type(self, line: str) -> Optional[str]:
        """Detect the type of code block from a line."""
        if re.match(self.FUNCTION_PATTERN, line):
            return 'function'
        elif re.match(self.CLASS_PATTERN, line):
            return 'class'
        elif re.match(self.SIGNAL_PATTERN, line):
            return 'signal'
        elif re.match(self.VARIABLE_PATTERN, line):
            return 'variable'
        elif re.match(self.REGION_PATTERN, line):
            return 'region'
        return None
    
    def _extract_name(self, line: str, block_type: str) -> str:
        """Extract function/variable name from line."""
        if block_type == 'function':
            match = re.search(r'func\s+(\w+)', line)
            return match.group(1) if match else ''
        elif block_type == 'variable':
            match = re.search(r'var\s+(\w+)', line)
            return match.group(1) if match else ''
        return ''
    
    def _group_blocks(self, blocks: List[Dict]) -> List[Dict]:
        """Group blocks into chunks within size limits."""
        chunks = []
        current_chunk = {
            'code': '',
            'start_line': 0,
            'end_line': 0,
            'blocks': [],
            'type': 'mixed',
            'relevance': 0.5  # Default relevance
        }
        
        current_size = 0
        
        for block in blocks:
            block_code = ''.join(block['lines'])
            block_size = len(block_code)
            
            # If single block exceeds max size, split it
            if block_size > self.max_chunk_size:
                # Split large block into sub-chunks
                sub_chunks = self._split_large_block(block, self.max_chunk_size)
                chunks.extend(sub_chunks)
                continue
            
            # Check if adding this block exceeds limit
            if current_size + block_size > self.max_chunk_size and current_chunk['blocks']:
                # Finalize current chunk
                current_chunk['end_line'] = current_chunk['blocks'][-1]['end_line']
                chunks.append(current_chunk.copy())
                
                # Start new chunk with overlap
                overlap_lines = self._get_overlap_lines(current_chunk, self.overlap)
                current_chunk = {
                    'code': overlap_lines,
                    'start_line': block['start_line'],
                    'end_line': block['end_line'],
                    'blocks': [block],
                    'type': block['type'],
                    'relevance': 0.5
                }
                current_size = len(overlap_lines) + block_size
            else:
                # Add to current chunk
                if not current_chunk['blocks']:
                    current_chunk['start_line'] = block['start_line']
                
                current_chunk['code'] += block_code
                current_chunk['blocks'].append(block)
                current_chunk['end_line'] = block['end_line']
                current_chunk['type'] = block['type'] if len(current_chunk['blocks']) == 1 else 'mixed'
                current_size += block_size
        
        # Add final chunk
        if current_chunk['blocks']:
            chunks.append(current_chunk)
        
        return chunks
    
    def _split_large_block(self, block: Dict, max_size: int) -> List[Dict]:
        """Split a large block into smaller sub-chunks."""
        sub_chunks = []
        block_code = ''.join(block['lines'])
        
        # Split by lines
        lines = block['lines']
        chunk_lines = []
        current_size = 0
        
        for line in lines:
            line_size = len(line)
            
            if current_size + line_size > max_size and chunk_lines:
                # Create sub-chunk
                sub_chunks.append({
                    'code': ''.join(chunk_lines),
                    'start_line': block['start_line'],
                    'end_line': block['start_line'] + len(chunk_lines),
                    'blocks': [block],  # Reference parent block
                    'type': f"{block['type']}_part",
                    'relevance': 0.5
                })
                
                # Start new sub-chunk with overlap
                overlap = chunk_lines[-max(1, self.overlap // 20):]  # Approximate line count
                chunk_lines = overlap
                current_size = sum(len(l) for l in overlap)
            
            chunk_lines.append(line)
            current_size += line_size
        
        # Add final sub-chunk
        if chunk_lines:
            sub_chunks.append({
                'code': ''.join(chunk_lines),
                'start_line': block['start_line'],
                'end_line': block['start_line'] + len(chunk_lines),
                'blocks': [block],
                'type': f"{block['type']}_part",
                'relevance': 0.5
            })
        
        return sub_chunks
    
    def _get_overlap_lines(self, chunk: Dict, overlap_chars: int) -> str:
        """Get last N characters from previous chunk for overlap."""
        code = chunk['code']
        if len(code) <= overlap_chars:
            return code
        return code[-overlap_chars:]
    
    def _score_relevance(self, chunks: List[Dict], query: str) -> List[Dict]:
        """Score chunk relevance based on user query keywords."""
        query_lower = query.lower()
        query_keywords = set(query_lower.split())
        
        # Add common GDScript terms
        gdscript_terms = {'func', 'var', 'signal', 'class', 'extends', 'if', 'for', 'while'}
        query_keywords.update(gdscript_terms)
        
        for chunk in chunks:
            code_lower = chunk['code'].lower()
            
            # Keyword matching score
            matches = sum(1 for keyword in query_keywords if keyword in code_lower)
            score = min(1.0, matches / max(1, len(query_keywords)))
            
            # Boost score if chunk type matches query intent
            if 'optimize' in query_lower and chunk['type'] == 'function':
                score = min(1.0, score + 0.2)
            elif 'fix' in query_lower and 'error' in code_lower:
                score = min(1.0, score + 0.3)
            
            chunk['relevance'] = score
        
        return chunks
    
    def get_context_for_query(self, file_path: str, query: str, max_context_chars: int = 600) -> str:
        """
        Get most relevant context for a query.
        
        Args:
            file_path: Path to GDScript file
            query: User's query
            max_context_chars: Maximum characters to return
            
        Returns:
            Most relevant code context as string
        """
        chunks = self.chunk_file(file_path, query)
        
        if not chunks:
            return ""
        
        # Accumulate chunks until we hit the limit
        result = []
        current_size = 0
        
        for chunk in chunks:
            chunk_code = chunk['code']
            if current_size + len(chunk_code) > max_context_chars:
                break
            
            result.append(chunk_code)
            current_size += len(chunk_code)
        
        return '\n'.join(result)


class FileBackupManager:
    """Safe file backup and rollback system."""
    
    def __init__(self, backup_dir: str = ".ether_backups"):
        self.backup_dir = Path(backup_dir)
        self.backup_dir.mkdir(parents=True, exist_ok=True)
    
    def create_backup(self, file_path: str) -> Optional[str]:
        """
        Create backup of file before modification.
        
        Returns:
            Backup file path or None if failed
        """
        source = Path(file_path)
        if not source.exists():
            return None
        
        # Create backup with timestamp
        timestamp = int(time.time())
        backup_name = f"{source.stem}_{timestamp}{source.suffix}"
        backup_path = self.backup_dir / backup_name
        
        try:
            import shutil
            shutil.copy2(source, backup_path)
            return str(backup_path)
        except Exception as e:
            print(f"[BACKUP] Failed to create backup: {e}")
            return None
    
    def rollback(self, backup_path: str, target_path: str) -> bool:
        """
        Restore file from backup.
        
        Returns:
            True if successful, False otherwise
        """
        backup = Path(backup_path)
        target = Path(target_path)
        
        if not backup.exists():
            return False
        
        try:
            import shutil
            shutil.copy2(backup, target)
            return True
        except Exception as e:
            print(f"[ROLLBACK] Failed: {e}")
            return False
    
    def cleanup_old_backups(self, max_age_hours: int = 24):
        """Remove backups older than specified hours."""
        import time
        cutoff = time.time() - (max_age_hours * 3600)
        
        for backup_file in self.backup_dir.glob("*.gd"):
            if backup_file.stat().st_mtime < cutoff:
                try:
                    backup_file.unlink()
                except Exception as e:
                    print(f"[CLEANUP] Failed to remove {backup_file}: {e}")


# Time import for backup manager
import time


def smart_load_context(file_path: str, query: str, max_chars: int = 600) -> str:
    """
    Convenience function to load smart context.
    
    Args:
        file_path: Path to GDScript file
        query: User's query
        max_chars: Maximum context characters
        
    Returns:
        Relevant code context
    """
    chunker = ContextChunker(max_chunk_size=max_chars)
    return chunker.get_context_for_query(file_path, query, max_chars)


# ── Session State & Memory (Merged from state.py) ─────────────────────────────

import json
import math
import re
import time
from collections import Counter
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

MEMORY_CAP = 150
MEMORY_TOP_K = 3
SIM_THRESHOLD = 0.15

WORKSPACE = Path("workspace")
MEMORY_FILE = WORKSPACE / "memory.json"


# ── Intent Classification ─────────────────────────────────────────────────────

_CASUAL = {"hi", "hey", "hello", "thanks", "ok", "okay", "cool", "great", "lol", "nice"}
_DEBUG  = {"error", "crash", "fix", "bug", "broken", "fail", "exception", "traceback"}
_BUILD  = {"create", "generate", "build", "make", "add", "write", "implement", "new"}
_ANALYZE= {"analyze", "explain", "what", "how", "why", "understand", "review", "check",
           "list", "find", "show", "tell", "describe", "issues", "problems", "look"}


def is_casual(text: str) -> bool:
    text = text.lower().strip()

    if len(text) < 6:
        if any(k in text for k in ["fix", "bug", "error"]):
            return False
        if any(k in text for k in ["explain", "what", "how"]):
            return False
        return True

    casual_patterns = [
        "hi", "hello", "hey", "yo",
        "thanks", "thank you",
        "congrats", "congratulations",
        "lol", "lmao", "haha",
        "how are you",
        "good morning", "good night",
        "nice", "cool"
    ]

    if any(k in text for k in ["fix", "bug", "error", "debug"]):
        return False
    if any(k in text for k in ["explain", "what", "how", "analyze", "why", "list", "find", "issues"]):
        return False

    return any(p in text for p in casual_patterns)


def classify(text: str) -> str:
    """Classify user intent. Returns: casual, debug, build, analyze, or task."""
    text_lower = text.lower()

    if any(k in text_lower for k in ["fix", "bug", "error", "debug", "crash", "broken", "fail"]):
        return "debug"

    if any(k in text_lower for k in ["build", "create", "make", "implement", "generate", "write", "add"]):
        return "build"

    # Catch analysis/review queries — these need real file context
    if any(k in text_lower for k in ["analyze", "explain", "list", "find", "show", "what",
                                      "how", "why", "review", "check", "issues", "problems",
                                      "tell me", "describe", "look at", "read"]):
        return "analyze"

    return "casual"


# ── Memory Functions ───────────────────────────────────────────────────────────

def _tokenize(text: str) -> List[str]:
    return [w for w in re.findall(r"[a-zA-Z_]\w*", text.lower()) if len(w) >= 3]


def _tfidf(tokens: List[str], idf: Dict[str, float]) -> Dict[str, float]:
    tf = Counter(tokens)
    total = max(len(tokens), 1)
    return {t: (c / total) * idf.get(t, 1.0) for t, c in tf.items()}


def _cosine(a: Dict[str, float], b: Dict[str, float]) -> float:
    common = set(a) & set(b)
    if not common:
        return 0.0
    dot = sum(a[k] * b[k] for k in common)
    mag_a = math.sqrt(sum(v * v for v in a.values()))
    mag_b = math.sqrt(sum(v * v for v in b.values()))
    return dot / (mag_a * mag_b) if mag_a and mag_b else 0.0


def _build_idf(entries: List[Dict]) -> Dict[str, float]:
    N = max(len(entries), 1)
    df: Counter = Counter()
    for e in entries:
        tokens = set(_tokenize(e.get("task", "") + " " + " ".join(e.get("tags", []))))
        df.update(tokens)
    return {t: math.log(N / (c + 1)) + 1.0 for t, c in df.items()}


def load_memory() -> List[Dict]:
    try:
        if MEMORY_FILE.exists():
            return json.loads(MEMORY_FILE.read_text(encoding="utf-8"))
    except Exception:
        pass
    return []


def save_memory(entries: List[Dict]) -> None:
    try:
        MEMORY_FILE.parent.mkdir(parents=True, exist_ok=True)
        MEMORY_FILE.write_text(
            json.dumps(entries[-MEMORY_CAP:], indent=2, ensure_ascii=False),
            encoding="utf-8",
        )
    except Exception:
        pass


def recall(query: str, top_k: int = MEMORY_TOP_K) -> List[Dict]:
    entries = load_memory()
    if not entries:
        return []
    idf = _build_idf(entries)
    qv = _tfidf(_tokenize(query), idf)
    scored = []
    for e in entries:
        ev = _tfidf(_tokenize(e.get("task", "") + " " + " ".join(e.get("tags", []))), idf)
        score = _cosine(qv, ev)
        if score >= SIM_THRESHOLD:
            scored.append((score, e))
    scored.sort(key=lambda x: x[0], reverse=True)
    return [e for _, e in scored[:top_k]]


def remember(task: str, intent: str, success: bool, tags: List[str] = None) -> None:
    entries = load_memory()
    entries.append({
        "task": task[:200],
        "intent": intent,
        "success": success,
        "tags": tags or [],
        "ts": time.strftime("%Y-%m-%d %H:%M"),
    })
    save_memory(entries)


# ── Session State ──────────────────────────────────────────────────────────────

@dataclass
class EtherSession:
    mode: str = "task"
    history: List[Dict[str, str]] = field(default_factory=list)
    project_loaded: bool = False
    project_files: List[str] = field(default_factory=list)
    file_contents: Dict[str, str] = field(default_factory=dict)
    project_map: Dict[str, Any] = field(default_factory=dict)
    active_file: Optional[str] = None
    chat_mode: str = "mixed"  # coding | general | mixed
    constraints: Dict[str, Any] = field(default_factory=lambda: {
        "max_history_turns": 20,
        "max_file_chars": 8000,
        "allow_memory": True,
    })

    def update_mode(self, intent: str) -> None:
        if intent == "casual":
            self.mode = "casual"
        else:
            self.mode = "task"

    def add_turn(self, role: str, content: str) -> None:
        self.history.append({"role": role, "content": content})
        cap = self.constraints["max_history_turns"] * 2
        if len(self.history) > cap:
            self.history = self.history[-cap:]

    def get_history(self) -> List[Dict[str, str]]:
        return self.history

    def get_memory_context(self, query: str) -> str:
        hits = recall(query)
        if not hits:
            return ""
        lines = ["Relevant past work:"]
        for h in hits:
            status = "✓" if h.get("success") else "✗"
            lines.append(f"  {status} {h['task'][:100]} [{h.get('intent', '')}]")
        return "\n".join(lines)

    def get_file_context(self, max_chars: int = None) -> str:
        cap = max_chars or self.constraints["max_file_chars"]
        if not self.file_contents:
            return ""
        parts = []
        used = 0
        priority = []
        if self.active_file and self.active_file in self.file_contents:
            priority.append(self.active_file)
        for f in self.project_files:
            if f not in priority:
                priority.append(f)
        for f in priority:
            content = self.file_contents.get(f, "")
            if used + len(content) > cap:
                break
            parts.append(f"# {f}\n{content}")
            used += len(content)
        return "\n\n".join(parts)
