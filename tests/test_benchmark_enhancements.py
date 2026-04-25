"""
Benchmark Enhancement Tests for Ether
======================================

Tests all 12 benchmark categories to ensure Ether scores 93+.

Test coverage:
- Category 1: Instruction Following (15% weight)
- Category 2: Reasoning & Logic (12% weight)
- Category 3: Code Generation Quality (20% weight)
- Category 4: Debug & Root Cause Analysis (20% weight)
- Category 5: Context Retention (5% weight)
- Category 8: Hallucination Resistance (10% weight)
- Category 10: Output Format Consistency (3% weight)

Total weighted coverage: 85% of benchmark score
"""

import pytest
import asyncio
from core.benchmark_enhancer import (
    get_instruction_enforcer,
    get_reasoning_scaffold,
    get_code_validator,
    get_debug_analyzer,
    get_hallucination_guard,
    get_context_manager,
    InstructionFollowingEnforcer,
    ReasoningScaffold,
    CodeQualityValidator,
    DebugAnalyzer,
    HallucinationGuard,
    ContextRetentionManager
)


class TestInstructionFollowing:
    """Category 1: Instruction Following (15% of benchmark weight)"""
    
    def setup_method(self):
        self.enforcer = get_instruction_enforcer()
    
    def test_extract_line_limit_constraint(self):
        """Test extraction of line limit constraints"""
        query = "Write a function under 10 lines"
        constraints = self.enforcer.extract_constraints(query)
        
        assert constraints['line_limit'] == 10
        assert 'Max 10 lines' in constraints['raw_constraints']
    
    def test_extract_sentence_count_constraint(self):
        """Test extraction of sentence count constraints"""
        query = "Answer in exactly one sentence"
        constraints = self.enforcer.extract_constraints(query)
        
        assert constraints['sentence_count'] == 1
        assert 'Exactly 1 sentence(s)' in constraints['raw_constraints']
    
    def test_extract_item_count_constraint(self):
        """Test extraction of item count constraints"""
        query = "List 5 items, numbered"
        constraints = self.enforcer.extract_constraints(query)
        
        assert constraints['item_count'] == 5
        assert constraints['output_format'] == 'numbered_list'
    
    def test_extract_no_comments_constraint(self):
        """Test extraction of no comments constraint"""
        query = "Write code with no comments"
        constraints = self.enforcer.extract_constraints(query)
        
        assert constraints['no_comments'] is True
    
    def test_extract_no_explanation_constraint(self):
        """Test extraction of no explanation constraint"""
        query = "Only the function signature, no explanation"
        constraints = self.enforcer.extract_constraints(query)
        
        assert constraints['no_explanation'] is True
        assert constraints['signature_only'] is True
    
    def test_build_constraint_instruction(self):
        """Test building constraint instruction string"""
        constraints = {
            'line_limit': 10,
            'sentence_count': None,
            'item_count': None,
            'no_comments': True,
            'no_explanation': False,
            'output_format': None,
            'requires_static_typing': False,
            'signature_only': False,
            'raw_constraints': []
        }
        
        instruction = self.enforcer.build_constraint_instruction(constraints)
        
        assert 'CRITICAL' in instruction
        assert 'EXACTLY 10 lines' in instruction
        assert 'Do NOT include any comments' in instruction
    
    def test_validate_output_line_limit(self):
        """Test validation of line limit constraint"""
        constraints = {'line_limit': 5, 'sentence_count': None, 'item_count': None,
                      'no_comments': False, 'no_explanation': False, 
                      'output_format': None, 'requires_static_typing': False,
                      'signature_only': False, 'raw_constraints': []}
        
        # Valid output
        output = "line1\nline2\nline3"
        result = self.enforcer.validate_output(output, constraints)
        assert result['valid'] is True
        
        # Invalid output
        output = "line1\nline2\nline3\nline4\nline5\nline6"
        result = self.enforcer.validate_output(output, constraints)
        assert result['valid'] is False
        assert 'Line limit exceeded' in result['issues'][0]
    
    def test_validate_output_no_comments(self):
        """Test validation of no comments constraint"""
        constraints = {'line_limit': None, 'sentence_count': None, 'item_count': None,
                      'no_comments': True, 'no_explanation': False,
                      'output_format': None, 'requires_static_typing': False,
                      'signature_only': False, 'raw_constraints': []}
        
        # Invalid - has comments
        output = "var x = 5  # This is a comment"
        result = self.enforcer.validate_output(output, constraints)
        assert result['valid'] is False
        assert 'Comments detected' in result['issues'][0]
        
        # Valid - no comments
        output = "var x = 5"
        result = self.enforcer.validate_output(output, constraints)
        assert result['valid'] is True
    
    def test_multi_constraint_extraction(self):
        """Test extraction of multiple constraints from single query"""
        query = "Write a GDScript function, under 10 lines, no comments, using static typing"
        constraints = self.enforcer.extract_constraints(query)
        
        assert constraints['line_limit'] == 10
        assert constraints['no_comments'] is True
        assert constraints['requires_static_typing'] is True
        assert len(constraints['raw_constraints']) >= 3


