# Changelog

All notable changes to CTHarvester will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

<!--
Add entries for the next release under [Unreleased] as you merge changes, using
the Keep a Changelog groups: Added / Changed / Deprecated / Removed / Fixed /
Security. `scripts/bump_version.py` renames this section to the new version at
release time, and release.yml publishes it verbatim as the GitHub release body.
-->

## [Unreleased]

### Changed
- **The Windows installer is now a per-user install into
  `%LOCALAPPDATA%\Programs\PaleoBytes\CTHarvester`** and no longer asks for administrator
  rights. It also carries a publisher name and a stable application id, so future
  versions upgrade in place instead of installing beside each other, and its Start
  menu shortcut sits in a PaleoBytes group alongside Modan2 and PaperMeister.
  Your preferences and logs are untouched by install or uninstall — both live
  under `%USERPROFILE%\PaleoBytes\CTHarvester`.
- **Preferences are now `preferences.json` in your OS configuration directory**,
  under `PaleoBytes/CTHarvester`:
  `%LOCALAPPDATA%\PaleoBytes\CTHarvester` on Windows,
  `~/Library/Application Support/PaleoBytes/CTHarvester` on macOS,
  `~/.config/PaleoBytes/CTHarvester` on Linux. They were previously written as
  `settings.yaml` under `%APPDATA%\CTHarvester` or `~/.config/CTHarvester`, and
  Export/Import in the Settings dialog now reads and writes JSON as well.

  **Logs stay where they are**, under `~/PaleoBytes/CTHarvester/logs/`. Settings
  and data are kept in separate roots on purpose: preferences are machine-local
  state that costs nothing to lose and set again, which is not true of anything
  else the application keeps for you, and a configuration file stored inside a
  directory whose own location is configurable cannot be read without first
  knowing where it is.

  `CTHARVESTER_CONFIG_DIR` and `CTHARVESTER_DATA_DIR` override the two roots.
  `CTHARVESTER_LOG_DIR` now moves the in-application log viewer and "Open log
  directory" along with the log files themselves — previously it moved only the
  files, and the UI kept looking at the default directory.
- **There is now one settings file.** `config/settings.yaml` held a second,
  hand-maintained copy of the defaults and has been removed; the defaults are
  defined once, in `SettingsManager._get_default_settings()`. The two copies had
  already drifted — the YAML carried three keys nothing reads and was missing
  three the application writes — and it was never bundled into the frozen build,
  so released versions had always run on the Python defaults while the manual
  documented the file.
- Startup no longer creates empty `data/` and `backups/` directories in your
  profile. They came from constants inherited from Modan2, which has a database;
  CTHarvester has none and nothing ever read them.

### Fixed
- **The manual documented preference and log locations that did not exist.** The
  log path was given three different wrong ways (`%APPDATA%\PaleoBytes\...`,
  `~/.local/share/PaleoBytes/...`, a `ctharvester_*.log` filename), the settings
  schema example used key names the application does not have, and a
  "database repair" section described a SQLite cache CTHarvester has never had.

### Changed / Internal

Nothing in this group changes how the application behaves. It is recorded
because most of it was found by measuring something that had never been
measured, and the same checks now run on every commit.

- **Type checking now covers the whole shipped tree.** `ui/widgets/` was the
  last excluded directory and the mypy exclude list is empty. Bringing it in
  surfaced two defects that the exclusion had been hiding: `MCubeWidget`
  assigned `self.parent`, which replaces `QWidget.parent()` on the instance so
  callers get the 2D viewer instead of the parent widget, and every mouse
  handler in `ObjectViewer2D` — plus `resizeEvent` — dereferenced collaborators
  that are attached after construction, so those four paths raised
  `AttributeError` on a viewer built on its own. Neither is reachable in the
  running application, where the collaborators are always wired up.
