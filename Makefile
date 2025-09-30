# Makefile for CTHarvester development tasks

.PHONY: help install install-dev clean test lint format type-check docs build run pre-commit

# Default target
help:
	@echo "CTHarvester Development Commands"
	@echo "================================="
	@echo ""
	@echo "Setup:"
	@echo "  make install          Install production dependencies"
	@echo "  make install-dev      Install development dependencies"
	@echo ""
	@echo "Code Quality:"
	@echo "  make format           Format code with black and isort"
	@echo "  make lint             Run flake8 linter"
	@echo "  make type-check       Run mypy type checker"
	@echo "  make pre-commit       Run all pre-commit hooks"
	@echo ""
	@echo "Testing:"
	@echo "  make test             Run all tests"
	@echo "  make test-cov         Run tests with coverage report"
	@echo "  make test-fast        Run tests without coverage"
	@echo ""
	@echo "Documentation:"
	@echo "  make docs             Build Sphinx documentation"
	@echo "  make docs-serve       Build and serve documentation"
	@echo ""
	@echo "Build:"
	@echo "  make build            Build executable for current platform"
	@echo "  make build-clean      Clean build artifacts"
	@echo ""
	@echo "Run:"
	@echo "  make run              Run CTHarvester application"
	@echo ""
	@echo "Maintenance:"
	@echo "  make clean            Clean all generated files"
	@echo "  make clean-pyc        Clean Python cache files"

# Installation
install:
	pip install -r requirements.txt

install-dev:
	pip install -r requirements.txt
	pip install -r requirements-dev.txt
	pre-commit install

# Code formatting
format:
	@echo "Running black..."
	black --line-length 100 .
	@echo "Running isort..."
	isort --profile black --line-length 100 .
	@echo "Formatting complete!"

# Linting
lint:
	@echo "Running flake8..."
	flake8 . --count --statistics
	@echo "Linting complete!"

# Type checking
type-check:
	@echo "Running mypy..."
	mypy . --ignore-missing-imports
	@echo "Type checking complete!"

# Pre-commit hooks
pre-commit:
	@echo "Running pre-commit hooks..."
	pre-commit run --all-files

# Testing
test:
	@echo "Running tests with coverage..."
	pytest tests/ --cov=. --cov-report=html --cov-report=term-missing -v

test-cov:
	@echo "Running tests with coverage..."
	pytest tests/ --cov=. --cov-report=html --cov-report=xml --cov-report=term-missing -v
	@echo "Coverage report generated in htmlcov/"

test-fast:
	@echo "Running tests (no coverage)..."
	pytest tests/ -v

test-unit:
	@echo "Running unit tests..."
	pytest tests/ -m unit -v

test-integration:
	@echo "Running integration tests..."
	pytest tests/ -m integration -v

# Documentation
docs:
	@echo "Building documentation..."
	cd docs && make html
	@echo "Documentation built in docs/_build/html/"

docs-serve: docs
	@echo "Serving documentation at http://localhost:8000"
	cd docs/_build/html && python -m http.server

docs-clean:
	cd docs && make clean

# Building
build:
	@echo "Building CTHarvester..."
	python build_cross_platform.py --clean

build-clean:
	@echo "Cleaning build artifacts..."
	rm -rf build dist *.spec
	@echo "Build artifacts cleaned!"

# Running
run:
	python CTHarvester.py

# Cleaning
clean: clean-pyc build-clean docs-clean
	@echo "Removing coverage files..."
	rm -rf .coverage htmlcov/ coverage.xml
	@echo "Removing pytest cache..."
	rm -rf .pytest_cache
	@echo "Removing mypy cache..."
	rm -rf .mypy_cache
	@echo "Clean complete!"

clean-pyc:
	@echo "Removing Python cache files..."
	find . -type d -name __pycache__ -exec rm -rf {} + 2>/dev/null || true
	find . -type f -name '*.pyc' -delete
	find . -type f -name '*.pyo' -delete
	find . -type f -name '*~' -delete
	@echo "Python cache cleaned!"

# Release
release-notes:
	@echo "Generating release notes..."
	python scripts/generate_release_notes.py --tag $(TAG) --output release_notes.md
	@echo "Release notes generated in release_notes.md"

# Development workflow shortcuts
dev-check: format lint test
	@echo "All development checks passed!"

dev-quick: format lint
	@echo "Quick development checks passed!"