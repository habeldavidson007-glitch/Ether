# Ether AI

[![Python 3.9+](https://img.shields.io/badge/python-3.9+-blue.svg)](https://www.python.org/downloads/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Tests](https://github.com/ether-ai/ether/actions/workflows/ci.yml/badge.svg)](https://github.com/ether-ai/ether/actions)
[![Code style: black](https://img.shields.io/badge/code%20style-black-000000.svg)](https://github.com/psf/black)
[![Ruff](https://img.shields.io/endpoint?url=https://raw.githubusercontent.com/astral-sh/ruff/main/assets/badge/v2.json)](https://github.com/astral-sh/ruff)

## 🎯 Overview

**Ether** is a focused, minimal AI assistant specifically designed for **Godot 4 game development**. It understands your project structure, generates complete working systems, and helps fix bugs with context-aware suggestions.

### Key Features

- 🧠 **Self-Improving Memory**: Learns from your corrections and adapts to your coding style
- 🎮 **Godot-Specific**: Deep understanding of Godot 4 architecture, GDScript, and scene systems
- 📁 **Project Awareness**: Analyzes your entire codebase for context-aware suggestions
- 🔍 **Static Analysis**: Detects issues before runtime with comprehensive code validation
- 🔗 **Dependency Tracking**: Maps relationships between scripts, scenes, and resources
- 🛠️ **Auto-Fix**: Suggests and applies fixes for common Godot development issues
- 📊 **Scene Graph Analysis**: Visualizes and validates scene hierarchies

## 🚀 Quick Start

### Prerequisites

- Python 3.9 or higher
- pip (Python package manager)
- Git

### Installation

#### Option 1: Modern PEP 517 Install (Recommended)

```bash
# Clone the repository
git clone https://github.com/ether-ai/ether.git
cd ether

# Install with development dependencies
pip install -e ".[dev]"

# Install pre-commit hooks (optional but recommended)
pre-commit install
```

#### Option 2: Simple Install

```bash
pip install -r requirements.txt
```

### Setup Script

**Linux/macOS:**
```bash
chmod +x setup.sh
./setup.sh
```

**Windows:**
```bash
setup.bat
```

## 📖 Usage

### Basic Commands

```bash
# Analyze your Godot project
python -m ether analyze /path/to/your/godot/project

# Fix detected issues
python -m ether fix /path/to/your/godot/project

# Generate documentation
python -m ether docs /path/to/your/godot/project

# Scan for cascade errors
python -m ether scan /path/to/your/godot/project
```

### Streamlit Interface

Ether includes a web-based interface for interactive analysis:

```bash
streamlit run ui/app.py
```

Then open your browser to `http://localhost:8501`.

### Configuration

Create a `.ether.toml` file in your project root:

```toml
[ether]
godot_version = "4.2"
exclude_patterns = ["addons/*", "tests/*"]
include_patterns = ["*.gd", "*.tscn", "*.tres"]
memory_enabled = true
auto_fix = false
```

## 🏗️ Architecture

Ether consists of several core modules:

| Module | Purpose |
|--------|---------|
| `Librarian` | Manages project-wide code memory and context |
| `StaticAnalyzer` | Performs static code analysis on GDScript |
| `DependencyGraph` | Tracks relationships between scripts and resources |
| `SceneGraphAnalyzer` | Validates scene hierarchies and node structures |
| `GodotValidator` | Checks for Godot-specific issues and best practices |
| `CodeFixer` | Applies automated fixes to detected problems |
| `CascadeScanner` | Detects potential cascade error patterns |

## 🧪 Testing

Run the test suite:

```bash
# Run all tests
pytest

# Run with coverage
pytest --cov=ether --cov-report=html

# Run specific test file
pytest tests/test_builder.py

# Run with verbose output
pytest -v
```

## 🛠️ Development

### Code Quality Tools

Ether uses several tools to maintain code quality:

```bash
# Format code
black .

# Sort imports
isort .

# Lint code
ruff check .

# Type checking
mypy ether/

# Run all pre-commit hooks
pre-commit run --all-files
```

### Project Structure

```
ether/
├── core/                  # Core analysis engines
│   ├── librarian.py       # Memory management
│   ├── static_analyzer.py # Code analysis
│   ├── dependency_graph.py # Dependency tracking
│   ├── scene_graph_analyzer.py # Scene validation
│   ├── godot_validator.py # Godot-specific checks
│   ├── code_fixer.py      # Auto-fix engine
│   └── cascade_scanner.py # Error pattern detection
├── ui/                    # User interface
│   └── app.py            # Streamlit interface
├── tests/                 # Test suite
│   ├── conftest.py       # Test configuration
│   ├── test_builder.py   # Builder tests
│   ├── test_librarian.py # Librarian tests
│   └── test_static_analyzer.py # Analyzer tests
└── utils/                 # Utility functions
```

## 📚 Documentation

- [Contributing Guide](CONTRIBUTING.md) - How to contribute to Ether
- [Changelog](CHANGELOG.md) - Version history and changes
- [Stabilization Roadmap](STABILIZATION_ROADMAP.md) - Development roadmap

## 🤝 Contributing

We welcome contributions! Please see our [Contributing Guide](CONTRIBUTING.md) for details on:

- Setting up your development environment
- Code style and standards
- Submitting pull requests
- Reporting issues

## 📄 License

This project is licensed under the MIT License - see the LICENSE file for details.

## 🙏 Acknowledgments

- Built with ❤️ for the Godot community
- Inspired by the need for better AI-assisted game development tools
- Thanks to all contributors and users!

## 📬 Contact

- **GitHub Issues**: [Report bugs or request features](https://github.com/ether-ai/ether/issues)
- **Discussions**: [Join the conversation](https://github.com/ether-ai/ether/discussions)

---

**Current Version**: 1.9.8  
**Last Updated**: 2026
