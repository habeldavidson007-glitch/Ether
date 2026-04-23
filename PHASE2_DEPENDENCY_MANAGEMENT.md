# Phase 2: Dependency Management & Modern Packaging

## Overview

This document summarizes the migration from the legacy `requirements.txt` approach to a modern, PEP 517-compliant `pyproject.toml` setup for the Ether AI project.

## The Shift to `pyproject.toml`

Previously, the project used a simple `requirements.txt` file to manage dependencies. While functional, this approach lacked:
- Standardized build system configuration
- Optional dependency groups
- Tool configuration in a single location
- Modern Python packaging standards compliance

The new `pyproject.toml` file addresses all these concerns and brings the project in line with current Python best practices.

## Installation

### Basic Installation (Runtime Dependencies Only)

To install only the runtime dependencies needed to run Ether AI:

```bash
pip install -e .
```

### Development Installation (All Dependencies)

To install both runtime and development dependencies (recommended for contributors):

```bash
pip install -e ".[dev]"
```

This installs:
- **Runtime dependencies**: streamlit, requests, numpy, pandas, tqdm, watchdog
- **Development dependencies**: pytest, black, ruff, mypy, isort, pre-commit

## Running Tests, Linters, and Formatters

With the new configuration, running development tools is straightforward:

### Tests (pytest)

```bash
pytest
```

The `pyproject.toml` configures pytest to automatically look in the `tests/` directory for files matching `test_*.py`.

### Code Formatting (black)

```bash
black .
```

Configured with 88-character line length and Python 3.9+ target version.

### Linting (ruff)

```bash
ruff check .
```

Configured to check for:
- **E**: pycodestyle errors
- **F**: Pyflakes errors
- **I**: Import sorting (isort-compatible)

### Type Checking (mypy)

```bash
mypy .
```

Configured for Python 3.9 with strict return type warnings.

### Import Sorting (isort)

```bash
isort .
```

Configured to use the "black" profile for compatibility with the black formatter.

## Benefits of This Change

### 1. Reproducibility
- Single source of truth for all project metadata and dependencies
- Consistent environment setup across different machines and CI/CD pipelines

### 2. Modern Standards Compliance
- PEP 517 compliant build system using hatchling
- Follows current Python packaging best practices
- Better integration with modern tooling and IDEs

### 3. Developer Experience
- Simplified dependency installation with optional groups
- Centralized tool configuration
- Easier onboarding for new contributors

### 4. Flexibility
- Optional dependencies allow users to install only what they need
- Development tools are separated from runtime requirements
- Clean separation between production and development environments

## File Structure

```
ether-ai/
├── pyproject.toml          # Project metadata, dependencies, and tool configs
├── requirements.txt        # DEPRECATED: Legacy file (kept for compatibility)
├── .gitignore              # Updated with dev/IDE exclusions
└── ...
```

## Migration Notes

- The `requirements.txt` file has been marked as deprecated but not removed to avoid breaking existing installations.
- All new installations should use `pip install -e ".[dev]"` instead of `pip install -r requirements.txt`.
- The `.gitignore` has been updated to exclude common development artifacts (caches, virtual environments, IDE files, build artifacts).

## Version Information

- **Project Version**: 1.9.8
- **Minimum Python Version**: 3.9
- **Build System**: hatchling
