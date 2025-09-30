Developer Guide
===============

This guide is for developers who want to contribute to or extend CTHarvester.

Architecture Overview
---------------------

Module Structure
~~~~~~~~~~~~~~~~

CTHarvester follows a modular architecture::

    CTHarvester/
    ├── core/                  # Core business logic
    │   ├── progress_tracker.py    # Progress tracking
    │   ├── progress_manager.py    # Progress management
    │   ├── thumbnail_manager.py   # Thumbnail coordination
    │   └── thumbnail_worker.py    # Worker threads
    ├── ui/                    # User interface
    │   ├── main_window.py         # Main application window
    │   ├── dialogs/               # Dialog windows
    │   └── widgets/               # Custom widgets
    ├── utils/                 # Utility functions
    │   ├── settings_manager.py    # YAML settings
    │   └── common.py              # Common utilities
    ├── config/                # Configuration
    │   ├── constants.py           # Application constants
    │   ├── settings.yaml          # Default settings
    │   ├── shortcuts.py           # Keyboard shortcuts
    │   └── tooltips.py            # Tooltip definitions
    ├── security/              # Security modules
    │   └── file_validator.py     # File validation
    └── tests/                 # Test suite

Design Principles
~~~~~~~~~~~~~~~~~

1. **Separation of Concerns**: UI, business logic, and data handling are separate
2. **Modularity**: Each module has a single, well-defined responsibility
3. **Testability**: Core logic is independent of UI for easy testing
4. **Thread Safety**: Proper synchronization for multithreaded operations
5. **Security First**: Input validation and secure file operations

Key Components
~~~~~~~~~~~~~~

**Progress Tracking:**

* ``SimpleProgressTracker``: Linear progress with ETA
* ``ProgressManager``: Weighted multi-level progress
* Signal/slot connections for UI updates

**Thumbnail Generation:**

* ``ThumbnailManager``: Coordinates worker threads
* ``ThumbnailWorker``: Processes individual thumbnails
* Support for both Rust and Python implementations

**Settings Management:**

* YAML-based configuration
* Platform-independent storage
* Import/Export functionality
* Dot notation access (``settings.get('app.language')``)

**Security:**

* ``SecureFileValidator``: Path traversal prevention
* Whitelist-based file extension validation
* Safe file operations

Development Setup
-----------------

Prerequisites
~~~~~~~~~~~~~

* Python 3.8+
* Git
* Virtual environment tool (venv or conda)
* Optional: Rust toolchain for building native module

Setting Up Development Environment
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

1. **Clone and setup:**

   .. code-block:: bash

      git clone https://github.com/yourusername/CTHarvester.git
      cd CTHarvester

      # Create virtual environment
      python -m venv venv
      source venv/bin/activate  # Linux/macOS
      # or
      venv\\Scripts\\activate    # Windows

      # Install dependencies
      pip install -r requirements.txt
      pip install -r requirements-dev.txt  # Development dependencies

2. **Install pre-commit hooks:**

   .. code-block:: bash

      pre-commit install

3. **Run tests:**

   .. code-block:: bash

      pytest tests/

Code Style and Standards
-------------------------

Python Style Guide
~~~~~~~~~~~~~~~~~~

We follow PEP 8 with some modifications:

* Line length: 100 characters (not 79)
* Use double quotes for strings
* Use type hints for function signatures
* Use Google-style docstrings

**Example:**

.. code-block:: python

    def process_image(
        image_path: str,
        threshold: int = 128,
        invert: bool = False
    ) -> np.ndarray:
        """Process a single CT image.

        Args:
            image_path: Path to the image file.
            threshold: Grayscale threshold value (0-255).
            invert: Whether to invert grayscale values.

        Returns:
            Processed image as numpy array.

        Raises:
            FileNotFoundError: If image_path doesn't exist.
            ValueError: If threshold is out of range.
        """
        # Implementation
        pass

Docstring Style
~~~~~~~~~~~~~~~

Use Google-style docstrings for all public APIs:

.. code-block:: python

    def function_name(param1: type1, param2: type2) -> return_type:
        """Short one-line summary.

        Longer description if needed. Can span multiple paragraphs.

        Args:
            param1: Description of param1.
            param2: Description of param2.

        Returns:
            Description of return value.

        Raises:
            ExceptionType: When this exception is raised.

        Example:
            >>> result = function_name("foo", 42)
            >>> print(result)
            'expected output'
        """