class TestReasoningAndLogic:
    """Category 2: Reasoning & Logic (12% of benchmark weight)"""
    
    def setup_method(self):
        self.scaffold = get_reasoning_scaffold()
    
    def test_trace_execution_template(self):
        """Test trace execution reasoning template"""
        prompt = self.scaffold.build_reasoning_prompt(
            'trace_execution',
            initial_state="Node A active",
            action_1="A sends signal to B",
            state_after_1="Node B active",
            action_2="B sends signal to C",
            state_after_2="Node C active",
            conclusion="C fires",
            final_answer="Node C"
        )
        
        assert 'REASONING STEPS' in prompt
        assert 'Node A active' in prompt
        assert 'step-by-step' in prompt.lower()
    
    def test_math_in_context_template(self):
        """Test math reasoning template"""
        prompt = self.scaffold.build_reasoning_prompt(
            'math_in_context',
            fact_1="Game runs at 60fps",
            fact_2="Physics tick is 1/60s",
            fact_3="Move 5 units per tick",
            step_1="Calculate ticks per second: 60",
            step_2="Calculate total ticks in 2 seconds: 120",
            step_3="Calculate distance: 120 * 5 = 600",
            result="600 units"
        )
        
        assert 'STEP-BY-STEP CALCULATION' in prompt
        assert '600 units' in prompt
    
    def test_contradiction_detection_template(self):
        """Test contradiction detection template"""
        prompt = self.scaffold.build_reasoning_prompt(
            'contradiction_detection',
            obs_1="Code sets speed to 0",
            obs_2="Code immediately moves by speed",
            conflict="Movement will be zero despite move call",
            root_cause="Speed variable is zero",
            solution="Set speed before moving"
        )
        
        assert 'LOGICAL ANALYSIS' in prompt
        assert 'Conflict detected' in prompt
    
    def test_validate_logic_chain(self):
        """Test logic chain validation"""
        chain = ["Step 1: Initial state", "Step 2: Action taken", "Step 3: Result"]
        result = self.scaffold.validate_logic(chain)
        
        assert result['consistent'] is True
        assert len(result['gaps']) == 0
        
        # Too short chain
        short_chain = ["Just one step"]
        result = self.scaffold.validate_logic(short_chain)
        
        assert result['consistent'] is False
        assert 'missing intermediate steps' in result['gaps'][0]


