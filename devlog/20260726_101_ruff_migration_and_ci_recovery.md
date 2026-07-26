# Devlog 101: Ruff Migration and Full CI Recovery — Lint Consolidation, Cross-Platform Test Fixes, Three Production Bugs

**Date:** 2026-07-26
**Current Version:** 0.2.3-beta.2
**Status:** ✅ Complete — all four CI workflows green for the first time
**Previous:** [devlog 100 - Code Quality Guide Adoption](./20260724_100_code_quality_guide_adoption.md)

---

## 🎯 Overview

Started as "what's the current project state?" and turned into closing the
deferred item 4 from devlog 100 (the Ruff migration), then repairing a CI matrix
that turned out to have been broken for weeks.

The starting point looked healthy — clean tree, 1238 tests, nine tidy workflows —
but almost nothing was actually passing on GitHub. Four of the five workflows
were red, and had been since devlog 100 landed. Because the failures were mostly
platform-specific, none of them reproduced on the development machine.

**Result:** 12 commits. Every workflow green. Along the way the sweep turned up
three genuine production bugs and two tooling bugs, none of which were visible
from reading the code.

| Workflow | Before (`e7375ad`) | After (`d06e6d3`) |
|---|---|---|
| Quick Tests (CI) | ❌ 10 failing jobs | ✅ 16/16 jobs |
| Security | ❌ pip-audit + dependency-lock | ✅ |
| Build | ❌ build-windows | ✅ all 3 OS |
| Build and Deploy Documentation | ❌ (3 consecutive runs) | ✅ |
| CodeQL | ✅ | ✅ |

---

## 📋 Work Completed

### 1. Two tests that passed only by accident (`a00ea8b`)

The local quick suite reported `1205 passed, 2 failed` on first run.

**`test_common.py::test_invalid_path_no_crash`** used `/root/invalid/...` as an
uncreatable path. `ensure_directories` warns instead of raising, and devlog 100
had turned on `filterwarnings = error` — so the warning became an exception. The
test therefore passed *only when directory creation succeeded*, i.e. only when
the suite ran as root. It failed for every normal user, including the `runner`
account on GitHub. Its stdout assertion, `"Warning" in out or len(out) == 0`, was
tautological and asserted nothing either way.

Fixed by using a regular file as the parent directory: `NotADirectoryError` is
raised for every user on every platform, so the failure is deterministic. The
assertion is now `pytest.warns(RuntimeWarning, match=...)`.

**`test_constants.py::test_version_import_fallback`** reloaded `config.constants`
with `version` blocked in `sys.modules` and never restored it. `monkeypatch` rolls
back `sys.modules` but not the module object that was already reloaded, so
`constants.__version__` stayed at `"0.0.0+unknown"` for the rest of the session
and `test_version_consistency.py` failed depending on collection order — flaky
under `-n auto`. Fixed with an explicit reload in `finally`; the assertions now
check the fallback value rather than just its type.

### 2. Restoring the dangerous flake8 rules (`62ebf59`)

Item 4 of devlog 100, part one. The pre-commit `extend-ignore` disabled 13 rules
that catch real defects. All are now enabled and clean tree-wide: `F821`, `F811`,
`F841`, `E722`, `E712`, `B001`, `B006`, `B008`, `B011`, `B014`, `B017`, `F403`,
`F405`.

`F821` (undefined name) had zero findings — a free win that should never have
been off. The rest needed work:

- **`F841` (31 sites)** were `except X as e` handlers that never used `e`. All log
  via `exc_info=True` or `logger.exception`, so dropping the binding loses
  nothing.
- **`MainWindow.update_curr_slice` computed `bounding_box` and `curr_slice_val`
  and threw both away.** A leftover copy of logic that moved to
  `ViewManager.update_3d_view` during the Phase 4.4 handler extraction — and
  which the delegating call directly below it already performs. 20 lines of dead
  code that looked load-bearing.
- **`tests/test_basic.py::test_image_utils_basic` wrapped its entire body in
  `except ImportError: pass`,** nominally to skip when PIL is missing. PIL is a
  hard dependency, so the branch was never a legitimate skip — it silently passed
  the test if any import anywhere in the chain broke.
- `B017`: three `pytest.raises(Exception)` narrowed to the actual
  `FileNotFoundError`.
- `F811` in `thumbnail_generator.py`: `def progress_callback` inside a branch
  shadowed the `None` default. Rewritten as named inner functions plus
  assignment.

