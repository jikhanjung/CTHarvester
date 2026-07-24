# Devlog 100: Code Quality Guide Adoption — Cross-Platform CI, Config Consolidation, Dependency Locking

**Date:** 2026-07-24
**Current Version:** 0.2.3-beta.2
**Status:** ✅ Items 1–3, 5–9 complete (item 4 deferred by request)
**Previous:** [devlog 099 - CI/CD Improvements](./20251008_099_cicd_improvements.md)

---

## 🎯 Overview

Audited CTHarvester against the Modan2 project's `docs/CODE_QUALITY_GUIDE.md` — a
reusable checklist of quality practices for multi-platform desktop software —
and implemented the resulting gap list.

The audit found the project already satisfies more than half the guide
(1123 tests with a layered/marked suite, coverage gate, security scanning,
per-module mypy adoption, 3-OS packaging, an established devlog practice). The
work below closes the gaps that mattered most, plus a repository hygiene fix
discovered along the way.

**Guide reference:** `../Modan2/docs/CODE_QUALITY_GUIDE.md` (v1.0, 2026-07-23)

---

## 📋 Audit Result Summary

| Guide section | Status before | Action |
|---|---|---|
| §1 Formatting & linting | ⚠️ 5 tools, over-broad ignores | Deferred (item 4) |
| §2 Type checking | ✅ mypy, per-module strict | — |
| §3 Testing strategy | ✅ layered, marked, pytest-qt, hypothesis | — |
| §4 Coverage | ✅ measured + 75% gate | Fixed summary/gate mismatch |
| §5 Cross-platform CI | ❌ **Linux only** | **Fixed** — 3-OS matrix + smoke job |
| §6 Dependencies | ⚠️ ranges only, no lock | **Fixed** — universal lockfiles |
| §7 Packaging | ✅ 3-OS build | Artifact smoke test still open |
| §8 Runtime robustness | ❌ no excepthook / slot guards | **Fixed** |
| §9 Resources | ✅ no silent `except: pass` | — |
| §10 i18n / encoding | ✅ encoding specified throughout | — |
| §11 Performance | ✅ benchmarks behind marker | — |
| §12 Security | ✅ validator, bandit, pip-audit, CodeQL | — |
| §13 Dead code | ⚠️ no vulture/radon, `C901` off | Deferred (item 4) |
| §14 Workflow gating | ⚠️ most checks non-gating | Deferred (item 4) |

---

## 🔧 Work Completed

### 0. Repository hygiene: line endings (`.gitattributes`)

**Problem:** `git status` reported **323 modified files** with
`118955 insertions(+), 118955 deletions(-)` — every added line matched a deleted
line, i.e. pure line-ending churn. The repository stored LF; the working tree on
`/mnt/d` (a Windows drive under WSL2) had been rewritten to CRLF. There was no
`.gitattributes` and `core.autocrlf` was unset.

**Fix:**
- Added `.gitattributes` mirroring `.editorconfig` (LF everywhere, CRLF only for
  `.bat`/`.cmd`), with explicit `binary` for `.png/.ico/.mo/.qm` and friends.
- `git add --renormalize .` — 321 files went clean; `CTHarvester.spec` and
  `VERSION_MANAGEMENT.md` were genuinely stored as CRLF and normalized to LF
  (verified content-identical modulo line endings).
- Re-checked out the working tree so files are physically LF on disk. This also
  fixed `scripts/setup_next_improvements.sh` and
  `packaging/linux/create_appimage.sh`, which had CRLF line endings — these fail
  to execute under WSL because the shebang line ends in `\r`.

---

### 1. pytest configuration de-duplication ⚠️ *silent misconfiguration*

**Problem:** Both `pytest.ini` and `pyproject.toml [tool.pytest.ini_options]`
existed. pytest reads **only one** config file and `pytest.ini` wins, so every
setting in `pyproject.toml` was **silently inert** — including:

- `filterwarnings = ["error", ...]` (guide §8) — never active
- `--cov-branch`, `minversion`, coverage report options

**Fix:**
- Deleted `pytest.ini`; `pyproject.toml` is now the single pytest config.
  Verified: `configfile: pyproject.toml`.
- Merged the marker set (kept `ui`/`qt` from `pytest.ini`, added `smoke`).
- Added `--strict-config` so an unknown/misspelled option fails instead of being
  ignored.
