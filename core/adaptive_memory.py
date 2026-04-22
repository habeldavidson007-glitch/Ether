"""
Adaptive Memory Engine (The Hippocampus)
-----------------------------------------
Replaces: memory_core, learning_engine, context_manager (state part)
Purpose: Self-improving memory with feedback learning and conversation history
"""

import os
import json
import hashlib
from pathlib import Path
from typing import Dict, List, Optional, Any
from collections import defaultdict
from datetime import datetime

class FeedbackEntry:
    def __init__(self, entry_id: str, query: str, original_code: str, 
                 suggested_fix: str, user_feedback: str, file_path: str = "", 
                 error_type: str = "", metadata: Optional[Dict] = None):
        self.entry_id = entry_id
        self.timestamp = datetime.now().isoformat()
        self.query = query
        self.original_code = original_code
        self.suggested_fix = suggested_fix
        self.user_feedback = user_feedback
        self.file_path = file_path
        self.error_type = error_type
        self.metadata = metadata or {}
        self.features = self._extract_features()
        
    def _extract_features(self) -> Dict[str, Any]:
        return {
            "file_extension": Path(self.file_path).suffix if self.file_path else "unknown",
            "error_type": self.error_type or "general",
            "query_length": len(self.query),
            "code_lines": len(self.original_code.split('\n')),
            "fix_lines": len(self.suggested_fix.split('\n')),
            "keywords": self._extract_keywords()
        }
        
    def _extract_keywords(self) -> List[str]:
        import re
        text = f"{self.query} {self.original_code}".lower()
        keywords = re.findall(r'\b(?:signal|export|onready|var|const|enum|func|class|extends|yield|await|match|break|continue|return|if|elif|else|for|while|try|catch|except|finally|node|scene|tree|process|physics|input)\b', text)
        return list(set(keywords))
        
    def to_dict(self) -> Dict:
        return {
            "id": self.entry_id, "timestamp": self.timestamp,
            "query": self.query[:200], "file_path": self.file_path,
            "error_type": self.error_type, "feedback": self.user_feedback,
            "features": self.features
        }