- **Property-based tests replace the placeholder.** `tests/property/` held one
  test whose body was `pytest.skip("Template")`; it now carries 14 properties
  over image downsampling, overflow-safe image averaging, and ROI coordinate
  handling. Hypothesis itself turned out not to be configured at all: the
  settings lived in a `[tool.hypothesis]` table in `pyproject.toml`, which
  Hypothesis does not read, so the runs were not deterministic as intended.
- **The test suite no longer writes your real preferences file.** The
  integration tests isolate settings with an environment variable, and the name
  they used was not one the application reads. Since closing a window saves
  settings, every run of those tests wrote the developer's own
  `preferences.json`. This only ever affected people running the test suite from
  a source checkout.
- Three tests that could not fail were repaired: an ETA test whose tolerance
  depended on how busy the CI machine was (it had failed on macOS three times),
  an assertion comparing two unrelated clocks, and a settings test whose body
  was skipped by a guard checking for an attribute under the wrong name. A
  handful of others asserted on literals they had just written rather than on
  anything the application computed.
- `tests/test_basic.py` was removed. It had been excluded from CI while still
  passing locally, and each of its six tests is covered — in some cases more
  strictly — by `test_smoke.py` or by the dedicated test file for the module
  concerned.
- The `bandit` security scan was reviewed against Ruff's `S` rules, which now
  implement 73 of its 75 checks. It stays: `B613` (bidirectional Unicode control
  characters, the "Trojan Source" class) has no Ruff equivalent and applies to
  any codebase. The reasoning is recorded next to the command.

## [0.2.3-beta.3] - 2026-07-27

