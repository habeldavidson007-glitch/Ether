# Ether Core Module - Consolidated Exports
# All functionality merged into unified modules

from .cortex import run_pipeline, Cortex, get_cortex
from .safety import preview_changes, apply_changes
from .ether_engine import EtherEngine, create_engine
from .dependency_graph import DependencyGraph, create_dependency_graph
from .scene_graph_analyzer import SceneGraphAnalyzer, create_scene_analyzer
from .code_fixer import CodeFixer, apply_fixes, fix_file
from .unified_search import get_unified_search, UnifiedSearchEngine
from .adaptive_memory import get_adaptive_memory, AdaptiveMemory
from .writer import get_writer
from .safety_preview import get_safety_preview
from .feedback_commands import get_feedback_manager

__all__ = [
    'run_pipeline', 'Cortex', 'get_cortex',
    'preview_changes', 'apply_changes',
    'EtherEngine', 'create_engine',
    'DependencyGraph', 'create_dependency_graph',
    'SceneGraphAnalyzer', 'create_scene_analyzer',
    'CodeFixer', 'apply_fixes', 'fix_file',
    'get_unified_search', 'UnifiedSearchEngine',
    'get_adaptive_memory', 'AdaptiveMemory',
    'get_writer',
    'get_safety_preview',
    'get_feedback_manager',
]
