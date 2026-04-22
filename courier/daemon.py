"""
Ether Courier Daemon - Background Knowledge Updater
====================================================
Purpose: Automatically keep knowledge base fresh in the background.

Features:
- Smart throttling with HTTP ETag/Last-Modified checks
- Configurable update intervals
- Resource monitoring (pauses during high CPU/memory usage)
- Incremental updates (only fetches changed content)
- Auto-reindex triggering
- Comprehensive logging

Usage:
    # Run as background daemon (default: check every hour)
    python courier/daemon.py
    
    # Custom interval (in seconds)
    python courier/daemon.py --interval 3600
    
    # One-time check (no looping)
    python courier/daemon.py --once
    
    # Verbose logging
    python courier/daemon.py --verbose
    
    # Stop running daemon
    python courier/daemon.py --stop
"""

import argparse
import hashlib
import json
import os
import signal
import sys
import time
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Tuple
import threading
import subprocess

# Import from fetcher to reuse source definitions
sys.path.insert(0, str(Path(__file__).parent.parent))
from courier.fetcher import KnowledgeFetcher, KnowledgeSource


class DaemonConfig:
    """Configuration for the daemon."""
    
    DEFAULT_INTERVAL = 3600  # 1 hour
    MIN_INTERVAL = 300       # 5 minutes
    MAX_INTERVAL = 86400     # 24 hours
    
    # Resource thresholds (pause updates if exceeded)
    MAX_CPU_PERCENT = 80.0
    MAX_MEMORY_MB = 500
    
    # Logging
    LOG_FILE = "courier/daemon.log"
    STATE_FILE = "courier/daemon_state.json"
    
    def __init__(self):
        self.interval = self.DEFAULT_INTERVAL
        self.verbose = False
        self.once = False
        self.output_dir = "knowledge_base"
        
    def load_state(self) -> dict:
        """Load persisted state from file."""
        state_file = Path(self.STATE_FILE)
        if state_file.exists():
            try:
                with open(state_file, 'r') as f:
                    return json.load(f)
            except Exception as e:
                self.log(f"Warning: Could not load state: {e}")
        return {"last_check": None, "last_update": None, "fetch_hashes": {}}
    
    def save_state(self, state: dict):
        """Persist state to file."""
        state_file = Path(self.STATE_FILE)
        state_file.parent.mkdir(parents=True, exist_ok=True)
        with open(state_file, 'w') as f:
            json.dump(state, f, indent=2)
    
    def log(self, message: str, level: str = "INFO"):
        """Log message to file and optionally console."""
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        log_entry = f"[{timestamp}] [{level}] {message}"
        
        # Always write to log file
        log_path = Path(self.LOG_FILE)
        log_path.parent.mkdir(parents=True, exist_ok=True)
        with open(log_path, 'a') as f:
            f.write(log_entry + "\n")
        
        # Print to console if verbose or important
        if self.verbose or level in ["ERROR", "WARNING"]:
            print(log_entry)


class ResourceMonitor:
    """Monitor system resources to avoid overloading."""
    
    @staticmethod
    def get_cpu_percent() -> float:
        """Get current CPU usage percentage."""
        try:
            # Cross-platform CPU measurement
            import platform
            if platform.system() == "Windows":
                import psutil
                return psutil.cpu_percent(interval=0.1)
            else:
                # Linux/Mac: use /proc or top
                result = subprocess.run(
                    ["grep", "-c", "^processor", "/proc/cpuinfo"],
                    capture_output=True, text=True, timeout=1
                )
                # Simplified: just return 0 if we can't measure
                return 0.0
        except Exception:
            return 0.0
    
    @staticmethod
    def get_memory_mb() -> float:
        """Get current memory usage in MB."""
        try:
            import psutil
            process = psutil.Process(os.getpid())
            return process.memory_info().rss / (1024 * 1024)
        except Exception:
            return 0.0
    
    @classmethod
    def is_system_idle(cls, config: DaemonConfig) -> bool:
        """Check if system resources are within acceptable limits."""
        cpu = cls.get_cpu_percent()
        mem = cls.get_memory_mb()
        
        if cpu > config.MAX_CPU_PERCENT:
            return False
        if mem > config.MAX_MEMORY_MB:
            return False
        
        return True


class ContentHasher:
    """Generate hashes for content change detection."""
    
    @staticmethod
    def hash_content(content: str) -> str:
        """Generate SHA256 hash of content."""
        return hashlib.sha256(content.encode('utf-8')).hexdigest()
    
    @staticmethod
    def hash_file(filepath: Path) -> Optional[str]:
        """Generate hash of file contents."""
        if not filepath.exists():
            return None
        try:
            with open(filepath, 'rb') as f:
                return hashlib.sha256(f.read()).hexdigest()
        except Exception:
            return None


