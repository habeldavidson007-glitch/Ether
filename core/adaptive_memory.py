"""
Adaptive Memory Engine (The Hippocampus) - Unified Memory System
================================================================
Replaces: ResponseCache, PersistentStorage, MemoryUnit, LRUCache

Purpose: Self-improving memory with feedback learning and conversation history

Features:
- Thread-safe operations with RLock
- Memory leak prevention with automatic cleanup
- Conversation history bounded at 20 entries
- LRU caching for responses
- Persistent JSON storage for patterns and feedback
"""

import os
import json
import hashlib
import threading
from pathlib import Path
from typing import Dict, List, Optional, Any
from collections import OrderedDict
from datetime import datetime
from functools import lru_cache


class ResponseCache:
    """Simple LRU cache for responses (replaces builder.py ResponseCache)."""
    
    def __init__(self, max_size: int = 100):
        self._cache: OrderedDict[str, Any] = OrderedDict()
        self._max_size = max_size
        self._lock = threading.RLock()
    
    def get(self, key: str) -> Optional[Any]:
        with self._lock:
            if key in self._cache:
                self._cache.move_to_end(key)
                return self._cache[key]
            return None
    
    def set(self, key: str, value: Any):
        with self._lock:
            if key in self._cache:
                self._cache.move_to_end(key)
            self._cache[key] = value
            while len(self._cache) > self._max_size:
                self._cache.popitem(last=False)
    
    def clear(self):
        with self._lock:
            self._cache.clear()


class AdaptiveMemory:
    """
    The Hippocampus: Learns from feedback, manages conversation history, and stores patterns.
    
    Thread-safe implementation with automatic memory management.
    Consolidates: AdaptiveMemory, ResponseCache, PersistentStorage, MemoryUnit, LRUCache
    """
    
    def __init__(self, storage_path: str = "memory_data", max_history_size: int = 20, 
                 auto_cleanup_interval: int = 100):
        self.storage_path = Path(storage_path)
        self.storage_path.mkdir(parents=True, exist_ok=True)
        
        # Subdirectories for different data types
        self.feedback_file = self.storage_path / "feedback_log.json"
        self.patterns_file = self.storage_path / "learned_patterns.json"
        self.history_file = self.storage_path / "conversation_history.json"
        
        # In-memory storage
        self.feedback_history: List[Dict] = []
        self.learned_patterns: Dict[str, List[Dict]] = {}
        self._conversation_history: List[Dict] = []
        self._history_max_length = max_history_size
        
        # Response cache (LRU)
        self.response_cache = ResponseCache(max_size=100)
        
        # Statistics
        self.total_accepted = 0
        self.total_rejected = 0
        self.operation_count = 0
        
        # Thread safety
        self._lock = threading.RLock()
        
        # Load persisted data
        self._load_data()
    
    def _load_data(self):
        """Load persisted data from disk."""
        try:
            if self.history_file.exists():
                with open(self.history_file, 'r') as f:
                    data = json.load(f)
                    self._conversation_history = data[-self._history_max_length:]
            
            if self.feedback_file.exists():
                with open(self.feedback_file, 'r') as f:
                    self.feedback_history = json.load(f)
            
            if self.patterns_file.exists():
                with open(self.patterns_file, 'r') as f:
                    self.learned_patterns = json.load(f)
        except Exception as e:
            logger.warning(f"Could not load memory data: {e}")
    
    def _save_data(self):
        """Persist data to disk."""
        try:
            with open(self.history_file, 'w') as f:
                json.dump(self._conversation_history, f, indent=2)
            
            with open(self.feedback_file, 'w') as f:
                json.dump(self.feedback_history, f, indent=2)
            
            with open(self.patterns_file, 'w') as f:
                json.dump(self.learned_patterns, f, indent=2)
        except Exception as e:
            logger.error(f"Could not save memory data: {e}")
    
    @property
    def conversation_history(self) -> List[Dict]:
        """Get conversation history (bounded to max_length entries)."""
        with self._lock:
            if len(self._conversation_history) > self._history_max_length:
                self._conversation_history = self._conversation_history[-self._history_max_length:]
            return self._conversation_history
    
    @conversation_history.setter
    def conversation_history(self, value: List[Dict]):
        """Set conversation history with automatic bounding."""
        with self._lock:
            self._conversation_history = value[-self._history_max_length:] if len(value) > self._history_max_length else value
    
    def add_to_conversation_history(self, entry: Dict):
        """Add entry to conversation history with automatic bounding."""
        with self._lock:
            self._conversation_history.append(entry)
            # Enforce hard limit - THIS IS THE CRITICAL FIX
            if len(self._conversation_history) > self._history_max_length:
                self._conversation_history = self._conversation_history[-self._history_max_length:]
            self._save_data()
    
    def get_conversation_history(self, limit: int = None) -> List[Dict]:
        """Get recent conversation history."""
        with self._lock:
            if limit is None:
                limit = self._history_max_length
            return self._conversation_history[-limit:]
    
    def clear_conversation_history(self):
        """Clear conversation history."""
        with self._lock:
            self._conversation_history.clear()
            self._save_data()
    
    def add_feedback(self, feedback_entry: Dict):
        """Add feedback entry."""
        with self._lock:
            self.feedback_history.append(feedback_entry)
            self._save_data()
    
    def add_pattern(self, pattern_key: str, pattern_data: Dict):
        """Add learned pattern."""
        with self._lock:
            if pattern_key not in self.learned_patterns:
                self.learned_patterns[pattern_key] = []
            self.learned_patterns[pattern_key].append(pattern_data)
            self._save_data()
    
    def get_patterns(self, pattern_key: str) -> List[Dict]:
        """Get patterns by key."""
        with self._lock:
            return self.learned_patterns.get(pattern_key, [])
    
    def cache_response(self, key: str, response: Any):
        """Cache a response."""
        self.response_cache.set(key, response)
    
    def get_cached_response(self, key: str) -> Optional[Any]:
        """Get cached response."""
        return self.response_cache.get(key)
    
    def get_stats(self) -> Dict:
        """Get memory statistics."""
        with self._lock:
            return {
                "conversation_turns": len(self._conversation_history),
                "feedback_entries": len(self.feedback_history),
                "pattern_keys": len(self.learned_patterns),
                "cache_size": len(self.response_cache._cache),
                "memory_safe": len(self._conversation_history) <= self._history_max_length
            }
    
    def cleanup(self):
        """Cleanup old data."""
        with self._lock:
            # Ensure history is bounded
            if len(self._conversation_history) > self._history_max_length * 2:
                self._conversation_history = self._conversation_history[-self._history_max_length:]
            self._save_data()


# Singleton instance
_memory_instance: Optional[AdaptiveMemory] = None
_memory_lock = threading.Lock()


def get_adaptive_memory(storage_path: str = "memory_data") -> AdaptiveMemory:
    """Get singleton AdaptiveMemory instance."""
    global _memory_instance
    with _memory_lock:
        if _memory_instance is None:
            _memory_instance = AdaptiveMemory(storage_path)
        return _memory_instance


# Simple LRU cache decorator for functions (replaces utils/project_loader.py LRUCache)
def memoize(maxsize: int = 128):
    """Decorator for memoization with LRU eviction."""
    return lru_cache(maxsize=maxsize)