class TestCodeGenerationQuality:
    """Category 3: Code Generation Quality (20% of benchmark weight)"""
    
    def setup_method(self):
        self.validator = get_code_validator('gdscript')
    
    def test_validate_syntax_balanced_parentheses(self):
        """Test syntax validation for balanced parentheses"""
        # Valid
        code = "func test():\n    var x = (1 + 2)"
        result = self.validator.validate_syntax(code)
        assert result['valid'] is True
        
        # Invalid
        code = "func test():\n    var x = (1 + 2"
        result = self.validator.validate_syntax(code)
        assert result['valid'] is False
        assert 'Mismatched parentheses' in result['issues'][0]
    
    def test_validate_syntax_balanced_brackets(self):
        """Test syntax validation for balanced brackets"""
        code = "var arr = [1, 2, 3]"
        result = self.validator.validate_syntax(code)
        assert result['valid'] is True
        
        code = "var arr = [1, 2, 3"
        result = self.validator.validate_syntax(code)
        assert result['valid'] is False
    
    def test_validate_singleton_pattern(self):
        """Test singleton pattern validation"""
        code = """
class_name GameManager
extends Node

static var instance: GameManager = null
"""
        result = self.validator.validate_pattern(code, 'singleton_gdscript')
        assert result is True
    
    def test_check_edge_cases_empty_input(self):
        """Test edge case detection for empty input handling"""
        code = """
func process(arr: Array) -> int:
    if arr.is_empty():
        return 0
    return arr.size()
"""
        requirements = {}
        result = self.validator.check_edge_cases(code, requirements)
        
        assert 'empty_input' in result['handled']
    
    def test_check_edge_cases_null_handling(self):
        """Test edge case detection for null handling"""
        code = """
func get_value(obj: Object) -> Variant:
    if obj == null:
        return null
    return obj.value
"""
        requirements = {}
        result = self.validator.check_edge_cases(code, requirements)
        
        assert 'null_handling' in result['handled']


class TestDebugAnalysis:
    """Category 4: Debug & Root Cause Analysis (20% of benchmark weight)"""
    
    def setup_method(self):
        self.analyzer = get_debug_analyzer()
    
    def test_identify_null_reference_strategy(self):
        """Test identification of null reference bugs"""
        query = "I'm getting an error: Invalid get index on null"
        result = self.analyzer.analyze_debug_query(query)
        
        assert result['strategy'] == 'null_reference'
        assert result['confidence'] > 0
    
    def test_identify_off_by_one_strategy(self):
        """Test identification of off-by-one errors"""
        query = "Index out of range error in my for loop"
        result = self.analyzer.analyze_debug_query(query)
        
        assert result['strategy'] == 'off_by_one'
    
    def test_identify_signal_mismatch_strategy(self):
        """Test identification of signal mismatch bugs"""
        query = "Signal connect failed, wrong number of arguments"
        result = self.analyzer.analyze_debug_query(query)
        
        assert result['strategy'] == 'signal_mismatch'
    
    def test_identify_delta_bug_strategy(self):
        """Test identification of delta multiplication bugs"""
        query = "My character moves faster at higher frame rates in _process"
        result = self.analyzer.analyze_debug_query(query)
        
        assert result['strategy'] == 'delta_bug'
    
    def test_generate_specific_fix_null_reference(self):
        """Test generation of line-specific fix for null reference"""
        code = """
var player: Player = null

func _ready():
    player.health = 100  # Line 4 - crash here
"""
        fix = self.analyzer.generate_specific_fix('null_reference', code, 4)
        
        assert 'Null reference' in fix
        assert 'line 4' in fix.lower() or 'Line 4' in fix
        assert 'Fix:' in fix
    
    def test_generate_specific_fix_off_by_one(self):
        """Test generation of line-specific fix for off-by-one error"""
        code = """
for i in range(10):
    print(arr[i])  # Accesses index 9, but what if arr has 9 elements?
"""
        fix = self.analyzer.generate_specific_fix('off_by_one', code, 2)
        
        assert 'Off-by-one' in fix
        assert 'line 2' in fix.lower() or 'Line 2' in fix