class AdaptiveMemory:
    """
    The Hippocampus: Learns from feedback, manages conversation history, and stores patterns.
    """
    
    def __init__(self, storage_path: str = "memory_data"):
        self.storage_path = Path(storage_path)
        self.storage_path.mkdir(parents=True, exist_ok=True)
        
        self.feedback_file = self.storage_path / "feedback_log.json"
        self.patterns_file = self.storage_path / "learned_patterns.json"
        self.history_file = self.storage_path / "conversation_history.json"
        
        # In-memory cache
        self.feedback_history: List[FeedbackEntry] = []
        self.learned_patterns: Dict[str, List[Dict]] = defaultdict(list)
        self.conversation_history: List[Dict] = []
        
        # Statistics
        self.total_accepted = 0
        self.total_rejected = 0
        self.success_rate = 0.0
        
        self._load_data()
        
    def _load_data(self):
        if self.feedback_file.exists():
            try:
                with open(self.feedback_file, 'r') as f:
                    data = json.load(f)
                    self.feedback_history = [
                        FeedbackEntry(
                            entry_id=item['id'], query=item['query'],
                            original_code=item.get('original_code', ''),
                            suggested_fix=item.get('suggested_fix', ''),
                            user_feedback=item['feedback'],
                            file_path=item.get('file_path', ''),
                            error_type=item.get('error_type', '')
                        ) for item in data
                    ]
                self._recalculate_stats()
            except Exception as e:
                print(f"[AdaptiveMemory] Error loading feedback: {e}")
                
        if self.patterns_file.exists():
            try:
                with open(self.patterns_file, 'r') as f:
                    self.learned_patterns = defaultdict(list, json.load(f))
            except Exception as e:
                print(f"[AdaptiveMemory] Error loading patterns: {e}")
                
        if self.history_file.exists():
            try:
                with open(self.history_file, 'r') as f:
                    self.conversation_history = json.load(f)
            except Exception as e:
                print(f"[AdaptiveMemory] Error loading history: {e}")
                
    def _save_data(self):
        try:
            with open(self.feedback_file, 'w') as f:
                json.dump([entry.to_dict() for entry in self.feedback_history], f, indent=2)
            with open(self.patterns_file, 'w') as f:
                json.dump(dict(self.learned_patterns), f, indent=2)
            with open(self.history_file, 'w') as f:
                json.dump(self.conversation_history, f, indent=2)
        except Exception as e:
            print(f"[AdaptiveMemory] Error saving data: {e}")
            
    def _recalculate_stats(self):
        self.total_accepted = sum(1 for e in self.feedback_history if e.user_feedback == 'accepted')
        self.total_rejected = sum(1 for e in self.feedback_history if e.user_feedback == 'rejected')
        total = self.total_accepted + self.total_rejected
        self.success_rate = (self.total_accepted / total * 100) if total > 0 else 0.0
        
    def record_feedback(self, query: str, original_code: str, suggested_fix: str,
                       user_feedback: str, file_path: str = "", error_type: str = "",
                       metadata: Optional[Dict] = None) -> str:
        entry_id = hashlib.md5(f"{datetime.now().isoformat()}:{query[:50]}".encode()).hexdigest()[:12]
        
        entry = FeedbackEntry(
            entry_id=entry_id, query=query, original_code=original_code,
            suggested_fix=suggested_fix, user_feedback=user_feedback,
            file_path=file_path, error_type=error_type, metadata=metadata
        )
        
        self.feedback_history.append(entry)
        self._recalculate_stats()
        self._update_patterns(entry)
        self._save_data()
        
        return entry_id
        
    def _update_patterns(self, entry: FeedbackEntry):
        if entry.user_feedback != 'accepted':
            return
            
        category = f"{entry.features['error_type']}_{entry.features['file_extension']}"
        
        pattern = {
            "query_pattern": entry.query[:100],
            "keywords": entry.features['keywords'],
            "fix_preview": entry.suggested_fix[:200],
            "success_count": 1,
            "last_used": entry.timestamp
        }
        
        existing = self.learned_patterns[category]
        similar_found = False
        
        for p in existing:
            shared_keywords = set(p['keywords']) & set(pattern['keywords'])
            if len(shared_keywords) >= 2:
                p['success_count'] += 1
                p['last_used'] = pattern['last_used']
                similar_found = True
                break
                
        if not similar_found:
            self.learned_patterns[category].append(pattern)
            
        self.learned_patterns[category] = sorted(
            self.learned_patterns[category],
            key=lambda x: x['success_count'], reverse=True
        )[:20]
        
    def get_learning_context(self, query: str, file_path: str = "", 
                            error_type: str = "") -> List[Dict]:
        ext = Path(file_path).suffix if file_path else ".gd"
        category = f"{error_type}_{ext}" if error_type else f"general_{ext}"
        
        candidates = []
        
        if category in self.learned_patterns:
            candidates.extend(self.learned_patterns[category])
        if f"general_{ext}" in self.learned_patterns:
            candidates.extend(self.learned_patterns[f"general_{ext}"])
            
        query_keywords = set(query.lower().split())
        for entry in self.feedback_history[-100:]:
            if entry.user_feedback == 'accepted':
                entry_keywords = set(entry.query.lower().split())
                similarity = len(query_keywords & entry_keywords) / max(len(query_keywords), 1)
                if similarity > 0.3:
                    candidates.append({
                        "query_example": entry.query,
                        "fix_example": entry.suggested_fix[:300],
                        "relevance": similarity
                    })
                    
        candidates = sorted(
            candidates,
            key=lambda x: x.get('success_count', 0) + x.get('relevance', 0) * 10,
            reverse=True
        )
        
        return candidates[:5]
        
    def add_to_history(self, role: str, content: str, query: str = ""):
        self.conversation_history.append({
            "role": role, "content": content[:2000], 
            "query": query[:200], "timestamp": datetime.now().isoformat()
        })
        # Keep last 50 messages
        self.conversation_history = self.conversation_history[-50:]
        self._save_data()
        
    def get_recent_history(self, limit: int = 10) -> List[Dict]:
        return self.conversation_history[-limit:]
        
    def clear_history(self):
        self.conversation_history.clear()
        self._save_data()
        
    def get_stats(self) -> Dict:
        return {
            "total_feedback": len(self.feedback_history),
            "accepted": self.total_accepted,
            "rejected": self.total_rejected,
            "success_rate": f"{self.success_rate:.1f}%",
            "pattern_categories": len(self.learned_patterns),
            "conversation_turns": len(self.conversation_history)
        }


# Singleton instance
_instance: Optional[AdaptiveMemory] = None

def get_adaptive_memory(storage_path: str = "memory_data") -> AdaptiveMemory:
    global _instance
    if _instance is None:
        _instance = AdaptiveMemory(storage_path)
    return _instance