### Added
- **Automatic initial setup after thumbnail generation.** The smallest pyramid
  level is analysed to detect an intensity threshold (Otsu's method), a region of
  interest, and the slice range containing the specimen; all three are applied as
  starting values and reported in the status line. Reset restores the full frame
  as before. When the scan does not separate cleanly the existing defaults are
  left untouched rather than a poor guess being applied.
- Release automation: `scripts/bump_version.py` (+ `make release`) bumps
  `version.py`, rolls this changelog, and tags `v<version>`; `release.yml`
  publishes the tag's changelog section with SHA256 checksums.

### Changed
- **The Rust thumbnail generator is now used by default.** `use_rust_module`
  shipped as `false`, so the compiled module was skipped even when present and
  every install ran the pure-Python path. The handler already falls back to
  Python on its own if the import fails, so the `false` default bought nothing.
  Existing installations keep whatever value their settings file already holds;
  change it under Settings, or delete the settings file to pick up the new
  default.

### Removed
- **Python 3.11 support. CTHarvester now requires Python 3.12.** This is a CI
  decision more than a technical one: a three-version sweep across three
  operating systems cost a lot and told us little, because neither group of
  users is exposed to the difference — anyone running from source sets up their
  own environment, and anyone installing a release gets a bundled interpreter
  and never chooses a Python version. Testing three versions while shipping one
  interpreter is effort spent on a risk nobody carries. `requires-python`, the
  CI matrix and the lockfiles' compile floor all say 3.12 now, and the locks
  moved up to numpy 2.5.1 / scipy 1.18.0 with the floor. If you run from source
  on 3.11, install 3.12.

### Changed / Internal
- **The published manual moved to `docs/manual/`.** The Sphinx source directory
  (`conf.py`, every `.rst`, `locale/`, `_templates/`) is now separated from the
  repository-only Markdown notes by a directory rather than by file extension.
  The old split relied on Sphinx not reading `.md` — an invisible rule that had
  already let a complete settings reference go unpublished, and one that adding
  `myst_parser` would have quietly inverted. Published URLs are unchanged. The
  Pages deploy now triggers on `docs/manual/**` instead of all of `docs/`, so
  editing an internal note no longer redeploys the site. Matches Modan2's layout.
- The documentation toolchain is part of the dev lockfiles (`--extra dev --extra
  docs`), so `make install-dev` leaves `make docs` and `make docs-watch` working
  without a second install.
- **Dependency lockfiles are per-platform instead of universal.** One
  `--universal` lock resolved a single version per package for all three
  operating systems and did not check wheel coverage, so a package whose wheels
  differ by platform could not be expressed — `pyqt5-qt5` publishes Windows
  wheels only up to 5.15.2, the lock pinned 5.15.19 everywhere, and every
  Windows CI job failed to install. There are now nine locks
  (`requirements[-dev|-build]-{linux,windows,macos}.lock`), each resolved
  against wheels its own platform can actually install, and the hand-written
  `pyqt5-qt5` environment markers that patched the symptom are gone. `pip-audit`
  now audits all three platform locks rather than only the Linux one, so
  Windows-only pins are no longer invisible to it. Contributors run the same
  `make install-dev`; it picks the lock matching the machine.
- CI/CD consolidated to nine workflows aligned with Modan2's layout.
- Linting and formatting consolidated onto **Ruff** (pinned `0.16.0`), replacing
  black, isort, flake8, pyupgrade and pylint. `ruff check` and
  `ruff format --check` now gate CI. Type annotations across the codebase were
  modernized to PEP 585/604 syntax (`Dict[str, X]` → `dict[str, X]`,
  `Optional[X]` → `X | None`) as part of the sweep.
- Previously-disabled lint rules that catch real defects are enabled and clean:
  undefined names, redefinitions, unused locals, bare excepts, mutable default
  arguments, blind `pytest.raises(Exception)` and redundant exception tuples.
- **pytest 9.** The test dependency moved from 8.4.2 to 9.1.1, declared as
  `>=9.0.0,<10.0.0` rather than a widened ceiling: the lockfiles pin an exact
  version and the resolver prefers the pin it already has, so a range that still
  admitted pytest 8 would have left the suite on pytest 8 indefinitely. The
  floor is what moves it. All five pytest plugins already resolved against 9
  within their existing ranges, and the full suite (1,311 tests, including slow
  and benchmark) passes unchanged — no test or configuration needed adjusting.
- **`SIM` and `TRY` lint rules enabled.** The one with teeth is `TRY400`:
  49 `except` blocks logged with `logger.error`, which records the message and
  throws the traceback away. They now use `logger.exception`, so a failure
  report carries the stack that produced it. The redundant `: {e}` those
  messages used to append is gone with it — the traceback has the exception.
  `TRY300` followed: 20 `try` blocks now put their success path in an `else`,
  so the `except` only guards what can actually fail. `TRY003` and `TRY301`
  remain off; `pyproject.toml` says why next to each.
- **`PTH` lint rules enabled; shipped code converted to `pathlib`.** 221 call
  sites across `security/`, `config/`, `utils/`, `core/`, `ui/` and `scripts/`,
  done in five verified stages. Public signatures still return `str` — `Path` is
  an internal detail — so nothing about the module APIs changed. The test tree's
  322 sites are waived, because converting them would change the types the tests
  feed the code under test. Two latent problems surfaced on the way: the
  documentation build resolved the repository root from the process working
  directory (wrong under `make docs-watch`), and `get_file_list()` was returning
  `Path` objects from a function declared to return strings.
- **`S` (bandit) lint rules enabled.** No existing vulnerability was found — the
  separate `bandit` job already covered this code — so the value is prospective:
  `eval`, `pickle`, `shell=True`, weak hashes and hardcoded secrets now fail in
  the PR's lint step rather than in a separate workflow. Of the 2,166 raw
  findings, 2,138 were `assert` and friends inside the test suite, waived for
  `tests/**`; the subprocess rules are waived with reasons in `pyproject.toml`;
  three `try`/`except`/`pass` blocks were fixed.

### Fixed
- **Documentation described features that do not exist.** The "Keyboard Power
  User Shortcuts" and "Hidden Features" sections of the advanced features guide
  listed nine shortcuts, three double-click actions, two middle-click actions,
  three context menus and drag-and-drop, none of which are implemented; two of
  the shortcuts it did list were bound to something else (`Ctrl+0` is fit-to-
  window, not reset-threshold). Corrected against `config/shortcuts.py`.
- Test count and coverage figures in the READMEs and docs were stale (1,150
  tests / ~91%; actual 1,295 / ~79%), and the Rust speedup was quoted as
  "10-50x" in nine places against the project's own measurements of 3-10x.
- **The packaged Linux build could not start.** PyOpenGL selects its backend by
  dotted-name import at runtime, which PyInstaller's static analysis cannot see,
  so no backend was bundled and the frozen executable died during import. Found
  by the new packaged-artifact smoke test, which now runs the frozen build
  headless on Windows, macOS and Linux after every build.
- `find_image_files()` accepted a `recursive` argument that was documented but
  never implemented; passing it returned a non-recursive result. Removed.
- `MainWindow.update_curr_slice` recomputed a bounding box and slice position and
  discarded both — a leftover copy of logic that moved to `ViewManager` during the
  Phase 4.4 handler extraction.
- Two tests passed only by accident: one asserted nothing unless run as root, the
  other left `config.constants` on its import-failure fallback for the rest of the
  session, breaking a later test depending on collection order.
- `make lock-check` (the gating `dependency-lock` CI job) reported the lockfiles
  stale whenever any dependency published a release, regardless of whether
  `pyproject.toml` had changed.
- **The `@log_performance` decorator could report a success as a failure.** Its
  success logging sat inside the same `try` as the wrapped call, so an exception
  raised while building or emitting that log line was caught by the handler
  below and recorded as *the wrapped function* having failed — then re-raised,
  losing what actually went wrong. Only the call is guarded now.
- **11 of the 15 relative links in the documentation notes were broken**, most
  of them pointing into `docs/user_guide/`, a directory that has never existed.
  `tests/test_docs_links.py` now checks every relative Markdown link under
  `docs/`, which is the one part of the documentation no build was validating.

## [0.2.3-beta.2] - 2025-10-08

> **Note:** the shortcut list below is what was planned for this release,
> not what shipped — several bindings differ in the application. The
> authoritative list is the user guide, or press `F1` in CTHarvester.
> Left as published rather than rewritten: a released changelog is a
> record.

### Added
- **Comprehensive keyboard shortcuts system** (24 shortcuts)
  - File operations: Open directory (Ctrl+O), Save cropped (Ctrl+S), Export (Ctrl+E)
  - View operations: Screenshot (F12)
  - Navigation: Previous/Next image (Ctrl+Left/Right), First/Last (Ctrl+Home/End)
  - Crop operations: Load/Save crop (Ctrl+Shift+L/S), Reset crop (Ctrl+R)
  - Threshold operations: Load/Save threshold (Ctrl+Alt+L/S), Reset threshold (Ctrl+T)
  - Help: Shortcuts help (F1)
  - Settings: Open settings (Ctrl+,)
- **Complete tooltip coverage** (100% on interactive elements)
  - Rich HTML formatting with keyboard shortcuts
  - Consistent styling across all UI elements
- **Professional UI styling system**
  - 8px grid spacing system for consistency
  - Standardized button sizes (32px height, 32x32px icons)
  - Unified color palette (Primary, Danger, Success, Warning, Neutral)
  - Centralized style configuration (`config/ui_style.py`)
- **Enhanced progress feedback**
  - Remaining items counter
  - ETA calculation with sophisticated smoothing
  - Percentage progress display
  - Cancel functionality for long operations
- **Comprehensive user documentation** (2,500+ lines)
  - Troubleshooting guide with 25+ scenarios
  - FAQ with 60+ questions answered
  - Advanced features guide with detailed examples
  - Complete workflow documentation
- **Performance benchmarking infrastructure**
  - Standard benchmark scenarios (Small/Medium/Large/XLarge)
  - 4 performance tests with memory profiling
  - Performance thresholds and validation
  - CI/CD compatible quick tests
- **Stress testing suite** (9 tests)
  - Memory leak detection tests
  - Long-running operation stability tests
  - Resource cleanup verification
  - Concurrent batch processing tests
- **Error recovery testing** (18 tests)
  - File system error handling (permission, OS errors)
  - Image processing errors (corrupt, invalid format)
  - Network drive disconnection scenarios
  - Graceful degradation mechanisms
- **Developer documentation** (1,500+ lines)
  - Error recovery guide (650 lines)
  - Performance guide (850 lines)
  - Best practices and patterns
  - Troubleshooting guides

### Changed
- **UI/UX improvements**
  - Applied consistent 8px grid spacing throughout
  - Standardized button styling and sizing
  - Enhanced progress dialog with remaining items
  - Improved keyboard navigation
- **Documentation organization**
  - Restructured user guide sections
  - Added comprehensive developer guides
  - Created detailed troubleshooting sections
- **Test suite expansion**
  - Total tests: 1,150 (+18 from previous version)
  - Quick tests: 1,133 (< 1 minute)
  - Slow tests: 17 (> 1 minute)
  - Performance tests: 4
  - Stress tests: 9
  - Error recovery tests: 18
  - Coverage maintained at ~91%

### Performance
- **Benchmark results**:
  - Small dataset (10 images, 512×512, 8-bit): < 1s
  - Medium dataset (100 images, 1024×1024, 8-bit): ~7s
  - Large dataset (500 images, 2048×2048, 16-bit): ~188s (3 minutes)
  - Image resize: < 200ms per image
- **Memory efficiency**:
  - Small datasets: < 150 MB
  - Medium datasets: < 200 MB (with batching)
  - Large datasets: < 3 GB (with batching)
  - Memory cleanup: > 50% freed after operations
- **Processing speed**:
  - Thumbnail generation (Rust): ~50ms per image
  - Thumbnail generation (Python): ~100-200ms per image
  - Full processing: ~300-400ms per image
- **Robustness verified**:
  - No memory leaks detected
  - All resources properly cleaned up
  - Stable performance over long operations
  - Linear scaling with dataset size

### Technical Details
- **UI Infrastructure**:
  - `ui/setup/shortcuts_setup.py`: Keyboard shortcut management
  - `config/ui_style.py`: Centralized UI styling
  - `config/tooltips.py`: Tooltip management
  - `tests/test_ui_style.py`: 23 UI style tests
- **Performance Infrastructure**:
  - `tests/benchmarks/benchmark_config.py`: Benchmark scenarios
  - `tests/benchmarks/test_performance.py`: 4 performance tests
  - `tests/benchmarks/test_stress.py`: 9 stress tests
  - `tests/test_error_recovery.py`: 18 error recovery tests
- **CI/CD Infrastructure** (Comprehensive improvements - Score: 95/100):
  - **Security Scanning**:
    - `.github/workflows/codeql.yml`: CodeQL SAST analysis (weekly + PR)
    - `.github/workflows/dependency-review.yml`: Dependency vulnerability checks on PRs
    - Enhanced Bandit and pip-audit security scanning
  - **Test Workflows**:
    - `.github/workflows/test.yml`: Quick tests (1,129 tests, ~30s with parallelization)
    - `.github/workflows/test-full.yml`: Comprehensive tests (1,150 tests, nightly + tags)
    - Python 3.11, 3.12, 3.13 matrix testing
    - Coverage threshold: 85% (up from 60%)
    - Parallel execution with pytest-xdist (2-3x speedup)
  - **Release Automation**:
    - `.github/workflows/release.yml`: CHANGELOG.md content extraction
    - `.github/workflows/update-readme-badges.yml`: Auto-updating test count badges
    - Enhanced release notes with installation guide and docs links
  - **Artifact Management**:
    - Test results: 7-day retention
    - Build artifacts: 14-day retention
    - Security reports: 30-day retention
  - **Documentation**:
    - `docs/CI_CD_AUDIT.md`: Comprehensive CI/CD audit report
    - `devlog/20251008_099_cicd_improvements.md`: Implementation details
- **Documentation**:
  - `docs/user_guide/troubleshooting.rst`: Troubleshooting guide
  - `docs/user_guide/faq.rst`: Frequently asked questions
  - `docs/user_guide/advanced_features.rst`: Advanced features
  - `docs/developer_guide/error_recovery.md`: Error recovery patterns
  - `docs/developer_guide/performance.md`: Performance characteristics



## [0.2.3-beta.1] - 2025-09-30

### Added
- **Comprehensive test suite** (195 tests with ~95% coverage)
  - Unit tests for core utilities, workers, image processing, security (186 tests)
  - Integration tests for thumbnail generation workflows (9 tests)
  - Test markers for unit, integration, slow, and Qt tests
- **CI/CD pipeline** with GitHub Actions
  - Automated testing on Python 3.12 and 3.13
  - Coverage reporting with Codecov integration
  - Automated builds and releases
- **Project retrospective document**
  - Comprehensive documentation of refactoring journey
  - Detailed test coverage expansion process
  - Lessons learned and best practices
- **Security validation module** (`security/file_validator.py`)
  - Directory traversal attack prevention
  - Path validation and sanitization
  - Secure file operations with FileSecurityError

### Changed
- **Major code refactoring** (Phase 1-4)
  - Modular architecture: config/, core/, ui/, utils/, security/
  - CTHarvester.py reduced from 4,840 lines to 151 lines (-96.6%)
  - Extracted 18 modules with clear separation of concerns
- **Documentation overhaul**
  - README.md expanded with testing section, project structure, contributing guide
  - README.ko.md synchronized with English version
  - Updated badges (Codecov, test count, Python 3.12+)
- **Memory management improvements**
  - Explicit resource cleanup (del statements)
  - Periodic garbage collection every 10 images
  - Try-finally blocks ensuring cleanup
- **Error handling enhancements**
  - Added traceback module import and usage
  - Comprehensive exception handling throughout
  - Finished signals guaranteed in all cases
- **Thread safety improvements**
  - Duplicate result processing prevention
  - Progress rate boundary validation
  - Single-thread strategy documented

### Fixed
- **Critical security vulnerabilities**
  - Directory traversal attack prevention
  - File path validation and sanitization
  - Null byte injection protection
  - Symbolic link traversal prevention
- **Memory leaks**
  - PIL Image objects now explicitly released
  - NumPy arrays properly cleaned up
  - Garbage collection triggered periodically
- **Pillow deprecation warnings** (147 warnings eliminated)
  - Removed deprecated `mode` parameter from Image.fromarray()
  - PIL now auto-detects mode from array dtype and shape
- **Import organization**
  - Added missing traceback module import
  - Updated import paths for new module structure

### Performance
- Test execution: 195 tests in ~2.5 seconds
- Code quality: 95% coverage for core utility modules
- Modules at 100% coverage: utils/common, utils/worker, utils/image_utils

### Technical Details
- **Test infrastructure**:
  - pytest 8.4.2 with pytest-cov, pytest-qt, pytest-timeout
  - AAA pattern (Arrange-Act-Assert)
  - Fixture-based test isolation
  - Platform-specific skip decorators
- **Module structure**:
  - config/: Global constants and configuration
  - core/: Business logic (progress, thumbnail generation)
  - ui/: User interface components (dialogs, widgets)
  - utils/: Reusable utility functions
  - security/: File validation and security checks
  - tests/: Comprehensive test suite
- **CI/CD workflows**:
  - test.yml: Automated testing with coverage
  - build.yml: Development builds on main
  - release.yml: Release builds on version tags


## [0.2.3-alpha.2] - 2025-09-29

### Changed
- Python fallback implementation simplified to use only PIL and NumPy
  - Removed tifffile and OpenCV dependencies for better compatibility
  - Single-threaded processing for predictable performance
  - Focus on code simplicity and maintainability as fallback solution

### Fixed
- Python thumbnail generation performance issues
  - Identified and documented np.array() conversion bottleneck
  - Reduced thread contention by using single thread
  - Improved logging to better track performance issues

### Performance
- Python fallback: ~25-30 minutes for 3000 images (acceptable for backup)
- Rust module remains primary solution: 2-3 minutes (10x faster)


## [0.2.3-alpha.1] - 2025-09-13

### Added
- Multithreading support for thumbnail generation
  - Parallel processing of multiple thumbnails
  - Improved performance for large image stacks

### Changed
- Improved thumbnail generation process
  - Better handling of bounding box scaling
  - More efficient image processing pipeline

### Fixed
- Bounding box scaling issues in thumbnail generation
- Windows Defender false positive by disabling UPX compression
- IndentationError issues in commented-out debug logs
- Thumbnail loading when minimum_volume is empty
- File path handling when loading existing thumbnails


## [0.2.2] - 2025-09-08

### Added
- Centralized logging system (CTLogger.py)
  - Daily log rotation with date-based filenames
  - Configurable log directory under user profile
  - UTF-8 encoding support for better compatibility
  - Automatic fallback to console output if file creation fails
  - Separate error stream to console for critical issues
- Comprehensive error handling throughout CTHarvester.py
  - Try-catch blocks for all file I/O operations
  - Error handling for image processing operations
  - Protected 3D scene manipulations
  - Safe settings load/save operations
  - Robust volume and mesh processing

### Changed
- Replaced all print statements with proper logger calls
  - Debug messages for verbose output
  - Info messages for normal operations
  - Warning messages for potential issues
  - Error messages with full exception details
- Improved error reporting with detailed exception logging

### Fixed
- IndexError in rangeSliderValueChanged when accessing level_info
  - Added boundary checks for array access
  - Validated curr_level_idx before use
  - Protected against uninitialized level_info
- Potential crashes from unhandled exceptions in:
  - File operations (open, save, export)
  - Image processing (thumbnail generation, screenshots)
  - 3D operations (volume updates, mesh generation)
  - Settings persistence


## [0.2.1] - 2025-09-08

### Added
- Comprehensive CI/CD pipeline with GitHub Actions
  - Reusable build workflow (`reusable_build.yml`) for consistent builds across platforms
  - Manual release action for creating releases with custom version tags
  - Support for pre-release versions (alpha, beta, rc)
  - Automated build number management
- Advanced version management system
  - New `manage_version.py` utility replacing `bump_version.py`
  - Semantic versioning with `semver` library support
  - Pre-release version support (alpha, beta, rc stages)
  - `VERSION_MANAGEMENT.md` documentation
- Proper application icons
  - Converted CTHarvester_64.png to icon.ico for Windows
  - Created icon.png for Linux AppImage builds
  - Added `convert_icon.py` utility for PNG to ICO conversion
- Dynamic copyright year display
  - Automatically updates copyright year in About dialog
  - Shows "© 2023-{current_year} Jikhan Jung"

### Changed
- Version management migrated from simple bump script to comprehensive semver-based system
- All GitHub Actions workflows now use centralized reusable build workflow
- Build artifacts properly named with version and build numbers
- Inno Setup configuration uses absolute paths for reliable builds
- Copyright display now uses dynamic year calculation

### Fixed
- Windows installer build issues
  - Corrected file paths for single-file PyInstaller builds
  - Fixed Inno Setup output directory path resolution
  - Disabled Korean language file for CI compatibility
- Linux AppImage build failures
  - Resolved missing icon file errors
  - Fixed desktop entry category validation
  - Always creates placeholder icon when needed
- GitHub Actions YAML syntax errors
  - Replaced heredoc syntax with echo commands
  - Fixed indentation and escaping issues
- Build path issues across all platforms

### Technical Details
- Build system improvements:
  - Windows: ZIP-packaged installer with Inno Setup
  - macOS: DMG creation for distribution
  - Linux: AppImage generation with proper desktop integration
- Version parsing now handles complex version strings safely
- All file paths converted to absolute paths during build process

## [0.2.0] - 2024-12-28

### Added
- Initial centralized version management through `version.py`
- Cross-platform build support (Windows, macOS, Linux)
- Basic GitHub Actions for automated builds

### Changed
- Version information now managed in single source of truth

### Fixed
- Version consistency across all build artifacts