Type Hints
~~~~~~~~~~

Use type hints for all function signatures:

.. code-block:: python

    from typing import Optional, List, Dict, Tuple

    def process_files(
        files: List[str],
        options: Optional[Dict[str, Any]] = None
    ) -> Tuple[int, int]:
        """Process multiple files."""
        pass

Testing
-------

Test Organization
~~~~~~~~~~~~~~~~~

Tests are organized by module::

    tests/
    ├── test_progress_tracker.py
    ├── test_thumbnail_manager.py
    ├── test_settings_manager.py
    └── test_file_validator.py

Running Tests
~~~~~~~~~~~~~

**Run all tests:**

.. code-block:: bash

   pytest

**Run specific test file:**

.. code-block:: bash

   pytest tests/test_settings_manager.py

**Run with coverage:**

.. code-block:: bash

   pytest --cov=. --cov-report=html

**Run specific test:**

.. code-block:: bash

   pytest tests/test_settings_manager.py::test_get_nested_setting

Writing Tests
~~~~~~~~~~~~~

Example test structure:

.. code-block:: python

    import pytest
    from core.progress_tracker import SimpleProgressTracker, ProgressInfo

    class TestSimpleProgressTracker:
        """Tests for SimpleProgressTracker class."""

        def test_initialization(self):
            """Test tracker initialization."""
            tracker = SimpleProgressTracker(total_items=100)
            assert tracker.completed_items == 0
            assert tracker.total_items == 100

        def test_update_progress(self):
            """Test progress update."""
            tracker = SimpleProgressTracker(total_items=100)
            tracker.update(increment=10)
            assert tracker.completed_items == 10

        def test_eta_calculation(self):
            """Test ETA calculation after sufficient samples."""
            results = []

            def callback(info: ProgressInfo):
                results.append(info)

            tracker = SimpleProgressTracker(
                total_items=100,
                callback=callback
            )

            for i in range(10):
                time.sleep(0.1)
                tracker.update()

            # After min_samples_for_eta, should have ETA
            assert results[-1].eta_seconds is not None

        @pytest.mark.parametrize("total,increment", [
            (100, 1),
            (1000, 10),
            (50, 5),
        ])
        def test_various_increments(self, total, increment):
            """Test with various total/increment combinations."""
            tracker = SimpleProgressTracker(total_items=total)
            for i in range(0, total, increment):
                tracker.update(increment=increment)
            assert tracker.completed_items == total

Test Coverage Goals
~~~~~~~~~~~~~~~~~~~

* Overall coverage: >70%
* Core modules: >80%
* Security modules: >90%

Contributing
------------

Contribution Workflow
~~~~~~~~~~~~~~~~~~~~~

1. **Fork and Clone:**

   * Fork the repository on GitHub
   * Clone your fork locally
   * Add upstream remote:

     .. code-block:: bash

        git remote add upstream https://github.com/original/CTHarvester.git

2. **Create Feature Branch:**

   .. code-block:: bash

      git checkout -b feature/your-feature-name

3. **Make Changes:**

   * Write code
   * Add tests
   * Update documentation
   * Run tests: ``pytest``
   * Check style: ``flake8`` or ``black --check .``

4. **Commit:**

   .. code-block:: bash

      git add .
      git commit -m "feat: Add your feature description"

   Follow conventional commits format:

   * ``feat:``: New feature
   * ``fix:``: Bug fix
   * ``docs:``: Documentation changes
   * ``refactor:``: Code refactoring
   * ``test:``: Adding tests
   * ``chore:``: Maintenance tasks

5. **Push and Create PR:**

   .. code-block:: bash

      git push origin feature/your-feature-name

   * Create pull request on GitHub
   * Fill out PR template
   * Link related issues
   * Wait for review

Code Review Process
~~~~~~~~~~~~~~~~~~~

All code changes go through review:

1. **Automated Checks:**

   * Tests must pass
   * Code coverage must not decrease
   * Style checks must pass

2. **Manual Review:**

   * At least one approving review required
   * Address review comments
   * Update as needed

3. **Merge:**

   * Squash and merge preferred
   * Delete branch after merge

Pull Request Guidelines
~~~~~~~~~~~~~~~~~~~~~~~

**Good PR:**

