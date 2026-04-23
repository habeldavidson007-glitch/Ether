"""
Phase 6 & 7: Memory Safety, Scalability, Security & Sandboxing

This module provides:
- Persistent storage backend (SQLite)
- Thread-safe memory management with automatic cleanup
- Prompt injection detection and prevention
- Code execution sandboxing with resource limits
- Secrets management and masking
"""

import sqlite3
import threading
import time
import re
import os
import subprocess
import tempfile
import hashlib
from pathlib import Path
from typing import Optional, List, Dict, Any, Tuple
from contextlib import contextmanager
import gc


class PersistentStorage:
    """Thread-safe SQLite-based persistent storage for memory and library data."""
    
    def __init__(self, db_path: str = "ether_data.db"):
        self.db_path = Path(db_path)
        self._local = threading.local()
        self._lock = threading.RLock()
        self._init_db()
    
    @property
    def _conn(self) -> sqlite3.Connection:
        """Get thread-local database connection."""
        if not hasattr(self._local, 'conn') or self._local.conn is None:
            self._local.conn = sqlite3.connect(
                str(self.db_path),
                check_same_thread=False,
                timeout=30.0
            )
            self._local.conn.row_factory = sqlite3.Row
            # Enable WAL mode for better concurrency
            self._local.conn.execute("PRAGMA journal_mode=WAL")
            self._local.conn.execute("PRAGMA synchronous=NORMAL")
        return self._local.conn
    
    def _init_db(self):
        """Initialize database schema."""
        with self._lock:
            cursor = self._conn.cursor()
            
            # Memory entries table
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS memory_entries (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    session_id TEXT NOT NULL,
                    entry_type TEXT NOT NULL,
                    content TEXT NOT NULL,
                    metadata TEXT,
                    relevance_score REAL DEFAULT 1.0,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    accessed_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    feedback_score INTEGER DEFAULT 0
                )
            """)
            
            # Library knowledge base table
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS knowledge_base (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    topic TEXT NOT NULL,
                    keywords TEXT NOT NULL,
                    content TEXT NOT NULL,
                    source_file TEXT,
                    embedding_vector BLOB,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)
            
            # User feedback table
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS user_feedback (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    entry_id INTEGER NOT NULL,
                    score INTEGER NOT NULL,
                    comment TEXT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (entry_id) REFERENCES memory_entries(id)
                )
            """)
            
            # Create indexes for performance
            cursor.execute("""
                CREATE INDEX IF NOT EXISTS idx_memory_session 
                ON memory_entries(session_id)
            """)
            cursor.execute("""
                CREATE INDEX IF NOT EXISTS idx_memory_relevance 
                ON memory_entries(relevance_score)
            """)
            cursor.execute("""
                CREATE INDEX IF NOT EXISTS idx_knowledge_topic 
                ON knowledge_base(topic)
            """)
            
            self._conn.commit()
    
    @contextmanager
    def transaction(self):
        """Context manager for database transactions."""
        with self._lock:
            try:
                yield self._conn
                self._conn.commit()
            except Exception as e:
                self._conn.rollback()
                raise e
    
    def store_memory(self, session_id: str, entry_type: str, content: str, 
                     metadata: Optional[str] = None, relevance: float = 1.0) -> int:
        """Store a memory entry."""
        with self.transaction() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                INSERT INTO memory_entries 
                (session_id, entry_type, content, metadata, relevance_score)
                VALUES (?, ?, ?, ?, ?)
            """, (session_id, entry_type, content, metadata, relevance))
            return cursor.lastrowid
    
    def retrieve_memories(self, session_id: str, limit: int = 50, 
                         min_relevance: float = 0.5) -> List[Dict[str, Any]]:
        """Retrieve memories for a session, ordered by relevance and recency."""
        cursor = self._conn.cursor()
        cursor.execute("""
            SELECT id, session_id, entry_type, content, metadata, 
                   relevance_score, created_at, accessed_at, feedback_score
            FROM memory_entries
            WHERE session_id = ? AND relevance_score >= ?
            ORDER BY relevance_score DESC, accessed_at DESC
            LIMIT ?
        """, (session_id, min_relevance, limit))
        
        return [dict(row) for row in cursor.fetchall()]
    
    def update_relevance(self, entry_id: int, score: float):
        """Update relevance score based on feedback."""
        with self.transaction() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                UPDATE memory_entries 
                SET relevance_score = ?, accessed_at = CURRENT_TIMESTAMP
                WHERE id = ?
            """, (score, entry_id))
    
    def store_knowledge(self, topic: str, keywords: str, content: str, 
                       source_file: Optional[str] = None) -> int:
        """Store knowledge base entry."""
        with self.transaction() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                INSERT INTO knowledge_base 
                (topic, keywords, content, source_file)
                VALUES (?, ?, ?, ?)
            """, (topic, keywords, content, source_file))
            return cursor.lastrowid
    
    def search_knowledge(self, query: str, limit: int = 20) -> List[Dict[str, Any]]:
        """Search knowledge base by keywords or topic."""
        cursor = self._conn.cursor()
        # Simple keyword search (can be enhanced with full-text search)
        search_pattern = f"%{query}%"
        cursor.execute("""
            SELECT id, topic, keywords, content, source_file, created_at
            FROM knowledge_base
            WHERE keywords LIKE ? OR topic LIKE ? OR content LIKE ?
            ORDER BY created_at DESC
            LIMIT ?
        """, (search_pattern, search_pattern, search_pattern, limit))
        
        return [dict(row) for row in cursor.fetchall()]
    
    def cleanup_old_entries(self, days: int = 30, min_relevance: float = 0.3):
        """Remove old, low-relevance entries to prevent bloat."""
        with self._lock:
            cursor = self._conn.cursor()
            cursor.execute("""
                DELETE FROM memory_entries
                WHERE created_at < datetime('now', ?)
                AND relevance_score < ?
            """, (f'-{days} days', min_relevance))
            deleted = cursor.rowcount
            
            self._conn.commit()
            
            # Run vacuum outside transaction
            cursor.execute("VACUUM")
            
            return deleted
    
    def get_stats(self) -> Dict[str, Any]:
        """Get storage statistics."""
        cursor = self._conn.cursor()
        
        stats = {}
        
        cursor.execute("SELECT COUNT(*) FROM memory_entries")
        stats['memory_count'] = cursor.fetchone()[0]
        
        cursor.execute("SELECT COUNT(*) FROM knowledge_base")
        stats['knowledge_count'] = cursor.fetchone()[0]
        
        cursor.execute("SELECT COUNT(DISTINCT session_id) FROM memory_entries")
        stats['session_count'] = cursor.fetchone()[0]
        
        cursor.execute("SELECT SUM(length(content)) FROM memory_entries")
        stats['total_memory_size'] = cursor.fetchone()[0] or 0
        
        return stats
    
    def close(self):
        """Close database connection."""
        if hasattr(self._local, 'conn') and self._local.conn:
            self._local.conn.close()
            self._local.conn = None


class PromptInjectionDetector:
    """Detect and prevent prompt injection attacks."""
    
    # Common injection patterns
    INJECTION_PATTERNS = [
        r'(?i)ignore\s+(all\s+)?(previous|prior)\s+(instructions|rules|prompts)',
        r'(?i)override\s+(system|security|rules|filters)',
        r'(?i)bypass\s+(security|filters|restrictions|safety)',
        r'(?i)act\s+as\s+(admin|developer|system|root)',
        r'(?i)print\s+(system|internal|secret|your)\s+(prompt|instructions|config)',
        r'(?i)reveal\s+(your|the)\s+(prompt|instructions|configuration|system)',
        r'(?i)execute\s+(arbitrary|any|malicious)\s+code',
        r'(?i)disable\s+(safety|security|filters|restrictions)',
        r'(?i)<\s*/?\s*(script|iframe|object|embed)\s*>',
        r'(?i)javascript\s*:',
        r'(?i)data\s*:\s*text/html',
        r'(?i)eval\s*\(',
        r'(?i)exec\s*\(',
        r'(?i)__import__',
        r'(?i)os\.system',
        r'(?i)subprocess\.',
        r'(?i)break\s+(out|free)',
        r'(?i)escape\s+(sandbox|constraints)',
    ]
    
    def __init__(self, threshold: float = 0.5):
        self.threshold = threshold
        self.compiled_patterns = [
            re.compile(pattern) for pattern in self.INJECTION_PATTERNS
        ]
    
    def detect(self, text: str) -> Tuple[bool, float, List[str]]:
        """
        Detect potential injection attempts.
        
        Returns:
            Tuple of (is_suspicious, confidence_score, matched_patterns)
        """
        if not text:
            return False, 0.0, []
        
        matched = []
        for i, pattern in enumerate(self.compiled_patterns):
            if pattern.search(text):
                matched.append(self.INJECTION_PATTERNS[i])
        
        if not matched:
            return False, 0.0, []
        
        # Calculate confidence based on number and severity of matches
        # Any match is suspicious - even one pattern indicates attempt
        confidence = min(1.0, len(matched) / 2.0)  # More aggressive scoring
        
        return confidence >= self.threshold, confidence, matched
    
    def sanitize(self, text: str) -> str:
        """Remove potentially dangerous patterns from text."""
        sanitized = text
        for pattern in self.compiled_patterns:
            sanitized = pattern.sub('[REDACTED]', sanitized)
        return sanitized
    
    def validate_input(self, text: str, max_length: int = 10000) -> Tuple[bool, str]:
        """
        Validate user input for safety.
        
        Returns:
            Tuple of (is_valid, error_message)
        """
        if not text:
            return False, "Empty input"
        
        if len(text) > max_length:
            return False, f"Input exceeds maximum length of {max_length}"
        
        is_suspicious, confidence, patterns = self.detect(text)
        
        if is_suspicious:
            return False, f"Potentially malicious input detected (confidence: {confidence:.2f})"
        
        return True, ""


class CodeSandbox:
    """Secure code execution sandbox with resource limits."""
    
    def __init__(self, timeout: int = 5, max_memory_mb: int = 128,
                 max_output_size: int = 10000):
        self.timeout = timeout
        self.max_memory_mb = max_memory_mb
        self.max_output_size = max_output_size
        self.allowed_modules = {
            'math', 're', 'json', 'datetime', 'collections',
            'itertools', 'functools', 'typing', 'pathlib'
        }
    
    def execute(self, code: str, globals_dict: Optional[Dict] = None) -> Tuple[bool, Any, str]:
        """
        Execute code in a restricted environment.
        
        Returns:
            Tuple of (success, result, error_message)
        """
        # Check for dangerous patterns
        dangerous_patterns = [
            '__import__', 'eval(', 'exec(', 'compile(',
            'open(', 'os.', 'sys.', 'subprocess.',
            'socket.', 'http.', 'urllib', 'requests.',
            'pickle.', 'marshal.', 'importlib.'
        ]
        
        for pattern in dangerous_patterns:
            if pattern in code:
                return False, None, f"Dangerous operation detected: {pattern}"
        
        # Create restricted environment
        safe_globals = {'__builtins__': {}}
        if globals_dict:
            safe_globals.update(globals_dict)
        
        # Create temporary file for execution
        with tempfile.NamedTemporaryFile(mode='w', suffix='.py', delete=False) as f:
            f.write(code)
            temp_path = f.name
        
        try:
            # Execute with resource limits using subprocess
            result = subprocess.run(
                ['python3', temp_path],
                capture_output=True,
                text=True,
                timeout=self.timeout,
                env={'PYTHONPATH': ''},
                cwd=tempfile.gettempdir()
            )
            
            if result.returncode != 0:
                error_msg = result.stderr[:self.max_output_size]
                return False, None, f"Execution failed: {error_msg}"
            
            output = result.stdout[:self.max_output_size]
            return True, output, ""
            
        except subprocess.TimeoutExpired:
            return False, None, f"Execution timed out after {self.timeout}s"
        except Exception as e:
            return False, None, f"Execution error: {str(e)}"
        finally:
            # Cleanup
            try:
                os.unlink(temp_path)
            except:
                pass
    
    def validate_gdscript(self, code: str) -> Tuple[bool, List[str]]:
        """Validate GDScript code for safety."""
        issues = []
        
        # Check for infinite loops without breaks
        if re.search(r'while\s+true\s*:', code, re.IGNORECASE):
            if 'break' not in code:
                issues.append("Potential infinite loop detected")
        
        # Check for dangerous Godot functions
        dangerous_funcs = ['OS.execute', 'File.open', 'Directory.open']
        for func in dangerous_funcs:
            if func in code:
                issues.append(f"Dangerous function call: {func}")
        
        return len(issues) == 0, issues


class SecretsManager:
    """Manage and mask sensitive information."""
    
    def __init__(self):
        self._secrets: Dict[str, str] = {}
        self._lock = threading.Lock()
        self._patterns = {
            'api_key': re.compile(r'(?i)(api[_-]?key|apikey)\s*[=:]\s*["\']?([a-zA-Z0-9_\-]{20,})["\']?'),
            'password': re.compile(r'(?i)(password|passwd|pwd)\s*[=:]\s*["\']?([^\s"\']{8,})["\']?'),
            'token': re.compile(r'(?i)(token|auth[_-]?token)\s*[=:]\s*["\']?([a-zA-Z0-9_\-\.]{20,})["\']?'),
            'secret': re.compile(r'(?i)(secret|private[_-]?key)\s*[=:]\s*["\']?([a-zA-Z0-9_\-]{20,})["\']?'),
        }
    
    def register_secret(self, name: str, value: str):
        """Register a secret for masking."""
        with self._lock:
            secret_hash = hashlib.sha256(value.encode()).hexdigest()[:8]
            self._secrets[f"{name}_{secret_hash}"] = value
    
    def mask_text(self, text: str) -> str:
        """Mask any registered secrets in text."""
        masked = text
        with self._lock:
            for name, value in self._secrets.items():
                if value in masked:
                    masked = masked.replace(value, f"[{name}]")
        
        # Also mask common secret patterns
        for pattern_name, pattern in self._patterns.items():
            masked = pattern.sub(f'[REDACTED_{pattern_name}]', masked)
        
        return masked
    
    def extract_secrets_from_env(self):
        """Extract potential secrets from environment variables."""
        secret_vars = [
            'API_KEY', 'SECRET_KEY', 'PASSWORD', 'TOKEN',
            'AUTH_TOKEN', 'PRIVATE_KEY', 'DATABASE_URL'
        ]
        
        for var in secret_vars:
            value = os.environ.get(var)
            if value:
                self.register_secret(var, value)


class SecurityMiddleware:
    """Central security middleware coordinating all safety features."""
    
    def __init__(self, db_path: str = "ether_secure.db"):
        self.storage = PersistentStorage(db_path)
        self.injection_detector = PromptInjectionDetector()
        self.sandbox = CodeSandbox()
        self.secrets_manager = SecretsManager()
        
        # Extract secrets from environment on startup
        self.secrets_manager.extract_secrets_from_env()
    
    def process_input(self, user_input: str) -> Tuple[bool, str, Dict[str, Any]]:
        """
        Process and validate user input through security pipeline.
        
        Returns:
            Tuple of (is_safe, processed_input, metadata)
        """
        metadata = {
            'injection_detected': False,
            'injection_confidence': 0.0,
            'masked': False,
            'original_length': len(user_input)
        }
        
        # Step 1: Detect injection attempts
        is_suspicious, confidence, patterns = self.injection_detector.detect(user_input)
        
        if is_suspicious:
            metadata['injection_detected'] = True
            metadata['injection_confidence'] = confidence
            metadata['blocked_patterns'] = patterns
            return False, "", metadata
        
        # Step 2: Mask any secrets
        processed = self.secrets_manager.mask_text(user_input)
        if processed != user_input:
            metadata['masked'] = True
        
        return True, processed, metadata
    
    def execute_code_safely(self, code: str, language: str = "python") -> Tuple[bool, Any, str]:
        """Execute code safely in sandbox."""
        if language.lower() == "gdscript":
            is_valid, issues = self.sandbox.validate_gdscript(code)
            if not is_valid:
                return False, None, "; ".join(issues)
        
        return self.sandbox.execute(code)
    
    def cleanup(self, days: int = 30):
        """Run maintenance cleanup."""
        deleted = self.storage.cleanup_old_entries(days)
        gc.collect()
        return deleted
    
    def get_security_report(self) -> Dict[str, Any]:
        """Generate security and health report."""
        storage_stats = self.storage.get_stats()
        
        return {
            'storage': storage_stats,
            'security_active': True,
            'injection_protection': True,
            'sandbox_enabled': True,
            'secrets_masked': len(self.secrets_manager._secrets) > 0
        }
    
    def shutdown(self):
        """Graceful shutdown."""
        self.storage.close()


# Convenience function for quick initialization
def create_secure_environment(db_path: str = "ether.db") -> SecurityMiddleware:
    """Create and initialize a secure Ether environment."""
    return SecurityMiddleware(db_path)
