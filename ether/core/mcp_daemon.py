"""
Ether MCP (Memory & Content Prefetch) Daemon
=============================================
Purpose: Autonomous background agent that manages idle-time fetching and memory caps.

Features:
- Monitors system idle state (CPU usage, user activity, Ollama status)
- Fetches general knowledge from web sources during idle periods
- Enforces 200MB memory cap with intelligent eviction
- Maintains prefetch queue for instant responses
- Thread-safe operation with main consciousness engine

Usage:
    mcp = MCPDaemon()
    mcp.start()  # Run in background
    # ... system runs normally ...
    mcp.stop()   # Graceful shutdown
"""

import os
import time
import threading
import logging
import psutil
import requests
from pathlib import Path
from typing import Dict, List, Optional, Set
from datetime import datetime, timedelta
from collections import deque
import hashlib

# Try to import feedparser for RSS feeds
try:
    import feedparser
    FEEDPARSER_AVAILABLE = True
except ImportError:
    FEEDPARSER_AVAILABLE = False
    logging.warning("feedparser not available. RSS feed fetching disabled.")

logger = logging.getLogger(__name__)

# Configuration
IDLE_THRESHOLD_CPU = 10.0  # CPU usage below this is considered idle
IDLE_THRESHOLD_SECONDS = 300  # 5 minutes of no user activity
FETCH_INTERVAL_SECONDS = 600  # Fetch every 10 minutes when idle
MAX_FETCH_PER_CYCLE = 3  # Max articles to fetch per cycle
MEMORY_CHECK_INTERVAL = 60  # Check memory every minute

# Knowledge sources (general, not just Godot)
RSS_FEEDS = [
    "https://hnrss.org/frontpage",  # Hacker News
    "https://rss.arxiv.org/rss/cs.AI",  # ArXiv AI
    "https://www.reddit.com/r/programming/.rss",  # Reddit Programming
    "https://feeds.feedburner.com/TechCrunch/",  # Tech news
]

WIKIPEDIA_TOPICS = [
    "Artificial intelligence",
    "Machine learning",
    "Computer programming",
    "Software engineering",
    "Data structure",
    "Algorithm",
]


class SystemMonitor:
    """Monitors system state to detect idle periods"""
    
    def __init__(self):
        self.cpu_history = deque(maxlen=10)
        self.last_user_activity = datetime.now()
        
    def is_idle(self) -> bool:
        """Check if system is idle"""
        # Check CPU usage
        cpu_percent = psutil.cpu_percent(interval=1)
        self.cpu_history.append(cpu_percent)
        
        avg_cpu = sum(self.cpu_history) / len(self.cpu_history)
        if avg_cpu > IDLE_THRESHOLD_CPU:
            return False
        
        # Check time since last activity (simplified - in production would check keyboard/mouse)
        time_since_activity = (datetime.now() - self.last_user_activity).total_seconds()
        if time_since_activity < IDLE_THRESHOLD_SECONDS:
            return False
        
        # Check if Ollama is running (optional - don't fetch if Ollama is busy)
        if self._is_ollama_busy():
            return False
        
        logger.debug(f"System idle: CPU={avg_cpu:.1f}%, idle_time={time_since_activity:.0f}s")
        return True
    
    def _is_ollama_busy(self) -> bool:
        """Check if Ollama is currently processing a request"""
        try:
            response = requests.get("http://localhost:11434/api/tags", timeout=2)
            # If we can reach Ollama, assume it might be busy
            # In production, would check active requests
            return False
        except:
            # Ollama not running or unreachable
            return True
    
    def record_user_activity(self):
        """Record user activity timestamp"""
        self.last_user_activity = datetime.now()


class KnowledgeFetcher:
    """Fetches and compresses knowledge from web sources"""
    
    def __init__(self, hippocampus):
        self.hippocampus = hippocampus
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'Ether-MCP-Daemon/1.0 (Knowledge Fetcher)'
        })
        self.fetched_hashes: Set[str] = set()  # Avoid duplicates
        
    def fetch_cycle(self) -> int:
        """Execute one fetch cycle, returns number of articles fetched"""
        fetched_count = 0
        
        # Fetch from RSS feeds
        if FEEDPARSER_AVAILABLE:
            fetched_count += self._fetch_rss_feeds()
        
        # Fetch Wikipedia summaries
        fetched_count += self._fetch_wikipedia()
        
        logger.info(f"Fetch cycle complete: {fetched_count} articles")
        return fetched_count
    
    def _fetch_rss_feeds(self) -> int:
        """Fetch articles from RSS feeds"""
        count = 0
        
        for feed_url in RSS_FEEDS[:2]:  # Limit to 2 feeds per cycle
            try:
                response = self.session.get(feed_url, timeout=10)
                response.raise_for_status()
                
                feed = feedparser.parse(response.content)
                
                for entry in feed.entries[:MAX_FETCH_PER_CYCLE]:
                    title = entry.get('title', '')
                    summary = entry.get('summary', '')
                    link = entry.get('link', '')
                    
                    # Create content snippet
                    content = f"Title: {title}\nSource: {feed.feed.get('title', 'Unknown')}\nURL: {link}\n\nSummary: {summary}"
                    
                    # Check for duplicates
                    content_hash = hashlib.md5(content.encode()).hexdigest()
                    if content_hash in self.fetched_hashes:
                        continue
                    
                    self.fetched_hashes.add(content_hash)
                    
                    # Add to prefetch queue
                    topic = self._extract_topic(title)
                    self.hippocampus.add_to_prefetch(topic, content)
                    
                    count += 1
                    if count >= MAX_FETCH_PER_CYCLE:
                        break
                        
            except Exception as e:
                logger.error(f"Failed to fetch RSS feed {feed_url}: {e}")
        
        return count
    
    def _fetch_wikipedia(self) -> int:
        """Fetch Wikipedia summaries for key topics"""
        count = 0
        
        for topic in WIKIPEDIA_TOPICS:
            try:
                url = f"https://en.wikipedia.org/api/rest_v1/page/summary/{topic.replace(' ', '_')}"
                response = self.session.get(url, timeout=10)
                response.raise_for_status()
                
                data = response.json()
                
                if 'extract' not in data:
                    continue
                
                content = f"Topic: {topic}\nSource: Wikipedia\n\n{data['extract']}"
                
                # Check for duplicates
                content_hash = hashlib.md5(content.encode()).hexdigest()
                if content_hash in self.fetched_hashes:
                    continue
                
                self.fetched_hashes.add(content_hash)
                
                # Add to prefetch queue
                self.hippocampus.add_to_prefetch(topic, content)
                
                count += 1
                
            except Exception as e:
                logger.debug(f"Failed to fetch Wikipedia '{topic}': {e}")
        
        return count
    
    def _extract_topic(self, title: str) -> str:
        """Extract main topic from title"""
        # Simple heuristic: first few words
        words = title.split()[:3]
        return ' '.join(words).lower()


