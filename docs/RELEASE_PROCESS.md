# Release Process

How to cut a CTHarvester release. The flow is automated end-to-end: one command
bumps the version, rolls the changelog, tags, and pushes; CI does the rest.

Modeled on Modan2's process — `version.py` is the single source of truth and the
GitHub release notes are the tag's own `CHANGELOG.md` section.

---

## TL;DR

```bash
# 1. Write release notes under "## [Unreleased]" in CHANGELOG.md, commit them.
# 2. Cut the release:
make release BUMP=patch        # 0.2.3 -> 0.2.4, tag v0.2.4, push -> CI builds & publishes
```

That's it. `release.yml` then runs tests, builds Windows/macOS/Linux installers,
and publishes a GitHub Release whose body is the changelog section, with SHA256
checksums attached.

---

## The moving parts

| Piece | Role |
|---|---|
| `version.py` | **Single source of truth** for the version. Everything else derives from it (`pyproject.toml`, `Cargo.toml`, `docs/conf.py`, `config/constants.py`) — enforced by `tests/test_version_consistency.py`. |
| `CHANGELOG.md` | Keep-a-Changelog format. The `[Unreleased]` section accumulates notes; at release time it becomes the version's section **and the GitHub release body**. |
| `scripts/bump_version.py` | Bumps `version.py`, rolls the changelog, commits, and tags `v<version>`. |
| `Makefile` (`release*` targets) | Thin wrappers over the script. |
| `.github/workflows/release.yml` | Triggered by a `v*.*.*` tag: verifies the tag matches `version.py`, runs the test workflow, builds all platforms, publishes the release. |
| `.github/workflows/manual-release.yml` | Alternative: build + release from the GitHub UI (`workflow_dispatch`) without a local checkout. |

---

## Step by step

### 1. Accumulate changelog notes (ongoing)

As you land changes, add bullets under `## [Unreleased]` in `CHANGELOG.md`, using
the Keep-a-Changelog groups: **Added / Changed / Deprecated / Removed / Fixed /
Security**. Write them for users reading a release page, not as commit messages.

To draft a starting point from commits:

```bash
make release-notes TAG=v0.2.4     # writes release_notes.md; hand-edit into CHANGELOG.md
```

### 2. Preview the release

```bash
make release-preview BUMP=patch
```

Dry run — changes nothing. Prints the computed version, the tag, and the git
steps. Use it to confirm the version part is what you expect.

### 3. Cut the release

Pick the bump part:

```bash
make release BUMP=patch        # 0.2.3       -> 0.2.4
make release BUMP=minor        # 0.2.3       -> 0.3.0
make release BUMP=major        # 0.2.3       -> 1.0.0
make release BUMP=prerelease   # 0.2.4-beta.1 -> 0.2.4-beta.2  (or 0.2.4 -> 0.2.4-rc.1)
make release-set VERSION=0.2.4 # explicit (e.g. promoting a prerelease to stable)
```

The script will:

1. Refuse if the working tree is dirty (the release commit must be *only* the
   bump).
2. Rewrite `version.py`.
3. Rename `## [Unreleased]` → `## [<version>] - <date>` and add a fresh empty
   `[Unreleased]`.
4. Print the changelog section that will become the release body, and abort if
   it is empty.
5. Commit `chore: release v<version>`, tag `v<version>`, and — after a
   confirmation prompt — push both.

To stage locally without pushing (inspect first, push yourself):

```bash
make release-local BUMP=patch
git show           # review the release commit
git push --follow-tags origin HEAD
```

### 4. CI takes over

Pushing the tag triggers `release.yml`:

1. **verify-version** — fails the release if the tag ≠ `version.py`.
2. **test** — the full `test.yml` matrix (lint, smoke, 3-OS tests).
3. **build** — `reusable_build.yml` builds the Windows/macOS/Linux installers.
4. **create-release** — generates `SHA256SUMS.txt`, extracts the changelog
   section, and publishes the GitHub Release (marked *pre-release* automatically
   for `-alpha` / `-beta` / `-rc` tags).

Watch it under the repo's **Actions** tab. The release appears under
**Releases** when the build job finishes.

---

## Versioning

[Semantic Versioning](https://semver.org/): `MAJOR.MINOR.PATCH[-PRERELEASE]`.
Pre-1.0, so `MAJOR` stays `0`; breaking changes bump `MINOR`.

Typical pre-release progression toward a minor release:

```
0.2.3  →  0.3.0-alpha.1  →  0.3.0-beta.1  →  0.3.0-rc.1  →  0.3.0
```

- `-alpha` / `-beta` / `-rc` tags are published as **pre-releases**.
- Promote a prerelease to stable with `make release-set VERSION=0.3.0`.

---

## Manual release (GitHub UI)

If you can't run the script locally, use the **Manual Release** workflow
(Actions → Manual Release → Run workflow):

- `version_tag`: e.g. `v0.2.4` (must match `version.py` on the default branch).
- `create_git_tag`: create and push the tag as part of the run.

It builds all platforms and publishes the release with the changelog section,
same as the tag-triggered path. Prefer `make release` when you can — it keeps
`version.py`, the changelog, and the tag in one reviewable commit.

---

## Troubleshooting

- **`release.yml` failed at `verify-version`.** The tag doesn't match
  `version.py`. Either you tagged by hand without bumping, or pushed the wrong
  tag. Fix `version.py` (and re-tag) or delete the tag.
- **Release body shows the wrong / empty notes.** The `## [<version>]` section
  was missing or empty when you tagged. `bump_version.py` guards against empty
  notes; a hand-pushed tag does not.
- **"working tree is not clean".** Commit or stash first — `bump_version.py`
  needs the bump to be an isolated commit.
- **Tag already exists.** Delete it (`git tag -d v0.2.4` and, if pushed,
  `git push --delete origin v0.2.4`) or choose a new version.
