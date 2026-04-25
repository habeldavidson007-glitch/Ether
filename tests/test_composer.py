"""
Test suite for the Compositional Architecture (Musical Measure Engine)

Tests verify:
- 176 measures are properly initialized
- Measures are numbered and containerized
- Stochastic selection produces unique compositions
- Harmonic compatibility checking works
- 16-bar structure is maintained
- Integration with Cortex works correctly
"""

import pytest
import asyncio
from personality.composer import (
    Conductor, MeasureLibrary, Measure, MeasureType, 
    DiceEngine, Bar, Score, CompositionalCortex,
    get_composer
)


class TestMeasureLibrary:
    """Test the 176-measure library"""
    
    def test_library_initialization(self):
        """Test that library initializes with 176 measures"""
        library = MeasureLibrary()
        library.initialize_default_measures()
        
        assert library.total_measures == 176
        assert len(library.by_type) == 12  # 12 measure types
    
    def test_measure_numbering(self):
        """Test that all measures are numbered 1-176"""
        library = MeasureLibrary()
        library.initialize_default_measures()
        
        measure_ids = set(library.measures.keys())
        expected_ids = set(range(1, 177))
        
        assert measure_ids == expected_ids
    
    def test_measures_by_type(self):
        """Test measures are organized by type"""
        library = MeasureLibrary()
        library.initialize_default_measures()
        
        # Check each type has measures
        assert len(library.get_by_type(MeasureType.OPENING)) == 12
        assert len(library.get_by_type(MeasureType.CONTEXT_GATHER)) == 12
        assert len(library.get_by_type(MeasureType.ANALYSIS)) == 24
        assert len(library.get_by_type(MeasureType.SOLUTION)) == 24
        assert len(library.get_by_type(MeasureType.EXAMPLE)) == 24
        assert len(library.get_by_type(MeasureType.EXPLANATION)) == 24
        assert len(library.get_by_type(MeasureType.VALIDATION)) == 16
        assert len(library.get_by_type(MeasureType.EXPANSION)) == 16
        assert len(library.get_by_type(MeasureType.CAVEAT)) == 8
        assert len(library.get_by_type(MeasureType.SUMMARY)) == 8
        assert len(library.get_by_type(MeasureType.FOLLOWUP)) == 6
        assert len(library.get_by_type(MeasureType.CLOSING)) == 2
    
    def test_measure_properties(self):
        """Test individual measure properties"""
        library = MeasureLibrary()
        library.initialize_default_measures()
        
        measure = library.get(1)
        assert measure.id == 1
        assert measure.type == MeasureType.OPENING
        assert callable(measure.function)
        assert isinstance(measure.harmony_rules, list)
        assert measure.weight > 0


class TestDiceEngine:
    """Test stochastic measure selection"""
    
    def test_seed_from_query(self):
        """Test that query generates deterministic seed"""
        dice = DiceEngine()
        
        seed1 = dice.seed_from_query("test query", {})
        seed2 = dice.seed_from_query("test query", {})
        
        # Same query should produce similar seeds (with small variation)
        assert abs(seed1 - seed2) < 2000  # ±10% variation max
    
    def test_different_queries_different_seeds(self):
        """Test that different queries produce different seeds"""
        dice = DiceEngine()
        
        seed1 = dice.seed_from_query("query one", {})
        seed2 = dice.seed_from_query("query two", {})
        
        assert seed1 != seed2
    
    def test_roll_selects_measure(self):
        """Test that dice roll selects a measure"""
        library = MeasureLibrary()
        library.initialize_default_measures()
        
        dice = DiceEngine()
        candidates = library.get_by_type(MeasureType.OPENING)
        
        selected = dice.roll(candidates)
        
        assert selected in candidates
        assert isinstance(selected, Measure)
    
    def test_harmonic_compatibility_filtering(self):
        """Test that incompatible measures are filtered"""
        library = MeasureLibrary()
        library.initialize_default_measures()
        
        dice = DiceEngine()
        
        # Get opening measures
        openings = library.get_by_type(MeasureType.OPENING)
        previous = openings[0]
        
        # Try to roll for context (should be compatible)
        contexts = library.get_by_type(MeasureType.CONTEXT_GATHER)
        selected = dice.roll(contexts, previous)
        
        assert selected in contexts


