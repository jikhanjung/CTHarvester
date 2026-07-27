# Code Quality Guidelines

This document describes the code quality tools and practices used in CTHarvester.

## Overview

CTHarvester uses multiple automated tools to maintain code quality:

- **Ruff**: Linter *and* formatter — replaces Black, isort, Flake8, pyupgrade and pylint
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
# Format code (and sort imports, via the I rules)
ruff format .
ruff check --fix .

# Lint — exactly what CI gates on
ruff check .
ruff format --check .

# Type check with mypy
mypy core/ utils/

# Security scan
bandit -r . -ll
```

## Tool Configuration

### Ruff (Linter + Formatter)

**Configuration**: `pyproject.toml` → `[tool.ruff]`

Ruff replaced Black, isort, Flake8, pyupgrade and pylint. One tool, one config,
one version to keep in sync.

**Settings**:
- Line length: 100 characters
- Target version: `py311` (matches `requires-python`)
- Rule groups: `E`, `F` (the flake8 core), `I` (isort), `N` (pep8-naming),
  `UP` (pyupgrade), `B` (bugbear), `C4` (comprehensions), `LOG`, `RUF012`
- Markdown is excluded from the formatter: ruff formats Python inside fences,
  which rewrites documentation examples nobody reviewed.

**Version pinning**: the exact version appears in three places and they must
match — `pyproject.toml` (dev extra, which feeds `requirements-dev-<os>.lock`),
`.pre-commit-config.yaml` (`rev`), and the `lint` job in
`.github/workflows/test.yml` (which installs from the lockfile). A newer ruff
formats code the pinned one accepted, so an accidental bump turns unrelated PRs
red. Bump all three together.

**Usage**:
```bash
ruff format .              # Format all files
ruff format --check .      # Check without modifying
ruff format --diff .       # Show diff without modifying
ruff check .               # Lint
ruff check --fix .         # Lint and apply safe fixes
ruff check --statistics .  # Counts per rule
```

**Deliberate exemptions** (`[tool.ruff.lint.per-file-ignores]`):
- `__init__.py` — `F401`, these files exist to re-export.
- `ui/**`, `CTHarvester.py` — `N802`/`N803`/`N815`. Qt dictates the spelling of
  every method it calls back into (`paintGL`, `mousePressEvent`); renaming them
  does not make the code more PEP 8, it makes it not work.
- `tests/**`, `scripts/**` — naming and import rules relaxed for test helpers
  and one-off analysis scripts.

**Still off, tracked in `TODOs.md`**: `C901` (complexity — refactor-sized),
plus the `DTZ`, `S`, `PTH`, `TRY` and `SIM` groups, which are worth adding one
at a time rather than in one large sweep.

### mypy (Type Checker)

**Configuration**: `pyproject.toml` → `[tool.mypy]`

**Settings**:
- Python version: 3.12+
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
1. **ruff-check**: Lint and apply safe fixes (includes import sorting and the
   syntax upgrades pyupgrade used to do)
2. **ruff-format**: Format code
3. **trailing-whitespace**: Remove trailing spaces
4. **end-of-file-fixer**: Ensure files end with newline
5. **check-yaml**: Validate YAML syntax
6. **check-added-large-files**: Prevent large files (>1MB)
7. **check-merge-conflict**: Detect merge conflicts
8. **check-toml**: Validate TOML syntax
9. **debug-statements**: Catch debug statements
10. **mixed-line-ending**: Fix line endings (LF)
11. **mypy**: Type check core modules
12. **bandit**: Security scan

**Usage**:
```bash
# Install hooks (one-time)
pre-commit install

# Run manually
pre-commit run --all-files

# Run specific hook
pre-commit run ruff-format --all-files

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

**ruff-format / ruff-check modified files**:
- Files are auto-formatted and safely auto-fixed
- Re-add them: `git add .`
- Commit again

**ruff-check errors that are not auto-fixable**:
- Fix the reported issues
- Common: undefined names, unused locals, mutable class defaults
- Ignore a specific line: `# noqa: <CODE>` — always with a reason, never bulk

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

- [Ruff Documentation](https://docs.astral.sh/ruff/)
- [mypy Documentation](https://mypy.readthedocs.io/)
- [Bandit Documentation](https://bandit.readthedocs.io/)
- [pre-commit Documentation](https://pre-commit.com/)
- [PEP 8 Style Guide](https://peps.python.org/pep-0008/)
- [Google Python Style Guide](https://google.github.io/styleguide/pyguide.html)
