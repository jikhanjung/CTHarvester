# Devlog 107: The Manual Gets Its Own Directory

**Date:** 2026-07-27
**Current Version:** 0.2.3-beta.2
**Status:** ✅ `docs/manual/` is the Sphinx source directory; `docs/` root is notes
**Previous:** [devlog 106 - Per-Platform Lockfiles](./20260727_106_per_platform_lockfiles.md)

---

## 🎯 Overview

Devlog 105 discovered that Markdown under `docs/` is never published, and made
the split explicit: `.rst` is the manual, `.md` is repository-only notes. This
replaces that rule with a directory boundary, which is what Modan2 already does.

---

## 🤔 Why the extension rule was not good enough

It worked. The objection is that it is **invisible and conditional**:

1. **It depends on a configuration absence.** `.md` is unpublished only because
   `conf.py` has no `myst_parser`. Adding it some day — a reasonable thing to
   want, since Markdown is easier to write — would silently turn nine internal
   notes into manual pages. A rule that inverts when someone enables an
   extension is not a rule, it is a coincidence that has held so far.
2. **It had already failed once.** `configuration.md` was a complete, audited
   reference for every settings key that had never been published at all. The
   convention did not prevent that, because nothing about the filename says
   "this will not reach a user".
3. **Modan2 had already solved it.** `docs/manual/` there holds `conf.py`, the
   `.rst` files, `locale/` and `_templates/`; `docs/` root holds twelve `.md`
   notes. Checking before designing something new turned an open question into a
   copy.

A directory says the same thing in a form that survives a `conf.py` change: the
Sphinx source directory is `docs/manual/`, so anything outside it *cannot* be
published, whatever extensions are enabled.

---

## 📁 What moved

Into `docs/manual/`: `conf.py`, `index.rst` and the eight manual pages,
`Makefile`, `requirements.txt`, `locale/`, `_templates/`.

Staying at the `docs/` root: the nine `.md` notes, `developer_guide/`,
`release-notes/`, and `README.md`, which now explains the split as a directory
boundary and records why it is not an extension rule.

Everything that pointed at the old paths, which is more than the move itself:

| Where | Change |
|---|---|
| `docs/manual/conf.py` | `sys.path` `..` → `../..`; `conf_py_path` → `/docs/manual/` |
| `.readthedocs.yaml` | `sphinx.configuration`, `python.install.requirements` |
| `.github/workflows/docs.yml` | trigger paths, pip install, two `cd`s, artifact path |
| `.github/workflows/test.yml` | the gating `docs` job |
| `Makefile` | `docs`, `docs-serve`, `docs-watch`, `docs-clean` |
| `.gitignore` | `docs/manual/_build/`, `docs/manual/_static/` |
| `tests/test_version_consistency.py` | the `conf.py` path it asserts on |
| `README.md`, `CONTRIBUTING.md` | build instructions and "which file do I edit" |

`developer_guide.rst`'s links to the internal notes are absolute GitHub URLs and
were unaffected — the notes did not move.

**Published URLs do not change.** The build output layout (`_build/html/{en,ko}`)
is the same; only the source path moved.

### One thing the move enables

`docs.yml` triggered on `docs/**`, so editing `CI_CD_AUDIT.md` redeployed the
documentation site. It now triggers on `docs/manual/**`. That narrowing was not
possible while both kinds of file shared a directory.

---

## 🧰 Sphinx was not installed, which was itself the finding

`make docs` failed locally with `sphinx-build: not found`. The build was verified
in a throwaway environment first, then the cause was worth fixing rather than
working around: `make install-dev` installs from the dev lockfiles, and the
documentation toolchain was not in them. It lived in `docs/requirements.txt` (for
CI) and in pyproject's `docs` extra (never installed by anything).

The dev locks are now compiled with `--extra dev --extra docs`, so
`make install-dev` leaves a contributor able to run `make docs` and
`make docs-watch` immediately. `docs` stays the single declaration —
`sphinx-intl` was added to it to match `docs/manual/requirements.txt`, which
remains the narrower set CI installs to build.

A self-referential extra (`dev = [..., "ctharvester[docs]"]`) was tried first as
the DRY option; uv went looking for `ctharvester` on the index and hung until it
was killed at five minutes. Two compile flags in the Makefile do the same job
without the mystery.

---

## 🧪 Verification

- `make docs` succeeds; **2 warnings, both pre-existing** (`_static` missing,
  and a `×` character defeating the Python lexer in `advanced_features.rst`)
- Korean build succeeds; `configuration.html` present in the output; the version
  in the rendered page is `0.2.3-beta.2`, so `conf.py`'s `from version import`
  still resolves through the deeper path
- `make lock-check` clean after regenerating all nine locks with the docs extra;
  dev locks dry-run install on 3.11 and 3.13
- `tests/test_version_consistency.py` passes — it asserts on the `conf.py` path
  and would have caught the move on its own
- All workflow YAML parses

---

## 💡 Lessons

1. **A convention that depends on a tool's absence is not a convention.** "`.md`
   is not published" was true only while `myst_parser` was not installed. The
   directory boundary is true regardless.

2. **Check what the sibling project did before designing.** `docs/manual/`
   existed in Modan2 already. The work was a copy, not a design.

3. **A tool missing from your own environment is a signal.** `sphinx-build: not
   found` could have been fixed with one `pip install`. Asked instead why
   `make install-dev` had not provided it, it pointed at a real gap in the dev
   lockfiles.

4. **Moving files is the small part.** Fourteen files moved; eight other places
   referenced them, in five different config formats. The test that hardcodes
   `docs/conf.py` was the only one that would have failed loudly.

---

**Next:** the `docs/user_guide/troubleshooting.rst` references, which point at a
path that has never existed, and the question of a link checker for the `.md`
notes that no build validates. Both in `TODOs.md`.
