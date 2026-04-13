#!/bin/bash
# =============================================================================
# Ether — Quick Run Script
# Godot AI Development Assistant
# =============================================================================
# This script quickly starts the Ether application.
# Run with: ./run.sh
# =============================================================================

set -e

echo "◈ Ether — Starting..."

# Activate virtual environment if it exists
if [ -d "venv" ]; then
    source venv/bin/activate
fi

# Run Streamlit
streamlit run app.py
