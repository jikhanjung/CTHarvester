# CLAUDE.md

Guidance for Claude Code (claude.ai/code) when working in this repository.

This file is deliberately short. It exists to route to documents that already
carry the detail, and to name the one thing that lives **outside** the repository.

## The family-wide conventions are not in this repository

`.guides/` is a symlink to a checkout of the shared PaleoBytes guide set;
`.guides/desktop/README.md` is the entry point (file locations, installer
identity, CI, packaging, code quality). There is a `web/` set beside it.

- **Referenced, not copied.** A copy drifts from the source and does not report
  that it has — that has already happened once, within a day of the guides being
  written.
- **Not committed here.** The guides are private and this repository is public,
  so copying them into `docs/` would publish them.
- **The link can dangle.** On a machine without the checkout it resolves to
  nothing, and a broken symlink reads as *an empty directory* rather than an
  error. Check the link before concluding the guides are silent on something.
  Setup is in devlog 119.

## Which document does which job

Keep them apart or they drift into each other:

| Document | Job |
|---|---|
| `CONTRIBUTING.md` | Development setup, workflow, and the quality checks CI gates on |
| `TODOs.md` | The **plan** — deferred work with enough context to resume, newest first |
| `devlog/` | The **record** — why a past change was made that way, including what was rejected. `devlog/README.md` is the index |
| `CHANGELOG.md` | What **shipped** |
| `VERSION_MANAGEMENT.md` | Versioning: `version.py` is the single source; use `scripts/bump_version.py` |
| `README.md` / `README.ko.md` | For users, not for development |

Add a `devlog/` entry per piece of work and a line to `devlog/README.md`, which
is a summarizing index rather than a bare list of links.
