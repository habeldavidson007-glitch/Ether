from .context_manager import EtherSession, classify, is_casual, recall, remember, ContextChunker, smart_load_context
from .scanner import build_project_map, extract_zip, select_context
from .safety import preview_changes, apply_changes
from .ether_engine import EtherEngine, create_engine
from .dependency_graph import DependencyGraph, create_dependency_graph
from .godot_validator import GodotValidator, create_validator
from .scene_graph_analyzer import SceneGraphAnalyzer, create_scene_analyzer
from .code_fixer import CodeFixer, apply_fixes, fix_file
from .gdscript_ast import GDScriptAST, SurgicalSplicer, CodeNode, NodeType
from .unified_search import get_unified_search
from .librarian import get_librarian
from .writer import get_writer
from .safety_preview import get_safety_preview


def run_pipeline(*args, **kwargs):
    """Lazy-imported run_pipeline to avoid importing heavy runtime deps at package import time."""
    from .cortex import run_pipeline as _run_pipeline
    return _run_pipeline(*args, **kwargs)


def get_adaptive_memory(*args, **kwargs):
    """Lazy-imported adaptive memory getter to avoid optional runtime deps during test collection."""
    from .adaptive_memory import get_adaptive_memory as _get_adaptive_memory
    return _get_adaptive_memory(*args, **kwargs)


def get_feedback_manager(*args, **kwargs):
    """Lazy-imported feedback manager to avoid optional runtime deps during test collection."""
    from .feedback_commands import get_feedback_manager as _get_feedback_manager
    return _get_feedback_manager(*args, **kwargs)

__all__ = [
    'EtherSession', 'classify', 'is_casual', 'recall', 'remember', 'ContextChunker', 'smart_load_context',
    'build_project_map', 'extract_zip', 'select_context',
    'run_pipeline',
    'preview_changes', 'apply_changes',
    'EtherEngine', 'create_engine',
    'DependencyGraph', 'create_dependency_graph',
    'GodotValidator', 'create_validator',
    'SceneGraphAnalyzer', 'create_scene_analyzer',
    'CodeFixer', 'apply_fixes', 'fix_file',
    'GDScriptAST', 'SurgicalSplicer', 'CodeNode', 'NodeType',
    'get_unified_search', 'get_adaptive_memory',
    # Legacy compatibility
    'get_librarian', 'get_writer',
]
