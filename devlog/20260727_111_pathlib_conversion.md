# Devlog 111: The pathlib Conversion, in Slices

**Date:** 2026-07-27
**Current Version:** 0.2.3-beta.2
**Status:** 🚧 In progress — stages 1 to 4 landed
**Previous:** [devlog 110 - pytest 9 and the Day's Ledger](./20260727_110_pytest_9_and_the_days_ledger.md)

---

## 🎯 Overview

`PTH` was the last of the code quality guide's lint groups and by far the
largest: **499 findings**, `os.path` to `pathlib`. Unlike `SIM` and `TRY`, ruff
can autofix almost none of it — **2 of 499** — so every site is a hand edit with
a decision attached.

This is being done a directory at a time, each slice verified against the full
suite before the next starts.

---

## 📐 The rule the whole conversion follows

**Public signatures keep returning `str`. `Path` is an internal detail,
converted back at the boundary.**

That constraint is what keeps this a refactor instead of an API change. Path
strings cross a lot of boundaries here — `settings_hash` dictionaries, Qt
widgets, the Rust thumbnail module, `SecureFileValidator`, and a test suite that
builds its fixtures with `os.path.join`. Letting `Path` objects leak through
those would turn a mechanical conversion into a typed-API migration, and the two
should not be attempted in one change.

`security/file_validator.py` is the clearest case: every entry point is
`str -> str`, and it still is. The internals use `Path`; `safe_join` ends with
`str(Path(base_dir).joinpath(*parts))`.

---

## 📦 Stage 1 — the small modules (33 sites)

`security/` (8), `config/` (15), `CTLogger.py` (5), the two build scripts (4),
`docs/manual/conf.py` (1).

Three things came out of it that were not "replace call A with call B".

### A trailing slash that would not have survived

`config/constants.py` built its directories like this:

```python
DEFAULT_STORAGE_DIRECTORY = os.path.join(DEFAULT_DB_DIRECTORY, "data/")
```

Note the trailing slash. `os.path.join` keeps it; `Path(...) / "data"` does not.
Four constants, all exported and imported across the codebase. Checked the
consumers before touching them: all four go only to `ensure_directories()`, and
nothing — code or test — reads their exact string form. Safe, but only because
it was checked; this is exactly the kind of difference that survives a code
review and fails on a user's machine.

### A latent bug in the docs config

`docs/manual/conf.py` found the repository root with
`os.path.abspath("../..")` — **relative to the process working directory.**
Under `make docs`, which cds into `docs/manual`, that is correct. Under
`make docs-watch`, where `sphinx-autobuild` runs from the repository root,
`"../.."` points *outside the repository entirely*.

The conversion did not cause this and would not have found it either, except
that writing `Path("../..").resolve()` makes the cwd dependence impossible to
miss in a way `os.path.abspath` did not. Now derived from `__file__`.

### The conversion hazard, in miniature

`config/i18n.py` broke two tests, and the reason is the thing to remember about
this whole exercise:

```python
@patch("os.path.exists")          # the test controlled the code through this
...
if not os.path.exists(qm_file):   # ...and the code stopped calling it
```

Converting to `qm_path.exists()` did not change behaviour at all — it changed
**what the tests were able to intercept**. Retargeted at `Path.exists` with
`autospec=True`, because the path is now the *receiver* rather than an argument
and only autospec records `self`. The assertions check the same behaviour they
did before: that the manager probes the conventional `.qm` location.

A conversion that "cannot change behaviour" can still invalidate every mock
aimed at the old call.

---

## 📦 Stage 2 — `utils/` (29 sites)

Mostly `open()` → `Path.open()` in `settings_manager.py`, plus the thumbnail
path helpers in `file_utils.py`.

`file_utils.py` is where the "boundary" rule earns itself. Its four public
functions all return `str` paths that callers put into dictionaries and pass to
PIL. Internally they now build a `Path` and convert once at the `return`:

```python
thumb_path = Path(base_dir) / THUMBNAIL_DIR_NAME
if level != 1:
    thumb_path = thumb_path / str(level)
thumb_dir = str(thumb_path)
```

One simplification fell out: `ensure_directories()` in `common.py` was
`if not os.path.exists(d): os.makedirs(d, exist_ok=True)` — an existence check
guarding a call whose entire purpose is to not need one. Now a single
`Path(d).mkdir(parents=True, exist_ok=True)`.

---

## 📦 Stage 3 — `core/` (47 sites)

The largest slice of shipped code: `file_handler.py`, `thumbnail_generator.py`,
`thumbnail_worker.py`, `sequential_processor.py`. Almost all of it is
`os.path.join` building a path that is then stored on `self` or handed to PIL,
the Rust module or `SecureFileValidator` — so almost all of it converts to a
`Path` expression wrapped in `str()` at the assignment.

Two things went wrong, and both are worth having on the record.

### A scripted replacement ate an `if`

The conversion was applied by script, matching exact source text. This pattern:

```python
if not os.path.exists(to_dir):
    os.makedirs(to_dir)
    logger.debug(f"Created directory {to_dir}")
else:
    logger.debug(f"Directory already exists: {to_dir}")
```

was replaced with a single `Path(to_dir).mkdir(parents=True, exist_ok=True)`,
which is the right call *for the two lines it matched* and left the `logger`
line and the `else:` branch dangling behind it. Syntax error, caught
immediately by ruff.

The repair kept the `if`/`else`, because the two branches log different
things — collapsing them would have silently dropped the distinction between
"created" and "already existed". **A pattern that looks mechanical in three
files is not mechanical in the fourth.**

### mypy caught the exact leak this conversion is trying to avoid

```
core/file_handler.py:378: error: Incompatible return value type
    (got "list[Path]", expected "list[str]")
```

`get_file_list` builds its entries with `Path(directory_path) / filename` and
returns them. The declared return type is `list[str]`, and callers treat the
entries as strings. Converting the `exists()` check was right; letting the
`Path` into the returned list was not.

This is the boundary rule failing in practice and being caught by a gate that
was advisory until this morning. Nothing in the test suite would have found it:
`Path` and `str` behave identically until something does string arithmetic on
the result.

---

## 📦 Stage 4 — `ui/` (25 sites)

Uneventful, which after stage 3 is worth saying. The one pattern that needed
thought appears twice — in `main_window.py` and `object_viewer_2d.py` — and is
the "retry with a lowercase extension" fallback for image files:

```python
base, ext = os.path.splitext(first_image_path)
alt_path = base + ext.lower()
```

`Path.with_suffix()` expresses this directly:

```python
first_path = Path(first_image_path)
alt_path = str(first_path.with_suffix(first_path.suffix.lower()))
```

Checked against the awkward inputs before trusting it: a name with several dots
(`a.b.TIF` → `a.b.tif`) and a name with no extension at all (`a` → `a`) both
behave the same as the `splitext` version.

---

## 🔭 What is left

| Stage | Target | Sites |
|---|---|---|
| 5 | `scripts/` | 48 |
| — | `tests/` | 322 — to be waived, see below |

### Why `tests/` will be waived rather than converted

322 of the 499 findings are in the test suite, and nearly all are
`os.path.join(self.temp_dir, "name")` producing a **string that is then handed
to the function under test**. Converting them changes the type the tests feed
the API, which changes what is being tested; wrapping them in `str(...)` adds
noise and tests nothing new. Doing it properly means rewriting those fixtures
onto pytest's `tmp_path`, which is a rewrite, not a conversion.

Same reasoning as waiving `S101` there: the rule is aimed at production code and
the test tree is a different context. It will be a per-file ignore with that
argument written next to it.

---

## 💡 Lessons so far

1. **"It cannot change behaviour" is not the same as "it cannot break tests."**
   The i18n mocks were aimed at a call that stopped existing.

2. **Check the string, not just the call.** `os.path.join(x, "data/")` and
   `Path(x) / "data"` are not the same string, and only one of them has a
   trailing separator.

3. **A conversion is a good time to notice what the old call was hiding.**
   `os.path.abspath(".")` reads as "an absolute path"; `Path.cwd()` reads as
   "wherever this process happens to be", which is the thing you actually want
   to think about.
