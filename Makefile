# Makefile for CTHarvester development tasks

.PHONY: help install install-dev clean test lint format type-check docs build run pre-commit lock lock-check

# Default target
help:
	@echo "CTHarvester Development Commands"
	@echo "================================="
	@echo ""
	@echo "Setup:"
	@echo "  make install          Install production dependencies (from this platform's lockfile)"
	@echo "  make install-dev      Install development dependencies (from this platform's lockfile)"
	@echo "  make lock             Regenerate the per-platform lockfiles from pyproject.toml"
	@echo "  make lock-check       Verify the lockfiles are up to date"
	@echo ""
	@echo "Code Quality:"
	@echo "  make format           Format code with ruff"
	@echo "  make lint             Run ruff (lint + format check)"
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
	@echo "  make docs-watch       Live-reloading docs build for authoring"
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

# Dependency locking
# pyproject.toml declares version RANGES; the lockfiles pin exact versions with
# hashes. Regenerate after changing dependencies in pyproject.toml.
#
# The locks are PER-PLATFORM, not universal. `--universal` resolves one version
# per package for all three operating systems at once and does not check wheel
# coverage, so a package whose wheels differ by platform cannot be expressed:
# pyqt5-qt5 publishes Windows wheels only up to 5.15.2 while Linux and macOS
# reach 5.15.19, and the universal lock pinned 5.15.19 for every platform, which
# took down every Windows CI job with "No matching distribution found". That was
# patched with hand-written environment markers in pyproject.toml; resolving once
# per platform removes the need for them and makes the whole class of bug
# impossible, because uv only considers wheels the target platform can install.
#
# Three variants x three platforms, nine files:
#   requirements-<os>.lock         runtime only          (pip-audit, CodeQL)
#   requirements-dev-<os>.lock     + test, lint and docs (test jobs)
#   requirements-build-<os>.lock   + PyInstaller         (build jobs)
#
# The dev lock takes `--extra docs` as well, so `make install-dev` leaves a
# contributor able to run `make docs` and `make docs-watch` straight away.
#
# Compiled at 3.12, which is both `requires-python`'s floor and the only version
# CI runs -- keep the three in step. A per-platform lock cannot fork by Python
# version the way `--universal` could (`--python-platform` and `--universal` are
# mutually exclusive), so this floor is exactly what every install gets.
UV ?= uv
PLATFORMS := linux windows macos
LOCK_ARGS = --python-version 3.12 --generate-hashes
COMPILE = $(UV) pip compile pyproject.toml $(LOCK_ARGS)

# Which lock `make install` uses. Anything that is not Linux or Darwin is
# treated as Windows: `uname -s` reports MINGW64_NT-* / MSYS_NT-* under Git Bash.
# Written as make conditionals rather than a shell `case`, because make counts
# parentheses inside $(shell ...) and a `case` arm's `)` would close it early.
UNAME_S := $(shell uname -s)
ifeq ($(UNAME_S),Linux)
HOST_PLATFORM := linux
else ifeq ($(UNAME_S),Darwin)
HOST_PLATFORM := macos
else
HOST_PLATFORM := windows
endif

lock:
	@for p in $(PLATFORMS); do \
		echo "Locking $$p ..."; \
		$(COMPILE) --python-platform $$p -o requirements-$$p.lock; \
		$(COMPILE) --python-platform $$p --extra dev --extra docs -o requirements-dev-$$p.lock; \
		$(COMPILE) --python-platform $$p --extra build -o requirements-build-$$p.lock; \
	done

# The generated header records the exact command line, which differs between
# `-o file` and `-o -`, so compare only the requirement lines. Kept POSIX-sh
# compatible (no process substitution) since make runs /bin/sh.
#
# The committed lockfile is COPIED to the temp path before recompiling into it.
# `uv pip compile` prefers versions already pinned in its output file, so
# compiling into an empty temp file resolves every dependency to the newest
# release while `make lock` (writing over the committed file) keeps the existing
# pins. Without the copy the two disagree the moment anything upstream ships a
# release, and this gate reports "stale" forever regardless of pyproject.toml.
# Seeding from the committed file asks the question the gate is actually for:
# does re-locking *this* pyproject.toml change anything? Upgrading dependencies
# is Dependabot's job, not this check's.
lock-check:
	@tmp=`mktemp -d`; status=0; \
	for p in $(PLATFORMS); do \
		for spec in "requirements-$$p.lock:" "requirements-dev-$$p.lock:--extra dev --extra docs" "requirements-build-$$p.lock:--extra build"; do \
			f=`echo "$$spec" | cut -d: -f1`; \
			extra=`echo "$$spec" | cut -d: -f2`; \
			cp "$$f" "$$tmp/candidate"; \
			$(COMPILE) --python-platform $$p $$extra -o "$$tmp/candidate" >/dev/null 2>&1; \
			grep -v '^#' "$$tmp/candidate" > "$$tmp/a"; \
			grep -v '^#' "$$f" > "$$tmp/b"; \
			if ! diff -q "$$tmp/a" "$$tmp/b" >/dev/null; then \
				echo "$$f is stale - run 'make lock'"; status=1; \
			fi; \
		done; \
	done; \
	rm -rf "$$tmp"; \
	if [ $$status -eq 0 ]; then echo "Lockfiles are up to date."; fi; \
	exit $$status

# Installation
# Installs come from the lockfile matching this machine's platform, so CI, a new
# contributor and a release build all resolve to byte-identical packages.
install:
	pip install --require-hashes -r requirements-$(HOST_PLATFORM).lock

install-dev:
	pip install --require-hashes -r requirements-dev-$(HOST_PLATFORM).lock
	pre-commit install

# Code formatting (ruff format + import sorting via the I rules)
format:
	@echo "Running ruff format..."
	ruff format .
	@echo "Running ruff check --fix (import sorting and other safe fixes)..."
	ruff check --fix .
	@echo "Formatting complete!"

# Linting - same checks CI gates on
lint:
	@echo "Running ruff check..."
	ruff check .
	@echo "Running ruff format --check..."
	ruff format --check .
	@echo "Linting complete!"

# Type checking
# Same invocation as the gating CI step and the pre-commit hook. Do not widen
# it to `mypy .` without making the other two match: the point of naming the
# directories is that this scope is the one that is kept clean.
type-check:
	@echo "Running mypy..."
	mypy --config-file pyproject.toml core/ utils/ ui/
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
# The published manual is docs/manual/ and nothing else: docs/*.md are
# repository-only notes that Sphinx never sees. See docs/README.md.
docs:
	@echo "Building documentation..."
	cd docs/manual && make html
	@echo "Documentation built in docs/manual/_build/html/"

docs-serve: docs
	@echo "Serving documentation at http://localhost:8000"
	cd docs/manual/_build/html && python -m http.server

# Rebuild and reload the browser on every save. This is the one to use while
# writing docs; `make docs` is a one-shot build.
docs-watch:
	@echo "Watching docs/manual/ - http://localhost:8000 (Ctrl+C to stop)"
	@command -v sphinx-autobuild >/dev/null || { echo "sphinx-autobuild not found - pip install -e '.[docs]'"; exit 1; }
	sphinx-autobuild docs/manual docs/manual/_build/html --port 8000 --open-browser

docs-clean:
	cd docs/manual && make clean

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
