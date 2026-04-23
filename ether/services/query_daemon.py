"""
ether/services/query_daemon.py
Service 3: Query Routing & Response Generation

Runs as a daemon that:
- Listens for incoming queries via socket/pipe
- Routes queries to appropriate handlers (Godot vs General)
- Retrieves prefetched knowledge from Hippocampus
- Coordinates with LLM for response generation
- Manages temperature and response diversity
"""

import time
import threading
import queue
from pathlib import Path
from datetime import datetime
from typing import Optional, Dict, Any, Callable
import json

# Import Ether core components
import sys
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from core.adaptive_memory import get_adaptive_memory
from ether.core.distiller import distill

class QueryDaemon:
    """Background service for query processing and routing."""
    
    def __init__(self):
        self.running = False
        self.thread: Optional[threading.Thread] = None
        self.memory = get_adaptive_memory()
        
        # Query queue
        self.query_queue: queue.Queue = queue.Queue(maxsize=100)
        
        # Registered handlers
        self.handlers: Dict[str, Callable] = {}
        
        # Statistics
        self.total_queries = 0
        self.total_routed = 0
        self.avg_response_time = 0.0
        
    def register_handler(self, name: str, handler: Callable):
        """Register a query handler."""
        self.handlers[name] = handler
        print(f"[QueryDaemon] Registered handler: {name}")
    
    def route_query(self, query: str, context: Dict[str, Any]) -> Optional[str]:
        """Route query to appropriate handler based on content."""
        query_lower = query.lower()
        
        # Godot-related queries
        godot_keywords = ['godot', 'gdscript', 'scene', 'node', 'shader', 'tscn', 
                         'gdextension', 'engine', 'export', 'signal', ' tween']
        
        if any(kw in query_lower for kw in godot_keywords):
            handler_name = 'godot_expert'
        else:
            handler_name = 'general_knowledge'
        
        if handler_name in self.handlers:
            self.total_routed += 1
            return self.handlers[handler_name](query, context)
        
        # Fallback to general handler
        if 'general_knowledge' in self.handlers:
            return self.handlers['general_knowledge'](query, context)
        
        return None
    
    def process_query(self, query_id: str, query: str, metadata: Dict[str, Any]):
        """Process a single query end-to-end."""
        start_time = time.time()
        
        try:
            # Retrieve relevant knowledge from memory
            # In full implementation, would use semantic search
            context = {
                'timestamp': datetime.now().isoformat(),
                'query_id': query_id,
                'metadata': metadata
            }
            
            # Route and get response
            response = self.route_query(query, context)
            
            elapsed = time.time() - start_time
            self.total_queries += 1
            
            # Update running average
            n = self.total_queries
            self.avg_response_time = ((self.avg_response_time * (n-1)) + elapsed) / n
            
            return {
                'query_id': query_id,
                'response': response,
                'elapsed_ms': round(elapsed * 1000, 2),
                'success': response is not None
            }
            
        except Exception as e:
            print(f"[QueryDaemon] Error processing query: {e}")
            return {
                'query_id': query_id,
                'response': None,
                'error': str(e),
                'success': False
            }
    
    def daemon_loop(self):
        """Main daemon loop - processes query queue."""
        print("[QueryDaemon] Starting query processing service...")
        while self.running:
            try:
                # Non-blocking get with timeout
                try:
                    item = self.query_queue.get(timeout=1.0)
                    query_id = item.get('id', 'unknown')
                    query = item.get('query', '')
                    metadata = item.get('metadata', {})
                    
                    result = self.process_query(query_id, query, metadata)
                    
                    # In full implementation, would send result back via socket/pipe
                    print(f"[QueryDaemon] Processed: {query_id} in {result.get('elapsed_ms')}ms")
                    
                except queue.Empty:
                    pass
                    
            except Exception as e:
                print(f"[QueryDaemon] Loop error: {e}")
    
    def submit_query(self, query: str, metadata: Dict[str, Any] = None) -> str:
        """Submit a query for async processing."""
        query_id = f"q_{datetime.now().strftime('%Y%m%d%H%M%S%f')}"
        
        if self.query_queue.full():
            print("[QueryDaemon] Warning: Query queue full, dropping oldest")
            try:
                self.query_queue.get_nowait()  # Drop oldest
            except queue.Empty:
                pass
        
        self.query_queue.put({
            'id': query_id,
            'query': query,
            'metadata': metadata or {}
        })
        
        return query_id
    
    def start(self):
        """Start the daemon thread."""
        if self.running:
            return
        
        self.running = True
        self.thread = threading.Thread(target=self.daemon_loop, daemon=True)
        self.thread.start()
        print("[QueryDaemon] Started")
    
    def stop(self):
        """Stop the daemon thread."""
        self.running = False
        if self.thread:
            self.thread.join(timeout=5)
        print("[QueryDaemon] Stopped")
    
    def get_stats(self) -> dict:
        """Get daemon statistics."""
        return {
            "running": self.running,
            "queue_size": self.query_queue.qsize(),
            "total_queries": self.total_queries,
            "total_routed": self.total_routed,
            "avg_response_time_ms": round(self.avg_response_time * 1000, 2),
            "handlers_registered": list(self.handlers.keys()),
            "memory_stats": self.memory.get_storage_stats()
        }


# Singleton instance
_instance: Optional[QueryDaemon] = None

def get_query_daemon() -> QueryDaemon:
    global _instance
    if _instance is None:
        _instance = QueryDaemon()
    return _instance


if __name__ == "__main__":
    # Test run
    daemon = get_query_daemon()
    
    # Register dummy handlers for testing
    def godot_handler(query, context):
        return f"[Godot Expert] Answering: {query[:50]}..."
    
    def general_handler(query, context):
        return f"[General Knowledge] Answering: {query[:50]}..."
    
    daemon.register_handler('godot_expert', godot_handler)
    daemon.register_handler('general_knowledge', general_handler)
    
    daemon.start()
    
    try:
        # Submit test queries
        for i in range(5):
            query_id = daemon.submit_query(f"Test query {i}", {"test": True})
            print(f"Submitted: {query_id}")
            time.sleep(0.5)
        
        # Wait for processing
        time.sleep(3)
        
    except KeyboardInterrupt:
        pass
    finally:
        daemon.stop()
        print("Final stats:", daemon.get_stats())