- **Made `filterwarnings = error` real.** The previous list ended with blanket
  `ignore::UserWarning` and `ignore::DeprecationWarning`, which nullified it.
  Replaced with narrow, commented ignores (PyQt5 sip deprecation,
  `pkg_resources`, `setuptools`, and the pymcubes item below).
- `norecursedirs`: initially replaced pytest's defaults, which broke hypothesis'
  `.hypothesis` directory handling (`UserWarning` → error, collection aborted).
  Corrected to *extend* the defaults (the leading `.*` pattern is what covers
  `.git`/`.tox`/`.venv`/`.hypothesis`).
- Updated the `pytest.ini` reference in `README.md` and `README.ko.md`.

**What `filterwarnings = error` surfaced — a latent NumPy 2.5 break in pymcubes.**
Enabling it was *not* uneventful (contrary to a first impression): the
integration and mcube-widget tests began failing/hanging. Root cause chain:

1. `mcubes.marching_cubes` (compiled Cython, `mcubes/src/_mcubes.pyx:23`) sets
   `ndarray.shape` directly — deprecated in NumPy 2.5.
2. With warnings-as-errors that `DeprecationWarning` became an exception inside
   the background **mesh-generation thread**.
3. The thread's error path (`MCubeWidget._on_mesh_error`) pops a modal
   `QMessageBox.exec_()`, which **blocks forever** in a headless test — the
   `test_thumbnail_workflow.py` hang.

This is exactly the class of "silent runtime degradation" the guide's §8 says
warnings-as-errors should expose: a real dependency issue that *will* become a
hard error when NumPy 2.5 ships. Since the offending code is upstream and
compiled, the fix is a **message-scoped ignore** (not a blanket
`DeprecationWarning` suppression), documented in `pyproject.toml`. See the
"pymcubes update" investigation appended at the end of this devlog for the
upgrade path that would remove the need for the ignore.

---

### 2. Cross-platform CI matrix (guide §5 — highest-value check)

**Problem:** `test.yml`, `test-full.yml` and `quality-gates.yml` all ran
`runs-on: ubuntu-latest`. The Python axis (3.11/3.12/3.13) existed but the OS
axis did not. CTHarvester ships an InnoSetup installer and a macOS DMG — builds
were 3-OS, tests were Linux-only.

**Fix — `test.yml` restructured into four jobs:**

| Job | Matrix | Purpose |
|---|---|---|
| `smoke` | 3 OS × py3.11/3.13 | Fast fail on import/startup breakage |
| `test` | Linux py3.11–3.13, Win/macOS py3.11/3.13 | Full quick suite (7 jobs) |
| `docs` | ubuntu | Sphinx build (advisory, unchanged) |
| `test-summary` | — | Aggregates and fails on smoke/test failure |

- Linux uses `xvfb-run`; Windows/macOS use `QT_QPA_PLATFORM=offscreen` directly.
- Coverage XML is uploaded once (Linux/py3.12); the gate itself stays in
  `quality-gates.yml` on the reference platform.
- Python 3.12 is excluded on Windows/macOS to keep the matrix affordable
  (min/max coverage is what catches version-only stdlib symbols).
- Removed the `pre-commit run --all-files || true` step — it was `|| true` *and*
  `continue-on-error`, and duplicates `quality-gates.yml`.

**Also fixed:** `libglut3.12` was pinned across four workflows. That package
name is specific to Ubuntu 24.04 and would break when runners move on. Replaced
with the version-agnostic `libglu1-mesa` + `freeglut3-dev` in `test.yml`,
`test-full.yml`, `reusable_build.yml` and `update-readme-badges.yml`.

**Decision — `test-full.yml` left Linux-only.** It is the nightly/release-tag
deep suite including performance benchmarks, which are tuned for one platform
and would be noisy across three. Cross-platform breadth is now covered by
`test.yml` on every PR.

---

### 3. Headless import/startup smoke test (`tests/test_smoke.py`)

The guide calls this "the one cheap test" that catches the largest class of
user-only crashes. New file, **62 tests**, all passing locally:

- `test_module_imports` — parametrized over every module discovered under
  `config/`, `core/`, `security/`, `ui/`, `utils/` plus `version`, `CTLogger`,
  `CTHarvester`. Exercises the real import graph, not mocks.
