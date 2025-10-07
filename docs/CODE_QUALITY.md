# Code Quality Guidelines

This document describes the code quality tools and practices used in CTHarvester.

## Overview

CTHarvester uses multiple automated tools to maintain code quality:

- **Black**: Code formatter for consistent style
- **isort**: Import statement organizer
- **Flake8**: Linter for code quality and style
- **mypy**: Static type checker
- **Bandit**: Security linter
- **pre-commit**: Automated hook system

## Quick Start

### Install Development Dependencies

```bash
pip install -e ".[dev]"
```

### Install Pre-commit Hooks

```bash
pre-commit install
```

This will automatically run all quality checks before each commit.

### Manual Checks

Run all checks manually:

```bash
pre-commit run --all-files
```

Run specific tools:

```bash
# Format code with Black
black .

# Sort imports with isort
isort .

# Run linter
flake8 .

# Type check with mypy
mypy core/ utils/

# Security scan
bandit -r . -ll
```

## Tool Configuration

### Black (Code Formatter)

**Configuration**: `pyproject.toml` → `[tool.black]`

**Settings**:
- Line length: 100 characters
- Target Python versions: 3.8-3.12
- Auto-formats on commit via pre-commit

**Usage**:
```bash
black .                    # Format all files
black --check .            # Check without modifying
black --diff .             # Show diff without modifying
```

### isort (Import Organizer)

**Configuration**: `pyproject.toml` → `[tool.isort]`

**Settings**:
- Profile: black (compatible with Black)
- Line length: 100 characters
- Multi-line output: 3 (vertical hanging indent)

**Usage**:
```bash
isort .                    # Sort all imports
isort --check .            # Check without modifying
isort --diff .             # Show diff without modifying
```

### Flake8 (Linter)

**Configuration**: `.flake8`

**Settings**:
- Max line length: 100 characters
- Max cyclomatic complexity: 15
- Docstring convention: Google style
- Ignored errors: E203, W503, E501 (Black conflicts)

**Usage**:
```bash
flake8 .                   # Lint all files
flake8 core/               # Lint specific directory
flake8 --statistics .      # Show error statistics
```

**Common Error Codes**:
- `E###`: PEP 8 style errors
- `W###`: PEP 8 style warnings
- `F###`: PyFlakes errors (imports, undefined names)
- `C###`: McCabe complexity
- `D###`: Docstring errors

### mypy (Type Checker)

**Configuration**: `pyproject.toml` → `[tool.mypy]`

**Settings**:
- Python version: 3.11+
- Strict mode: Gradually enforced per module
- Ignores: Qt widgets (PyQt5 stub issues)

**Strictness Levels**:

1. **Fully Typed** (strictest):
   - `core/file_handler.py`
   - `utils/image_utils.py`
   - `utils/settings_manager.py`
   - `utils/common.py`
   - All UI handlers

2. **Check Bodies** (permissive):
   - Most other modules
   - Type errors caught in function bodies
   - Missing annotations allowed

3. **Ignored**:
   - `ui/widgets/*` (Qt compatibility issues)
   - `tests/*` (not type-checked)

**Usage**:
```bash
mypy core/ utils/          # Type check specific modules
mypy --strict core/        # Run in strict mode
mypy --install-types       # Install missing type stubs
```

### Bandit (Security Linter)

**Configuration**: `.pre-commit-config.yaml`

**Settings**:
- Confidence level: LOW
- Severity level: LOW
- Skipped tests: B101 (assert_used), B601 (paramiko)

**Usage**:
```bash
bandit -r . -ll            # Scan all files
bandit -r core/ -ll        # Scan specific directory
bandit -r . -f json -o bandit-report.json  # JSON report
```

**Common Issues**:
- `B608`: Hardcoded SQL
- `B310`: URL open without timeout
- `B404`: subprocess usage

### Pre-commit Hooks

**Configuration**: `.pre-commit-config.yaml`

**Hooks** (in order):
1. **black**: Format code
2. **isort**: Sort imports
3. **flake8**: Lint code
4. **pyupgrade**: Upgrade syntax (Python 3.8+)
5. **trailing-whitespace**: Remove trailing spaces
6. **end-of-file-fixer**: Ensure files end with newline
7. **check-yaml**: Validate YAML syntax
8. **check-added-large-files**: Prevent large files (>1MB)
9. **check-merge-conflict**: Detect merge conflicts
10. **check-toml**: Validate TOML syntax
11. **debug-statements**: Catch debug statements
12. **mixed-line-ending**: Fix line endings (LF)
13. **mypy**: Type check core modules
14. **bandit**: Security scan