`C901`, `F541`, `E228` and `B007` stayed off — refactor-sized or cosmetic, and
better handled in bulk by Ruff.

### 3. Repository root cleanup (`ae14319`)

Five unreferenced markdown files at the root moved to `docs/`. `docs/RELEASE_NOTES.md`
still announced v0.2.3-beta.1 as the "Current Release" months after beta.2
shipped, and quoted stale test/coverage numbers; archived under
`docs/release-notes/` rather than refreshed, since that drift is the argument for
having one source. `CHANGELOG.md` is canonical — `release.yml` publishes its
sections verbatim.

`CTLogger.py` was investigated and left at the root: `CTHarvester.py` imports it,
`pyproject.toml` declares it in `py-modules`, and `test_smoke.py` asserts it is
importable.

### 4. Ruff migration (`43b80ab`) — item 4, part two

black + isort + flake8 + pyupgrade + pylint → **ruff**, pinned to `0.16.0` in the
two places that must agree: `pyproject.toml`'s dev extra (which feeds
`requirements-dev.lock` and therefore CI) and `.pre-commit-config.yaml`'s `rev`.

Rule set is Modan2's: `E, F, I, N, UP, B, C4, LOG, RUF012`. `.flake8` deleted;
`[tool.black]`, `[tool.isort]` and `[tool.pylint.*]` removed. `ruff check` and
`ruff format --check` are now **gating** in CI.

**Markdown had to be excluded from the formatter.** Ruff formats Python inside
markdown fences: the first `ruff format` pass wanted to rewrite 108 files /
3102 diff lines, including documentation examples in `CONTRIBUTING.md` and the
devlog. Excluding `*.md` brought it to 22 files / 275 lines — the genuine
black↔ruff-format divergence. This is exactly the trap `TODOs.md` recorded from
Modan2, and it reproduced on the first try.

The sweep beyond the reformat:

- **233 pyupgrade findings** fixed by moving `target-version` to `py311`. It had
  been `py38` while `requires-python` already said `>=3.11` — so the codebase was
  being held to a Python version it did not support. PEP 585/604 annotations
  throughout: `Dict[str, X]` → `dict[str, X]`, `Optional[X]` → `X | None`.
- 8 mutable class defaults annotated `ClassVar`.
- `B904`: two `raise` statements inside `except` now chain with `from`.
- `B905`: `zip()` calls whose lengths are validated equal immediately above now
  say `strict=True`.
- `E721`: `type(x) == SomeError` → `is`.

Naming rules are relaxed per-file for `ui/` and `CTHarvester.py`. Qt dictates the
spelling of every method it calls back into (`paintGL`, `mousePressEvent`);
renaming them does not make the code more PEP 8, it makes it not work.

The `ct_thumbnail` availability probe deliberately keeps its `import` rather than
taking ruff's `importlib.util.find_spec` suggestion: it is a compiled Rust
extension, and `find_spec` reports a wheel present that then fails to load on an
ABI mismatch. Only an actual import proves it usable.

---

## 🔧 CI Recovery

With the lint work done, the push revealed how much was actually red. The
failures split cleanly into "already broken" and "only breaks off this machine".

### 5. Documentation build — broken since `23ef4aa` (`6799414`)

Failed at "Build English documentation" on every run since version.py became the
single source of truth:

```
File "version.py", line 6, in <module>
    import semver
ModuleNotFoundError: No module named 'semver'
```

`docs/conf.py` does `from version import __version__`; `version.py` parses that
string with semver at import time; the docs job installs only
`docs/requirements.txt` — sphinx, the theme, sphinx-intl. Sphinx died reading
conf.py before looking at a single page. It passed locally only because a dev
environment has semver from the project's own dependencies.

Reproduced by building in a fresh venv containing exactly `docs/requirements.txt`,
then fixed by adding the dependency there with a comment explaining why a
non-Sphinx package lives in that file. Making version.py's semver import lazy was
rejected: the eager parse is what validates the version string, and
`constants.py` deliberately treats an import failure as an honest error.

### 6. Pillow: 18 CVEs behind a version ceiling (`0fcd51a`)

`pip-audit` had been failing on `pillow==11.3.0` (PYSEC-2026-165, -2249..-2257,
-2874, -3451..-3496). All are fixed somewhere in 12.1.1–12.3.0, and the
`<12.0.0` ceiling made every fix unreachable.

The floor was raised to `12.3.0`, not just the ceiling widened: with
`>=11.0.0,<13.0.0` the lockfile resolves to a fixed version while the declared
range still permits a vulnerable install for anyone resolving from
`pyproject.toml` directly. Supersedes Dependabot #5.