- `test_third_party_native_extensions_load` — touches `PyQt5.sip`, `PIL._imaging`
  (via `PIL.Image.new`), numpy. A wheel can install yet ship a broken binary.
- `test_main_window_starts_and_closes` — constructs the real
  `CTHarvesterMainWindow`, shows it offscreen, waits for exposure, closes it.
- `test_bundled_resources_exist` — icons and `.qm` translations resolve via
  `resource_path`.
- `test_python_version_is_supported` — fails below the declared 3.11 minimum.

---

### 5. Version single source of truth

**Problem:** `version.py` claims to be the SSOT but three files had drifted:

| File | Before | After |
|---|---|---|
| `version.py` | `0.2.3-beta.2` | (unchanged — the source) |
| `pyproject.toml` | `0.2.3-beta.1` ❌ | `dynamic = ["version"]` |
| `Cargo.toml` | `0.2.3` ❌ | `0.2.3-beta.2` |
| `docs/conf.py` | `0.2.3` ❌ | imported from `version.py` |
| `config/constants.py` fallback | `0.2.3` | `0.0.0+unknown` |

**Fix:**
- `pyproject.toml`: `dynamic = ["version"]` +
  `[tool.setuptools.dynamic] version = {attr = "version.__version__"}`.
- `config/constants.py`: the hardcoded `ImportError` fallback silently drifts and
  then lies in the About dialog and bug reports. Changed to an obviously-unknown
  value — an honest failure mode beats a plausible wrong one.
- New `tests/test_version_consistency.py` (5 tests) pins all of the above,
  including "pyproject must not hardcode a version".

**Bug found and fixed along the way:** `pip install -e .` was installing an
**empty distribution**. setuptools' flat-layout auto-discovery reported
`discovered packages -- []` because the repository root has too many top-level
directories. Since `quality-gates.yml` installs with `pip install -e ".[dev]"`,
the project itself was never actually installed there. Added explicit
`[tool.setuptools] py-modules` and `[tool.setuptools.packages.find]`.

Verified: `importlib.metadata.version("CTHarvester")` → `0.2.3b2`
(PEP 440 normalization of `0.2.3-beta.2`).

---

### 6. Global exception hook + Qt slot guards (guide §8)

**Problem:** No `sys.excepthook`, no slot-guarding pattern. In PyQt5 ≥ 5.5 an
exception escaping a slot runs `sys.excepthook` and then calls `abort()` — the
window vanishes with nothing in the log.

**New module `ui/exception_handler.py`**, built on the existing (already
excellent) `ui/errors.py` catalog:

- **`guard_slot(context, error_code=None, reraise=False)`** — the primary layer.
  Catches `Exception` (deliberately *not* `KeyboardInterrupt`/`SystemExit`),
  unwinds the override-cursor stack, logs with traceback, and shows a dialog via
  `show_error()` with an inferred or explicit `ErrorCode`.
- **`install_global_exception_hook(show_dialog=True)`** — the backstop. Returns
  the previous hook so tests can restore it. Documented honestly: it cannot stop
  PyQt5 from aborting, but it guarantees the traceback reaches the log.
- **`restore_all_override_cursors()`** — bounded unwind of nested wait cursors.
- `_show_error_safely()` — the reporting path itself never raises.

**Applied to 10 connected slots in `ui/main_window.py`:**
`open_dir`, `save_result`, `export_3d_model`, `create_thumbnail`,
`comboLevelIndexChanged`, `sliderValueChanged`, `rangeSliderValueChanged`,
`slider2SliderReleased`, `show_advanced_settings`, `show_info`.

Hook installed in `CTHarvester.main()` immediately after `CTHarvesterApp`
construction.

**Real bug found and fixed — `guard_slot` signal arity.** The first
implementation wrapped the slot in `def wrapper(*args, **kwargs)`. PyQt5 (sip)
inspects a slot's signature and passes only as many signal arguments as the slot
declares — but a variadic wrapper looks like it accepts everything, so sip
forwarded *all* signal arguments to slots that declared none:

```
TypeError: comboLevelIndexChanged() takes 1 positional argument but 2 were given
TypeError: rangeSliderValueChanged() takes 1 positional argument but 3 were given
```

