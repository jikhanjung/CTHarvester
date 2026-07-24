# Makefile for CTHarvester development tasks

.PHONY: help install install-dev clean test lint format type-check docs build run pre-commit lock lock-check

# Default target
help:
	@echo "CTHarvester Development Commands"
	@echo "================================="
	@echo ""
	@echo "Setup:"
	@echo "  make install          Install production dependencies (from lockfile)"
	@echo "  make install-dev      Install development dependencies (from lockfile)"
	@echo "  make lock             Regenerate requirements*.lock from pyproject.toml"
	@echo "  make lock-check       Verify the lockfiles are up to date"
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
# Installs come from the lockfiles so every machine - CI, a new contributor, a
# release build - resolves to byte-identical packages.
install:
	pip install --require-hashes -r requirements.lock

install-dev:
	pip install --require-hashes -r requirements-dev.lock
	pre-commit install

# Dependency locking
# pyproject.toml declares version RANGES; requirements*.lock pins exact versions
# with hashes. Regenerate after changing dependencies in pyproject.toml.
# --universal produces a single lock valid on Linux/macOS/Windows via markers.
UV ?= uv
LOCK_ARGS = --universal --python-version 3.11 --generate-hashes

lock:
	$(UV) pip compile pyproject.toml $(LOCK_ARGS) -o requirements.lock
	$(UV) pip compile pyproject.toml $(LOCK_ARGS) --extra dev -o requirements-dev.lock
	$(UV) pip compile pyproject.toml $(LOCK_ARGS) --extra build -o requirements-build.lock

# The generated header records the exact command line, which differs between
# `-o file` and `-o -`, so compare only the requirement lines. Kept POSIX-sh
# compatible (no process substitution) since make runs /bin/sh.
lock-check:
	@tmp=`mktemp -d`; status=0; \
	$(UV) pip compile pyproject.toml $(LOCK_ARGS) -o "$$tmp/run.lock" >/dev/null 2>&1; \
	$(UV) pip compile pyproject.toml $(LOCK_ARGS) --extra dev -o "$$tmp/dev.lock" >/dev/null 2>&1; \
	$(UV) pip compile pyproject.toml $(LOCK_ARGS) --extra build -o "$$tmp/build.lock" >/dev/null 2>&1; \
	for pair in "run.lock requirements.lock" "dev.lock requirements-dev.lock" "build.lock requirements-build.lock"; do \
		set -- $$pair; \
		grep -v '^#' "$$tmp/$$1" > "$$tmp/a"; \
		grep -v '^#' "$$2" > "$$tmp/b"; \
		if ! diff -q "$$tmp/a" "$$tmp/b" >/dev/null; then \
			echo "$$2 is stale - run 'make lock'"; status=1; \
		fi; \
	done; \
	rm -rf "$$tmp"; \
	if [ $$status -eq 0 ]; then echo "Lockfiles are up to date."; fi; \
	exit $$status

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
# Bump version.py + roll CHANGELOG + commit + tag v<version>, then push (which
# triggers release.yml to build all platforms and publish the GitHub release).
# BUMP selects the part: patch (default) | minor | major | prerelease.
# Examples:
#   make release BUMP=patch          # 0.2.3 -> 0.2.4, tag, and push
#   make release-local BUMP=minor    # bump + tag locally, do NOT push
#   make release-preview BUMP=patch  # dry run, change nothing
#   make release-set VERSION=1.0.0   # set an explicit version, tag, and push
BUMP ?= patch

release:
	python scripts/bump_version.py $(BUMP) --push

release-local:
	python scripts/bump_version.py $(BUMP)

release-preview:
	python scripts/bump_version.py $(BUMP) --dry-run

release-set:
	python scripts/bump_version.py --set $(VERSION) --push

# Draft a CHANGELOG section from conventional commits (a writing aid; the
# curated CHANGELOG.md is what release.yml actually publishes).
release-notes:
	@echo "Drafting release notes from commits..."
	python scripts/generate_release_notes.py --tag $(TAG) --output release_notes.md
	@echo "Draft written to release_notes.md — hand-edit into CHANGELOG.md"

# Development workflow shortcuts
dev-check: format lint test
	@echo "All development checks passed!"

dev-quick: format lint
	@echo "Quick development checks passed!"
