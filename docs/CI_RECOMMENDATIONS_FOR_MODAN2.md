# CI/CD Recommendations for Modan2

**Author context:** written from CTHarvester after adopting Modan2's
`docs/CODE_QUALITY_GUIDE.md` and aligning CTHarvester's CI to Modan2's shape.
Recording, in the other direction, the few things CTHarvester's CI does that
Modan2's does **not** yet — worth porting back.

**Date:** 2026-07-24
**Modan2 CI reviewed:** `test.yml` (ruff+mypy lint, OS matrix, smoke),
`security.yml` (pip-audit), `build.yml`, `docs.yml`, `release.yml`,
`manual-release.yml`, `reusable_build.yml`.

---

## Where Modan2 is already ahead (for context)

Modan2's CI is, in several respects, cleaner than CTHarvester's was — these are
things CTHarvester copied *from* Modan2, not the reverse:

- **Single lint tool (ruff + ruff-format)**, pinned in CI and pre-commit.
  CTHarvester still runs black + isort + flake8 + pylint.
- **Single pytest config.** Modan2 keeps its pytest config in one place;
  CTHarvester had a `pytest.ini` / `pyproject.toml` overlap that silently
  disabled `filterwarnings`.
- **Selective, low-noise `filterwarnings`.** Modan2 ignores third-party
  `DeprecationWarning`/`PendingDeprecationWarning` and turns *one specific*
  signal into an error (`error:Glyph.*missing from font`, the tofu-text guard),
  rather than broad warnings-as-errors. CTHarvester went broad-error + scoped
  ignores and immediately hit a pymcubes NumPy-2.5 deprecation it had to special-
  case. Modan2's targeted approach is arguably the lower-maintenance design.
- **CHANGELOG-sourced release notes** and a **commit-count build number**
  shared across build/release paths.

So this document is short by design: Modan2 does not need much.

---

## Recommended additions (prioritized)

### 1. Dependency lockfiles + hash-verified installs — *highest value*

**Gap.** Modan2 installs from `requirements.txt` / `config/requirements-ci.txt`,
which specify version **ranges**. CI, a new contributor, and a release build can
each resolve a *different* set of wheels. This is precisely the
"corrupted/half-broken environment" class the code-quality guide (§6) warns
about — and the guide is Modan2's own document.

**Recommendation.** Generate a universal, hashed lockfile and install from it
everywhere:

```bash
uv pip compile pyproject.toml --universal --python-version 3.11 \
    --generate-hashes -o requirements.lock
uv pip compile pyproject.toml --universal --python-version 3.11 \
    --generate-hashes --extra dev -o requirements-dev.lock
```

- `--universal` emits one lock valid on Linux/macOS/Windows via environment
  markers, so the same file serves the whole OS matrix.
- CI and release builds: `pip install --require-hashes -r requirements-dev.lock`.
- Add a **`make lock-check`** target (regenerate to a temp file, `diff` ignoring
  the header) and a gating CI job, so a `pyproject.toml` dependency change that
  forgets to re-lock fails the build instead of silently drifting.

**Effort:** ~1 hour. **Payoff:** reproducible builds; the shipped installer is
provably built from the packages CI tested. See CTHarvester's `Makefile`
(`lock` / `lock-check`) and `.github/workflows/security.yml` for a working
implementation.

### 2. CodeQL static analysis (`codeql.yml`)

**Gap.** Modan2's `security.yml` runs `pip-audit` (dependency CVEs) but there is
no **static application security testing** of Modan2's own code — no data-flow
analysis for injection, path traversal, or tainted-file handling.

**Recommendation.** Add a `codeql.yml` (GitHub-native, free for public repos,
zero maintenance) on push-to-main + weekly. For a morphometrics app that ingests
user files and archives, data-flow analysis catches a class of bug that
pip-audit and pattern linters cannot. Modan2 being the larger codebase, the
expected value is higher than for CTHarvester.

