from .context_manager import EtherSession, classify, is_casual, recall, remember, ContextChunker, smart_load_context
from utils.project_scanner import build_project_map, extract_zip, select_context
from .cortex import run_pipeline
from .safety import preview_changes, apply_changes
from .ether_engine import EtherEngine, create_engine
from .dependency_graph import DependencyGraph, create_dependency_graph
from .code_fixer import CodeFixer, apply_fixes, fix_file
from ether.godot.gdscript_analyzer import GDScriptAnalyzer, Finding, ScriptNode, analyze_gdscript
from .unified_search import get_unified_search
from .adaptive_memory import get_adaptive_memory
from .librarian import get_librarian
from .writer import get_writer
from .safety_preview import get_safety_preview
from .feedback_commands import get_feedback_manager

__all__ = [
    'EtherSession', 'classify', 'is_casual', 'recall', 'remember', 'ContextChunker', 'smart_load_context',
    'build_project_map', 'extract_zip', 'select_context',
    'run_pipeline',
    'preview_changes', 'apply_changes',
    'EtherEngine', 'create_engine',
    'DependencyGraph', 'create_dependency_graph',
    'CodeFixer', 'apply_fixes', 'fix_file',
    'GDScriptAnalyzer', 'Finding', 'ScriptNode', 'analyze_gdscript',
    'get_unified_search', 'get_adaptive_memory',
    # Legacy compatibility
    'get_librarian', 'get_writer',
]