Pillow 12 is a major bump, but the API surface here is three stable calls
(`Image.open`, `Image.fromarray`, the `Image.Image` type). Verified by running
the whole suite on 12.3.0 including slow and benchmark tests.

*A one-off core dump appeared during that verification and did not reproduce; the
same run on 11.3.0 produced identical results, so it was noise, not a Pillow
regression.*

### 7. The universal lockfile did not install on Windows (`f8e3f57`)

Every Windows job — both smoke legs, both test legs, and the installer build —
had been failing at "Install Python dependencies":

```
ERROR: Could not find a version that satisfies the requirement
pyqt5-qt5==5.15.19 (from versions: 5.15.2)
```

`pyqt5-qt5` ships the bundled Qt runtime and **stopped publishing Windows wheels
after 5.15.2**; 5.15.19 has manylinux and macOS wheels only.
`uv pip compile --universal` does not check wheel-tag coverage, so it pinned one
version for every platform.

Naming the package directly with markers makes the resolver fork. Both bounds are
required — given only the Windows pin, uv unifies on 5.15.2 everywhere, and
5.15.2 has no `macosx_11_0_arm64` wheel, which would trade the Windows breakage
for a break on the Apple-silicon runners.

Verified by resolving against each target rather than assuming:

| lockfile | `--python-platform windows` |
|---|---|
| old | unsatisfiable, uv naming the three platforms that do have wheels |
| new | resolves, selecting 5.15.2 |

All six `{windows, macos, linux} × {3.11, 3.13}` combinations resolve.

### 8. macOS-only test failures (`0734dc2`)

Six tests failed on the macOS legs and nowhere else. Three distinct causes, none
actually macOS-specific once understood:

**`test_security` (3 tests)** — `/var` is a symlink to `/private/var` on macOS, so
`tempfile.mkdtemp()` returns an unresolved path. `validate_path()` normalises
through `Path.resolve()`, which follows symlinks; the tests compared against
`os.path.abspath()`, which does not. The validator is right — resolving symlinks
*is* the security property. **Reproduced on Linux** by pointing `TMPDIR` at a
symlink, which fails the same three tests before the change and passes all of
them after.

**`test_progress_tracker` (2 tests)** asserted absolute wall-clock ceilings
(`elapsed < 0.2`, `eta < 2`) and failed at 0.2105 and 4.83 on a loaded runner. An
absolute ceiling asserts the machine is idle, not anything about the code. The
ETA test now checks the invariant that actually holds: with 10 of 100 items done,
the estimate should be about 9× elapsed, whatever speed the machine ran at.

**`test_stress` (memory)** — two problems.
`test_repeated_operations` compared `second_half_avg < first_half_avg * 1.5`,
which evaluates to `0.0 < 0.0` when RSS never moves: **it failed precisely when
the result was perfect.** `test_memory_cleanup_after_operation` asserted RSS falls
back toward baseline after `gc.collect()`, which no allocator guarantees — it read
0% freed on macOS and under WSL2.

The latter was rewritten around weak references to the decoded arrays, which
tests the property the name promises (nothing in our code keeps them alive)
deterministically on every platform. RSS is now printed for diagnostics and never
asserted on. Verified with a negative control: injecting a module-level reference
makes it fail with "30 of 30 arrays still reachable".

### 9. A low-resolution clock in the progress code (`790d02b`)

Seven Windows failures and two macOS ones traced to one defect in **production
code**, not the tests.

`SimpleProgressTracker` and `ProgressManager` measured elapsed time with
`time.time()`. On Windows that advances in ~15.6 ms steps, so any update landing
in the same tick as the start read elapsed as exactly `0.0`:

- `progress_tracker` skipped the speed sample entirely (`if elapsed > 0`), so
  `speed_samples` stayed empty and ETA never materialised → `assert 0 > 0`,
  `assert None is not None`.
- `progress_manager.calculate_eta()` returned `""` from its `elapsed <= 0` guard,
  which sat **above** the checks for finished work → `assert '' == 'Completing...'`.

Both now use `time.perf_counter()`: monotonic, so an NTP step cannot make elapsed
go backwards, and high-resolution everywhere. `calculate_eta()` also decides
`"Completing..."` before consulting the clock, because finished work is a fact
about the counters. Two regression tests pin that ordering; a negative control
restoring the old arrangement reproduces the exact Windows message.

