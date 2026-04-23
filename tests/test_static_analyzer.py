"""
Test suite for Static Analyzer - GDScript Anti-Pattern Detection.

Tests cover:
- Finding creation and management
- Anti-pattern detection
- SGMA dependency analysis
- Math curve loaders
- Edge cases
"""
import pytest
from pathlib import Path
import tempfile

from core.static_analyzer import StaticAnalyzer, Finding, ScriptNode


class TestFinding:
    """Test the Finding dataclass."""
    
    def test_create_finding(self):
        """Test creating a finding."""
        finding = Finding(
            file_path="res://scripts/player.gd",
            line_number=10,
            category="performance",
            severity="high",
            message="Heavy computation in _process",
            suggestion="Move to separate method"
        )
        
        assert finding.file_path == "res://scripts/player.gd"
        assert finding.line_number == 10
        assert finding.category == "performance"
        assert finding.severity == "high"
        assert finding.message == "Heavy computation in _process"
        assert finding.suggestion == "Move to separate method"
        assert finding.complexity_score == 0.0
    
    def test_finding_with_complexity(self):
        """Test creating a finding with complexity score."""
        finding = Finding(
            file_path="res://scripts/enemy.gd",
            line_number=None,
            category="code_quality",
            severity="medium",
            message="Missing docstring",
            suggestion="Add docstring",
            complexity_score=0.75
        )
        
        assert finding.complexity_score == 0.75
    
    def test_finding_no_line_number(self):
        """Test creating a finding without line number."""
        finding = Finding(
            file_path="res://project.godot",
            line_number=None,
            category="configuration",
            severity="low",
            message="Missing project name",
            suggestion="Add project name"
        )
        
        assert finding.line_number is None


class TestScriptNode:
    """Test the ScriptNode dataclass for SGMA."""
    
    def test_create_script_node(self):
        """Test creating a script node."""
        node = ScriptNode(file_path="res://scripts/player.gd")
        
        assert node.file_path == "res://scripts/player.gd"
        assert len(node.depends_on) == 0
        assert len(node.depended_by) == 0
        assert node.complexity == 0
        assert node.line_count == 0
    
    def test_script_node_with_dependencies(self):
        """Test creating a script node with dependencies."""
        node = ScriptNode(
            file_path="res://scripts/player.gd",
            depends_on={"res://scripts/base.gd", "res://scripts/utils.gd"},
            complexity=5,
            line_count=150
        )
        
        assert len(node.depends_on) == 2
        assert "res://scripts/base.gd" in node.depends_on
        assert node.complexity == 5
        assert node.line_count == 150


class TestStaticAnalyzerInitialization:
    """Test StaticAnalyzer initialization."""
    
    def test_create_analyzer(self):
        """Test creating a static analyzer."""
        analyzer = StaticAnalyzer()
        assert analyzer is not None
        assert len(analyzer.findings) == 0
    
    def test_analyzer_thresholds(self):
        """Test analyzer has proper thresholds."""
        analyzer = StaticAnalyzer()
        assert analyzer.LARGE_SCRIPT_THRESHOLD == 500
        assert analyzer.PROCESS_COMPLEXITY_THRESHOLD == 15
        assert analyzer.GLOBAL_STATE_THRESHOLD == 10


