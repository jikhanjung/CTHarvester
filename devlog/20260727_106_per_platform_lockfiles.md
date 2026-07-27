# Devlog 106: Per-Platform Lockfiles, and What a Universal Lock Cannot Say

**Date:** 2026-07-27
**Current Version:** 0.2.3-beta.2
**Status:** ✅ Nine per-platform locks; the `pyqt5-qt5` marker workaround removed
**Previous:** [devlog 105 - Complexity Backlog Cleared and Manual Audit](./20260727_105_complexity_backlog_cleared_and_manual_audit.md)

---

## 🎯 Overview

The last item devlog 105 brought back from Modan2: replace the single
`--universal` lockfile with one lock per platform. This is the change that makes
the `pyqt5-qt5` defect — which took down every Windows CI job — structurally
impossible rather than merely patched.

---

## 🔧 What was wrong with `--universal`

`uv pip compile --universal` resolves **one version per package** for Linux,
macOS and Windows together, expressing platform differences through environment
markers. What it does not do is check **wheel-tag coverage**. So a package whose
wheels differ by platform cannot be expressed:

- `pyqt5-qt5` (the bundled Qt runtime, pulled in transitively by `pyqt5`) stopped
  publishing Windows wheels after **5.15.2**. Linux and macOS reach **5.15.19**.
- The universal lock pinned 5.15.19 for everything, and
  `pip install --require-hashes` died on Windows with *"No matching distribution
  found for pyqt5-qt5==5.15.19"*.

The patch at the time was to name `pyqt5-qt5` in `pyproject.toml` twice, with
`sys_platform` markers, to force the resolver to fork. It worked, and it was a
workaround for a tool limitation sitting in the project's public dependency
list — where a reader has no way to tell it apart from a real constraint.

Resolving once per platform removes the premise. `uv` only considers wheels the
target platform can install, so it picks the right version by itself:

```
$ printf 'pyqt5>=5.15.0,<6.0.0\n' > nomarker.in
$ for p in windows linux macos; do uv pip compile nomarker.in --python-platform $p ... ; done
windows: pyqt5-qt5==5.15.2
linux:   pyqt5-qt5==5.15.19
macos:   pyqt5-qt5==5.15.19
```

That was checked **before** touching anything, with the markers removed, on a
minimal input. The markers are now gone from `pyproject.toml`.

---

## 📦 The new layout — nine files

Three variants x three platforms. The variant split is CTHarvester's own and is
kept, because each is consumed by a different job:

| File | Contents | Consumed by |
|---|---|---|
| `requirements-<os>.lock` | runtime only | pip-audit, CodeQL |
| `requirements-dev-<os>.lock` | + test and lint | lint, smoke, test matrix |
| `requirements-build-<os>.lock` | + PyInstaller, maturin | the three build jobs |

`make install` / `make install-dev` pick the lock matching the machine, so a
contributor's command line does not change. The platform is derived from
`uname -s` via make conditionals rather than a shell `case` — make counts
parentheses inside `$(shell ...)`, and a `case` arm's `)` closes the expansion
early. That mistake cost one `/bin/sh: Syntax error: end of file unexpected`
before it was obvious.

---

## ⚖️ The tradeoff, stated plainly

`--universal` can fork by **Python version** as well as by platform, and it was
doing so:

```
numpy==2.4.6 ; python_full_version < '3.12'
numpy==2.5.1 ; python_full_version >= '3.12'
scipy==1.17.1 ; python_full_version < '3.12'
scipy==1.18.0 ; python_full_version >= '3.12'
```

`--python-platform` and `--universal` are mutually exclusive (uv rejects the
combination outright), so a per-platform lock is compiled at one Python floor —
3.11 here — and that fork is gone. **Every leg of the 3.11-3.13 matrix now
installs the 3.11-compatible resolution**: numpy 2.4.6, not 2.5.1.

This is a real loss and worth naming rather than discovering later. It was
accepted because an uninstallable Windows lock is a broken build while an older
numpy on the 3.13 leg is a narrower test surface. If testing against numpy 2.5
on the newer legs matters, it needs a deliberate second axis of locks, and
that is now in `TODOs.md` rather than in someone's memory.

