# Devlog 112: Two Version Tools, One Release

**Date:** 2026-07-27
**Current Version:** 0.2.3-beta.3
**Status:** ✅ v0.2.3-beta.3 published as a pre-release; version tooling consolidated
**Previous:** [devlog 111 - The pathlib Conversion, in Slices](./20260727_111_pathlib_conversion.md)

---

## 🎯 Overview

The task was "bump to 0.2.3-beta.3 and cut a pre-release". The release itself
needed one command. Getting to the point where that command was safe to run
took a rewrite of the release tooling, because the tooling could not have
produced a working release.

---

## 🔀 There were two version tools

| | `manage_version.py` (repo root) | `scripts/bump_version.py` |
|---|---|---|
| Origin | carried over from Modan2 | added this cycle |
| Commands | major/minor/patch, premajor/preminor/prepatch, **stage**, **release** | patch/minor/major/prerelease, `--set` |
| CHANGELOG | appends a stub | **rolls `[Unreleased]` into the new version** |
| Safety | y/N at each step | `--dry-run`, refuses an empty changelog, confirms before `--push` |
| Referenced by | `VERSION_MANAGEMENT.md`, both READMEs | `make release` |

**The documented tool was not the tool the build used.** And the README's
example syntax — `python manage_version.py bump patch` — matched neither: there
is no `bump` subcommand in either script.

There is a small irony in `CHANGELOG.md:449`, which records that
`manage_version.py` was introduced *"replacing bump_version.py"*. This cycle
brought the name back, without removing what had replaced it.

### Which one to keep

The engine and the vocabulary came from different tools, so the answer was
neither "keep Modan2's" nor "keep ours":

- `bump_version.py` has the better **engine** — rolling the changelog into a
  dated section is what makes `release.yml` able to publish release notes
  verbatim, and refusing to tag an undocumented release is a real guard.
- `manage_version.py` has the better **vocabulary** — `premajor/preminor/
  prepatch [alpha|beta|rc]`, `stage <alpha|beta|rc>`, `release` cover the whole
  pre-release lifecycle that Modan2's `VERSION_MANAGEMENT.md` documents.

So: keep the engine, adopt the vocabulary, delete the duplicate. Every one of
the nine transitions in Modan2's documentation was checked against the new
implementation before committing:

```
0.2.3-beta.2  prerelease  ->  0.2.3-beta.3
1.2.3         premajor    ->  2.0.0-alpha.1
1.2.3         preminor beta -> 1.3.0-beta.1
1.2.3         prepatch rc ->  1.2.4-rc.1
1.3.0-alpha.4 stage beta  ->  1.3.0-beta.1
1.3.0-rc.2    release     ->  1.3.0
```

Adding the commands pushed `compute_new_version` to complexity 16. The `C901`
ratchet only moves down, so the pre-release and stage branches were extracted
into `_start_prerelease_cycle` and `_move_stage` rather than the threshold
being raised.

---

## 🚨 The gap that would have broken the release

**Neither tool updated `Cargo.toml`.**

`ct_thumbnail`, the Rust extension, carries its own version, and
`tests/test_version_consistency.py::test_cargo_version_matches` gates on it
matching `version.py`. `bump_version.py`'s own docstring says Cargo derives
from `version.py` — and then it commits `version.py` and `CHANGELOG.md` only.

So running the release as it stood would have produced a commit and a tag
whose **own CI fails**, on a check that exists precisely to prevent this. The
release workflow has a `verify-version` job as its first step; that is what
would have gone red.

Modan2's tooling has no equivalent because Modan2 has no Rust component. This
is one of the places where "align with Modan2" means adding something Modan2
does not need, not copying what it has.

`Cargo.toml` is now rewritten and committed with the rest, and
`verify-version` passed on the real tag.

---

## 🏷️ A tag that did not get created

Worth recording because the cause was procedural, not a bug.

The bump was run as `python scripts/bump_version.py prerelease | head -20`.
`head` closed the pipe after twenty lines, the script took a broken pipe while
printing its git steps, and died **after `git commit` and before `git tag`**.
The release commit existed; the tag did not.

The commit was intact — `version.py`, `Cargo.toml`, `CHANGELOG.md`, nothing
else — so the fix was to create the annotated tag the script would have
created, on that commit. Modan2's `VERSION_MANAGEMENT.md` documents exactly
this shape of recovery, for the case where something has to change between the
version commit and the tag.

**Do not pipe a script that performs git operations through `head`.** The
output is not the point of running it.

---

## 📦 v0.2.3-beta.3

Published 2026-07-27, **`prerelease=true`** — `release.yml` detects `beta`,
`alpha` or `rc` in the tag and sets the flag, so nothing extra had to be
passed.

| Artifact | Size |
|---|---|
| `CTHarvester-Windows-Installer-v0.2.3-beta.3-build368.zip` | 63 MB |
| `CTHarvester-macOS-Installer-v0.2.3-beta.3-build368.dmg` | 203 MB |
| `CTHarvester-Linux-v0.2.3-beta.3-build368.AppImage` | 130 MB |
| `SHA256SUMS.txt` | 422 B |

Six workflows green: Release, Build, Quick Tests, Full Test Suite, Security,
CodeQL.

The release body is the `[0.2.3-beta.3]` changelog section verbatim — roughly
nine months since `0.2.3-beta.2` (2025-10-08). What a user will notice:
automatic threshold/ROI detection after thumbnail generation, the Rust
generator becoming the default, **Python 3.11 support dropped**, and the
packaged Linux build that could not start at all being fixed.

---

## 💡 Lessons

1. **Two tools for one job is worse than either tool.** Not because of the
   duplication, but because the documentation and the build ended up pointing
   at different ones, and nobody notices until a release is attempted.

2. **A single source of truth needs something enforcing it in both
   directions.** `version.py` was declared canonical and a test gated on
   Cargo agreeing with it — but nothing *made* Cargo agree. The check existed;
   the update did not.

3. **"Align with the other project" is not "copy the other project."** The
   command vocabulary came from Modan2; the changelog rolling stayed ours; the
   Cargo handling exists in neither and had to be written.

4. **Trying to ship is how release tooling gets tested.** The `Cargo.toml` gap
   had been there since the script was written and would have stayed invisible
   until exactly this moment.

---

**Next:** the backlog is unchanged — installer signing, property-based tests,
and widening mypy's scope to `ui/`. The next version step is `prerelease`,
`stage rc`, or `release`, whichever the beta warrants.
