# docs/ layout

Two kinds of document live here, and the file extension is what tells them
apart.

## `.rst` — the published manual

Built by Sphinx, listed in `index.rst`'s toctree, and deployed to
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

Build it with `make html` (or `make -C docs html` from the repo root); the
`docs` job in `.github/workflows/test.yml` gates on it.

## `.md` — repository-only notes

**Not built and not published.** Sphinx reads `.rst` only — there is no
`myst_parser` in `conf.py` — so a Markdown file added here is readable on GitHub
and nowhere else. That is deliberate: these are notes for people **working on**
CTHarvester, and they would only dilute a user manual.

| File | Covers |
|---|---|
| `ARCHITECTURE.md` | Module layout and data flow |
| `CODE_QUALITY.md` | Ruff, mypy, bandit, pre-commit |
| `RELEASE_PROCESS.md`, `RELEASE_CHECKLIST.md` | Cutting a release |
| `CI_CD_AUDIT.md`, `CI_RECOMMENDATIONS_FOR_MODAN2.md` | CI history and notes |
| `GITHUB_PAGES_SETUP.md` | One-time Pages configuration |
| `SETTINGS_DIALOG_INFO.md` | Implementation note from when the dialog landed; the user-facing version is `user_guide.rst` |
| `developer_guide/error_recovery.md`, `developer_guide/performance.md` | Long-form developer references, linked from `developer_guide.rst` |
| `release-notes/` | Archived per-version notes; `CHANGELOG.md` is canonical |

## Which one am I writing?

If a user of the application would read it, write `.rst` and add it to
`index.rst`'s toctree — otherwise it will not reach them. Everything else is
`.md`.

This split was made explicit after `configuration.md` — a complete reference for
every setting — turned out to have never been published at all.