`thumbnail_manager` tested `not progress_manager.start_time`, safe only because
`time()` returns a large number — `perf_counter()`'s zero point is arbitrary, so
that is now an `is None` check.

Also in this pass: a **self-inflicted regression** from the F841 sweep. An
assertion added to `test_i18n` matched a path against `str(call)`, which breaks on
Windows where the call repr escapes backslashes and the real path has single
ones. And `test_create_directory_oserror` used `/root/nopermission` — the same
POSIX assumption as item 1, which maps to a creatable path on Windows
("DID NOT RAISE").

Pillow 12's stricter stubs also caught `img = img.convert(...)` rebinding an
`ImageFile` to an `Image` in `safe_load_image`; split into two names, which also
makes it obvious which object the context manager closes.

### 10. `wait_cursor` aborted the process (`68c5816`)

The macOS legs reported `Fatal Python error: Aborted` and a dead xdist worker on
every run; Ubuntu py3.11 hit the same thing intermittently on a different test,
failing with an xdist `INTERNALERROR`. The traceback pointed at
`utils/ui_utils.py` in `wait_cursor`.

`QApplication.setOverrideCursor()` with no QApplication instance **does not raise
— Qt calls `qFatal` and aborts.** Reproduced on Linux in one command:

```
$ python -c "...QApplication.setOverrideCursor(Qt.WaitCursor)"
QPixmap: Must construct a QGuiApplication before a QPixmap
exit=134            # SIGABRT
```

Exactly what CI reported. `wait_cursor` and `override_cursor` now check for an
instance first and yield without touching the cursor if there is none. A cursor
hint is cosmetic; it must never take the process down.

`test_save_image_stack_no_crop` is what walked into it: it patches
`ui.handlers.export_handler.QApplication`, but `wait_cursor` resolves
`QApplication` through its own module, so the real Qt call went through. The
sibling test directly below it already patched `utils.ui_utils.QApplication` with
a comment saying why.

This one fix turned both macOS legs and the intermittent Ubuntu failure green.

### 11. Windows file handle in teardown (`ab6cd53`) — *root cause unresolved*

The last remaining test failure. Tests that hand PIL corrupt and truncated images
leave something holding a handle on Windows, so the fixture's `shutil.rmtree`
fails with `WinError 32`. POSIX unlinks open files without complaint, which is
why it only appears there.

The first attempt — `gc.collect()` before `rmtree` — **was disproved by CI**,
which rules out the obvious explanation: whatever holds the handle is still
reachable rather than garbage. Pinning it down needs a Windows environment.

What does not need further diagnosis is the consequence. A temp directory that
outlives its test is a housekeeping detail, not a test result. Teardown now
retries, then falls back to `ignore_errors`. The tests themselves are unchanged.

### 12. Inno Setup installer URL 404 (`d06e6d3`)

The Windows installer build failed at "Download and Install Inno Setup".
jrsoftware.org keeps only the current 6.x under `/is/6/`, so the pinned
`innosetup-6.2.2.exe` stopped existing. The whole versioned path scheme is gone,
and `jrsoftware.org/download.php/is.exe` now serves an HTML landing page rather
than a binary — there is no versioned URL left there to pin to.

**Modan2 had already hit this and solved it**: GitHub release assets are
permanent. Matched its source and version (`issrc` release `is-6_7_3`,
innosetup-6.7.3.exe) so the two projects do not drift on installer tooling.

*Worth recording: the first fix drafted here was Chocolatey, which would have
worked but left the version unpinned. Checking the sibling project produced a
better answer.*

---

## 🐛 Tooling bug found: `make lock-check` failed permanently

Not a CI-visible symptom at first — it surfaced while verifying the Ruff
lockfile change, and reproducing it on the pre-change commit showed it had been
failing all along. The gating `dependency-lock` job in `security.yml` was red
regardless of whether `pyproject.toml` had changed.

`uv pip compile` prefers versions already pinned in its **output file**.
`make lock` writes over the committed lockfile, so it keeps the existing pins;
`lock-check` compiled into an empty temp file, so it resolved everything to the
newest release. The two disagreed the moment anything upstream shipped a version.

`lock-check` now seeds the temp files from the committed lockfiles first, which
asks the question the gate is actually for: *does re-locking this pyproject.toml
change anything?* Upgrading dependencies is Dependabot's job. Verified both
directions — passes in sync, still fails when a dependency is added without
re-locking.

---

## 📁 Files Changed

111 files, +1441 / −1476 across 12 commits.

