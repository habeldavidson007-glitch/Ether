"""
Ether v1.9 — Godot AI Development Assistant (CLI Edition)
==========================================================
Full local mode: No Streamlit, no browser, pure terminal interface.
OPTIMIZATIONS:
1. Intent-Aware Routing: Greetings respond instantly via fast path
2. Lazy Loading: Project files loaded on-demand, not all at once
3. Cached Intelligence: Repeated queries return instantly from cache
4. RAG-Enhanced Context: Semantic search retrieves relevant code snippets
5. Lightweight Model: qwen2.5-coder:1.5b-instruct-q4_k_m (~1.2GB)
6. CLI Native: Zero web framework overhead, minimal memory footprint
7. HYBRID STATIC ANALYSIS: Instant GDScript anti-pattern detection (no LLM)
8. SGMA INTEGRATION: Static Graph Analysis for dependency mapping
9. ULTRA-LIGHT CONTEXT: 300 char limit for 2GB RAM systems

Run: python ether_cli.py
Requires: ollama serve && ollama pull qwen2.5-coder:1.5b-instruct-q4_k_m
"""

import sys
import json
import time
from pathlib import Path
from typing import Dict, List, Any, Optional

# Import EtherBrain from core.builder
from core.builder import EtherBrain


class EtherCLI:
    """Command-line interface for Ether."""
    
    def __init__(self):
        self.brain = EtherBrain()
        self.running = True
        self.project_path: Optional[str] = None
        self.last_optimized_code: Optional[str] = None  # Store last optimized code
        self.last_optimized_file_path: Optional[str] = None  # Store path of last optimized file
        
        # Welcome message
        print("\n" + "=" * 70)
        print("  ◈ ETHER v1.9 CLI — Godot AI Development Assistant")
        print("=" * 70)
        print("\n  Local • Private • Advanced Code Analysis")
        print("  Model: qwen2.5-coder:1.5b-instruct-q4_k_m (~1.2GB quantized)")
        print("  Fallback: gemma:2b (auto-switch on timeout)")
        print("\n  ⚡ NEW: Hybrid Static Analysis + SGMA + Smart Context Loader!")
        print("  🧠 Optimized for 2GB RAM - Adaptive context (300-600 chars)")
        print("\n  Commands:")
        print("    /load <path>   — Load Godot project folder")
        print("    /status        — Show project stats")
        print("    /mode <name>   — Switch mode (coding/general/mixed)")
        print("    /clear         — Clear chat history")
        print("    /save [path]   — Save last optimized code to file")
        print("    /help          — Show this help")
        print("    /quit          — Exit Ether")
        print("\n  ⚡ Auto-Save: Optimized code is automatically saved to the original file!")
        print("\n  Just type your question to chat with Ether!")
        print("-" * 70 + "\n")
    
    def load_project(self, path: str) -> bool:
        """Load a Godot project from directory."""
        # Remove quotes if present
        path = path.strip('"').strip("'")
        project_dir = Path(path).expanduser().resolve()
        
        if not project_dir.exists():
            print(f"❌ Error: Directory '{path}' does not exist.")
            return False
        
        if not project_dir.is_dir():
            print(f"❌ Error: '{path}' is not a directory.")
            return False
        
        # Check for Godot project file
        project_file = project_dir / "project.godot"
        if not project_file.exists():
            print(f"⚠ Warning: No 'project.godot' found. This might not be a Godot project.")
        
        # Use LazyProjectLoader (the only available loader)
        try:
            from utils.project_loader import LazyProjectLoader
            
            loader = LazyProjectLoader()
            success, msg = loader.load_from_folder(project_dir)
            
            if success:
                self.brain.project_loader = loader
                self.brain.project_stats = loader.get_stats()
                self.project_path = str(project_dir.absolute())
                
                stats = self.brain.project_stats
                print(f"\n✓ Project loaded: {stats['script_count']} scripts, {stats['scene_count']} scenes")
                print(f"  Path: {self.project_path}")
                print(f"  (Lazy loaded - files read on demand)\n")
                
                return True
            else:
                print(f"❌ Error loading project: {msg}")
                return False
                    
        except Exception as e:
            print(f"❌ Error loading project: {e}")
            import traceback
            traceback.print_exc()
            return False
    
    def show_status(self):
        """Display current project status."""
        stats = self.brain.project_stats
        
        if not stats or stats.get('total_files', 0) == 0:
            print("\n📊 No project loaded.")
            print("  Use /load <path> to load a Godot project.\n")
            return
        
        print("\n📊 Project Status:")
        print(f"  📁 Scripts:     {stats.get('script_count', 0)}")
        print(f"  🎬 Scenes:      {stats.get('scene_count', 0)}")
        print(f"  📦 Resources:   {stats.get('resource_count', 0)}")
        print(f"  📄 Total Files: {stats.get('total_files', 0)}")
        print(f"  💾 Loaded:      {stats.get('loaded_files', 0)} (lazy)")
        print(f"  🧠 Mode:        {self.brain.chat_mode}")
        
        cache_stats = self.brain.get_cache_stats()
        if cache_stats:
            print(f"  🗃 Cache:       {cache_stats.get('entries', 0)} entries")
        
        print()
    
    def show_help(self):
        """Display help information."""
        print("\n" + "-" * 70)
        print("ETHER CLI HELP")
        print("-" * 70)
        print("""
  COMMANDS:
    /load <path>      Load a Godot project directory
    /status           Show current project statistics
    /mode <name>      Switch chat mode: coding, general, or mixed
    /clear            Clear chat history and cache
    /help             Show this help message
    /quit             Exit Ether
  
  CHAT MODES:
    coding   — Focus on code, GDScript, technical implementation
    general  — Game design, architecture, high-level guidance
    mixed    — Adaptive: balances code and explanation
  
  EXAMPLES:
    /load C:/Users/Name/GodotProjects/MyGame
    /mode coding
    How do I implement player movement?
    What's the best way to structure my game states?
  
  TIPS:
    • Be specific about what you need
    • Mention file names for targeted analysis
    • Use /mode to switch between coding and design focus
""")
        print("-" * 70 + "\n")
    
    def process_command(self, line: str) -> bool:
        """Process CLI commands starting with /. Returns True if should continue."""
        parts = line.strip().split(maxsplit=1)
        cmd = parts[0].lower()
        arg = parts[1] if len(parts) > 1 else ""
        
        if cmd in ['/quit', '/exit', '/q']:
            self.running = False
            print("\n  Goodbye! Happy coding! 🎮\n")
            return False
        
        elif cmd == '/load':
            if not arg:
                print("❌ Usage: /load <path_to_godot_project>")
            else:
                self.load_project(arg)
        
        elif cmd == '/status':
            self.show_status()
        
        elif cmd == '/mode':
            if not arg:
                print(f"Current mode: {self.brain.chat_mode}")
                print("Usage: /mode <coding|general|mixed>")
            else:
                valid_modes = ['coding', 'general', 'mixed']
                if arg.lower() in valid_modes:
                    self.brain.set_chat_mode(arg.lower())
                    print(f"✓ Mode switched to: {arg.upper()}")
                else:
                    print(f"❌ Invalid mode. Choose from: {', '.join(valid_modes)}")
        
        elif cmd == '/clear':
            self.brain.history.clear()
            if hasattr(self.brain, 'cache') and hasattr(self.brain.cache, 'clear'):
                self.brain.cache.clear()
            print("✓ Chat history and cache cleared.\n")
        
        elif cmd == '/save':
            if self.last_optimized_code:
                # Default to last optimized file path if available, otherwise use generic name
                save_path = arg if arg else self.last_optimized_file_path or "optimized_code.gd"
                try:
                    with open(save_path, 'w', encoding='utf-8') as f:
                        f.write(self.last_optimized_code)
                    print(f"✓ Code saved to: {save_path}\n")
                except Exception as e:
                    print(f"❌ Error saving file: {e}\n")
            else:
                print("❌ No optimized code to save. Run 'optimize <file>' first.\n")
        
        elif cmd == '/help':
            self.show_help()
        
        else:
            print(f"❌ Unknown command: {cmd}")
            print("Type /help for available commands.\n")
        
        return True
    
    def chat(self, query: str):
        """Send query to Ether and display response with change summary."""
        start_time = time.time()
        
        # Get response from brain using process_query
        result, log = self.brain.process_query(query)
        
        elapsed = time.time() - start_time
        
        # Display response header
        print(f"\n{'ETHER':<10} [{elapsed:.1f}s]")
        print("-" * 60)
        
        # Extract text from result with safe fallback
        if isinstance(result, str):
            response = result
        else:
            response = result.get("text") or result.get("summary") or result.get("root_cause") or "No response generated."
        
        # Check if this is an optimization result (contains full code)
        # handle_optimize stores code in brain.last_optimized_code directly
        if hasattr(self.brain, 'last_optimized_code') and self.brain.last_optimized_code:
            self.last_optimized_code = self.brain.last_optimized_code
        if hasattr(self.brain, 'last_optimized_file_path') and self.brain.last_optimized_file_path:
            self.last_optimized_file_path = self.brain.last_optimized_file_path
        
        # If this is a build/debug response, show change summary first
        if isinstance(result, dict) and (result.get("type") == "build" or result.get("type") == "debug"):
            changes = result.get("changes", [])
            if changes:
                print("\n📝 Changes Made:")
                for change in changes[:5]:  # Show up to 5 changes
                    file_path = change.get("file", "unknown.gd")
                    action = change.get("action", "modify")
                    
                    # Analyze content for line changes (simple heuristic)
                    content = change.get("content", "")
                    if content:
                        lines = content.split('\n')
                        added = sum(1 for l in lines if l.strip() and not l.strip().startswith('#'))
                        print(f"   • {file_path}: {action} ({added}+ lines)")
                    else:
                        print(f"   • {file_path}: {action}")
                
                if len(changes) > 5:
                    print(f"   ... and {len(changes) - 5} more files")
                print()
        
        # Display full response
        lines = str(response).split('\n')
        for i, line in enumerate(lines):
            if i > 0 and i % 20 == 0:
                # Pause for very long responses
                time.sleep(0.1)
            print(line)
        
        # Add to history
        self.brain.history.append({"role": "user", "content": query})
        self.brain.history.append({"role": "assistant", "content": response})
        
        print()
    
    def run(self):
        """Main CLI loop."""
        while self.running:
            try:
                # Get user input
                mode_indicator = f"[{self.brain.chat_mode.upper()}]"
                project_indicator = f"📁 {Path(self.project_path).name}" if self.project_path else "📁 (no project)"
                
                prompt = f"\nYOU {mode_indicator} {project_indicator}\n> "
                
                try:
                    line = input(prompt)
                except EOFError:
                    # Handle Ctrl+D
                    print("\n\n  Goodbye!\n")
                    break
                
                line = line.strip()
                
                if not line:
                    continue
                
                # Check if it's a command
                if line.startswith('/'):
                    self.process_command(line)
                    continue
                
                # Regular chat message
                self.chat(line)
                
            except KeyboardInterrupt:
                # Handle Ctrl+C
                print("\n\nInterrupted. Type /quit to exit.\n")
                continue
            
            except Exception as e:
                print(f"\n❌ Error: {e}\n")
                continue
        
        sys.exit(0)


def main():
    """Entry point."""
    cli = EtherCLI()
    cli.run()


if __name__ == "__main__":
    main()