class TestHallucinationResistance:
    """Category 8: Hallucination Resistance (10% of benchmark weight)"""
    
    def setup_method(self):
        self.guard = get_hallucination_guard()
    
    def test_detect_invented_node_names(self):
        """Test detection of invented Godot node names"""
        response = "Use the PhysicsInterpolator3D node for smooth movement"
        result = self.guard.check_confidence("", response)
        
        assert result['likely_hallucinated'] is True
        assert len(result['invented_terms']) > 0
    
    def test_detect_old_godot_version_references(self):
        """Test detection of outdated Godot 3.x references"""
        response = "Use KinematicBody for character movement"
        result = self.guard.check_confidence("", response)
        
        assert result['likely_hallucinated'] is True
    
    def test_accept_valid_response(self):
        """Test acceptance of valid response"""
        response = "Use CharacterBody3D for character movement in Godot 4"
        result = self.guard.check_confidence("", response)
        
        assert result['likely_hallucinated'] is False
        assert result['recommendation'] == 'accept'
    
    def test_build_verification_prompt(self):
        """Test verification prompt generation"""
        prompt = self.guard.build_verification_prompt("How do I use the FooBar node?")
        
        assert 'not certain' in prompt.lower()
        assert 'Do NOT invent' in prompt


class TestContextRetention:
    """Category 5: Context Retention (5% of benchmark weight)"""
    
    def setup_method(self):
        self.manager = get_context_manager(max_history=20)
    
    def test_extract_numeric_facts(self):
        """Test extraction of numeric facts from conversation"""
        messages = [
            {'role': 'user', 'content': 'My player has 100 HP and takes 15 damage per hit'},
            {'role': 'assistant', 'content': 'That means they can take 6 hits before dying.'}
        ]
        
        facts = self.manager.extract_key_facts(messages)
        
        assert len(facts) > 0
        assert any('100' in f.get('numbers', []) for f in facts)
        assert any('15' in f.get('numbers', []) for f in facts)
    
    def test_optimize_context_window(self):
        """Test context window optimization"""
        # Create history longer than max
        history = [{'role': 'user', 'content': f'Message {i}'} for i in range(25)]
        current_query = "What was my HP?"
        
        optimized = self.manager.optimize_context_window(history, current_query)
        
        # Should be reduced but retain key info
        assert len(optimized) <= 22  # max_history + some buffer
        assert len(optimized) < len(history)
    
    def test_preserve_key_facts_in_optimization(self):
        """Test that key facts are preserved during optimization"""
        history = [
            {'role': 'user', 'content': 'My player has 100 HP'},
        ] + [{'role': 'user', 'content': f'Filler message {i}'} for i in range(25)]
        
        optimized = self.manager.optimize_context_window(history, "Question")
        
        # First message should be preserved as key fact
        assert len(optimized) > 0
        # Check if fact summary was added
        has_summary = any('KEY CONTEXT' in str(msg) for msg in optimized)
        assert has_summary


class TestOutputFormatConsistency:
    """Category 10: Output Format Consistency (3% of benchmark weight)"""
    
    def setup_method(self):
        self.enforcer = get_instruction_enforcer()
    
    def test_json_format_constraint(self):
        """Test JSON format constraint extraction"""
        query = "Return the result as JSON"
        constraints = self.enforcer.extract_constraints(query)
        
        assert constraints['output_format'] == 'json'
    
    def test_numbered_list_format_constraint(self):
        """Test numbered list format constraint extraction"""
        query = "Give me a numbered list of items"
        constraints = self.enforcer.extract_constraints(query)
        
        assert constraints['output_format'] == 'numbered_list'
    
    def test_validate_numbered_list_output(self):
        """Test validation of numbered list output"""
        constraints = {'line_limit': None, 'sentence_count': None, 'item_count': 3,
                      'no_comments': False, 'no_explanation': False,
                      'output_format': 'numbered_list', 'requires_static_typing': False,
                      'signature_only': False, 'raw_constraints': []}
        
        # Valid numbered list
        output = "1. First item\n2. Second item\n3. Third item"
        result = self.enforcer.validate_output(output, constraints)
        assert result['valid'] is True
        
        # Invalid - wrong count
        output = "1. First item\n2. Second item"
        result = self.enforcer.validate_output(output, constraints)
        assert result['valid'] is False


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