| Area | Files |
|---|---|
| Lint/format config | `pyproject.toml`, `.pre-commit-config.yaml`, `.flake8` (deleted), `Makefile` |
| CI | `.github/workflows/test.yml`, `reusable_build.yml` |
| Dependencies | `pyproject.toml`, `requirements.txt`, `requirements-dev.txt`, `requirements*.lock`, `docs/requirements.txt` |
| Production code | `core/progress_manager.py`, `core/progress_tracker.py`, `core/thumbnail_manager.py`, `core/thumbnail_generator.py`, `core/file_handler.py`, `core/volume_processor.py`, `ui/main_window.py`, `ui/widgets/*`, `ui/dialogs/progress_dialog.py`, `utils/ui_utils.py`, `utils/image_utils.py`, `security/file_validator.py` |
| Tests | `test_common.py`, `test_constants.py`, `test_security.py`, `test_progress_tracker.py`, `test_progress_manager.py`, `test_i18n.py`, `test_file_utils.py`, `test_file_handler_error_paths.py`, `test_export_handler.py`, `benchmarks/test_stress.py`, `test_basic.py`, and others touched by the F841 sweep |
| Docs | `docs/CODE_QUALITY.md`, `CONTRIBUTING.md`, `TODOs.md`, `CHANGELOG.md`, `docs/release-notes/` (new) |

---

## 🧪 Verification

- Full suite including slow and benchmark tests: **1236 passed, 5 skipped, 0 failed**
- `ruff check` clean; `ruff format --check` clean (144 files)
- `mypy --config-file pyproject.toml core/ utils/`: no issues in 23 source files
- All pre-commit hooks pass on `--all-files`
- `make lock-check` passes; `pip install --require-hashes --dry-run` passes
- `pip-audit -r requirements.lock`: no known vulnerabilities
- **CI: all four workflows green** (16/16 test-matrix jobs across Linux, Windows,
  macOS × Python 3.11/3.12/3.13)

Two limitations worth naming: `pytest-xdist` is not installed on the development
machine, so `-n auto` could not be reproduced locally — CI was the check. And the
Windows file-handle issue in item 11 needs Windows semantics to appear at all.

---

## 💡 Lessons

1. **A green local suite says nothing about a cross-platform matrix.** Every
   failure repaired here was invisible on the development machine. The three-OS
   matrix from devlog 100 was the right investment; its value only materialised
   once someone read what it was saying.

2. **A test that can only pass under one environment is not a test.** The `/root`
   path assumption appeared twice, independently. Both times the test passed for
   the author (root or Windows) and failed for everyone else. A deterministic
   failure — a file used as a directory's parent — is available and costs nothing.

3. **Watch for assertions that fail on the ideal outcome.**
   `second_half_avg < first_half_avg * 1.5` fails when both are zero, which is
   the best possible memory profile. Multiplicative bounds need additive slack
   near the origin.

4. **Absolute time bounds assert that the machine is idle.** `elapsed < 0.2` and
   `eta < 2` say nothing about the code. Scale-invariant relationships — "the
   estimate should be ~9× elapsed" — hold at any speed.

5. **Qt aborts where Python would raise.** `setOverrideCursor` with no
   QApplication calls `qFatal`, so no `try` block can help and the failure
   surfaces as "node down" rather than a test failure. Any Qt call reachable from
   a non-GUI context needs an instance check.

6. **`time.time()` is the wrong clock for durations.** It is wall-clock (an NTP
   step can run it backwards) and coarse on Windows. `perf_counter()` for
   elapsed, always — but its zero point is arbitrary, so truthiness checks on a
   timestamp must become `is None`.

7. **A check whose false-positive rate reaches 100% has stopped being a check.**
   `lock-check` had been failing on every run for weeks. A permanently red gate
   trains everyone to ignore it, which is worse than not having it.

8. **Check the sibling project first.** Modan2 had already solved the Inno Setup
   404 with a better answer than the one drafted here. Two projects sharing a
   stack should share the fix, not each derive their own.

9. **A rule that flags nothing is free to enable.** `F821` had zero findings and
   had been disabled anyway. Turning off a rule because a batch of others is
   noisy costs the ones that were already clean.

---

**Next:** the Windows file-handle root cause (needs a Windows box); additional
ruff rule groups one at a time (`DTZ`, 17 findings, is the smallest and highest
value); `C901` complexity refactoring across 11 functions; flipping mypy to
gating once the numpy 2.5 stub issue is resolved; and the packaged-artifact
smoke test, which Modan2 already has in `reusable_build.yml`. All recorded in
`TODOs.md`.