Verified across the matrix before committing, since a single lock now has to
serve all three interpreters:

```
uv pip install --dry-run --python-version {3.11,3.12,3.13} --python-platform linux \
    --require-hashes -r requirements-dev-linux.lock     → all three resolve
uv pip install --dry-run --python-version {3.11,3.13} --python-platform {windows,macos} \
    --require-hashes -r requirements-build-<os>.lock    → OK
```

---

## 🔍 pip-audit was auditing one third of what we ship

Found while updating `security.yml`. The audit job ran `pip-audit -r
requirements.lock` on a Linux runner. Under a universal lock that was almost
defensible — one file, one set of pins. Under per-platform locks it plainly is
not: **the Windows lock pins different versions**, and `pyqt5-qt5==5.15.2` is
exactly the sort of package a platform gets stuck on and a CVE later lands in.
Auditing only Linux would never look at it.

All three are audited now, from the one Linux runner, using `--no-deps`:

```yaml
for lock in requirements-linux.lock requirements-windows.lock requirements-macos.lock; do
  pip-audit --no-deps -r "$lock"
done
```

`--no-deps` is what makes a foreign platform's lock auditable on Linux — it
audits the pinned lines as written instead of trying to resolve them into the
host environment. A complete lock has nothing left to resolve, so nothing is
lost. Confirmed locally against all three: no known vulnerabilities.

This is a gap the previous design was hiding, not one the change introduced.

---

## 🧪 Verifying the gate still gates

`make lock-check` now runs nine compiles instead of three. Tested in both
directions:

- **Add `click>=8.0.0` to `pyproject.toml`, do not re-lock** → all nine files
  reported stale, exit 1. ✅
- **Restore** → "Lockfiles are up to date", exit 0. ✅

One limitation, confirmed deliberately and worth recording: hand-editing a pin
to another **in-range** version (`semver==3.0.4` → `3.0.3`) is **not** detected.
That falls out of the seeding fix from devlog 105 — the committed lock is copied
into the temp file first, so uv prefers the pins already there. Modan2's
implementation has the same property. It is the correct behaviour for what this
gate is for ("does re-locking *this* `pyproject.toml` change anything?"); the
hash check at install time is what catches a doctored lock, not this. A pin
moved *outside* the declared range would still be caught, because uv would have
to move it back.

---

## 📁 Files Changed

- `Makefile` — `lock`, `lock-check`, `install`, `install-dev`, host detection
- `pyproject.toml` — `pyqt5-qt5` markers removed
- 9 lockfiles added, 3 removed
- `.github/workflows/` — `test.yml` (lint + two matrix jobs, now selecting by
  `runner.os` under `shell: bash`), `test-full.yml`, `reusable_build.yml`
  (three build jobs), `security.yml` (audit all three + dry-run), `codeql.yml`
- `docs/CI_RECOMMENDATIONS_FOR_MODAN2.md` — §1 marked superseded, addendum §3
  updated with the two findings above
- `docs/CODE_QUALITY.md`, `CHANGELOG.md`, `TODOs.md`

No Python source changed.

---

## 💡 Lessons

1. **A workaround in a public dependency list has no way to announce itself.**
   The `pyqt5-qt5` markers read like project constraints. They were a
   compensation for a resolver limitation, and the only thing marking them as
   such was a twelve-line comment.

2. **Changing the shape of the data exposes what the old shape hid.** Auditing
   one lock looked complete when there was one lock. Splitting it into three did
   not create the pip-audit gap — it made it impossible not to see.

3. **Name the thing you gave up.** Losing the Python-version fork is the price
   of this change. Written down here and in `TODOs.md`, it is a known tradeoff;
   left unwritten, it is a mystery for whoever notices numpy 2.4.6 on the 3.13
   leg six months from now.

4. **Verify the new mechanism against the old failure.** The single most useful
   thing done here took two minutes: compile a one-line requirements file for
   three platforms *before* migrating, and confirm uv picks 5.15.2 on Windows
   unaided. Everything after that was mechanical.

---

**Next:** `docs/manual/` — separating the published Sphinx manual from the
repository-only `.md` notes by directory rather than by file extension, matching
the layout Modan2 already uses.