This is not a test-only artifact: in the running app **every guarded slot
connected to an argument-emitting signal would break on interaction** — a button
`clicked(bool)`, `currentIndexChanged(int)`, `rangeChanged(v1, v2)`. The fix
makes `wrapper` introspect the wrapped function and trim surplus positional
arguments to what it actually accepts, reproducing PyQt's native behaviour.
Slots that *do* declare the signal's args still receive them.

**New `tests/test_exception_handler.py`** (21 tests): return-value passthrough,
exception swallowing, logging, `functools.wraps` metadata, `reraise`,
`KeyboardInterrupt`/`SystemExit` passthrough, single and **nested** cursor
restoration, explicit vs inferred error code, widget-method usage, hook
install/restore/delegation, and a **`TestSignalArity`** group (5 tests) pinning
the arity fix — including a real `QPushButton.clicked` → guarded slot round-trip.

---

### 7. Dependency lockfiles (guide §6)

**Problem:** `requirements.txt` specified ranges only; no lockfile. A fresh
install could pull a different, possibly broken resolution than what CI tested.

**Fix — `uv pip compile --universal`:**

`pip-compile` (pip-tools 7.6) has no universal mode; a Linux-generated lock could
break the new Windows/macOS CI jobs. `uv`'s `--universal` emits one lock valid on
all three platforms via environment markers
(e.g. `numpy==2.4.6 ; python_full_version < '3.12'`).

- `requirements.lock` — 19 packages, hashed
- `requirements-dev.lock` — 59 packages, hashed
- Both generated with `--python-version 3.11` (the declared minimum) and
  `--generate-hashes`.

Added to `[project.optional-dependencies].dev` so the lock covers what CI
actually needs: `pytest-timeout`, `pytest-xdist`, `types-PyYAML` (previously
installed ad hoc in workflow steps).

**Makefile:**
- `make install` / `make install-dev` → `pip install --require-hashes -r *.lock`
- `make lock` → regenerate both
- `make lock-check` → fail if the lock is stale relative to `pyproject.toml`
  (POSIX-sh compatible; verified it detects both the fresh and stale cases)

**CI:**
- `test.yml` and `quality-gates.yml` install via
  `pip install --require-hashes -r requirements-dev.lock`.
- pip cache keys now hash `requirements*.lock`.
- New gating `dependency-lock` job in `quality-gates.yml`: runs `make lock-check`
  and a `--require-hashes --dry-run` install.

`requirements*.txt` are retained for backward compatibility with headers that
now state plainly they are *not* what CI installs.

---

### 8. Coverage gate/summary mismatch

`quality-gates.yml` enforced `--cov-fail-under=75` but its step summary printed
"Coverage meets minimum threshold (60%)". Corrected to 75% with a comment tying
the two together.

---

## 🚫 Deferred

**Item 4 — make lint/type/security checks gating.** Skipped at the user's
request; the tree should be cleaned before flipping these. Specifically still
non-gating:

- `quality-gates.yml`: flake8, pylint, mypy (`|| true` + `continue-on-error`),
  bandit, pip-audit
- `test.yml`: docs build (`continue-on-error`, preserved from before)
- `.pre-commit-config.yaml` flake8 `extend-ignore` still disables **`F821`
  (undefined name)**, `F811`, `F841`, `E722`, `B006`, `B008`, `C901`. `F821`
  catches real `NameError`s statically and should not be off.
- Ruff consolidation (5 tools → 1) not started.

**Also still open from the guide:**
- Packaged-artifact smoke test — `reusable_build.yml` verifies the executable
  *file exists* but never launches it (§7)
- Installer signing / notarization (§7)
- `vulture` / `radon` dead-code and complexity automation (§13)
- 7 naive `datetime.now()` call sites (`DTZ` rules) in
  `core/thumbnail_generator.py` and `ui/handlers/thumbnail_creation_handler.py`

---

## 📁 Files Changed

**Added**
- `.gitattributes`
- `tests/test_smoke.py`
- `tests/test_version_consistency.py`
- `tests/test_exception_handler.py`
- `ui/exception_handler.py`
- `requirements.lock`, `requirements-dev.lock`

**Removed**
- `pytest.ini` (merged into `pyproject.toml`)