* Focused on single feature/fix
* Includes tests
* Updates documentation
* Clear description
* Links to related issues

**PR Template:**

.. code-block:: markdown

   ## Description
   Brief description of changes

   ## Type of Change
   - [ ] Bug fix
   - [ ] New feature
   - [ ] Documentation update
   - [ ] Refactoring

   ## Testing
   - [ ] Tests added/updated
   - [ ] All tests passing
   - [ ] Manual testing performed

   ## Checklist
   - [ ] Code follows style guidelines
   - [ ] Self-review performed
   - [ ] Documentation updated
   - [ ] No new warnings

   ## Related Issues
   Closes #123

Building and Packaging
----------------------

Building Rust Module
~~~~~~~~~~~~~~~~~~~~

.. code-block:: bash

   cd rust_thumbnail
   cargo build --release
   cd ..

The compiled library will be placed in ``target/release/``.

Creating Executable
~~~~~~~~~~~~~~~~~~~

**Using PyInstaller:**

.. code-block:: bash

   # Windows
   pyinstaller --onefile --noconsole --icon=CTHarvester_64.png CTHarvester.py

   # Linux/macOS
   pyinstaller --onefile --icon=CTHarvester_64.png CTHarvester.py

**Output:**

* Executable in ``dist/`` directory
* Standalone, no Python required

Building Documentation
~~~~~~~~~~~~~~~~~~~~~~

.. code-block:: bash

   cd docs
   make html

Output in ``docs/_build/html/``.

Release Process
~~~~~~~~~~~~~~~

1. **Update Version:**

   * Update ``config/constants.py``
   * Update ``docs/conf.py``
   * Update ``setup.py`` (if using)

2. **Update Changelog:**

   * Add release notes
   * List all changes since last release

3. **Create Release:**

   .. code-block:: bash

      git tag -a v1.0.0 -m "Release v1.0.0"
      git push origin v1.0.0

4. **Build Artifacts:**

   * Build executables for all platforms
   * Build documentation
   * Create source distribution

5. **Publish Release:**

   * Create GitHub release
   * Attach built artifacts
   * Copy changelog to release notes
   * Mark as latest release

Debugging Tips
--------------

Logging
~~~~~~~

CTHarvester uses Python's logging module:

.. code-block:: python

   import logging
   logger = logging.getLogger(__name__)

   logger.debug("Detailed information")
   logger.info("General information")
   logger.warning("Warning message")
   logger.error("Error occurred")

Set log level in settings or via command line.

Common Debugging Scenarios
~~~~~~~~~~~~~~~~~~~~~~~~~~~

**Threading Issues:**

* Use ``QMutexLocker`` for thread-safe operations
* Check for race conditions with ``threading.current_thread()``
* Use ``logging`` instead of ``print()`` in threads

**Memory Leaks:**

* Use ``memory_profiler`` to track memory usage
* Check for circular references
* Use weak references where appropriate

**Performance Issues:**

* Profile with ``cProfile``
* Use ``line_profiler`` for line-by-line profiling
* Check I/O operations (often the bottleneck)

**Qt/GUI Issues:**

* Only update UI from main thread
* Use signals/slots for cross-thread communication
* Check event loop is running

Resources
---------

Documentation
~~~~~~~~~~~~~

* `PyQt5 Documentation <https://www.riverbankcomputing.com/static/Docs/PyQt5/>`_
* `NumPy Documentation <https://numpy.org/doc/>`_
* `Pillow Documentation <https://pillow.readthedocs.io/>`_
* `Sphinx Documentation <https://www.sphinx-doc.org/>`_

Tools
~~~~~

* **pytest**: Testing framework
* **black**: Code formatter
* **flake8**: Linter
* **mypy**: Type checker
* **coverage.py**: Coverage reporting
* **PyInstaller**: Executable builder

Community
~~~~~~~~~

* **GitHub Issues**: Bug reports and feature requests
* **Discussions**: Questions and general discussion
* **Pull Requests**: Code contributions
* **Wiki**: Additional documentation

Getting Help
~~~~~~~~~~~~

1. Check this documentation
2. Search existing issues
3. Ask in GitHub Discussions
4. Create new issue if needed

When asking for help, include:

* Python version
* Operating system
* CTHarvester version
* Error message (full traceback)
* Minimal reproduction steps
* What you've tried