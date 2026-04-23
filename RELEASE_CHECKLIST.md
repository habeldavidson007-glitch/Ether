# Ether AI v1.9.8 Release Checklist

## 📋 Pre-Release Preparation

### Code Quality
- [ ] All 65+ tests passing (`pytest`)
- [ ] Code formatted with Black (`black .`)
- [ ] Imports sorted with isort (`isort .`)
- [ ] No linting errors (`ruff check .`)
- [ ] Type checking passes (`mypy ether/`)
- [ ] Pre-commit hooks pass (`pre-commit run --all-files`)
- [ ] CI/CD pipeline green on GitHub Actions

### Documentation
- [ ] README.md updated with current features
- [ ] CHANGELOG.md includes all changes for v1.9.8
- [ ] CONTRIBUTING.md is current
- [ ] Docstrings added for new public functions/classes
- [ ] Version numbers consistent across all files:
  - [ ] `pyproject.toml` (version = "1.9.8")
  - [ ] `README.md` badge and text
  - [ ] `CHANGELOG.md` heading
  - [ ] `__init__.py` (if applicable)

### Dependencies
- [ ] `pyproject.toml` dependencies are up to date
- [ ] `requirements.txt` marked as deprecated
- [ ] No security vulnerabilities in dependencies

---

## 🧪 Testing

### Unit Tests
- [ ] Run full test suite: `pytest -v`
- [ ] Verify 65+ tests pass
- [ ] Check code coverage: `pytest --cov=ether --cov-report=html`
- [ ] Review coverage report in `htmlcov/index.html`

### Integration Tests
- [ ] Test on Linux/Ubuntu
- [ ] Test on macOS (if available)
- [ ] Test on Windows (if available)
- [ ] Verify cross-platform path handling works

### Manual Testing
- [ ] Test basic commands:
  - [ ] `python -m ether analyze <project>`
  - [ ] `python -m ether fix <project>`
  - [ ] `python -m ether scan <project>`
- [ ] Test Streamlit interface: `streamlit run ui/app.py`
- [ ] Verify installation: `pip install -e ".[dev]"`

---

## 📦 Build & Package

### Local Build
- [ ] Build package: `python -m build`
- [ ] Verify dist/ contains:
  - [ ] `.tar.gz` source distribution
  - [ ] `.whl` wheel distribution
- [ ] Validate with twine: `twine check dist/*`

### Installation Test
- [ ] Create fresh virtual environment
- [ ] Install from built package
- [ ] Verify all modules import correctly
- [ ] Run smoke tests

---

## 🔖 Git & Tagging

### Repository State
- [ ] All changes committed
- [ ] Main/master branch is stable
- [ ] No unmerged feature branches blocking release

### Tagging
- [ ] Create annotated tag:
  ```bash
  git tag -a v1.9.8 -m "Release v1.9.8 - Stabilization Complete"
  ```
- [ ] Verify tag:
  ```bash
  git show v1.9.8
  ```
- [ ] Push tag to remote:
  ```bash
  git push origin v1.9.8
  ```

---

## 🚀 Publishing

### PyPI (Optional/Future)
- [ ] Upload to TestPyPI first:
  ```bash
  twine upload --repository testpypi dist/*
  ```
- [ ] Test installation from TestPyPI
- [ ] Upload to PyPI:
  ```bash
  twine upload dist/*
  ```

### GitHub Release
- [ ] Go to GitHub Releases page
- [ ] Create new release from tag v1.9.8
- [ ] Add release notes from CHANGELOG.md
- [ ] Attach built distributions (optional)
- [ ] Mark as latest release
- [ ] Publish release

---

## 📢 Post-Release

### Communication
- [ ] Announce release on GitHub Discussions
- [ ] Update project website (if applicable)
- [ ] Notify contributors
- [ ] Share on social media (optional)

### Cleanup
- [ ] Delete any temporary test files
- [ ] Clean build artifacts: `rm -rf dist/ build/ *.egg-info`
- [ ] Archive release notes and documentation

### Next Steps
- [ ] Create v1.9.9 milestone
- [ ] Plan next release features
- [ ] Review open issues and PRs

---

## ✅ Final Verification

Before marking release complete:

- [ ] All checklist items completed
- [ ] Tests passing on CI/CD
- [ ] Documentation accessible
- [ ] Release published on GitHub
- [ ] No critical bugs reported

---

**Release Manager**: _________________  
**Release Date**: ___________________  
**Status**: ☐ In Progress ☐ Complete ☐ Blocked

---

*Note: This checklist ensures a smooth, reproducible release process. Do not skip steps.*