**Modified**
- `pyproject.toml` — pytest config, dynamic version, packages, dev extras
- `Makefile` — `lock`, `lock-check`, lock-based install targets
- `CTHarvester.py` — install global exception hook
- `ui/main_window.py` — `@guard_slot` on 10 slots
- `config/constants.py` — honest version fallback
- `docs/conf.py` — version imported from `version.py`
- `Cargo.toml` — version synced
- `requirements.txt`, `requirements-dev.txt` — headers point at the locks
- `.github/workflows/test.yml` — OS matrix, smoke job, lock install
- `.github/workflows/quality-gates.yml` — `dependency-lock` job, lock install,
  coverage threshold text
- `.github/workflows/test-full.yml`, `reusable_build.yml`,
  `update-readme-badges.yml` — `libglut3.12` → `libglu1-mesa`/`freeglut3-dev`
- `README.md`, `README.ko.md` — `pytest.ini` reference
- `CTHarvester.spec`, `VERSION_MANAGEMENT.md` — CRLF → LF

---

## 🧪 Verification

| Check | Result |
|---|---|
| `tests/test_smoke.py` | 62 passed |
| `tests/test_version_consistency.py` | 5 passed |
| `tests/test_exception_handler.py` | 16 passed |
| `pytest` configfile resolution | `configfile: pyproject.toml` |
| `pip install -e . --no-deps` | installs `0.2.3b2` |
| `make lock-check` (fresh) | "Lockfiles are up to date." |
| `make lock-check` (stale) | correctly fails |
| `pip install --require-hashes --dry-run -r requirements-dev.lock` | passes |
| All modified workflow YAML | parses |

**Local environment note:** the full suite could not be completed in this WSL2
environment initially — `libGLU` was absent, so `gluLookAt` was undefined and the
OpenGL widget tests aborted the process (`SIGABRT`), which also hung the
`pytest-xdist` master because `--timeout` cannot interrupt a hard crash. Fixed by
installing `libglu1-mesa`; the CI workflows now install it explicitly.

**Per-file hang/failure triage.** A shell-level `timeout` scan of every test
file (hard kill, unlike pytest-timeout) separated my regressions from the
environment:

| File | Cause | Verdict |
|---|---|---|
| `integration/test_thumbnail_workflow.py` | filterwarnings → pymcubes deprecation → mesh-error modal dialog hang | **mine** → fixed (scoped ignore) |
| `ui/test_mcube_widget.py` | same deprecation promoted to error | **mine** → fixed (scoped ignore); 13 pass |
| `test_export_handler.py` | OpenGL `SIGABRT` (rc=134) — same on clean tree | environmental |
| `test_common.py` | `PermissionError: /root/invalid` | environmental (non-root) |
| `ui/test_utils.py` | rc=5, collects 0 tests — same on clean tree | pre-existing |
| `benchmarks/test_performance.py` | PIL `_idat.fileno` on large-TIFF save; `benchmark` marker, excluded from CI quick suite | pre-existing |

The two "mine" rows were both consequences of correctly enabling
`filterwarnings = error`, resolved by the message-scoped pymcubes ignore. The
`guard_slot` arity `TypeError` (above) was the third and most serious regression —
a real app bug, not just a test failure.

---

## 💡 Lessons

1. **A config file that is never read is worse than no config.** The
   `pytest.ini` / `pyproject.toml` overlap made `filterwarnings = error` look
   configured for months while it did nothing. `--strict-config` now guards the
   remaining surface.
2. **"Backward compatibility" copies drift.** `requirements*.txt`,
   `pyproject.toml`'s version, `Cargo.toml`, `docs/conf.py` and the
   `constants.py` fallback all claimed to follow `version.py` and three of them
   didn't. Derivation beats duplication; where duplication is unavoidable, a test
   should assert it.
3. **A hardcoded fallback should look broken when it is.** `0.2.3` as an
   `ImportError` fallback is indistinguishable from a real version in a bug
   report; `0.0.0+unknown` is not.
4. **Auto-discovery failing silently is a packaging bug.** `pip install -e .`
   producing an empty distribution went unnoticed because nothing asserted the
   package was importable *from the install*.
5. **Cross-platform CI is cheap relative to what it catches** — and the smoke job
   makes it cheaper by failing in ~2 minutes instead of 30 when a platform is
   fundamentally broken.

---

## Appendix — pymcubes / NumPy 2.5 update investigation

Prompted by the question "what happens if we update pymcubes?" — because the
NumPy 2.5 deprecation above comes from inside it.

