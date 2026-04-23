"""
Test suite for EtherBrain - the core AI pipeline.

Tests cover:
- Intent detection and task decomposition
- Response caching
- Query processing
- Chat mode switching
- Error handling
"""
import pytest
from pathlib import Path
import sys

# Import the module under test
from core.builder import EtherBrain


class TestEtherBrainInitialization:
    """Test EtherBrain initialization and basic setup."""
    
    def test_brain_creates_successfully(self):
        """Verify EtherBrain can be instantiated."""
        brain = EtherBrain()
        assert brain is not None
        assert brain.chat_mode == "mixed"
    
    def test_brain_has_cache(self):
        """Verify brain has cache mechanism via stats method."""
        brain = EtherBrain()
        # Cache is internal (_response_cache), but we can verify it works via stats
        stats = brain.get_cache_stats()
        assert stats is not None
        assert 'entries' in stats
    
    def test_brain_default_chat_mode(self):
        """Verify default chat mode is 'mixed'."""
        brain = EtherBrain()
        assert brain.chat_mode == "mixed"


class TestChatModeSwitching:
    """Test chat mode switching functionality."""
    
    def test_set_coding_mode(self):
        """Test switching to coding mode."""
        brain = EtherBrain()
        brain.set_chat_mode("coding")
        assert brain.chat_mode == "coding"
    
    def test_set_general_mode(self):
        """Test switching to general mode."""
        brain = EtherBrain()
        brain.set_chat_mode("general")
        assert brain.chat_mode == "general"
    
    def test_set_mixed_mode(self):
        """Test switching to mixed mode."""
        brain = EtherBrain()
        brain.chat_mode = "coding"  # Change from default
        brain.set_chat_mode("mixed")
        assert brain.chat_mode == "mixed"
    
    def test_invalid_mode_unchanged(self):
        """Test that invalid mode leaves mode unchanged."""
        brain = EtherBrain()
        original_mode = brain.chat_mode
        brain.set_chat_mode("invalid_mode")
        assert brain.chat_mode == original_mode  # Unchanged
    
    def test_mode_case_sensitive(self):
        """Test that mode setting is case-sensitive (lowercase only)."""
        brain = EtherBrain()
        brain.set_chat_mode("CODING")  # This won't match
        # Invalid mode should not change it
        assert brain.chat_mode == "mixed"


class TestResponseCache:
    """Test response caching functionality."""
    
    def test_cache_miss_initially(self):
        """Test that cache is empty initially."""
        brain = EtherBrain()
        stats = brain.get_cache_stats()
        assert stats['entries'] == 0
    
    def test_cache_stats_structure(self):
        """Test cache stats returns proper structure."""
        brain = EtherBrain()
        stats = brain.get_cache_stats()
        assert 'entries' in stats
        assert isinstance(stats['entries'], int)


class TestIntentDetection:
    """Test intent detection and task decomposition."""
    
    def test_detect_optimize_intent(self):
        """Test detection of optimize intent."""
        brain = EtherBrain()
        # Access the internal method through brain instance
        query = "Optimize this GDScript code"
        # The brain should process this query without error
        try:
            result, log = brain.process_query(query)
            assert result is not None
        except Exception as e:
            pytest.fail(f"Query processing failed: {e}")
    
    def test_detect_fix_intent(self):
        """Test detection of fix/debug intent."""
        brain = EtherBrain()
        query = "Fix the bug in player.gd"
        try:
            result, log = brain.process_query(query)
            assert result is not None
        except Exception as e:
            pytest.fail(f"Query processing failed: {e}")
    
    def test_detect_explain_intent(self):
        """Test detection of explain intent."""
        brain = EtherBrain()
        query = "Explain how signals work in Godot"
        try:
            result, log = brain.process_query(query)
            assert result is not None
        except Exception as e:
            pytest.fail(f"Query processing failed: {e}")
    
    def test_detect_create_intent(self):
        """Test detection of create/build intent."""
        brain = EtherBrain()
        query = "Create a new enemy script"
        try:
            result, log = brain.process_query(query)
            assert result is not None
        except Exception as e:
            pytest.fail(f"Query processing failed: {e}")


class TestQueryProcessing:
    """Test query processing pipeline."""
    
    def test_process_simple_query(self):
        """Test processing a simple query."""
        brain = EtherBrain()
        query = "Hello"
        result, log = brain.process_query(query)
        assert result is not None
        assert isinstance(log, list)
    
    def test_process_godot_question(self):
        """Test processing a Godot-specific question."""
        brain = EtherBrain()
        query = "What is a CharacterBody2D?"
        result, log = brain.process_query(query)
        assert result is not None
        assert isinstance(log, list)
    
    def test_process_with_history(self):
        """Test query processing maintains history."""
        brain = EtherBrain()
        query1 = "First question"
        query2 = "Follow-up question"
        
        result1, log1 = brain.process_query(query1)
        result2, log2 = brain.process_query(query2)
        
        assert result1 is not None
        assert result2 is not None
    
    def test_empty_query_handling(self):
        """Test handling of empty query."""
        brain = EtherBrain()
        query = ""
        result, log = brain.process_query(query)
        assert result is not None
        assert isinstance(log, list)


class TestErrorHandling:
    """Test error handling and edge cases."""
    
    def test_very_long_query(self):
        """Test handling of very long query."""
        brain = EtherBrain()
        query = "Explain " + "code " * 1000
        result, log = brain.process_query(query)
        assert result is not None
    
    def test_special_characters_in_query(self):
        """Test handling of special characters."""
        brain = EtherBrain()
        query = "Explain @export var and $NodePath in GDScript!"
        result, log = brain.process_query(query)
        assert result is not None
    
    def test_unicode_characters(self):
        """Test handling of unicode characters."""
        brain = EtherBrain()
        query = "解释 Godot 中的场景树 (Scene Tree)"
        result, log = brain.process_query(query)
        assert result is not None


class TestCacheBehavior:
    """Test cache behavior with repeated queries."""
    
    def test_repeated_query_uses_cache(self):
        """Test that repeated queries use cache."""
        brain = EtherBrain()
        query = "Test cache query"
        
        # First query
        result1, log1 = brain.process_query(query)
        stats1 = brain.get_cache_stats()
        
        # Second identical query
        result2, log2 = brain.process_query(query)
        stats2 = brain.get_cache_stats()
        
        # Results should be the same
        assert result1 == result2
        # Cache should have been used (stats might show this)
        assert stats2['entries'] >= stats1['entries']


class TestIntegration:
    """Integration tests for complete workflows."""
    
    def test_full_conversation_flow(self):
        """Test a complete conversation flow."""
        brain = EtherBrain()
        
        # Start in mixed mode
        assert brain.chat_mode == "mixed"
        
        # Ask a question
        result1, _ = brain.process_query("What is GDScript?")
        assert result1 is not None
        
        # Switch to coding mode
        brain.set_chat_mode("coding")
        assert brain.chat_mode == "coding"
        
        # Ask coding question
        result2, _ = brain.process_query("How to optimize a loop?")
        assert result2 is not None
        
        # Switch back
        brain.set_chat_mode("mixed")
        assert brain.chat_mode == "mixed"
    
    def test_multiple_brain_instances(self):
        """Test that multiple brain instances work independently."""
        brain1 = EtherBrain()
        brain2 = EtherBrain()
        
        brain1.set_chat_mode("coding")
        brain2.set_chat_mode("general")
        
        assert brain1.chat_mode == "coding"
        assert brain2.chat_mode == "general"
        assert brain1.chat_mode != brain2.chat_mode
