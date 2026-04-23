"""
ether/services/fetch_daemon.py
Service 1: Autonomous Background Fetching & Distillation

Runs as a daemon that:
- Monitors system idle state (CPU < 10%, no user input)
- Fetches from diverse web sources when idle
- Runs content through the Distiller
- Stores compressed knowledge in Hippocampus
- Enforces 200MB cap automatically
"""

import time
import threading
import psutil
from pathlib import Path
from datetime import datetime, timedelta
from typing import Optional, List

# Import Ether core components
import sys
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from ether.core.distiller import distill
from ether.core.sources import get_all_sources
from courier.fetcher import fetch_url_content
from core.adaptive_memory import get_adaptive_memory

class FetchDaemon:
    """Background service for autonomous knowledge acquisition."""
    
    def __init__(self, check_interval_sec: int = 60, idle_threshold: float = 10.0):
        self.check_interval = check_interval_sec
        self.idle_threshold = idle_threshold  # CPU % threshold
        self.running = False
        self.thread: Optional[threading.Thread] = None
        self.memory = get_adaptive_memory()
        
        # Track last fetch per source to avoid duplicates
        self.last_fetch: dict = {}
        self.fetch_cooldown = timedelta(hours=6)  # Don't fetch same source twice in 6 hours
        
        # Statistics
        self.total_fetched = 0
        self.total_distilled = 0
        self.bytes_stored = 0
        
    def is_system_idle(self) -> bool:
        """Check if system is idle enough to fetch."""
        cpu_percent = psutil.cpu_percent(interval=1.0)
        return cpu_percent < self.idle_threshold
    
    def should_fetch_source(self, source_id: str) -> bool:
        """Check if source is due for fetching."""
        now = datetime.now()
        last_time = self.last_fetch.get(source_id)
        
        if last_time is None:
            return True
        
        return (now - last_time) > self.fetch_cooldown
    
    def fetch_and_process(self, source: dict) -> bool:
        """Fetch from source, distill, and store."""
        try:
            url = source['url']
            source_id = source.get('id', url)
            
            # Fetch raw content
            print(f"[FetchDaemon] Fetching: {source['name']} ({url})")
            raw_content = fetch_url_content(url, timeout=10)
            
            if not raw_content or len(raw_content) < 100:
                print(f"[FetchDaemon] Skipped: Content too short")
                return False
            
            # Distill to pure knowledge
            distilled = distill(raw_content, source_type="html")
            
            if distilled['density_score'] < 0.3:
                print(f"[FetchDaemon] Skipped: Low density ({distilled['density_score']})")
                return False
            
            # Store in memory with compression
            key = f"web_{source_id}_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
            content_to_store = f"[SOURCE: {source['name']}]\n{distilled['content']}"
            
            if self.memory.store_knowledge(key, content_to_store):
                self.total_fetched += 1
                self.total_distilled += 1
                self.last_fetch[source_id] = datetime.now()
                
                stats = self.memory.get_storage_stats()
                print(f"[FetchDaemon] Stored: {key} | Density: {distilled['density_score']} | " +
                      f"Storage: {stats['compressed_size_mb']}MB / {stats['ram_cap_mb']}MB " +
                      f"({stats['usage_percent']}%)")
                return True
            
        except Exception as e:
            print(f"[FetchDaemon] Error: {e}")
        
        return False
    
    def run_cycle(self):
        """Execute one fetch cycle."""
        if not self.is_system_idle():
            return
        
        sources = get_all_sources()
        available_sources = [s for s in sources if self.should_fetch_source(s.get('id', s['url']))]
        
        if not available_sources:
            return
        
        # Pick random source
        import random
        source = random.choice(available_sources)
        self.fetch_and_process(source)
    
    def daemon_loop(self):
        """Main daemon loop."""
        print("[FetchDaemon] Starting background fetch service...")
        while self.running:
            try:
                self.run_cycle()
            except Exception as e:
                print(f"[FetchDaemon] Loop error: {e}")
            
            time.sleep(self.check_interval)
    
    def start(self):
        """Start the daemon thread."""
        if self.running:
            return
        
        self.running = True
        self.thread = threading.Thread(target=self.daemon_loop, daemon=True)
        self.thread.start()
        print("[FetchDaemon] Started")
    
    def stop(self):
        """Stop the daemon thread."""
        self.running = False
        if self.thread:
            self.thread.join(timeout=5)
        print("[FetchDaemon] Stopped")
    
    def get_stats(self) -> dict:
        """Get daemon statistics."""
        return {
            "running": self.running,
            "total_fetched": self.total_fetched,
            "total_distilled": self.total_distilled,
            "storage_stats": self.memory.get_storage_stats(),
            "sources_tracked": len(self.last_fetch)
        }


# Singleton instance
_instance: Optional[FetchDaemon] = None

def get_fetch_daemon() -> FetchDaemon:
    global _instance
    if _instance is None:
        _instance = FetchDaemon()
    return _instance


if __name__ == "__main__":
    # Test run
    daemon = get_fetch_daemon()
    daemon.start()
    
    try:
        # Run for 5 minutes for testing
        time.sleep(300)
    except KeyboardInterrupt:
        pass
    finally:
        daemon.stop()
        print("Final stats:", daemon.get_stats())