**Environment:** installed `PyMCubes==0.1.6`, `numpy==2.5.1`. NumPy 2.5 is
already present, so the deprecation is live, not hypothetical.

**Does updating help? No.**

- **0.1.6 is the latest release** on PyPI (`pip index versions pymcubes`:
  `0.1.6, 0.1.5, …`). It is already installed.
- **The `master` branch is not fixed either.** `mcubes/src/_mcubes.pyx` still
  does direct shape assignment in both entry points:
  - line 23–24: `verts.shape = (-1, 3)` / `faces.shape = (-1, 3)` (`marching_cubes`)
  - line 33–34: same in `marching_cubes_func`
- **No upstream issue or PR** tracks the NumPy 2.5 deprecation (repo has 4 open
  issues, none related).

So a version bump — or even a VCS install from `master` — changes nothing.

**Severity / timeline.** NumPy's 2.5 release notes deprecate setting `.shape`
"because mutating an array is unsafe if shared, especially across threads" and
recommend `np.reshape(..., copy=False)`. **No removal version is announced**, so
today it is a warning only; `marching_cubes` returns correct results (verified:
`(N,3)` verts/faces). The real risk is deferred: whenever NumPy turns this into a
hard error, pymcubes 0.1.6 breaks unconditionally and no warning filter helps.

**Our call sites:** `ui/handlers/export_handler.py:150`,
`ui/widgets/mcube_widget.py:122`. The reshape happens *inside* pymcubes before it
returns, so we cannot avoid triggering it from our side.

**Options (not yet applied — investigation only):**

1. **Status quo — message-scoped pytest ignore** (what this devlog shipped).
   Correct for the actual symptom (tests under `-W error`). Production is
   unaffected because the app does not run warnings-as-errors. *Lowest effort;
   recommended default.*
2. **Suppress at our two call sites** with `warnings.catch_warnings()` /
   `simplefilter("ignore", DeprecationWarning)`. Protects any run under a strict
   warning filter, not just pytest. Caveat: `catch_warnings` mutates global state
   and is not thread-safe, and `mcube_widget` calls into pymcubes from a worker
   thread — needs care to avoid racing the main thread's filters.
3. **Upstream fix.** One-line-per-site change
   (`verts = verts.reshape(-1, 3)`); submit a PR to pmneila/PyMCubes. Removes the
   need for any local ignore, benefits everyone, but depends on a maintainer
   merge + release (repo activity is low).
4. **Pin a NumPy ceiling** (`numpy<2.5`) — rejected: fights the ecosystem and
   forgoes NumPy fixes for a mere deprecation warning.

**Recommendation:** keep option 1 now; open an upstream PR (option 3) as the real
remediation and, if/when NumPy announces a removal version, revisit with option 2
as a stopgap. Track via a follow-up issue.

---

## 💡 Lessons

1. **A config file that is never read is worse than no config.** The
   `pytest.ini` / `pyproject.toml` overlap made `filterwarnings = error` look
   configured for months while it did nothing. `--strict-config` now guards the
   remaining surface.
2. **"Backward compatibility" copies drift.** `requirements*.txt`,
   `pyproject.toml`'s version, `Cargo.toml`, `docs/conf.py` and the
   `constants.py` fallback all claimed to follow `version.py` and three of them
   didn't. Derivation beats duplication; where duplication is unavoidable, a test
   should assert it.
3. **A hardcoded fallback should look broken when it is.** `0.2.3` as an
   `ImportError` fallback is indistinguishable from a real version in a bug
   report; `0.0.0+unknown` is not.
4. **Auto-discovery failing silently is a packaging bug.** `pip install -e .`
   producing an empty distribution went unnoticed because nothing asserted the
   package was importable *from the install*.
5. **Cross-platform CI is cheap relative to what it catches** — and the smoke job
   makes it cheaper by failing in ~2 minutes instead of 30 when a platform is
   fundamentally broken.
6. **Warnings-as-errors earns its keep — and a variadic decorator is a trap.**
   Turning it on surfaced a real NumPy 2.5 break in a dependency; wrapping Qt
   slots in `*args` silently broke PyQt's argument-count introspection. Both were
   invisible until a test actually exercised them, which is the whole argument for
   the smoke + integration coverage added here.

---

## Follow-up — CI consolidation to Modan2's shape (same day)