**Usage**:
```bash
# Install hooks (one-time)
pre-commit install

# Run manually
pre-commit run --all-files

# Run specific hook
pre-commit run black --all-files

# Update hook versions
pre-commit autoupdate

# Skip hooks (emergency only)
git commit --no-verify
```

## Coding Standards

### Style Guide

- **Line length**: 100 characters
- **Indentation**: 4 spaces (no tabs)
- **Quotes**: Double quotes for strings, single for dict keys
- **Imports**: Grouped by stdlib, third-party, local
- **Docstrings**: Google style
- **Type hints**: Required for new code in core/utils

### Docstring Format

```python
def process_image(image_path: str, size: int = 256) -> np.ndarray:
    """Process an image file and return numpy array.

    Args:
        image_path: Path to the image file
        size: Target size for resizing (default: 256)

    Returns:
        Processed image as numpy array

    Raises:
        FileNotFoundError: If image file doesn't exist
        ValueError: If size is invalid

    Example:
        >>> img = process_image("/path/to/image.png", size=512)
        >>> img.shape
        (512, 512, 3)
    """
    # Implementation
    pass
```

### Type Hints

```python
from typing import Optional, List, Dict, Tuple

# Basic types
def get_name() -> str:
    return "CTHarvester"

# Optional types
def find_file(path: str) -> Optional[str]:
    # Returns str or None
    pass

# Collections
def get_files() -> List[str]:
    return ["file1.txt", "file2.txt"]

# Complex types
def process_data(
    input_data: Dict[str, int],
    options: Optional[List[str]] = None
) -> Tuple[bool, str]:
    return True, "Success"
```

## CI/CD Integration

### GitHub Actions

Pre-commit hooks run automatically on:
- Pull requests
- Pushes to main branch
- Manual workflow dispatch

**Workflow**: `.github/workflows/lint.yml` (if exists)

### Local Development

1. **Before committing**:
   ```bash
   # Hooks run automatically
   git add .
   git commit -m "Your message"
   ```

2. **If hooks fail**:
   - Fix the issues shown
   - Re-add modified files: `git add .`
   - Commit again

3. **Skip hooks** (not recommended):
   ```bash
   git commit --no-verify
   ```

## Troubleshooting

### Hook Failures

**Black/isort modified files**:
- Files are auto-formatted
- Re-add them: `git add .`
- Commit again

**Flake8 errors**:
- Fix the reported issues
- Common: unused imports, undefined names, line length
- Ignore specific line: `# noqa: E501`

**mypy errors**:
- Add type hints or fix type mismatches
- Ignore specific line: `# type: ignore[error-code]`
- Add to exclusions if Qt-related

**Bandit warnings**:
- Review security implications
- Fix or add `# nosec` comment if safe

### Performance

**Slow pre-commit**:
```bash
# Run only modified files
git commit

# Skip slow hooks
SKIP=mypy,bandit git commit
```

**Cache issues**:
```bash
# Clear pre-commit cache
pre-commit clean

# Reinstall hooks
pre-commit install --install-hooks --overwrite
```

## Best Practices

### Code Reviews

1. **Run checks before PR**:
   ```bash
   pre-commit run --all-files
   pytest
   ```

2. **Address all linter warnings**
3. **Add type hints to new functions**
4. **Write docstrings for public APIs**
5. **Keep cyclomatic complexity < 15**

### Gradual Improvement

- **New code**: Full type hints + docstrings
- **Modified code**: Add type hints if touching >20 lines
- **Legacy code**: Improve gradually, don't rewrite

### Exceptions

When to skip rules:
- **Tests**: Docstrings optional
- **Scripts**: Less strict typing
- **Qt widgets**: Skip type checking
- **Generated code**: Exclude from linting

## Resources

- [Black Documentation](https://black.readthedocs.io/)
- [isort Documentation](https://pycqa.github.io/isort/)
- [Flake8 Documentation](https://flake8.pycqa.org/)
- [mypy Documentation](https://mypy.readthedocs.io/)
- [Bandit Documentation](https://bandit.readthedocs.io/)
- [pre-commit Documentation](https://pre-commit.com/)
- [PEP 8 Style Guide](https://peps.python.org/pep-0008/)
- [Google Python Style Guide](https://google.github.io/styleguide/pyguide.html)
