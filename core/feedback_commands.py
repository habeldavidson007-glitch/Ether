"""
Feedback Commands Module
------------------------
Handles user feedback recording for the Adaptive Memory system.
Allows users to accept/reject suggestions to train Ether.
"""

from typing import Optional, Dict, Any
try:
    from .adaptive_memory import get_adaptive_memory
except ImportError:
    from adaptive_memory import get_adaptive_memory


class FeedbackManager:
    """Manages user feedback commands and interactions."""
    
    def __init__(self):
        self.memory = get_adaptive_memory()
        self.pending_interaction: Optional[Dict[str, Any]] = None
        
    def store_pending_interaction(self, query: str, original_code: str, 
                                  suggested_fix: str, file_path: str = "",
                                  error_type: str = "", metadata: Optional[Dict] = None):
        """Store the last interaction for later feedback."""
        self.pending_interaction = {
            "query": query,
            "original_code": original_code,
            "suggested_fix": suggested_fix,
            "file_path": file_path,
            "error_type": error_type,
            "metadata": metadata or {}
        }
        
    def accept_last(self) -> str:
        """Mark the last interaction as accepted."""
        if not self.pending_interaction:
            return "❌ No pending interaction to accept. Use /optimize or ask for a fix first."
            
        data = self.pending_interaction
        entry_id = self.memory.record_feedback(
            query=data["query"],
            original_code=data["original_code"],
            suggested_fix=data["suggested_fix"],
            user_feedback="accepted",
            file_path=data.get("file_path", ""),
            error_type=data.get("error_type", ""),
            metadata=data.get("metadata", {})
        )
        
        self.pending_interaction = None
        
        stats = self.memory.get_stats()
        return (
            f"✓ Feedback recorded: ACCEPTED\n"
            f"  Entry ID: {entry_id}\n"
            f"  Success Rate: {stats['success_rate']}\n"
            f"  Total Patterns Learned: {stats['total_patterns']}"
        )
        
    def reject_last(self, reason: str = "") -> str:
        """Mark the last interaction as rejected."""
        if not self.pending_interaction:
            return "❌ No pending interaction to reject."
            
        data = self.pending_interaction
        metadata = data.get("metadata", {})
        if reason:
            metadata["rejection_reason"] = reason
            
        entry_id = self.memory.record_feedback(
            query=data["query"],
            original_code=data["original_code"],
            suggested_fix=data["suggested_fix"],
            user_feedback="rejected",
            file_path=data.get("file_path", ""),
            error_type=data.get("error_type", ""),
            metadata=metadata
        )
        
        self.pending_interaction = None
        
        stats = self.memory.get_stats()
        return (
            f"✗ Feedback recorded: REJECTED\n"
            f"  Entry ID: {entry_id}\n"
            f"  Reason: {reason or 'Not specified'}\n"
            f"  Success Rate: {stats['success_rate']}\n"
            f"  This pattern will be avoided in future suggestions."
        )
        
    def get_feedback_status(self) -> str:
        """Get current feedback statistics."""
        stats = self.memory.get_stats()
        
        output = [
            "╔════════════════════════════════════════╗",
            "║     ETHER LEARNING STATUS              ║",
            "╠════════════════════════════════════════╣",
            f"║ Total Feedback: {stats['total_feedback']:>22} ║",
            f"║ Accepted:     {stats['accepted']:>22} ║",
            f"║ Rejected:     {stats['rejected']:>22} ║",
            f"║ Success Rate: {stats['success_rate']:>22} ║",
            f"║ Pattern Categories: {stats['pattern_categories']:>18} ║",
            f"║ Total Patterns:   {stats['total_patterns']:>18} ║",
            "╚════════════════════════════════════════╝",
            "",
            "💡 Tip: Use /accept or /reject after optimizations",
            "   to help Ether learn your coding preferences!"
        ]
        
        return "\n".join(output)
        
    def clear_pending(self):
        """Clear pending interaction without recording."""
        self.pending_interaction = None


def get_feedback_manager() -> FeedbackManager:
    """Singleton accessor for FeedbackManager."""
    if not hasattr(get_feedback_manager, "_instance"):
        get_feedback_manager._instance = FeedbackManager()
    return get_feedback_manager._instance


if __name__ == "__main__":
    # Test the module
    manager = get_feedback_manager()
    
    print("=== TESTING FEEDBACK MANAGER ===\n")
    
    # Store a mock interaction
    manager.store_pending_interaction(
        query="Optimize this function",
        original_code="func test():\n    var x = 1\n    return x",
        suggested_fix="func test():\n    return 1",
        file_path="test.gd",
        error_type="optimization"
    )
    
    print("1. Testing ACCEPT:")
    print(manager.accept_last())
    print()
    
    # Store another mock interaction
    manager.store_pending_interaction(
        query="Fix bug",
        original_code="var x = null",
        suggested_fix="var x = Vector3.ZERO",
        file_path="player.gd",
        error_type="bugfix"
    )
    
    print("2. Testing REJECT:")
    print(manager.reject_last("Suggestion was incorrect"))
    print()
    
    print("3. Testing STATUS:")
    print(manager.get_feedback_status())
    print()
    
    print("4. Testing NO PENDING:")
    print(manager.accept_last())
    print()
    
    print("✓ Feedback Manager module working correctly!")
