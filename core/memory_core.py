"""
Memory Core - Persistent Learning & Pattern Recognition for Ether
Stores fix history, warning patterns, and user preferences to enable self-learning.
"""

import json
import hashlib
import os
from datetime import datetime
from typing import Dict, List, Any, Optional
from pathlib import Path


class MemoryCore:
    """Persistent memory system for Ether to learn from past fixes."""
    
    def __init__(self, project_path: str):
        self.project_path = Path(project_path)
        self.memory_file = self.project_path / ".ether_memory.json"
        self.data: Dict[str, Any] = {
            "fix_history": [],
            "warning_patterns": {},
            "user_preferences": {},
            "file_stats": {},
            "last_updated": None
        }
        self._load()
    
    def _load(self):
        """Load memory from disk."""
        if self.memory_file.exists():
            try:
                with open(self.memory_file, 'r', encoding='utf-8') as f:
                    self.data = json.load(f)
            except (json.JSONDecodeError, IOError):
                self.data = {"fix_history": [], "warning_patterns": {}, "user_preferences": {}, "file_stats": {}}
    
    def _save(self):
        """Save memory to disk."""
        self.data["last_updated"] = datetime.now().isoformat()
        try:
            with open(self.memory_file, 'w', encoding='utf-8') as f:
                json.dump(self.data, f, indent=2)
        except IOError as e:
            print(f"[MEMORY] Failed to save: {e}")
    
    def _hash_code(self, code: str) -> str:
        """Create a lightweight hash of code for similarity checking."""
        # Normalize whitespace for better matching
        normalized = " ".join(code.split())
        return hashlib.md5(normalized.encode()).hexdigest()[:12]
    
    def record_fix(self, file_path: str, issues_fixed: List[str], 
                   success: bool, context: Optional[Dict] = None):
        """Record a fix operation for future learning."""
        entry = {
            "timestamp": datetime.now().isoformat(),
            "file": file_path,
            "issues": issues_fixed,
            "success": success,
            "context": context or {}
        }
        self.data["fix_history"].append(entry)
        
        # Update pattern recognition
        for issue in issues_fixed:
            key = f"{file_path}:{issue}"
            if key not in self.data["warning_patterns"]:
                self.data["warning_patterns"][key] = {"count": 0, "successes": 0}
            self.data["warning_patterns"][key]["count"] += 1
            if success:
                self.data["warning_patterns"][key]["successes"] += 1
        
        # Keep history limited to last 500 entries
        if len(self.data["fix_history"]) > 500:
            self.data["fix_history"] = self.data["fix_history"][-500:]
        
        self._save()
    
    def get_similar_fixes(self, file_path: str, code_hash: str) -> List[Dict]:
        """Find similar past fixes for context."""
        matches = []
        for entry in reversed(self.data["fix_history"][-50:]):
            if entry["file"] == file_path:
                matches.append(entry)
        return matches
    
    def get_warning_pattern(self, file_path: str, issue_type: str) -> Dict:
        """Get statistics for a specific warning pattern."""
        key = f"{file_path}:{issue_type}"
        return self.data["warning_patterns"].get(key, {"count": 0, "successes": 0})
    
    def get_recurring_issues(self, file_path: str) -> List[str]:
        """Identify issues that frequently appear in a file."""
        recurring = []
        for key, stats in self.data["warning_patterns"].items():
            if key.startswith(file_path):
                if stats["count"] >= 3:  # Appeared 3+ times
                    issue = key.split(":", 1)[1]
                    recurring.append(issue)
        return recurring
    
    def store_preference(self, key: str, value: Any):
        """Store a user preference."""
        self.data["user_preferences"][key] = value
        self._save()
    
    def get_preference(self, key: str, default: Any = None) -> Any:
        """Retrieve a user preference."""
        return self.data["user_preferences"].get(key, default)
    
    def update_file_stats(self, file_path: str, stats: Dict):
        """Update statistics for a specific file."""
        self.data["file_stats"][file_path] = {
            **self.data["file_stats"].get(file_path, {}),
            **stats,
            "last_analyzed": datetime.now().isoformat()
        }
        self._save()
    
    def get_summary(self) -> Dict:
        """Get a summary of memory state."""
        return {
            "total_fixes": len(self.data["fix_history"]),
            "patterns_tracked": len(self.data["warning_patterns"]),
            "files_tracked": len(self.data["file_stats"]),
            "success_rate": self._calculate_success_rate()
        }
    
    def _calculate_success_rate(self) -> float:
        """Calculate overall success rate of fixes."""
        if not self.data["fix_history"]:
            return 0.0
        successes = sum(1 for entry in self.data["fix_history"] if entry["success"])
        return round((successes / len(self.data["fix_history"])) * 100, 1)


def create_memory_core(project_path: str) -> MemoryCore:
    """Factory function to create a MemoryCore instance."""
    return MemoryCore(project_path)
