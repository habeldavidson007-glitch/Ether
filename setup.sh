#!/bin/bash
# Ether AI Assistant - Linux/Mac Setup Script
# This script sets up the development environment for Ether

set -e

echo "🔧 Setting up Ether AI Assistant..."

# Check Python version
PYTHON_VERSION=$(python3 --version 2>&1 | cut -d' ' -f2)
echo "✓ Python version: $PYTHON_VERSION"

# Create virtual environment
if [ ! -d ".venv" ]; then
    echo "📦 Creating virtual environment..."
    python3 -m venv .venv
else
    echo "✓ Virtual environment already exists"
fi

# Activate virtual environment
echo "🔄 Activating virtual environment..."
source .venv/bin/activate

# Upgrade pip
echo "⬆️  Upgrading pip..."
pip install --upgrade pip

# Install main dependencies
echo "📥 Installing main dependencies..."
pip install -e .

# Install development dependencies
echo "🛠️  Installing development dependencies..."
pip install -r requirements-dev.txt

# Install pre-commit hooks
echo "🪝 Setting up pre-commit hooks..."
pre-commit install

# Run initial tests
echo "🧪 Running initial test suite..."
pytest

echo ""
echo "✅ Setup complete!"
echo ""
echo "To activate the virtual environment, run:"
echo "  source .venv/bin/activate"
echo ""
echo "To run tests:"
echo "  pytest"
echo ""
echo "To run linters:"
echo "  ruff check ."
echo "  black --check ."
echo "  mypy ."