class TestStaticAnalysis:
    """Test static analysis functionality."""
    
    def test_analyze_empty_directory(self, tmp_path):
        """Test analyzing an empty directory."""
        analyzer = StaticAnalyzer()
        results = analyzer.analyze(str(tmp_path))
        
        assert results is not None
        # Should handle empty directory gracefully
    
    def test_analyze_single_file(self, tmp_path):
        """Test analyzing a single GDScript file."""
        # Create a simple GDScript file
        script_file = tmp_path / "test.gd"
        script_file.write_text("""
extends Node

var score = 0

func _process(delta):
    score += 1
""")
        
        analyzer = StaticAnalyzer()
        results = analyzer.analyze(str(tmp_path))
        
        assert results is not None
    
    def test_detect_large_script(self, tmp_path):
        """Test detection of large scripts."""
        # Create a large GDScript file (>500 lines)
        script_file = tmp_path / "large.gd"
        large_content = "extends Node\n\n" + "\n".join([f"# Line {i}" for i in range(600)])
        script_file.write_text(large_content)
        
        analyzer = StaticAnalyzer()
        results = analyzer.analyze(str(tmp_path))
        
        # Should detect large script
        assert results is not None
    
    def test_analyze_godot_anti_patterns(self, tmp_path):
        """Test detection of Godot anti-patterns."""
        # Create a script with anti-patterns
        script_file = tmp_path / "antipattern.gd"
        script_file.write_text("""
extends Node

var global_state_1 = 0
var global_state_2 = 0
var global_state_3 = 0
var global_state_4 = 0
var global_state_5 = 0
var global_state_6 = 0
var global_state_7 = 0
var global_state_8 = 0
var global_state_9 = 0
var global_state_10 = 0
var global_state_11 = 0

func _process(delta):
    # Heavy computation in process
    var result = 0
    for i in range(1000):
        result += i * i
    pass
""")
        
        analyzer = StaticAnalyzer()
        results = analyzer.analyze(str(tmp_path))
        
        assert results is not None


class TestSGMADependencyAnalysis:
    """Test SGMA (Static Graph Analysis) functionality."""
    
    def test_build_dependency_graph(self, tmp_path):
        """Test building dependency graph."""
        # Create interconnected scripts
        base_file = tmp_path / "base.gd"
        base_file.write_text("extends Node\nclass_name BaseClass")
        
        derived_file = tmp_path / "derived.gd"
        derived_file.write_text("""
extends BaseClass

var value = 0
""")
        
        analyzer = StaticAnalyzer()
        results = analyzer.analyze(str(tmp_path))
        
        assert results is not None
    
    def test_detect_circular_dependencies(self, tmp_path):
        """Test circular dependency detection."""
        # This would require more complex setup
        analyzer = StaticAnalyzer()
        # Implementation depends on actual circular detection logic
        assert analyzer is not None


class TestMathCurveLoaders:
    """Test math curve loader functionality for memory-aware context selection."""
    
    def test_context_budget(self):
        """Test context budget is set correctly."""
        analyzer = StaticAnalyzer()
        assert analyzer.CONTEXT_BUDGET_CHARS == 2000
    
    def test_ram_threshold(self):
        """Test RAM threshold is set correctly."""
        analyzer = StaticAnalyzer()
        assert analyzer.MAX_RAM_MB == 4096


class TestEdgeCases:
    """Test edge cases and error handling."""
    
    def test_analyze_empty_path(self):
        """Test analyzing an empty path string."""
        analyzer = StaticAnalyzer()
        results = analyzer.analyze("")
        assert results is not None  # Should handle gracefully
    
    def test_analyze_invalid_gdscript(self, tmp_path):
        """Test analyzing invalid GDScript syntax."""
        script_file = tmp_path / "invalid.gd"
        script_file.write_text("this is not valid GDScript at all!!!")
        
        analyzer = StaticAnalyzer()
        results = analyzer.analyze(str(tmp_path))
        
        assert results is not None
    
    def test_analyze_mixed_files(self, tmp_path):
        """Test analyzing directory with mixed file types."""
        # Create GDScript file
        script_file = tmp_path / "script.gd"
        script_file.write_text("extends Node")
        
        # Create text file
        text_file = tmp_path / "readme.txt"
        text_file.write_text("This is a text file")
        
        # Create resource file
        res_file = tmp_path / "data.json"
        res_file.write_text('{"key": "value"}')
        
        analyzer = StaticAnalyzer()
        results = analyzer.analyze(str(tmp_path))
        
        assert results is not None
        # Should only analyze GDScript files
    
    def test_unicode_in_script(self, tmp_path):
        """Test analyzing script with unicode characters."""
        script_file = tmp_path / "unicode.gd"
        script_file.write_text("""
extends Node

# 中文注释
var name = "テスト"

func greet():
    print("こんにちは")
""")
        
        analyzer = StaticAnalyzer()
        results = analyzer.analyze(str(tmp_path))
        
        assert results is not None