After the above, the workflow set was aligned with Modan2's layout and trimmed
from **13 workflows to 9** (the lint-tooling choice — black/isort/flake8 — was
kept; only the Ruff-migration part of item 4 stays deferred).

**Consolidated:**
- `quality-gates.yml` **deleted**; its jobs moved to mirror Modan2's split:
  - code-quality + type-checking → a new **`lint` job in `test.yml`**
    (black/isort gating; flake8 real-error subset gating; full flake8 + mypy
    advisory — mypy is advisory because `python_version=3.11` trips the numpy
    2.5 stubs' 3.12 `type` syntax).
  - coverage gate → folded into `test.yml`'s test job (`--cov-fail-under=75` on
    the reference leg).
  - bandit + pip-audit + dependency-lock → a new **`security.yml`** (weekly +
    push/PR), matching Modan2's single security workflow.
- `test.yml` gained `workflow_call`; `release.yml` now gates on it (`uses:
  ./.github/workflows/test.yml`), like Modan2.
- `build.yml` / `release.yml` / `manual-release.yml` switched from
  `github.run_number` to a shared **commit-count build number**
  (`git rev-list --count HEAD`), so every build path stamps a consistent number.

**Removed as overkill for a solo, commit-to-main project** (analysis in
`docs/CI_RECOMMENDATIONS_FOR_MODAN2.md`):
- `dependency-review.yml` — fires only on PRs (never, here); CVE coverage
  duplicates pip-audit.
- `performance-tracking.yml` — benchmark-trend tracking is for SLA'd products;
  run benchmarks on demand instead.
- `update-readme-badges.yml` — cosmetic auto-commit bot; use Codecov's badge.
- `generate-release-notes.yml.disabled` — dead file; release notes come from
  CHANGELOG.md in `release.yml`.

**Kept as valuable extras Modan2 lacks:** `codeql.yml` (cheap SAST) and
`test-full.yml` (nightly slow/benchmark/stress suite).

**Reverse direction:** `docs/CI_RECOMMENDATIONS_FOR_MODAN2.md` records what
Modan2's CI would gain from CTHarvester (lockfiles + `--require-hashes`, CodeQL,
ruff `S` ruleset, a version-consistency test), plus the shared packaged-artifact
smoke-test gap.

Final workflow set (9): `test.yml`, `security.yml`, `codeql.yml`, `build.yml`,
`docs.yml`, `release.yml`, `manual-release.yml`, `reusable_build.yml`,
`test-full.yml`.

---

## 💡 Lessons

1. **A config file that is never read is worse than no config.** The
   `pytest.ini` / `pyproject.toml` overlap made `filterwarnings = error` look
   configured for months while it did nothing. `--strict-config` now guards the
   remaining surface.
2. **"Backward compatibility" copies drift.** `requirements*.txt`,
   `pyproject.toml`'s version, `Cargo.toml`, `docs/conf.py` and the
   `constants.py` fallback all claimed to follow `version.py` and three of them
   didn't. Derivation beats duplication; where duplication is unavoidable, a test
   should assert it.
3. **A hardcoded fallback should look broken when it is.** `0.2.3` as an
   `ImportError` fallback is indistinguishable from a real version in a bug
   report; `0.0.0+unknown` is not.
4. **Auto-discovery failing silently is a packaging bug.** `pip install -e .`
   producing an empty distribution went unnoticed because nothing asserted the
   package was importable *from the install*.
5. **Cross-platform CI is cheap relative to what it catches** — and the smoke job
   makes it cheaper by failing in ~2 minutes instead of 30 when a platform is
   fundamentally broken.
6. **Warnings-as-errors earns its keep — and a variadic decorator is a trap.**
   Turning it on surfaced a real NumPy 2.5 break in a dependency; wrapping Qt
   slots in `*args` silently broke PyQt's argument-count introspection. Both were
   invisible until a test actually exercised them, which is the whole argument for
   the smoke + integration coverage added here.
7. **Match the CI to the project, not to a checklist.** CTHarvester had 13
   workflows for a solo beta tool; four never fired or tracked nothing. Fewer,
   gating workflows beat many advisory ones.

---

**Next:** item 4 (Ruff consolidation + flipping checks to gating) once the tree
is clean, then the packaged-artifact smoke test, then an upstream PyMCubes PR.