class TestScoreComposition:
    """Test 16-bar score composition"""
    
    @pytest.mark.asyncio
    async def test_complete_composition(self):
        """Test that conductor creates complete 16-bar compositions"""
        conductor = Conductor()
        
        score = await conductor.compose("How do I create a player controller?")
        
        assert score.is_complete
        assert len(score.bars) == 16
        assert score.completion_ratio == 1.0
    
    @pytest.mark.asyncio
    async def test_unique_compositions(self):
        """Test that same query produces different compositions"""
        conductor = Conductor()
        
        score1 = await conductor.compose("Explain Godot signals")
        score2 = await conductor.compose("Explain Godot signals")
        
        seq1 = score1.get_metadata()['measure_sequence']
        seq2 = score2.get_metadata()['measure_sequence']
        
        # Should be different due to stochastic selection
        assert seq1 != seq2
        assert len(seq1) == 16
        assert len(seq2) == 16
    
    @pytest.mark.asyncio
    async def test_score_content_extraction(self):
        """Test that content can be extracted from score"""
        conductor = Conductor()
        
        score = await conductor.compose("What is a node in Godot?")
        
        content = score.get_content()
        metadata = score.get_metadata()
        
        assert isinstance(content, str)
        assert len(content) > 0
        assert 'measure_sequence' in metadata
        assert 'query_hash' in metadata
    
    @pytest.mark.asyncio
    async def test_bar_structure(self):
        """Test that bars have correct structure"""
        conductor = Conductor()
        
        score = await conductor.compose("Test query")
        
        for i, bar in enumerate(score.bars):
            assert bar.position == i
            assert isinstance(bar.measure, Measure)
            assert isinstance(bar.result, dict)
            assert 'measure_id' in bar.result


class TestCompositionalCortex:
    """Test integration with Cortex"""
    
    def test_compositional_cortex_initialization(self):
        """Test compositional cortex wrapper"""
        cc = CompositionalCortex()
        
        assert cc.conductor is not None
        assert cc.library.total_measures == 176
    
    @pytest.mark.asyncio
    async def test_generate_response(self):
        """Test response generation via compositional cortex"""
        cc = CompositionalCortex()
        
        result = await cc.generate_response("How do I optimize my game?")
        
        assert 'text' in result
        assert 'metadata' in result
        assert 'composition' in result
        assert result['stats']['harmonic_validity'] == True
    
    def test_measure_library_info(self):
        """Test getting library information"""
        cc = CompositionalCortex()
        
        info = cc.get_measure_library_info()
        
        assert info['total_measures'] == 176
        assert 'by_type' in info
        assert info['architecture'] == '16-bar compositional structure'


class TestIntegrationWithCortex:
    """Test integration with main Cortex class"""
    
    @pytest.mark.asyncio
    async def test_cortex_with_composer_enabled(self):
        """Test Cortex with composer enabled"""
        from core.cortex import Cortex
        
        cortex = Cortex(enable_watchdog=False, enable_composer=True)
        
        assert cortex.enable_composer == True
        assert cortex._composer is not None
    
    @pytest.mark.asyncio
    async def test_cortex_compositional_pipeline(self):
        """Test compositional pipeline in Cortex"""
        from core.cortex import Cortex
        
        cortex = Cortex(enable_watchdog=False, enable_composer=True)
        
        result, log = await cortex.process_query_compositional(
            "Create a simple GDScript function"
        )
        
        assert result['type'] == 'compositional'
        assert result['architecture'] == 'musical_measure_176'
        assert result['bars_composed'] == 16
        assert 'composition' in result
        assert result['composition']['harmonic_validity'] == True
    
    @pytest.mark.asyncio
    async def test_cortex_fallback_when_composer_disabled(self):
        """Test fallback to standard pipeline when composer disabled"""
        from core.cortex import Cortex
        
        cortex = Cortex(enable_watchdog=False, enable_composer=False)
        
        result, log = await cortex.process_query_compositional(
            "Test query"
        )
        
        # Should fall back to standard pipeline (check for warning or standard result type)
        # The fallback happens silently, so we check that it doesn't crash and returns valid result
        assert result is not None
        assert 'text' in result or 'type' in result


class TestCombinationCount:
    """Test theoretical combination calculations"""
    
    def test_combination_count_calculation(self):
        """Test that combination count is calculated correctly"""
        conductor = Conductor()
        
        count = conductor.get_combination_count()
        
        # Should be in trillions
        assert count > 1e12  # More than 1 trillion
        assert count < 1e18  # Less than 1 quadrillion
    
    def test_trillion_claim_verification(self):
        """Verify the 39+ trillion claim"""
        conductor = Conductor()
        
        count = conductor.get_combination_count()
        trillions = count / 1e12
        
        # The claim is "39+ trillion"
        assert trillions > 39, f"Expected >39 trillion, got {trillions:.1f} trillion"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
