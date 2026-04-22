"""
Adaptive Memory Core - The "Hippocampus"
=========================================
Replaces: memory_core.py, learning_engine.py, context_manager.py (state portion)

A self-improving memory system that:
1. Stores conversation history and session state
2. Records user feedback (accepted/rejected fixes)
3. Learns patterns from successful interactions
4. Adapts to project-specific coding styles
5. Provides contextual examples for LLM prompts

No fine-tuning required - uses retrieval-augmented learning.
"""

import os
import json
import hashlib
from typing import Dict, List, Optional, Tuple, Any
from pathlib import Path
from datetime import datetime
from collections import defaultdict


class MemoryEntry:
    """Represents a single memory entry (conversation or feedback)."""
    
    def __init__(self, entry_id: str, entry_type: str, data: Dict):
        self.entry_id = entry_id
        self.entry_type = entry_type  # 'conversation', 'feedback', 'pattern'
        self.timestamp = datetime.now().isoformat()
        self.data = data
        
    def to_dict(self) -> Dict:
        return {
            "id": self.entry_id,
            "type": self.entry_type,
            "timestamp": self.timestamp,
            "data": self.data
        }
        
    @classmethod
    def from_dict(cls, data: Dict) -> 'MemoryEntry':
        entry = cls(
            entry_id=data['id'],
            entry_type=data['type'],
            data=data['data']
        )
        entry.timestamp = data.get('timestamp', datetime.now().isoformat())
        return entry


