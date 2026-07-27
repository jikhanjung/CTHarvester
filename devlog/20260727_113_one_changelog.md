# Devlog 113: One Changelog

**Date:** 2026-07-27
**Current Version:** 0.2.3-beta.3
**Status:** ✅ The manual publishes the canonical `CHANGELOG.md`; stray Markdown excluded
**Previous:** [devlog 112 - Two Version Tools, One Release](./20260727_112_version_tooling_and_beta3_release.md)

---

## 🎯 Overview

After v0.2.3-beta.3 shipped, a question: *if the version goes up and release
notes go in, shouldn't `docs/manual/` reflect that too?*

Half of it already did. The other half turned out to be a second copy of the
release history that had been drifting for months.

---

## ✅ What was already handled

`docs/manual/conf.py` imports `release` from `version.py`, so every page of the
manual already read **0.2.3-beta.3** — the title bar included. Nothing to do.
That is the single-source-of-truth chain working as designed.

## ❌ What was not

`docs/manual/changelog.rst` was a **hand-written second changelog**, separate
from `CHANGELOG.md`. `make release` rolls the latter; nothing touched the
former. So the manual published alongside v0.2.3-beta.3 contained a changelog
page whose newest entry was **0.2.3-beta.2**.

And this was the second divergence, not the first. The file already carried a
note, added in devlog 105, saying its 0.2.3-beta.2 entry listed keyboard
shortcuts that shipped with different bindings. Two hand-maintained copies of
the same history had already failed to stay in step once; the release made it
twice, this time by omitting a version outright.

---

## 🔗 The fix: include, don't duplicate

`changelog.rst` is now two lines:

```rst
.. include:: ../../CHANGELOG.md
   :parser: myst_parser.sphinx_
```

One file to edit. `make release` rolls `[Unreleased]` into a dated section, and
the published manual follows **as a side effect** — no second edit, nothing to
forget.

`CHANGELOG.md` stays at the repository root, because that is where GitHub, the
release workflow and `bump_version.py` all expect it. The manual reaches out to
it rather than the other way round.

The accuracy note moved into `CHANGELOG.md`, next to the entry it corrects.
That is where a correction belongs, and it now reaches both readerships from
one place instead of only the manual's.

### What was checked rather than assumed

- **English build**: succeeds, 2 warnings, both pre-existing.
- **Korean build**: succeeds; the page renders `[0.2.3-beta.3]`.
- **Korean warnings**: 33 before, **29 after**. Diffed the two sets rather than
  trusting the total — **zero new**, four removed. The four were the
  translation catalogue for the old hand-written `changelog.rst` breaking rst
  markup; they went away with the file.
- **Rendered output**: contains the version, the moved note, and the correct
  title.

### One limitation, stated

The included content is **not translated**. gettext extracts from sources
inside `docs/manual/`, and `CHANGELOG.md` is outside it, so the Korean manual's
changelog page is in English. Acceptable for release notes; recorded so nobody
has to rediscover it.

---

## 🧪 A prediction, tested the same day

`docs/README.md` — written this morning, in devlog 107 — argued for a directory
boundary over a file-extension rule with this reasoning:

> adding `myst_parser` some day would have silently turned nine internal notes
> into manual pages

Enabling `myst_parser` **is** that change. It arrived about six hours later.

Nothing happened. The notes at the `docs/` root are outside the Sphinx source
directory, so making Markdown parseable did not make them publishable. Under
the old extension-based rule, this one-line config change would have required
auditing every `.md` file in the tree.

That is the value of the boundary being structural rather than conventional,
demonstrated rather than argued.

---

## ⚠️ Where the boundary does not reach

It protects `docs/` from `docs/manual/`. It does nothing **inside**
`docs/manual/` — and with myst enabled, a `.md` file dropped there becomes a
document, then warns that it is not in any toctree.

Modan2 found this after adding a `docs/manual/README.md`. CTHarvester has no
Markdown in that directory, so there was no symptom to notice — which is the
argument for adding the guard now rather than after someone adds a README and
wonders why the build got noisy.

`"**.md"` in `exclude_patterns`, verified in **both** directions:

| | probe `.md` in `docs/manual/` | changelog include |
|---|---|---|
| without the pattern | `document isn't included in any toctree`, page generated | renders |
| with the pattern | no warning, no page | renders |

A directive reads its file directly and never goes through source discovery, so
the include is unaffected either way — and `CHANGELOG.md` is outside the source
directory regardless.

---

## 💡 Lessons

1. **"Is it reflected everywhere?" is a better question than "did I update
   it?"** The version was propagating correctly through `conf.py` and the
   changelog was not, and only one of those was visible from the release
   itself.

2. **A hand-maintained copy diverges twice before anyone counts.** The shortcut
   list had already drifted; the missing version was the second failure of the
   same structure. The fix is not "be more careful", it is "have one file".

3. **Diff the warnings, do not count them.** 33 → 29 looks like an improvement
   and could have hidden a new warning among four removed ones. It did not, but
   the total alone could not say so.

4. **A rule written for a hypothetical is worth more when the hypothetical
   arrives.** Six hours between predicting what enabling `myst_parser` would
   cost and enabling it.

5. **Guard the case with no symptom.** The stray-Markdown problem is real,
   reproducible, and currently invisible here. Another project hitting it first
   is the cheapest possible warning.

---

**Next:** unchanged — installer signing, property-based tests, widening mypy to
`ui/`, and deciding whether the `bandit` job still earns its place next to
ruff's `S`. All in `TODOs.md`.
