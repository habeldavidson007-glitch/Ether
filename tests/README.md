# Ether Test Suite

Comprehensive test coverage for the Ether AI Development Assistant.

## Overview

This test suite ensures:
- ✅ Core functionality works as expected
- ✅ Refactoring doesn't break existing features
- ✅ Edge cases are handled properly
- ✅ Performance remains optimal

## Test Coverage

### Core Modules Tested

1. **test_builder.py** (24 tests)
   - EtherBrain initialization
   - Chat mode switching
   - Response caching
   - Intent detection
   - Query processing
   - Error handling
   - Integration scenarios

2. **test_librarian.py** (22 tests)
   - Inverted index creation and search
   - Mode-aware filtering
   - Knowledge retrieval
   - Edge cases (unicode, special characters, etc.)

3. **test_static_analyzer.py** (19 tests)
   - Finding and ScriptNode dataclasses
   - Static analysis functionality
   - SGMA dependency analysis
   - Math curve loaders
   - Edge cases

**Total: 65 tests**

## Running Tests

### Run All Tests
```bash
cd /workspace
python -m pytest tests/ -v
```

### Run Specific Test File
```bash
python -m pytest tests/test_builder.py -v
python -m pytest tests/test_librarian.py -v
python -m pytest tests/test_static_analyzer.py -v
```

### Run with Coverage
```bash
pip install pytest-cov
python -m pytest tests/ --cov=core --cov-report=html
```

### Run Specific Test Class
```bash
python -m pytest tests/test_builder.py::TestEtherBrainInitialization -v
```

### Run Specific Test
```bash
python -m pytest tests/test_builder.py::TestEtherBrainInitialization::test_brain_creates_successfully -v
```

## Test Structure

```
tests/
├── __init__.py          # Package initialization
├── conftest.py          # Pytest fixtures and configuration
├── test_builder.py      # Tests for EtherBrain (AI pipeline)
├── test_librarian.py    # Tests for knowledge base retrieval
└── test_static_analyzer.py  # Tests for static analysis
```

## Fixtures

The `conftest.py` file provides reusable fixtures:

- `sample_godot_project`: Creates a minimal Godot project structure
- `sample_gdscript_code`: Sample GDScript code for testing
- `sample_tscn_content`: Sample TSCN scene content
- `mock_llm_response`: Mock LLM response for testing

## Adding New Tests

1. Create a new test file: `tests/test_<module>.py`
2. Import the module to test
3. Use descriptive class names: `Test<Feature>`
4. Use descriptive test names: `test_<behavior>_when_<condition>`
5. Follow AAA pattern: Arrange, Act, Assert

Example:
```python
def test_feature_works_correctly():
    # Arrange
    component = Component()
    
    # Act
    result = component.do_something()
    
    # Assert
    assert result == expected_value
```

## Continuous Integration

Add this to your CI pipeline:

```yaml
# GitHub Actions example
name: Tests
on: [push, pull_request]
jobs:
  test:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3
      - name: Set up Python
        uses: actions/setup-python@v4
        with:
          python-version: '3.12'
      - name: Install dependencies
        run: pip install -r requirements.txt pytest
      - name: Run tests
        run: pytest tests/ -v
```

## Test Status

✅ **All 65 tests passing**

Last updated: 2025