class AdaptiveMemoryCore:
    """
    Main adaptive memory system with self-learning capabilities.
    
    Features:
    - Conversation history with context windowing
    - Feedback recording and pattern learning
    - Project-specific style adaptation
    - Intelligent retrieval of relevant memories
    - Persistent storage with automatic cleanup
    """
    
    def __init__(self, storage_path: str = "memory_data", 
                 max_history: int = 100,
                 auto_save: bool = True):
        self.storage_path = Path(storage_path)
        self.storage_path.mkdir(parents=True, exist_ok=True)
        
        self.max_history = max_history
        self.auto_save = auto_save
        
        # File paths
        self.history_file = self.storage_path / "conversation_history.json"
        self.feedback_file = self.storage_path / "feedback_log.json"
        self.patterns_file = self.storage_path / "learned_patterns.json"
        self.session_file = self.storage_path / "current_session.json"
        
        # In-memory storage
        self.conversation_history: List[MemoryEntry] = []
        self.feedback_history: List[MemoryEntry] = []
        self.learned_patterns: Dict[str, List[Dict]] = defaultdict(list)
        self.current_session: Dict[str, Any] = {}
        
        # Statistics
        self.stats = {
            "total_conversations": 0,
            "total_feedback": 0,
            "accepted_fixes": 0,
            "rejected_fixes": 0,
            "success_rate": 0.0,
            "pattern_categories": 0
        }
        
        # Load existing data
        self._load_all_data()
        
    def _load_all_data(self):
        """Load all persistent data from disk."""
        self._load_history()
        self._load_feedback()
        self._load_patterns()
        self._load_session()
        self._recalculate_stats()
        
    def _load_history(self):
        """Load conversation history."""
        if self.history_file.exists():
            try:
                with open(self.history_file, 'r') as f:
                    data = json.load(f)
                    self.conversation_history = [
                        MemoryEntry.from_dict(item) for item in data
                    ]
                # Trim to max_history
                self.conversation_history = self.conversation_history[-self.max_history:]
                print(f"[MemoryCore] Loaded {len(self.conversation_history)} conversation entries")
            except Exception as e:
                print(f"[MemoryCore] Error loading history: {e}")
                
    def _load_feedback(self):
        """Load feedback history."""
        if self.feedback_file.exists():
            try:
                with open(self.feedback_file, 'r') as f:
                    data = json.load(f)
                    self.feedback_history = [
                        MemoryEntry.from_dict(item) for item in data
                    ]
                print(f"[MemoryCore] Loaded {len(self.feedback_history)} feedback entries")
            except Exception as e:
                print(f"[MemoryCore] Error loading feedback: {e}")
                
    def _load_patterns(self):
        """Load learned patterns."""
        if self.patterns_file.exists():
            try:
                with open(self.patterns_file, 'r') as f:
                    self.learned_patterns = defaultdict(list, json.load(f))
                self.stats["pattern_categories"] = len(self.learned_patterns)
                print(f"[MemoryCore] Loaded {len(self.learned_patterns)} pattern categories")
            except Exception as e:
                print(f"[MemoryCore] Error loading patterns: {e}")
                
    def _load_session(self):
        """Load current session state."""
        if self.session_file.exists():
            try:
                with open(self.session_file, 'r') as f:
                    self.current_session = json.load(f)
                print(f"[MemoryCore] Restored session state")
            except Exception as e:
                print(f"[MemoryCore] Error loading session: {e}")
                
    def _save_all_data(self):
        """Save all data to disk."""
        if not self.auto_save:
            return
            
        try:
            # Save history
            with open(self.history_file, 'w') as f:
                json.dump([entry.to_dict() for entry in self.conversation_history[-self.max_history:]], 
                         f, indent=2)
                
            # Save feedback
            with open(self.feedback_file, 'w') as f:
                json.dump([entry.to_dict() for entry in self.feedback_history], f, indent=2)
                
            # Save patterns
            with open(self.patterns_file, 'w') as f:
                json.dump(dict(self.learned_patterns), f, indent=2)
                
            # Save session
            with open(self.session_file, 'w') as f:
                json.dump(self.current_session, f, indent=2)
                
        except Exception as e:
            print(f"[MemoryCore] Error saving data: {e}")
            
    def _recalculate_stats(self):
        """Recalculate statistics from loaded data."""
        self.stats["total_conversations"] = len(self.conversation_history)
        self.stats["total_feedback"] = len(self.feedback_history)
        
        accepted = sum(1 for e in self.feedback_history 
                      if e.data.get('feedback') == 'accepted')
        rejected = sum(1 for e in self.feedback_history 
                      if e.data.get('feedback') == 'rejected')
                      
        self.stats["accepted_fixes"] = accepted
        self.stats["rejected_fixes"] = rejected
        
        total = accepted + rejected
        self.stats["success_rate"] = (accepted / total * 100) if total > 0 else 0.0
        self.stats["pattern_categories"] = len(self.learned_patterns)
        
    def add_to_history(self, query: str, response: str, 
                      metadata: Optional[Dict] = None) -> str:
        """Add a conversation turn to history."""
        entry_id = hashlib.md5(f"{datetime.now().isoformat()}:{query[:50]}".encode()).hexdigest()[:12]
        
        entry = MemoryEntry(
            entry_id=entry_id,
            entry_type='conversation',
            data={
                "query": query,
                "response": response,
                "metadata": metadata or {}
            }
        )
        
        self.conversation_history.append(entry)
        
        # Auto-trim
        if len(self.conversation_history) > self.max_history:
            self.conversation_history = self.conversation_history[-self.max_history:]
            
        if self.auto_save:
            self._save_all_data()
            
        return entry_id
        
    def record_feedback(self, query: str, original_code: str, 
                       suggested_fix: str, user_feedback: str,
                       file_path: str = "", error_type: str = "",
                       metadata: Optional[Dict] = None) -> str:
        """
        Record user feedback for a code suggestion.
        
        Args:
            query: User's original question
            original_code: Code before fix
            suggested_fix: Suggested fix
            user_feedback: 'accepted' or 'rejected'
            file_path: Path to modified file
            error_type: Type of error fixed
            metadata: Additional context
            
        Returns:
            Entry ID for tracking
        """
        entry_id = hashlib.md5(f"{datetime.now().isoformat()}:{query[:50]}".encode()).hexdigest()[:12]
        
        # Extract features
        features = self._extract_features(original_code, suggested_fix, file_path, error_type)
        
        entry = MemoryEntry(
            entry_id=entry_id,
            entry_type='feedback',
            data={
                "query": query,
                "original_code": original_code,
                "suggested_fix": suggested_fix,
                "feedback": user_feedback,
                "file_path": file_path,
                "error_type": error_type,
                "features": features,
                "metadata": metadata or {}
            }
        )
        
        self.feedback_history.append(entry)
        
        # Learn from accepted fixes
        if user_feedback == 'accepted':
            self._update_patterns(entry)
            
        self._recalculate_stats()
        
        if self.auto_save:
            self._save_all_data()
            
        print(f"[MemoryCore] Recorded {user_feedback} feedback (Success: {self.stats['success_rate']:.1f}%)")
        return entry_id
        
    def _extract_features(self, original_code: str, suggested_fix: str,
                         file_path: str, error_type: str) -> Dict:
        """Extract features from code for pattern matching."""
        import re
        
        features = {
            "file_extension": Path(file_path).suffix if file_path else "unknown",
            "error_type": error_type or "general",
            "original_lines": len(original_code.split('\n')),
            "fix_lines": len(suggested_fix.split('\n')),
            "has_function": bool(re.search(r'\b(?:func|def)\s+\w+', original_code)),
            "has_class": bool(re.search(r'\bclass\s+\w+', original_code)),
            "has_signal": bool(re.search(r'\bsignal\s+', original_code)),
            "keywords": self._extract_keywords(original_code)
        }
        
        return features
        
    def _extract_keywords(self, text: str) -> List[str]:
        """Extract programming keywords from text."""
        import re
        keywords = re.findall(
            r'\b(?:signal|export|onready|var|const|enum|func|class|extends|yield|await|'
            r'match|break|continue|return|if|elif|else|for|while|try|catch|except|'
            r'finally|node|scene|tree|process|physics|input)\b',
            text.lower()
        )
        return list(set(keywords))
        
    def _update_patterns(self, entry: MemoryEntry):
        """Update learned patterns from accepted feedback."""
        features = entry.data.get('features', {})
        
        # Categorize by error type and file extension
        category = f"{features.get('error_type', 'general')}_{features.get('file_extension', '.gd')}"
        
        pattern = {
            "query_pattern": entry.data['query'][:100],
            "keywords": features.get('keywords', []),
            "fix_preview": entry.data['suggested_fix'][:200],
            "original_preview": entry.data['original_code'][:200],
            "success_count": 1,
            "last_used": entry.timestamp,
            "file_type": features.get('file_extension', '.gd')
        }
        
        # Check for similar existing patterns
        existing = self.learned_patterns[category]
        merged = False
        
        for p in existing:
            # Check keyword overlap
            shared = set(p.get('keywords', [])) & set(pattern['keywords'])
            if len(shared) >= 2:
                p['success_count'] += 1
                p['last_used'] = pattern['last_used']
                merged = True
                break
                
        if not merged:
            self.learned_patterns[category].append(pattern)
            
        # Keep only top patterns per category
        self.learned_patterns[category] = sorted(
            self.learned_patterns[category],
            key=lambda x: x.get('success_count', 0),
            reverse=True
        )[:20]
        
    def get_learning_context(self, query: str, file_path: str = "",
                            error_type: str = "") -> List[Dict]:
        """
        Retrieve relevant learned patterns for current query.
        Use this to inject few-shot examples into LLM prompts.
        
        Returns:
            List of successful past fixes as context
        """
        ext = Path(file_path).suffix if file_path else ".gd"
        category = f"{error_type}_{ext}" if error_type else f"general_{ext}"
        
        candidates = []
        
        # Get patterns from specific category
        if category in self.learned_patterns:
            candidates.extend(self.learned_patterns[category])
            
        # Get from general category
        general_cat = f"general_{ext}"
        if general_cat in self.learned_patterns and general_cat != category:
            candidates.extend(self.learned_patterns[general_cat])
            
        # Find similar queries in recent feedback
        query_keywords = set(query.lower().split())
        for entry in self.feedback_history[-50:]:
            if entry.data.get('feedback') == 'accepted':
                entry_query = entry.data.get('query', '')
                entry_keywords = set(entry_query.lower().split())
                
                similarity = len(query_keywords & entry_keywords) / max(len(query_keywords), 1)
                if similarity > 0.3:
                    candidates.append({
                        "query_example": entry_query,
                        "fix_example": entry.data.get('suggested_fix', '')[:300],
                        "relevance": similarity,
                        "source": "feedback_history"
                    })
                    
        # Sort by relevance/success count
        candidates = sorted(
            candidates,
            key=lambda x: x.get('success_count', 0) + x.get('relevance', 0) * 10,
            reverse=True
        )
        
        return candidates[:5]
        
    def generate_training_prompt(self, query: str, file_path: str = "",
                                error_type: str = "") -> str:
        """Generate prompt section with learned examples for LLM."""
        examples = self.get_learning_context(query, file_path, error_type)
        
        if not examples:
            return ""
            
        prompt = "\n\n## Learned Patterns from Previous Successes:\n"
        prompt += "Based on previously accepted fixes, consider these approaches:\n\n"
        
        for i, ex in enumerate(examples, 1):
            if 'fix_example' in ex:
                prompt += f"Example {i}:\n"
                prompt += f"  Query: \"{ex.get('query_example', 'N/A')[:80]}...\"\n"
                prompt += f"  Successful Fix: {ex.get('fix_example', 'N/A')[:150]}...\n\n"
            elif 'fix_preview' in ex:
                prompt += f"Pattern {i} ({ex.get('success_count', 1)} successes):\n"
                prompt += f"  Keywords: {', '.join(ex.get('keywords', [])[:5])}\n"
                prompt += f"  Approach: {ex.get('fix_preview', 'N/A')[:150]}...\n\n"
                
        prompt += "Apply similar reasoning and style to the current task.\n"
        return prompt
        
    def set_session_value(self, key: str, value: Any):
        """Set a value in the current session."""
        self.current_session[key] = value
        if self.auto_save:
            self._save_all_data()
            
    def get_session_value(self, key: str, default: Any = None) -> Any:
        """Get a value from the current session."""
        return self.current_session.get(key, default)
        
    def get_recent_history(self, limit: int = 10) -> List[Dict]:
        """Get recent conversation history."""
        return [
            {"query": e.data.get('query', ''), "response": e.data.get('response', '')}
            for e in self.conversation_history[-limit:]
        ]
        
    def clear_history(self):
        """Clear conversation history."""
        self.conversation_history.clear()
        if self.auto_save:
            self._save_all_data()
            
    def clear_feedback(self):
        """Clear feedback history and patterns."""
        self.feedback_history.clear()
        self.learned_patterns.clear()
        self._recalculate_stats()
        if self.auto_save:
            self._save_all_data()
            
    def get_stats(self) -> Dict:
        """Get memory core statistics."""
        return {
            **self.stats,
            "history_entries": len(self.conversation_history),
            "session_keys": len(self.current_session),
            "total_patterns": sum(len(p) for p in self.learned_patterns.values())
        }
        
    def export_report(self, output_path: str):
        """Export detailed memory report."""
        report = {
            "summary": self.get_stats(),
            "top_patterns": {},
            "recent_feedback": [e.to_dict() for e in self.feedback_history[-20:]],
            "session_state": self.current_session
        }
        
        # Top 3 patterns per category
        for category, patterns in self.learned_patterns.items():
            report["top_patterns"][category] = patterns[:3]
            
        with open(output_path, 'w') as f:
            json.dump(report, f, indent=2)
            
        print(f"[MemoryCore] Report exported to {output_path}")


# Singleton instance
_memory_instance: Optional[AdaptiveMemoryCore] = None

def get_adaptive_memory(storage_path: str = "memory_data",
                       max_history: int = 100) -> AdaptiveMemoryCore:
    """Get or create adaptive memory core instance."""
    global _memory_instance
    
    if _memory_instance is None:
        _memory_instance = AdaptiveMemoryCore(storage_path, max_history)
        
    return _memory_instance
