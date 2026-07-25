# Release notes archive

Historical, hand-written release notes. **Nothing here is current** — they are
kept because they carry detail that never made it into the changelog.

The canonical release notes are [`CHANGELOG.md`](../../CHANGELOG.md) at the
repository root. `scripts/bump_version.py` renames its `[Unreleased]` section to
the new version at release time, and `.github/workflows/release.yml` publishes
that section verbatim as the GitHub release body. Write new entries there, not
here.

| File | Covers |
|---|---|
| `v0.2.1.md` | v0.2.1 |
| `v0.2.2.md` | v0.2.2 |
| `v0.2.3-beta.1.md` | v0.2.3-beta.1 |
| `v0.2.3-beta.1-enhanced.md` | v0.2.3-beta.1, second pass — was `docs/RELEASE_NOTES.md`, and still called itself "Current Release" long after v0.2.3-beta.2 shipped. Archived rather than updated: that drift is exactly why the changelog is the single source now. |