class MCPDaemon:
    """Main MCP Daemon orchestrating monitoring and fetching"""
    
    def __init__(self, hippocampus=None):
        self.hippocampus = hippocampus
        self.monitor = SystemMonitor()
        self.fetcher: Optional[KnowledgeFetcher] = None
        self.running = False
        self.thread: Optional[threading.Thread] = None
        self.last_fetch = datetime.min
        
    def start(self, hippocampus=None):
        """Start the daemon in background thread"""
        if self.running:
            logger.warning("MCP Daemon already running")
            return
        
        if hippocampus:
            self.hippocampus = hippocampus
        
        if not self.hippocampus:
            logger.error("Cannot start MCP Daemon: No Hippocampus instance provided")
            return
        
        self.fetcher = KnowledgeFetcher(self.hippocampus)
        self.running = True
        
        self.thread = threading.Thread(target=self._run_loop, daemon=True)
        self.thread.start()
        
        logger.info("MCP Daemon started")
    
    def stop(self):
        """Stop the daemon gracefully"""
        self.running = False
        if self.thread:
            self.thread.join(timeout=5)
        logger.info("MCP Daemon stopped")
    
    def _run_loop(self):
        """Main daemon loop"""
        while self.running:
            try:
                # Check if system is idle
                if self.monitor.is_idle():
                    # Check if enough time since last fetch
                    if (datetime.now() - self.last_fetch).total_seconds() > FETCH_INTERVAL_SECONDS:
                        logger.info("System idle, starting fetch cycle...")
                        self.fetcher.fetch_cycle()
                        self.last_fetch = datetime.now()
                
                # Enforce memory cap
                if hasattr(self.hippocampus, '_enforce_memory_cap'):
                    self.hippocampus._enforce_memory_cap()
                
                # Sleep until next check
                time.sleep(MEMORY_CHECK_INTERVAL)
                
            except Exception as e:
                logger.error(f"MCP Daemon error: {e}")
                time.sleep(60)  # Wait before retrying
    
    def trigger_fetch_now(self) -> int:
        """Manually trigger a fetch cycle (for testing/debugging)"""
        if not self.fetcher:
            logger.error("Cannot fetch: Daemon not started")
            return 0
        
        return self.fetcher.fetch_cycle()
    
    def get_status(self) -> dict:
        """Get daemon status"""
        return {
            "running": self.running,
            "last_fetch": self.last_fetch.isoformat() if self.last_fetch != datetime.min else None,
            "prefetch_stats": self.hippocampus.get_prefetch_stats() if self.hippocampus else {},
            "memory_stats": self.hippocampus.get_memory_stats() if self.hippocampus else {}
        }


# Singleton instance
_mcp_instance: Optional[MCPDaemon] = None


def get_mcp_daemon() -> MCPDaemon:
    """Get or create MCP Daemon singleton"""
    global _mcp_instance
    if _mcp_instance is None:
        _mcp_instance = MCPDaemon()
    return _mcp_instance


# CLI interface for testing
if __name__ == "__main__":
    import sys
    
    print("=" * 60)
    print("Ether MCP Daemon - Test Interface")
    print("=" * 60)
    
    # Create a test Hippocampus
    sys.path.insert(0, str(Path(__file__).parent))
    from consciousness import Hippocampus
    
    hippocampus = Hippocampus(max_size_mb=50)  # Small cap for testing
    
    # Start daemon
    mcp = get_mcp_daemon()
    mcp.start(hippocampus)
    
    print("\nMCP Daemon started. Monitoring for idle periods...")
    print("Press Ctrl+C to stop")
    
    try:
        # Manual fetch for testing
        print("\nTriggering manual fetch cycle...")
        count = mcp.trigger_fetch_now()
        print(f"Fetched {count} articles")
        
        # Show stats
        status = mcp.get_status()
        print(f"\nStatus: {status}")
        
        # Keep running briefly
        time.sleep(10)
        
    except KeyboardInterrupt:
        print("\nStopping...")
    
    finally:
        mcp.stop()
        print("\n✅ MCP Daemon test complete")
