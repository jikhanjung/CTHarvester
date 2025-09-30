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

- Python 3.8 or higher
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
   make install-dev
   # or manually:
   pip install -r requirements.txt
   pip install -r requirements-dev.txt
   ```

3. **Install pre-commit hooks**:
   ```bash
   pre-commit install
   ```

4. **Verify setup**:
   ```bash
   make test
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
make format

# Run linter
make lint

# Run type checker (optional)
make type-check

# Run tests
make test

# Or run all checks at once
make dev-check
```

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

- Aim for >70% overall coverage
- Core modules should have >80% coverage
- Security modules should have >90% coverage

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

## Questions?

- Check [documentation](docs/)
- Search [existing issues](https://github.com/OWNER/CTHarvester/issues)
- Ask in [discussions](https://github.com/OWNER/CTHarvester/discussions)
- Create new issue if needed

## License

By contributing, you agree that your contributions will be licensed under the same license as the project (MIT License).