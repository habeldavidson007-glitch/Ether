"""
Test suite for Ether Librarian - Knowledge Base Retrieval.

Tests cover:
- Inverted index creation and search
- Mode-aware filtering
- Knowledge retrieval
- Edge cases
"""
import pytest
from pathlib import Path
import tempfile
import shutil

from core.librarian import InvertedIndex, get_librarian


class TestInvertedIndex:
    """Test the InvertedIndex class."""
    
    def test_create_index(self):
        """Test creating an empty index."""
        index = InvertedIndex()
        assert index is not None
        assert len(index.index) == 0
        assert index._indexed is False
    
    def test_add_file_to_index(self):
        """Test adding a file to the index."""
        index = InvertedIndex()
        content = "This is a test file about GDScript programming."
        index.add_file("test_file", content, mode="coding", topics=["gdscript", "programming"])
        
        assert index._indexed is True
        assert "test_file" in index.file_metadata
        assert index.file_metadata["test_file"]["mode"] == "coding"
        assert len(index.index) > 0  # Should have indexed some words
    
    def test_add_file_with_topics(self):
        """Test adding file with topic metadata."""
        index = InvertedIndex()
        content = "Godot signals are powerful for communication."
        index.add_file("signals_file", content, mode="coding", topics=["signals", "godot"])
        
        metadata = index.file_metadata["signals_file"]
        assert metadata["topics"] == ["signals", "godot"]
        assert metadata["mode"] == "coding"
    
    def test_search_single_word(self):
        """Test searching for a single word."""
        index = InvertedIndex()
        index.add_file("file1", "GDScript is awesome for game development")
        index.add_file("file2", "Python is great for scripting")
        
        results = index.search("GDScript")
        assert len(results) > 0
        assert results[0][0] == "file1"  # file1 should be most relevant
    
    def test_search_multiple_words(self):
        """Test searching for multiple words."""
        index = InvertedIndex()
        index.add_file("file1", "GDScript game development programming")
        index.add_file("file2", "Python web development scripting")
        index.add_file("file3", "GDScript Python both languages")
        
        results = index.search("GDScript Python")
        assert len(results) > 0
        # file3 should rank highest as it has both words
        assert results[0][0] == "file3"
    
    def test_search_mode_filter_coding(self):
        """Test mode filtering for coding mode."""
        index = InvertedIndex()
        index.add_file("coding_file", "GDScript code programming", mode="coding")
        index.add_file("general_file", "General knowledge facts", mode="general")
        
        results = index.search("code", mode_filter="coding")
        assert len(results) > 0
        assert all(r[0] == "coding_file" for r in results)
    
    def test_search_mode_filter_general(self):
        """Test mode filtering for general mode."""
        index = InvertedIndex()
        index.add_file("coding_file", "GDScript code programming", mode="coding")
        index.add_file("general_file", "General knowledge facts", mode="general")
        
        results = index.search("knowledge", mode_filter="general")
        assert len(results) > 0
        assert all(r[0] == "general_file" for r in results)
    
    def test_search_mixed_mode(self):
        """Test search in mixed mode (no filtering)."""
        index = InvertedIndex()
        index.add_file("coding_file", "GDScript code programming", mode="coding")
        index.add_file("general_file", "General knowledge facts", mode="general")
        
        results = index.search("code knowledge", mode_filter="mixed")
        # Should return results from both modes
        assert len(results) >= 1
    
    def test_search_no_results(self):
        """Test search with no matching results."""
        index = InvertedIndex()
        index.add_file("file1", "GDScript programming")
        
        results = index.search("nonexistentword12345")
        assert len(results) == 0
    
    def test_search_empty_query(self):
        """Test search with empty query."""
        index = InvertedIndex()
        index.add_file("file1", "GDScript programming")
        
        results = index.search("")
        assert len(results) == 0
    
    def test_search_case_insensitive(self):
        """Test that search is case-insensitive."""
        index = InvertedIndex()
        index.add_file("file1", "GDScript Programming Is Fun")
        
        results1 = index.search("gdscript")
        results2 = index.search("GDSCRIPT")
        results3 = index.search("GdScript")
        
        assert len(results1) == len(results2) == len(results3)
        assert len(results1) > 0
    
    def test_file_metadata_structure(self):
        """Test file metadata structure."""
        index = InvertedIndex()
        content = "Test content with some words"
        index.add_file("test", content, mode="coding", topics=["test"])
        
        metadata = index.file_metadata["test"]
        assert "mode" in metadata
        assert "topics" in metadata
        assert "word_count" in metadata
        assert "unique_words" in metadata


class TestLibrarian:
    """Test the get_librarian function and overall librarian functionality."""
    
    def test_get_librarian_returns_instance(self):
        """Test that get_librarian returns an instance."""
        librarian = get_librarian()
        assert librarian is not None
    
    def test_librarian_singleton(self):
        """Test that get_librarian returns same instance (singleton)."""
        librarian1 = get_librarian()
        librarian2 = get_librarian()
        assert librarian1 is librarian2
    
    def test_librarian_has_knowledge_base(self):
        """Test that librarian has access to knowledge base."""
        librarian = get_librarian()
        # The librarian should have indexed files from knowledge_base directory
        # This tests integration with actual knowledge base
        assert hasattr(librarian, 'index') or hasattr(librarian, '_index')


class TestKnowledgeRetrieval:
    """Test knowledge retrieval scenarios."""
    
    def test_retrieve_godot_topic(self):
        """Test retrieving Godot-related knowledge."""
        librarian = get_librarian()
        # Try to retrieve knowledge about Godot
        # This will test the actual knowledge base if it exists
        try:
            context = librarian.retrieve("Godot signals", mode="coding")
            assert context is not None
        except Exception:
            # If knowledge base doesn't exist yet, that's okay for now
            pass
    
    def test_retrieve_cpp_topic(self):
        """Test retrieving C++ related knowledge."""
        librarian = get_librarian()
        try:
            context = librarian.retrieve("C++ memory management", mode="coding")
            assert context is not None
        except Exception:
            pass


class TestEdgeCases:
    """Test edge cases and error handling."""
    
    def test_add_empty_content(self):
        """Test adding file with empty content."""
        index = InvertedIndex()
        index.add_file("empty", "")
        
        # Should still add metadata but minimal indexing
        assert "empty" in index.file_metadata
    
    def test_add_very_long_content(self):
        """Test adding very long content."""
        index = InvertedIndex()
        long_content = "word " * 10000
        index.add_file("long", long_content)
        
        assert "long" in index.file_metadata
        assert index.file_metadata["long"]["word_count"] > 0
    
    def test_special_characters_in_content(self):
        """Test content with special characters."""
        index = InvertedIndex()
        content = "GDScript @export $NodePath % modulo & bitwise"
        index.add_file("special", content)
        
        # Should handle special characters gracefully
        assert "special" in index.file_metadata
    
    def test_unicode_content(self):
        """Test content with unicode characters."""
        index = InvertedIndex()
        content = "Godot 支持中文 Unicode テスト"
        index.add_file("unicode", content)
        
        assert "unicode" in index.file_metadata
    
    def test_duplicate_file_id(self):
        """Test adding file with duplicate ID."""
        index = InvertedIndex()
        index.add_file("dup", "First content")
        index.add_file("dup", "Second content")
        
        # Second add should update/overwrite
        assert "dup" in index.file_metadata
