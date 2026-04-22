#!/usr/bin/env python3
"""
ETHER CORE - Master Control Program (MCP)
==========================================
Central orchestrator for all Ether modules and background services.

Features:
- Process health monitoring
- Resource management (CPU/RAM throttling)
- Unified API for module communication
- Auto-recovery for crashed services
- Centralized logging
- Configuration management

Usage:
    python ether_core.py start      # Start all services
    python ether_core.py stop       # Stop all services
    python ether_core.py status     # Show service status
    python ether_core.py restart    # Restart all services
    python ether_core.py monitor    # Interactive monitoring dashboard
"""

import os
import sys
import json
import time
import signal
import subprocess
import threading
from pathlib import Path
from datetime import datetime
from typing import Dict, List, Optional, Any
import logging

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('ether_core.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger('EtherCore')


class ServiceConfig:
    """Configuration for a managed service."""
    
    def __init__(self, name: str, script: str, args: List[str] = None, 
                 auto_restart: bool = True, max_restarts: int = 3,
                 cpu_limit: float = 50.0, ram_limit_mb: int = 512):
        self.name = name
        self.script = script
        self.args = args or []
        self.auto_restart = auto_restart
        self.max_restarts = max_restarts
        self.cpu_limit = cpu_limit  # Percentage
        self.ram_limit_mb = ram_limit_mb
        self.restart_count = 0
        self.last_start_time = 0
        self.process: Optional[subprocess.Popen] = None
        self.status = 'stopped'  # stopped, running, crashed, disabled
        self.pid: Optional[int] = None


class EtherCore:
    """Master Control Program for Ether AI Assistant."""
    
    def __init__(self, config_path: str = 'ether_core_config.json'):
        self.config_path = Path(config_path)
        self.services: Dict[str, ServiceConfig] = {}
        self.running = False
        self.monitor_thread: Optional[threading.Thread] = None
        self.load_config()
        self.setup_signal_handlers()
        
    def load_config(self):
        """Load or create default configuration."""
        if self.config_path.exists():
            with open(self.config_path, 'r') as f:
                config = json.load(f)
                for svc_data in config.get('services', []):
                    self.register_service(**svc_data)
            logger.info(f"Loaded configuration from {self.config_path}")
        else:
            self.create_default_config()
            
    def create_default_config(self):
        """Create default configuration with all Ether services."""
        base_dir = Path(__file__).parent
        
        default_services = [
            {
                'name': 'knowledge_daemon',
                'script': str(base_dir / 'courier' / 'daemon.py'),
                'args': ['--interval', '3600'],
                'auto_restart': True,
                'cpu_limit': 20.0,
                'ram_limit_mb': 256
            },
            {
                'name': 'rag_indexer',
                'script': str(base_dir / 'core' / 'rag_index.py'),
                'args': ['--watch'],
                'auto_restart': True,
                'cpu_limit': 30.0,
                'ram_limit_mb': 512
            },
            {
                'name': 'memory_core',
                'script': str(base_dir / 'core' / 'memory_core.py'),
                'args': ['--background'],
                'auto_restart': True,
                'cpu_limit': 15.0,
                'ram_limit_mb': 128
            }
        ]
        
        config = {'services': default_services}
        with open(self.config_path, 'w') as f:
            json.dump(config, f, indent=2)
            
        for svc_data in default_services:
            self.register_service(**svc_data)
            
        logger.info(f"Created default configuration at {self.config_path}")
        
    def register_service(self, name: str, script: str, args: List[str] = None,
                        auto_restart: bool = True, max_restarts: int = 3,
                        cpu_limit: float = 50.0, ram_limit_mb: int = 512):
        """Register a service for management."""
        self.services[name] = ServiceConfig(
            name=name,
            script=script,
            args=args or [],
            auto_restart=auto_restart,
            max_restarts=max_restarts,
            cpu_limit=cpu_limit,
            ram_limit_mb=ram_limit_mb
        )
        logger.info(f"Registered service: {name}")
        
    def start_service(self, name: str) -> bool:
        """Start a specific service."""
        if name not in self.services:
            logger.error(f"Service {name} not found")
            return False
            
        service = self.services[name]
        
        if service.status == 'running':
            logger.info(f"Service {name} is already running")
            return True
            
        # Check restart limit
        if service.restart_count >= service.max_restarts:
            logger.error(f"Service {name} exceeded max restarts ({service.max_restarts})")
            service.status = 'disabled'
            return False
            
        try:
            cmd = [sys.executable, service.script] + service.args
            service.process = subprocess.Popen(
                cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                preexec_fn=os.setsid if os.name != 'nt' else None
            )
            service.pid = service.process.pid
            service.status = 'running'
            service.last_start_time = time.time()
            
            logger.info(f"Started service {name} (PID: {service.pid})")
            return True
            
        except Exception as e:
            logger.error(f"Failed to start service {name}: {e}")
            service.status = 'crashed'
            return False
            
    def stop_service(self, name: str, force: bool = False) -> bool:
        """Stop a specific service."""
        if name not in self.services:
            logger.error(f"Service {name} not found")
            return False
            
        service = self.services[name]
        
        if service.status != 'running' or service.process is None:
            service.status = 'stopped'
            return True
            
        try:
            if force:
                service.process.kill()
            else:
                service.process.terminate()
                
            # Wait for graceful shutdown
            try:
                service.process.wait(timeout=5)
            except subprocess.TimeoutExpired:
                service.process.kill()
                service.process.wait()
                
            service.status = 'stopped'
            service.process = None
            service.pid = None
            
            logger.info(f"Stopped service {name}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to stop service {name}: {e}")
            return False
            
    def start_all(self):
        """Start all registered services."""
        logger.info("Starting all services...")
        self.running = True
        
        for name in self.services:
            self.start_service(name)
            
        # Start monitoring thread
        self.monitor_thread = threading.Thread(target=self._monitor_loop, daemon=True)
        self.monitor_thread.start()
        
        logger.info("All services started")
        
    def stop_all(self, force: bool = False):
        """Stop all services."""
        logger.info("Stopping all services...")
        self.running = False
        
        for name in list(self.services.keys()):
            self.stop_service(name, force=force)
            
        logger.info("All services stopped")
        
    def restart_service(self, name: str) -> bool:
        """Restart a service."""
        self.stop_service(name)
        time.sleep(1)
        return self.start_service(name)
        
    def get_status(self) -> Dict[str, Any]:
        """Get status of all services."""
        status = {
            'timestamp': datetime.now().isoformat(),
            'running': self.running,
            'services': {}
        }
        
        for name, service in self.services.items():
            service_info = {
                'status': service.status,
                'pid': service.pid,
                'restarts': service.restart_count,
                'uptime': None
            }
            
            if service.status == 'running' and service.last_start_time > 0:
                service_info['uptime'] = time.time() - service.last_start_time
                
            # Get resource usage if running
            if service.status == 'running' and service.pid:
                try:
                    import psutil
                    proc = psutil.Process(service.pid)
                    service_info['cpu_percent'] = proc.cpu_percent()
                    service_info['memory_mb'] = proc.memory_info().rss / 1024 / 1024
                except (ImportError, psutil.NoSuchProcess):
                    pass
                    
            status['services'][name] = service_info
            
        return status
        
    def _monitor_loop(self):
        """Monitor services and auto-restart crashed ones."""
        while self.running:
            try:
                for name, service in self.services.items():
                    if service.status != 'running':
                        continue
                        
                    # Check if process is still alive
                    if service.process and service.process.poll() is not None:
                        logger.warning(f"Service {name} crashed (exit code: {service.process.returncode})")
                        service.status = 'crashed'
                        service.process = None
                        
                        # Auto-restart if enabled
                        if service.auto_restart:
                            service.restart_count += 1
                            logger.info(f"Auto-restarting {name} (attempt {service.restart_count}/{service.max_restarts})")
                            time.sleep(2)  # Wait before restart
                            self.start_service(name)
                            
                time.sleep(5)  # Check every 5 seconds
                
            except Exception as e:
                logger.error(f"Monitor loop error: {e}")
                time.sleep(5)
                
    def setup_signal_handlers(self):
        """Setup signal handlers for graceful shutdown."""
        def signal_handler(signum, frame):
            logger.info(f"Received signal {signum}, shutting down...")
            self.stop_all()
            sys.exit(0)
            
        signal.signal(signal.SIGINT, signal_handler)
        signal.signal(signal.SIGTERM, signal_handler)
        
    def save_config(self):
        """Save current configuration."""
        config = {
            'services': [
                {
                    'name': svc.name,
                    'script': svc.script,
                    'args': svc.args,
                    'auto_restart': svc.auto_restart,
                    'max_restarts': svc.max_restarts,
                    'cpu_limit': svc.cpu_limit,
                    'ram_limit_mb': svc.ram_limit_mb
                }
                for svc in self.services.values()
            ]
        }
        
        with open(self.config_path, 'w') as f:
            json.dump(config, f, indent=2)
            
        logger.info(f"Configuration saved to {self.config_path}")


def print_status_table(status: Dict[str, Any]):
    """Print formatted status table."""
    print("\n" + "="*70)
    print("                    ETHER CORE - Service Status")
    print("="*70)
    print(f"Timestamp: {status['timestamp']}")
    print(f"Core Running: {status['running']}")
    print("-"*70)
    print(f"{'Service':<20} {'Status':<12} {'PID':<8} {'Uptime':<10} {'CPU':<8} {'RAM':<8}")
    print("-"*70)
    
    for name, info in status['services'].items():
        uptime = f"{info['uptime']:.0f}s" if info['uptime'] else '-'
        cpu = f"{info.get('cpu_percent', 0):.1f}%" if 'cpu_percent' in info else '-'
        ram = f"{info.get('memory_mb', 0):.1f}MB" if 'memory_mb' in info else '-'
        
        print(f"{name:<20} {info['status']:<12} {str(info['pid'] or '-'):<8} {uptime:<10} {cpu:<8} {ram:<8}")
        
    print("="*70 + "\n")


def main():
    """Main entry point."""
    if len(sys.argv) < 2:
        print("Usage: python ether_core.py [start|stop|status|restart|monitor|config]")
        sys.exit(1)
        
    core = EtherCore()
    command = sys.argv[1].lower()
    
    if command == 'start':
        core.start_all()
        print("✓ All services started")
        print_status_table(core.get_status())
        
        # Keep running
        try:
            while True:
                time.sleep(1)
        except KeyboardInterrupt:
            core.stop_all()
            
    elif command == 'stop':
        core.stop_all()
        print("✓ All services stopped")
        
    elif command == 'status':
        status = core.get_status()
        print_status_table(status)
        
    elif command == 'restart':
        core.stop_all()
        time.sleep(2)
        core.start_all()
        print("✓ All services restarted")
        print_status_table(core.get_status())
        
    elif command == 'monitor':
        print("Starting interactive monitor (Ctrl+C to exit)...")
        core.start_all()
        
        try:
            while True:
                os.system('cls' if os.name == 'nt' else 'clear')
                status = core.get_status()
                print_status_table(status)
                time.sleep(2)
        except KeyboardInterrupt:
            core.stop_all()
            
    elif command == 'config':
        core.save_config()
        print(f"✓ Configuration saved to {core.config_path}")
        
    else:
        print(f"Unknown command: {command}")
        print("Usage: python ether_core.py [start|stop|status|restart|monitor|config]")
        sys.exit(1)


if __name__ == '__main__':
    main()
