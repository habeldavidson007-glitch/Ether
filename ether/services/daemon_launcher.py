"""
ether/services/daemon_launcher.py
==================================
Daemon Launcher Script for Ether AI Assistant

This script starts the UnifiedDaemon as a background service with
memory constraints suitable for low-RAM systems (2GB).

Usage:
    python ether/services/daemon_launcher.py

The daemon will:
- Run in the background monitoring system idle time
- Perform autonomous knowledge fetching
- Handle semantic indexing
- Enforce memory caps to prevent OOM issues
"""

import os
import sys
import logging
import signal
import time
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

# Setup logging
log_dir = project_root / "logs"
log_dir.mkdir(exist_ok=True)

log_file = log_dir / "daemon.log"

# Configure logging - file and console
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler(log_file, encoding='utf-8'),
        logging.StreamHandler(sys.stdout)
    ]
)

logger = logging.getLogger(__name__)


def setup_signal_handlers(daemon_instance):
    """Setup graceful shutdown handlers."""
    def signal_handler(signum, frame):
        logger.info(f"Received signal {signum}, shutting down gracefully...")
        if daemon_instance:
            daemon_instance.stop()
        sys.exit(0)
    
    # Register handlers for common termination signals
    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)
    
    # Windows-specific handler
    if os.name == 'nt':
        try:
            signal.signal(signal.SIGBREAK, signal_handler)
        except (AttributeError, ValueError):
            pass  # SIGBREAK not available on all Windows versions


def main():
    """Main entry point for daemon launcher."""
    logger.info("=" * 60)
    logger.info("Ether Daemon Launcher Starting")
    logger.info("=" * 60)
    
    # Import here to allow logging setup first and lazy loading
    try:
        from ether.core.unified_daemon import UnifiedDaemon
    except ImportError as e:
        logger.error(f"Failed to import UnifiedDaemon: {e}")
        logger.error("Make sure ether package is installed correctly")
        sys.exit(1)
    
    # RAM limit for low-memory systems (2GB target)
    ram_limit_mb = 200
    logger.info(f"Initializing daemon with RAM limit: {ram_limit_mb}MB")
    
    # Create daemon instance
    daemon = UnifiedDaemon(memory_cap_mb=ram_limit_mb)
    
    # Setup signal handlers for graceful shutdown
    setup_signal_handlers(daemon)
    
    try:
        # Start the daemon (runs in background thread internally)
        daemon.start()
        logger.info("Daemon started successfully")
        logger.info("Press Ctrl+C to stop the daemon")
        
        # Keep the main thread alive while daemon runs in background
        # This allows signal handlers to work properly
        while True:
            time.sleep(1)
            
    except KeyboardInterrupt:
        logger.info("KeyboardInterrupt received, initiating shutdown...")
    except Exception as e:
        logger.error(f"Unexpected error in daemon loop: {e}", exc_info=True)
    finally:
        # Ensure clean shutdown
        logger.info("Stopping daemon...")
        daemon.stop()
        logger.info("Daemon stopped. Goodbye!")


if __name__ == "__main__":
    main()
