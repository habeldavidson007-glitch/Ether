# Contributing to Ether AI

Thank you for your interest in contributing to Ether! This guide will help you get started.

## 📋 Table of Contents

- [Code of Conduct](#code-of-conduct)
- [Getting Started](#getting-started)
- [Development Setup](#development-setup)
- [Development Workflow](#development-workflow)
- [Code Standards](#code-standards)
- [Testing](#testing)
- [Submitting Changes](#submitting-changes)
- [Reporting Issues](#reporting-issues)

## Code of Conduct

Please be respectful and constructive in all interactions. We welcome contributors of all backgrounds and experience levels.

## Getting Started

1. **Fork the repository** on GitHub
2. **Clone your fork** locally:
   ```bash
   git clone https://github.com/YOUR_USERNAME/ether.git
   cd ether
   ```
3. **Add the upstream remote**:
   ```bash
   git remote add upstream https://github.com/ether-ai/ether.git
   ```

## Development Setup

### Prerequisites

- Python 3.9 or higher
- pip (Python package manager)
- Git
- Virtual environment tool (venv, virtualenv, etc.)

### Setting Up Your Environment

1. **Create a virtual environment**:
   ```bash
   python -m venv .venv
   source .venv/bin/activate  # Linux/macOS
   .venv\Scripts\activate     # Windows
   ```

2. **Install development dependencies**:
   ```bash
   pip install -e ".[dev]"
   ```

3. **Install pre-commit hooks**:
   ```bash
   pre-commit install
   ```

4. **Verify setup**:
   ```bash
   pytest
   ```

## Development Workflow

### Branch Naming

Use descriptive branch names:
- `feature/add-new-analyzer` - New features
- `fix/resolve-cascade-issue` - Bug fixes
- `docs/update-readme` - Documentation updates
- `refactor/improve-performance` - Code refactoring

### Making Changes

1. **Create a new branch**:
   ```bash
   git checkout -b feature/your-feature-name
   ```

2. **Make your changes** following our code standards

3. **Run tests** to ensure nothing is broken:
   ```bash
   pytest
   ```

4. **Run code quality tools**:
   ```bash
   pre-commit run --all-files
   ```

5. **Commit your changes** with clear messages:
   ```bash
   git commit -m "feat: add new scene analyzer"
   ```

### Commit Message Format

We follow a simple commit message convention:

```
<type>: <description>

[optional body]

[optional footer]
```

**Types:**
- `feat`: New feature
- `fix`: Bug fix
- `docs`: Documentation changes
- `style`: Code style changes (formatting, etc.)
- `refactor`: Code refactoring
- `test`: Adding or updating tests
- `chore`: Maintenance tasks

**Example:**
```
feat: add cascade error detection

Implemented CascadeScanner module to detect potential
cascade errors in Godot projects.

Closes #123
```

## Code Standards

### Formatting

We use **Black** for code formatting with a line length of 88 characters.

```bash
black .
```

### Import Sorting

We use **isort** with the Black profile:

```bash
isort .
```

### Linting

We use **Ruff** for fast linting:

```bash
ruff check .
```

### Type Checking

We use **Mypy** for static type checking:

```bash
mypy ether/
```

### Best Practices

1. **Use pathlib for paths**: Always use `pathlib.Path` instead of `os.path`
   ```python
   from pathlib import Path
   
   # Good
   config_path = Path.home() / ".ether" / "config.toml"
   
   # Avoid
   import os
   config_path = os.path.join(os.path.expanduser("~"), ".ether", "config.toml")
   ```

2. **Write docstrings**: All public functions and classes should have docstrings

3. **Add type hints**: Use type annotations for function parameters and return values

4. **Keep functions focused**: Functions should do one thing well

5. **Write tests**: All new features should include tests

## Testing

### Running Tests

```bash
# Run all tests
pytest

# Run with coverage
pytest --cov=ether --cov-report=html

# Run specific test file
pytest tests/test_librarian.py

# Run specific test function
pytest tests/test_librarian.py::test_add_memory

# Run tests matching a pattern
pytest -k "memory"

# Run with verbose output
pytest -v
```

### Writing Tests

1. **Test files** should be named `test_*.py` in the `tests/` directory
2. **Test functions** should be named `test_*`
3. **Use fixtures** from `conftest.py` for common setup
4. **Assert expected behavior** clearly

Example:
```python
def test_librarian_adds_memory(librarian):
    """Test that Librarian correctly adds new memory entries."""
    initial_count = len(librarian.memories)
    
    librarian.add_memory("test_key", "test_value")
    
    assert len(librarian.memories) == initial_count + 1
    assert librarian.get_memory("test_key") == "test_value"
```

## Submitting Changes

### Pull Request Process

1. **Update your branch** with latest upstream changes:
   ```bash
   git fetch upstream
   git rebase upstream/main
   ```

2. **Push to your fork**:
   ```bash
   git push origin feature/your-feature-name
   ```

3. **Create a Pull Request** on GitHub:
   - Provide a clear title and description
   - Reference any related issues
   - Include screenshots if applicable
   - List any breaking changes

4. **Address review feedback** promptly

5. **Ensure all CI checks pass** before requesting merge

### PR Checklist

Before submitting your PR, please ensure:

- [ ] Tests pass locally (`pytest`)
- [ ] Code is formatted (`black .`)
- [ ] Imports are sorted (`isort .`)
- [ ] No linting errors (`ruff check .`)
- [ ] Type checking passes (`mypy ether/`)
- [ ] Documentation is updated
- [ ] Commit messages are clear and follow convention

## Reporting Issues

### Bug Reports

When reporting bugs, please include:

1. **Description**: Clear description of the bug
2. **Steps to Reproduce**: Detailed steps to reproduce the issue
3. **Expected Behavior**: What should happen
4. **Actual Behavior**: What actually happens
5. **Environment**:
   - Python version
   - OS (Windows/Linux/macOS)
   - Ether version
6. **Logs/Error Messages**: Full error output if available

### Feature Requests

When requesting features, please include:

1. **Problem Statement**: What problem does this solve?
2. **Proposed Solution**: How should it work?
3. **Use Cases**: Examples of how it would be used
4. **Alternatives Considered**: Any other approaches you've thought about

## Questions?

If you have questions, feel free to:
- Open a [Discussion](https://github.com/ether-ai/ether/discussions)
- Ask in the PR or issue comments
- Check existing documentation

---

Thank you for contributing to Ether! 🎉