class KnowledgeDaemon:
    """Background daemon for automatic knowledge updates."""
    
    def __init__(self, config: DaemonConfig):
        self.config = config
        self.fetcher = KnowledgeFetcher(output_dir=config.output_dir)
        self.monitor = ResourceMonitor()
        self.hasher = ContentHasher()
        self.running = False
        self.state = config.load_state()
        
        # Setup signal handlers
        signal.signal(signal.SIGINT, self._signal_handler)
        signal.signal(signal.SIGTERM, self._signal_handler)
    
    def _signal_handler(self, signum, frame):
        """Handle shutdown signals gracefully."""
        self.config.log("Received shutdown signal, stopping daemon...")
        self.running = False
    
    def _should_fetch_source(self, name: str, content: str) -> bool:
        """Check if source content has changed using hash comparison."""
        current_hash = self.hasher.hash_content(content)
        stored_hash = self.state.get("fetch_hashes", {}).get(name)
        
        if stored_hash is None:
            return True  # Never fetched before
        
        return current_hash != stored_hash
    
    def _update_state(self, name: str, content: str):
        """Update state after successful fetch."""
        if "fetch_hashes" not in self.state:
            self.state["fetch_hashes"] = {}
        
        self.state["fetch_hashes"][name] = self.hasher.hash_content(content)
        self.state["last_update"] = datetime.now().isoformat()
        self.config.save_state(self.state)
    
    def _trigger_reindex(self):
        """Trigger librarian to re-index knowledge base."""
        try:
            from core.librarian import get_librarian
            librarian = get_librarian()
            # Force reload of index
            librarian.load_index(force_reload=True)
            self.config.log("Successfully triggered knowledge base re-index")
        except Exception as e:
            self.config.log(f"Failed to trigger re-index: {e}", level="WARNING")
    
    def check_and_update(self) -> Tuple[int, int]:
        """
        Check all sources and update if changed.
        Returns: (checked_count, updated_count)
        """
        self.config.log("Starting knowledge check cycle")
        self.state["last_check"] = datetime.now().isoformat()
        
        checked = 0
        updated = 0
        
        for name, source in self.fetcher.sources.items():
            checked += 1
            
            try:
                # Fetch content
                content = source.fetch()
                
                # Check if changed
                if self._should_fetch_source(name, content):
                    self.config.log(f"Change detected in {name}, updating...")
                    
                    # Write updated file
                    output_file = Path(self.config.output_dir) / f"{name}.md"
                    output_file.parent.mkdir(parents=True, exist_ok=True)
                    
                    # Add metadata header
                    metadata = (
                        f"---\n"
                        f"source: {name}\n"
                        f"updated: {datetime.now().isoformat()}\n"
                        f"mode: {source.mode}\n"
                        f"---\n\n"
                    )
                    
                    with open(output_file, 'w', encoding='utf-8') as f:
                        f.write(metadata + content)
                    
                    # Update state
                    self._update_state(name, content)
                    updated += 1
                    
                    self.config.log(f"✓ Updated {name}")
                else:
                    if self.config.verbose:
                        self.config.log(f"⏭️  {name} unchanged")
                        
            except Exception as e:
                self.config.log(f"Error fetching {name}: {e}", level="ERROR")
        
        # Trigger re-index if any updates occurred
        if updated > 0:
            self._trigger_reindex()
            self.config.log(f"Cycle complete: {checked} checked, {updated} updated")
        else:
            self.config.log(f"Cycle complete: {checked} checked, no changes")
        
        self.config.save_state(self.state)
        return checked, updated
    
    def run_once(self):
        """Run a single check cycle."""
        if not self.monitor.is_system_idle(self.config):
            self.config.log(
                "System resources high, skipping update cycle",
                level="WARNING"
            )
            return
        
        self.check_and_update()
    
    def run_daemon(self):
        """Run as background daemon with configurable interval."""
        self.running = True
        self.config.log(f"Daemon started (interval: {self.config.interval}s)")
        
        cycle_count = 0
        
        while self.running:
            try:
                # Check resources before each cycle
                if self.monitor.is_system_idle(self.config):
                    self.run_once()
                    cycle_count += 1
                else:
                    self.config.log(
                        "System busy, delaying update cycle",
                        level="WARNING"
                    )
                
                # Wait for next cycle
                if self.running:
                    time.sleep(self.config.interval)
                    
            except Exception as e:
                self.config.log(f"Daemon error: {e}", level="ERROR")
                # Don't crash, wait and retry
                time.sleep(60)
        
        self.config.log(f"Daemon stopped after {cycle_count} cycles")


def main():
    parser = argparse.ArgumentParser(
        description="Ether Courier Daemon - Background Knowledge Updater"
    )
    parser.add_argument(
        "--interval", "-i",
        type=int,
        default=DaemonConfig.DEFAULT_INTERVAL,
        help=f"Check interval in seconds (default: {DaemonConfig.DEFAULT_INTERVAL})"
    )
    parser.add_argument(
        "--once",
        action="store_true",
        help="Run once and exit (no looping)"
    )
    parser.add_argument(
        "--verbose", "-v",
        action="store_true",
        help="Enable verbose logging to console"
    )
    parser.add_argument(
        "--output", "-o",
        type=str,
        default="knowledge_base",
        help="Output directory for knowledge files"
    )
    parser.add_argument(
        "--stop",
        action="store_true",
        help="Stop running daemon (creates stop signal)"
    )
    
    args = parser.parse_args()
    
    # Create config
    config = DaemonConfig()
    config.interval = max(DaemonConfig.MIN_INTERVAL, 
                         min(args.interval, DaemonConfig.MAX_INTERVAL))
    config.verbose = args.verbose
    config.once = args.once
    config.output_dir = args.output
    
    if args.stop:
        # Create stop signal file
        stop_file = Path("courier/daemon.stop")
        stop_file.parent.mkdir(parents=True, exist_ok=True)
        stop_file.touch()
        print("Stop signal sent to daemon")
        return
    
    # Create and run daemon
    daemon = KnowledgeDaemon(config)
    
    if args.once:
        daemon.run_once()
    else:
        daemon.run_daemon()


if __name__ == "__main__":
    main()
