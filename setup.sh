#!/bin/bash
# =============================================================================
# Ether — Setup Script
# Godot AI Development Assistant
# =============================================================================
# This script sets up the development environment for Ether.
# Run with: ./setup.sh
# =============================================================================

set -e  # Exit on error

echo "◈ Ether — Setting up development environment"
echo "=============================================="

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Helper functions
log_info() {
    echo -e "${BLUE}[INFO]${NC} $1"
}

log_success() {
    echo -e "${GREEN}[OK]${NC} $1"
}

log_warn() {
    echo -e "${YELLOW}[WARN]${NC} $1"
}

log_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

# Check Python version
check_python() {
    log_info "Checking Python version..."
    if ! command -v python3 &> /dev/null; then
        log_error "Python 3 is required but not installed."
        exit 1
    fi
    
    PYTHON_VERSION=$(python3 --version | cut -d' ' -f2 | cut -d'.' -f1,2)
    log_success "Python $PYTHON_VERSION detected"
}

# Install dependencies (system-wide or in existing venv)
install_deps() {
    log_info "Installing dependencies..."
    
    if [ ! -f "requirements.txt" ]; then
        log_error "requirements.txt not found!"
        exit 1
    fi
    
    # Check if we're in a virtual environment
    if [ -n "$VIRTUAL_ENV" ]; then
        log_info "Installing in virtual environment..."
    else
        log_warn "No virtual environment detected. Installing system-wide."
        log_info "Consider running: python3 -m venv venv && source venv/bin/activate"
    fi
    
    pip install --upgrade pip --quiet
    pip install -r requirements.txt --quiet
    
    log_success "Dependencies installed"
}

# Create necessary directories
setup_directories() {
    log_info "Setting up directory structure..."
    
    mkdir -p workspace/knowledge
    mkdir -p workspace/project
    mkdir -p logs
    
    log_success "Directory structure ready"
}

# Verify installation
verify_install() {
    log_info "Verifying installation..."
    
    # Check if streamlit is installed
    if ! python -c "import streamlit" &> /dev/null; then
        log_error "Streamlit installation failed!"
        exit 1
    fi
    
    # Check if core modules are importable
    if ! python -c "from core import EtherSession" &> /dev/null; then
        log_warn "Core module import check failed (may need additional setup)"
    fi
    
    log_success "Installation verified"
}

# Show next steps
show_next_steps() {
    echo ""
    echo "=============================================="
    echo -e "${GREEN}✓ Setup complete!${NC}"
    echo "=============================================="
    echo ""
    echo "To run Ether:"
    echo "  1. Activate the virtual environment:"
    echo "     source venv/bin/activate"
    echo ""
    echo "  2. Start the Streamlit app:"
    echo "     streamlit run app.py"
    echo ""
    echo "Or use the quick start command:"
    echo "  ./run.sh"
    echo ""
}

# Main execution
main() {
    check_python
    install_deps
    setup_directories
    verify_install
    show_next_steps
}

# Run main function
main "$@"