**Effort:** ~15 min (copy CTHarvester's `codeql.yml`, adjust `paths-ignore`).

### 3. Enable the `S` (bandit) ruleset in ruff

**Gap.** Modan2's ruff `select` is `E, F, I, N, UP, B, C4, LOG, RUF012`. It does
**not** include `S` (flake8-bandit), and there is no standalone bandit. The
quality guide (§12) explicitly calls for "bandit (or Ruff's `S` rules)" for a
file-ingesting desktop app.

**Recommendation.** Add `"S"` to the ruff `select`, with the usual test-tree
carve-out, so `eval`/`exec`/`pickle`/`shell=True`/unsafe-YAML/weak-hash/insecure
path patterns are caught in-editor with no new tool:

```toml
[tool.ruff.lint]
select = [ ..., "S" ]

[tool.ruff.lint.per-file-ignores]
"tests/**" = ["S101"]  # asserts are fine in tests
```

This fits Modan2's stated "phased adoption" plan (devlog R05). Expect a first
pass of findings to triage; auto-fixable ones are rare in `S`, so budget a
dedicated review.

**Effort:** ~1–3 hours depending on finding count.

### 4. A version single-source-of-truth test

**Gap.** Modan2 has `version.py`, but (as of review) no test asserting that every
other file deriving a version stays in sync with it. This is the exact drift
CTHarvester just hit: `pyproject.toml` sat at `0.2.3-beta.1` while `version.py`
said `0.2.3-beta.2`.

**Recommendation.** A ~40-line `tests/test_version_consistency.py` that asserts
`pyproject.toml` uses a dynamic version (not a hardcoded literal), and that any
other version-bearing files (installer scripts, docs `conf.py`, a Rust
`Cargo.toml` if present) match `version.py`. Cheap insurance against a
bump-one-file-forget-another release. See CTHarvester's file of the same name.

**Effort:** ~30 min.

---

## Shared gap (neither project has it yet)

### Packaged-artifact smoke test

Both projects build per-OS installers in CI but verify only that the executable
*file exists* — neither installs the produced artifact in a clean runner and
launches it headless. This is the "works from source, broken when frozen"
surface (PyInstaller missing a data file, an unbundled native lib) that source
tests cannot reach (guide §7).

**Recommendation (both repos).** After the build job, on a clean runner: install
the artifact, launch it with an offscreen Qt platform, assert it reaches an idle
main window, then quit. Gate the release on it.

---

## Not recommended for Modan2

For completeness, some CI that CTHarvester carried and is now *removing* as
overkill — Modan2 should not add these either:

- **`dependency-review` action** — only fires on pull requests; low value for a
  solo, commit-to-main workflow, and its CVE coverage duplicates `pip-audit`.
- **A dedicated performance-tracking workflow** — benchmark-trend tracking is for
  products with performance SLAs; running benchmarks behind a marker on demand is
  enough.
- **A README-badge auto-commit bot** — cosmetic; adds churn to history. Use
  Codecov/shields.io badges that render from live data instead.

---

## Summary

| Recommendation | Value | Effort | Guide § |
|---|---|---|---|
| 1. Lockfiles + `--require-hashes` + `lock-check` gate | High | ~1 h | §6 |
| 2. CodeQL SAST | Medium-High | ~15 min | §12 |
| 3. ruff `S` ruleset | Medium | 1–3 h | §12 |
| 4. Version-consistency test | Medium | ~30 min | §5/§7 |
| — Packaged-artifact smoke test (shared) | High | ~2 h | §7 |

Items 1 and 2 are the ones worth doing soon; 3 and 4 fit Modan2's existing
phased-adoption cadence.

---

# Addendum — 2026-07-27

A second pass, after CTHarvester finished adopting the guide (devlogs 101–105).
Everything below was checked against the Modan2 tree rather than assumed.

## 1. Markdown under `docs/` is not published — 12 files ⚠️

**This is the one worth acting on.**

`docs/conf.py` has no `myst_parser`, so Sphinx reads `.rst` only. Every `.md`
file under `docs/` therefore builds into nothing: it is readable on GitHub and
nowhere else. Modan2 has 12 of them, and `index.rst`'s toctree lists only the
8 `.rst` files.

CTHarvester had the same setup and the same blind spot. It surfaced when a
documentation audit called `docs/configuration.md` complete — a 457-line
reference for every settings key that had never appeared on the documentation
site at all.

Worth checking which of Modan2's 12 are user-facing. Two options:

- **Add `myst-parser`** and put the user-facing ones in the toctree.
- **Split by extension explicitly** — `.rst` is the published manual, `.md` is
  repository-only developer notes — and convert the ones on the wrong side.
  CTHarvester took this route; see `docs/README.md` there for the wording.

Either is fine. Leaving it implicit is what costs you a document nobody reads.

## 2. PyOpenGL backends and PyInstaller — informational

CTHarvester's packaged Linux build could not start at all:

```
File "OpenGL/platform/__init__.py", line 52, in _load
TypeError: 'NoneType' object is not callable
```

PyOpenGL selects its backend at runtime through `OpenGL.plugins`, importing the
module by dotted name (`OpenGL.platform.glx` and friends). PyInstaller's static
analysis cannot see a dotted-name import, so no backend was bundled.

Modan2 uses PyOpenGL and passes no `--hidden-import` at all, so this looked like
a shared risk — but Modan2's packaged smoke test passes on all three platforms,
so the bundle is fine as built. Recorded only so the signature is recognisable
if it ever appears. The fix is `OpenGL.platform.{glx,egl,osmesa,win32,darwin}`
in hidden imports.

This is also the third time the packaged-artifact smoke test has justified
itself: CTHarvester added it on Modan2's model and it failed on its first run,
catching exactly this.

## 3. Where Modan2 is *still* ahead — CTHarvester should copy these back

Checked while looking for things to recommend, and found the reverse:

- **Per-platform lockfiles** (`--python-platform linux|windows|macos`).
  CTHarvester used one `--universal` lock and hit a defect Modan2's approach
  cannot have: `pyqt5-qt5` stopped shipping Windows wheels after 5.15.2, uv does
  not check wheel-tag coverage, and the single pin broke every Windows CI job.
  CTHarvester patched it with environment markers; Modan2's per-platform locks
  are the better design.
- **`lock-check` seeding.** Modan2's Makefile already copies the committed lock
  into the temp file before recompiling, with a comment explaining exactly why.
  CTHarvester's did not, so its gating `dependency-lock` job failed on every
  upstream release for weeks. Modan2 got this right first.

## 4. A complexity ratchet, if you want one

Modan2 has no `[tool.ruff.lint.mccabe]` setting, so `C901` is unenforced. Current
distribution:

| max-complexity | functions over |
|---|---|
| 10 | 53 |
| 15 | 12 |
| 20 | 1 |
| 30 | 0 |

Enabling `C901` at 15 would mean refactoring 12 functions first, which is why it
tends not to get enabled at all. The ratchet avoids that: set `max-complexity` to
the current worst value (30 here), so the rule passes today and nothing can get
*worse*, then lower it as functions are split.

CTHarvester went 32 → 28 → 20 → 18 → 15 over eight functions this way and is now
at the guide's threshold. The cost is one config line up front instead of a
refactoring project.

## Summary of this addendum

| Item | Value | Effort |
|---|---|---|
| 1. Publish or explicitly exclude `docs/*.md` | **High** | 1–2 h |
| 2. PyOpenGL hidden imports | Informational | — |
| 3. (CTHarvester adopting Modan2's lock design) | — | — |
| 4. `C901` ratchet | Medium | 5 min + ongoing |
