from .context_manager import EtherSession, classify, is_casual, recall, remember, ContextChunker, smart_load_context
from .scanner import build_project_map, extract_zip, select_context
from .builder import run_pipeline
from .safety import preview_changes, apply_changes
from .ether_engine import EtherEngine, create_engine
from .dependency_graph import DependencyGraph, create_dependency_graph
from .godot_validator import GodotValidator, create_validator
from .scene_graph_analyzer import SceneGraphAnalyzer, create_scene_analyzer
from .code_fixer import CodeFixer, apply_fixes, fix_file
from .gdscript_ast import GDScriptAST, SurgicalSplicer, CodeNode, NodeType
from .memory_core import MemoryCore, create_memory_core
from .cascade_scanner import CascadeScanner, create_cascade_scanner, CascadeReport, CascadeWarning
from .godot_expert import GodotExpert, SemanticSceneEditor
from .librarian import get_librarian
from .writer import get_writer
from .learning_engine import get_learning_engine
from .compressed_search import get_compressed_search
from .structural_rag import get_structural_index

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
    'MemoryCore', 'create_memory_core',
    'CascadeScanner', 'create_cascade_scanner', 'CascadeReport', 'CascadeWarning',
    'GodotExpert', 'SemanticSceneEditor',
    # New modules
    'get_librarian', 'get_writer',
    'get_learning_engine',
    'get_compressed_search',
    'get_structural_index',
]
