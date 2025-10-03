# Contributing to CTHarvester

Thank you for your interest in contributing to CTHarvester! This document provides guidelines and instructions for contributing.

## Table of Contents

- [Code of Conduct](#code-of-conduct)
- [Getting Started](#getting-started)
- [Development Setup](#development-setup)
- [Development Workflow](#development-workflow)
- [Coding Standards](#coding-standards)
- [Testing Guidelines](#testing-guidelines)
- [Documentation](#documentation)
- [Submitting Changes](#submitting-changes)

## Code of Conduct

By participating in this project, you agree to maintain a respectful and inclusive environment for all contributors.

## Getting Started

1. **Fork the repository** on GitHub
2. **Clone your fork** locally:
   ```bash
   git clone https://github.com/YOUR_USERNAME/CTHarvester.git
   cd CTHarvester
   ```
3. **Add upstream remote**:
   ```bash
   git remote add upstream https://github.com/ORIGINAL_OWNER/CTHarvester.git
   ```

## Development Setup

### Prerequisites

- Python 3.11 or higher (3.12+ recommended)
- Git
- Virtual environment tool (venv or conda)

### Setup Instructions

1. **Create virtual environment**:
   ```bash
   python -m venv venv
   source venv/bin/activate  # Linux/macOS
   # or
   venv\Scripts\activate  # Windows
   ```

2. **Install dependencies**:
   ```bash
   # Install with development dependencies
   pip install -e .[dev]

   # Or install separately
   pip install -e .
   pip install pytest pytest-cov pytest-qt black flake8 mypy pre-commit
   ```

3. **Install pre-commit hooks**:
   ```bash
   pre-commit install
   ```

   This automatically runs code quality checks (black, isort, flake8, mypy) before each commit.

4. **Verify setup**:
   ```bash
   # Run tests
   pytest tests/ -v

   # Run application
   python CTHarvester.py
   ```

## Development Workflow

### 1. Create a Branch

Create a feature branch for your changes:

```bash
git checkout -b feature/your-feature-name
# or
git checkout -b fix/issue-number-description
```

Branch naming conventions:
- `feature/` - New features
- `fix/` - Bug fixes
- `docs/` - Documentation changes
- `refactor/` - Code refactoring
- `test/` - Test additions/changes
- `chore/` - Maintenance tasks

### 2. Make Changes

- Write code following our [coding standards](#coding-standards)
- Add tests for new functionality
- Update documentation as needed
- Run code quality checks frequently

### 3. Run Quality Checks

Before committing, ensure all checks pass:

```bash
# Format code
black .
isort .

# Run linter
flake8 . --max-line-length=100

# Run type checker on core modules
mypy core/ utils/ --ignore-missing-imports

# Run tests
pytest tests/ -v

# Run tests with coverage
pytest tests/ --cov=. --cov-report=html

# Run specific test categories
pytest tests/ -m unit              # Unit tests only
pytest tests/ -m integration       # Integration tests
pytest tests/ -m "not slow"        # Skip slow tests
pytest tests/ -m benchmark         # Performance benchmarks
```

**Pre-commit hooks** will automatically run these checks before each commit.

### 4. Commit Changes

Use [Conventional Commits](https://www.conventionalcommits.org/) format:

```bash
git commit -m "feat: add thumbnail export feature"
git commit -m "fix: resolve memory leak in image processing"
git commit -m "docs: update installation instructions"
```

Commit types:
- `feat:` - New feature
- `fix:` - Bug fix
- `docs:` - Documentation only
- `style:` - Code style changes (formatting)
- `refactor:` - Code refactoring
- `perf:` - Performance improvements
- `test:` - Adding/updating tests
- `build:` - Build system changes
- `ci:` - CI/CD changes
- `chore:` - Maintenance tasks

For breaking changes, add `!` or `BREAKING CHANGE:` in commit body:
```bash
git commit -m "feat!: redesign settings API"
```

### 5. Push and Create Pull Request

```bash
git push origin feature/your-feature-name
```

Then create a pull request on GitHub.

## Coding Standards

### Python Style Guide

We follow PEP 8 with these modifications:

- **Line length**: 100 characters (not 79)
- **Quotes**: Double quotes for strings
- **Imports**: Organized by `isort`
- **Formatting**: Enforced by `black`

### Type Hints

Use type hints for function signatures:

```python
def process_image(
    image_path: str,
    threshold: int = 128,
    invert: bool = False
) -> np.ndarray:
    """Process a single image."""
    pass
```

### Docstrings

Use Google-style docstrings:

```python
def function_name(param1: str, param2: int) -> bool:
    """Short one-line summary.

    Longer description if needed.

    Args:
        param1: Description of param1.
        param2: Description of param2.

    Returns:
        Description of return value.

    Raises:
        ValueError: When validation fails.

    Example:
        >>> result = function_name("test", 42)
        >>> print(result)
        True
    """
    pass
```

### Code Organization

- Keep functions small and focused (< 50 lines)
- Use descriptive variable names
- Avoid global variables
- Separate concerns (UI, business logic, data)
- Use dependency injection where possible

## Testing Guidelines

### Writing Tests

- Place tests in `tests/` directory
- Name test files: `test_<module_name>.py`
- Use descriptive test names: `test_<what>_<condition>_<expected_result>`

Example:

```python
import pytest
from module import function

class TestFunction:
    """Tests for function."""

    def test_function_with_valid_input_returns_expected_result(self):
        """Test function with valid input."""
        result = function("valid")
        assert result == "expected"

    def test_function_with_invalid_input_raises_value_error(self):
        """Test function with invalid input."""
        with pytest.raises(ValueError):
            function("invalid")

    @pytest.mark.parametrize("input,expected", [
        ("a", "A"),
        ("b", "B"),
        ("c", "C"),
    ])
    def test_function_with_various_inputs(self, input, expected):
        """Test function with various inputs."""
        assert function(input) == expected
```

### Running Tests

```bash
# Run all tests
make test

# Run specific test file
pytest tests/test_module.py

# Run specific test
pytest tests/test_module.py::TestClass::test_method

# Run with coverage
make test-cov

# Run only unit tests
make test-unit

# Run only integration tests
make test-integration
```

### Test Coverage

- **Overall**: Maintain ≥85% coverage
- **New modules**: ≥90% coverage required
- **Core modules**: Currently at ~95% coverage
- **Total**: 485+ tests passing

Check coverage report:
```bash
pytest tests/ --cov=. --cov-report=html
open htmlcov/index.html  # View coverage report
```

## Documentation

### Code Documentation

- All public APIs must have docstrings
- Include usage examples in docstrings
- Document complex algorithms
- Add comments for non-obvious code

### User Documentation

When adding new features, update:

- `docs/user_guide.rst` - User-facing features
- `docs/api/` - API documentation
- `README.md` - If affects installation/usage
- `CHANGELOG.md` - Add entry to Unreleased section

### Building Documentation

```bash
# Build HTML documentation
make docs

# Serve documentation locally
make docs-serve

# Visit: http://localhost:8000
```

## Submitting Changes

### Pull Request Process

1. **Update your branch**:
   ```bash
   git fetch upstream
   git rebase upstream/main
   ```

2. **Ensure all checks pass**:
   ```bash
   make dev-check
   ```

3. **Push to your fork**:
   ```bash
   git push origin feature/your-feature-name
   ```

4. **Create Pull Request** on GitHub

5. **Fill out PR template** completely

6. **Link related issues**

### Pull Request Guidelines

**Good PR:**
- Focused on single feature/fix
- Includes tests
- Updates documentation
- Passes all CI checks
- Has clear description
- Links to related issues

**PR Title Format:**
```
type: Brief description

Examples:
feat: Add thumbnail export functionality
fix: Resolve memory leak in image processing
docs: Update installation guide for macOS
```

**PR Description Template:**
```markdown
## Description
Brief description of changes

## Type of Change
- [ ] Bug fix (non-breaking change which fixes an issue)
- [ ] New feature (non-breaking change which adds functionality)
- [ ] Breaking change (fix or feature that would cause existing functionality to not work as expected)
- [ ] Documentation update

## Testing
- [ ] Tests added/updated
- [ ] All tests passing
- [ ] Manual testing performed

## Checklist
- [ ] Code follows style guidelines
- [ ] Self-review performed
- [ ] Comments added for complex code
- [ ] Documentation updated
- [ ] No new warnings
- [ ] Tests added that prove fix/feature works
- [ ] Dependent changes merged and published

## Related Issues
Closes #123
```

### Review Process

1. **Automated Checks**: Must pass before review
   - Tests
   - Linting
   - Code coverage

2. **Code Review**: At least one approving review required
   - Address review comments
   - Update code as needed
   - Request re-review

3. **Merge**: Maintainer will merge when approved

## Development Tips

### Useful Commands

```bash
# Quick formatting check
make format

# Run linter only
make lint

# Fast test run (no coverage)
make test-fast

# Build documentation
make docs

# Clean all generated files
make clean

# Run application
make run
```

### Troubleshooting

**Import errors after updating dependencies:**
```bash
pip install -r requirements.txt --upgrade
```

**Pre-commit hooks failing:**
```bash
pre-commit run --all-files
```

**Tests failing:**
```bash
# Clear pytest cache
rm -rf .pytest_cache
pytest tests/ -v
```

**Type checking issues:**
```bash
mypy . --ignore-missing-imports --no-strict-optional
```

## Project Architecture (Updated Phase 3)

CTHarvester follows a clean, modular architecture after multiple refactoring phases:

```
CTHarvester/
├── core/                      # Core business logic
│   ├── file_handler.py            # File operations & CT stack detection
│   ├── thumbnail_generator.py     # Thumbnail generation (Rust/Python)
│   ├── thumbnail_manager.py       # Thumbnail coordination & workers
│   ├── thumbnail_worker.py        # Worker threads
│   ├── volume_processor.py        # Volume cropping & ROI
│   ├── progress_manager.py        # Progress tracking
│   └── progress_tracker.py        # Simple progress tracker
│
├── ui/                        # User interface
│   ├── main_window.py             # Main application window
│   ├── dialogs/                   # Dialog windows
│   ├── widgets/                   # Custom Qt widgets
│   ├── handlers/                  # UI event handlers
│   └── setup/                     # UI setup modules
│
├── utils/                     # Utilities
│   ├── image_utils.py             # Image processing (with error handling)
│   ├── file_utils.py              # File system utilities
│   ├── settings_manager.py        # YAML-based configuration
│   ├── error_messages.py          # User-friendly error messages
│   └── performance_logger.py      # Performance tracking (NEW in Phase 3)
│
├── config/                    # Configuration
│   ├── constants.py               # Application constants
│   ├── settings.yaml              # Default settings
│   ├── shortcuts.py               # Keyboard shortcuts
│   ├── tooltips.py                # Tooltip definitions
│   ├── i18n.py                    # Internationalization
│   └── view_modes.py              # View mode definitions
│
├── security/                  # Security validation
│   └── file_validator.py          # Secure file operations
│
├── tests/                     # Test suite (485+ tests)
│   ├── conftest.py                # Shared fixtures & mocks
│   ├── test_*.py                  # Test modules
│   └── ...
│
└── docs/                      # Sphinx documentation
    ├── index.rst                  # Documentation index
    ├── user_guide.rst             # User guide
    ├── developer_guide.rst        # Developer guide
    └── changelog.rst              # Version history
```

### Recent Improvements (Phase 2 & 3)

**Phase 2: Type Safety & Testing**
- Reduced `type:ignore` from 28 to 9 (68% reduction)
- Added Protocol definitions for type safety
- Centralized test fixtures in `conftest.py`
- Created performance regression tests

**Phase 3: Production Readiness**
- Added `utils/performance_logger.py` for performance tracking
- Improved exception handling with specific error types
- Added structured logging with `exc_info=True` and `extra_fields`
- Better error diagnostics (MemoryError, OSError, FileNotFoundError, etc.)

## Questions?

- Check [documentation](docs/)
- Search [existing issues](https://github.com/jikhanjung/CTHarvester/issues)
- Ask in [discussions](https://github.com/jikhanjung/CTHarvester/discussions)
- Create new issue if needed

## License

By contributing, you agree that your contributions will be licensed under the same license as the project (MIT License).
