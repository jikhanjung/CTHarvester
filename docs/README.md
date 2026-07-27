# docs/ layout

Two kinds of document live here, and **the directory** is what tells them apart.

## `docs/manual/` — the published manual

The Sphinx source directory: `conf.py`, the `.rst` pages, `locale/` and
`_templates/`. Built and deployed to
<https://jikhanjung.github.io/CTHarvester>. Written for people **using**
CTHarvester.

| File | Covers |
|---|---|
| `installation.rst` | Getting it installed |
| `user_guide.rst` | The main workflow, the Settings dialog, shortcuts |
| `configuration.rst` | Every key in `settings.yaml` |
| `advanced_features.rst` | Pyramid levels, large datasets, tips |
| `troubleshooting.rst` | Symptoms and fixes |
| `faq.rst` | Questions, with performance figures |
| `developer_guide.rst` | Contributing, architecture overview, testing |
| `changelog.rst` | Release history |

Build it with `make docs` from the repo root (or `make html` inside
`docs/manual/`); `make docs-watch` rebuilds and reloads while you write. The
`docs` job in `.github/workflows/test.yml` gates on the build, and
`.github/workflows/docs.yml` deploys on pushes that touch `docs/manual/**`.

Adding a page means adding it to `index.rst`'s toctree. A file that is not in
the toctree is not in the manual.

## `docs/` root — repository-only notes

**Outside the Sphinx source directory, so not built and not published.** These
are notes for people **working on** CTHarvester; they would only dilute a user
manual.

| File | Covers |
|---|---|
| `ARCHITECTURE.md` | Module layout and data flow |
| `CODE_QUALITY.md` | Ruff, mypy, bandit, pre-commit |
| `RELEASE_PROCESS.md`, `RELEASE_CHECKLIST.md` | Cutting a release |
| `CI_CD_AUDIT.md`, `CI_RECOMMENDATIONS_FOR_MODAN2.md` | CI history and notes |
| `GITHUB_PAGES_SETUP.md` | One-time Pages configuration |
| `SETTINGS_DIALOG_INFO.md` | Implementation note from when the dialog landed; the user-facing version is `manual/user_guide.rst` |
| `developer_guide/error_recovery.md`, `developer_guide/performance.md` | Long-form developer references, linked from `manual/developer_guide.rst` |
| `release-notes/` | Archived per-version notes; `CHANGELOG.md` is canonical |

## Which one am I writing?

If a user of the application would read it, it belongs in `docs/manual/` as
`.rst`, in the toctree. Everything else stays at the `docs/` root.

## Why a directory and not a file extension

This split used to be by extension — `.rst` published, `.md` not — because
Sphinx reads `.rst` only and `conf.py` has no `myst_parser`. That rule was
invisible and fragile: `configuration.md`, a complete reference for every
setting, was audited and found complete while having never been published at
all, and adding `myst_parser` some day would have silently turned nine internal
notes into manual pages. A directory boundary states the same rule in a form
that survives a configuration change, and it matches the layout Modan2 uses.
