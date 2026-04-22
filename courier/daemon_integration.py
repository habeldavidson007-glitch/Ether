"""
Daemon Integration Helper - Add to Ether CLI startup
=====================================================
This script shows how to integrate the background daemon into Ether CLI.

Option 1: Start daemon on CLI launch (recommended)
Option 2: Run as separate system service
Option 3: Manual trigger via command
"""

import subprocess
import sys
import os
from pathlib import Path

def start_daemon(interval=3600, background=True):
    """Start the knowledge daemon."""
    daemon_path = Path(__file__).parent / "daemon.py"
    
    cmd = [sys.executable, str(daemon_path), "--interval", str(interval)]
    
    if background:
        # Start as background process
        if os.name == 'nt':  # Windows
            subprocess.Popen(cmd, creationflags=subprocess.DETACHED_PROCESS)
        else:  # Linux/Mac
            subprocess.Popen(cmd, start_new_session=True)
        print(f"✓ Knowledge daemon started (interval: {interval}s)")
    else:
        # Run in foreground
        subprocess.run(cmd)
    
    return True

def stop_daemon():
    """Stop the running daemon."""
    daemon_path = Path(__file__).parent / "daemon.py"
    subprocess.run([sys.executable, str(daemon_path), "--stop"])
    print("✓ Knowledge daemon stopped")

def check_daemon_status():
    """Check if daemon is running."""
    state_file = Path(__file__).parent.parent / "knowledge_base" / ".daemon_state.json"
    if state_file.exists():
        import json
        with open(state_file) as f:
            state = json.load(f)
            return state.get('running', False)
    return False

if __name__ == "__main__":
    if len(sys.argv) > 1:
        if sys.argv[1] == "start":
            interval = int(sys.argv[2]) if len(sys.argv) > 2 else 3600
            start_daemon(interval)
        elif sys.argv[1] == "stop":
            stop_daemon()
        elif sys.argv[1] == "status":
            status = "running" if check_daemon_status() else "stopped"
            print(f"Daemon status: {status}")
    else:
        print("Usage: python daemon_integration.py [start|stop|status] [interval]")
