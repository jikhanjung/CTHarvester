# TODOs

Deferred work, with enough context to pick up later. Newest first.

---

## Code quality guide status

Live status against `../Modan2/docs/CODE_QUALITY_GUIDE.md` (v1.0, 2026-07-23),
Appendix A's prioritised adoption checklist. Verified 2026-07-26. The table in
devlog 100 is the snapshot from the original audit; this one is the current
state and should be updated as items land.

| # | Item | Status | Where it stands |
|---|---|---|---|
| 1 | Cross-platform CI matrix + headless smoke test | ✅ | 3 OS x Python 3.11-3.13, `tests/test_smoke.py` |
| 2 | Lint + tests gating | ⚠️ | ruff, the test matrix and the docs build gate. One `\|\| true` remains: mypy, blocked on the numpy 2.5 stub issue |
| 3 | Expand the lint ruleset incrementally | ⚠️ | `E, F, I, N, UP, B, C4, LOG, DTZ, RUF012`. `SIM` (40), `TRY` (138), `PTH` (502), `S` (2083) not yet |
| 4 | `filterwarnings = error` | ✅ | `pyproject.toml`, narrow documented ignores only |
| 5 | Lockfile + pip-audit + Dependabot | ✅ | 3 lockfiles with hashes, pip-audit gating, `.github/dependabot.yml` |
| 6 | Coverage gate | ✅ | `--cov-fail-under=75` on the reference leg |
| 7 | Static type checking, scoped | ✅ | mypy per-module strict; runs in CI (advisory, see #2) |
| 8 | Dead-code / complexity automation | ⚠️ | `C901` enabled as a ratchet at 32 (2026-07-26). vulture evaluated and rejected — 5 of its 6 findings were false positives (re-exports, `__exit__` params, Qt callback signatures); Modan2 does not use it either. The refactoring backlog is below |
| 9 | Packaged-artifact smoke test; signed installers | ⚠️ | Smoke test done (2026-07-26): `--self-test` entry point, run against the frozen build on all 3 OSes in `reusable_build.yml`. Installer signing/notarization still open |
| 10 | Property-based / fuzz tests | ⚠️ | `tests/property/test_image_properties.py` exists but its body is `pytest.skip("Template - to be implemented in Phase 4")` |

**Working order** (cheapest first, per the guide's own ordering): ~~#3 `DTZ`~~,
~~#2 docs build gating~~, ~~#9 packaged smoke test~~ and ~~#8 complexity
ratchet~~ (all done 2026-07-26). Remaining: the complexity backlog below,
#10 property tests, mypy gating, installer signing.

### Complexity backlog (`C901`)

`max-complexity` is pinned at **28**, the current worst function, so nothing can
get worse. The guide's threshold is 15. Lower the number in
`[tool.ruff.lint.mccabe]` as each of these is split — never raise it:

| Function | Complexity |
|---|---|
| ~~`core/thumbnail_manager.py::process_level`~~ | ~~32~~ → **9** (done 2026-07-26) |
| `core/thumbnail_generator.py::generate_python` | 28 |
| `core/thumbnail_generator.py::load_thumbnail_data` | 20 |
| `ui/dialogs/progress_dialog.py::_calculate_eta` | 20 |
| `ui/handlers/thumbnail_creation_handler.py::create_thumbnail_rust` | 18 |
| `build.py::main` | 17 |
| `core/file_handler.py::sort_file_list_from_dir` | 17 |
| `core/sequential_processor.py::process_level` | 16 |

---

## Lint hardening: restore dangerous flake8 rules + migrate to Ruff ✅ done

**Status:** complete (2026-07-26)
**Context:** item 4 of the code-quality-guide adoption
(`devlog/20260724_100_code_quality_guide_adoption.md`), deferred at the time.

### 1. Restore dangerous flake8 rules ✅

Re-enabled and cleaned tree-wide before the migration: `F821`, `F811`, `F841`,
`E722`, `E712`, `B001`, `B006`, `B008`, `B011`, `B014`, `B017`, `F403`, `F405`.

### 2. Migrate black + isort + flake8 + pyupgrade + pylint → Ruff ✅

Ruff pinned to `0.16.0` in three places that must stay in lockstep:
`pyproject.toml` dev extra (which feeds `requirements-dev.lock`),
`.pre-commit-config.yaml` `rev`, and — transitively, via the lockfile — the
`lint` job in `.github/workflows/test.yml`.

Rule set: `E, F, I, N, UP, B, C4, LOG, RUF012`, config in
`[tool.ruff]`. `.flake8` deleted; `[tool.black]`, `[tool.isort]` and
`[tool.pylint.*]` removed from `pyproject.toml`. `ruff check` and
`ruff format --check` are **gating** in CI.

Markdown is excluded from the formatter — ruff formats Python inside fences and
would rewrite documentation examples. This is the trap Modan2 hit.

---

## Remaining lint work (deliberately not done in the migration)

- **`C901` (complexity)** — 11 functions over the threshold. Refactor-sized, not
  a lint fix. Enable the rule once they are split.
- **Additional rule groups**, worth adding one at a time so each triage stays
  reviewable. Counts measured on 2026-07-26 with ruff 0.16.0:
  - `DTZ` (17) — naive `datetime.now()`. Smallest and highest value; do this next.
  - `SIM` (40), `TRY` (138), `PTH` (502) — large, mostly mechanical.
  - `S` (2083) — bandit's rules. The number is inflated by `assert` in tests
    (`S101`), which needs a per-file-ignore before the count means anything.
    Only worth it if it lets the standalone bandit job in `security.yml` go away;
    until then bandit already covers this ground.
- **mypy is still advisory** in the `lint` job. The blocker is unchanged: the
  config pins `python_version = "3.11"`, which the numpy 2.5 stubs reject (they
  use 3.12 `type` syntax). Bump `python_version` or scope-exclude numpy, then
  drop the `|| true`. Note this does not reproduce locally on numpy 2.3 — the
  lockfile pins 2.5.1 for Python 3.12.

---

## Fixed along the way: `make lock-check` reported "stale" forever

`uv pip compile` prefers versions already pinned in its output file. `make lock`
writes over the committed lockfile (keeping its pins); `lock-check` compiled into
an empty temp file (resolving everything to the newest release). The two
therefore disagreed the moment any transitive dependency shipped a version,
which made the gating `dependency-lock` job in `security.yml` fail regardless of
whether `pyproject.toml` had actually changed. `lock-check` now seeds the temp
files from the committed lockfiles first. Verified both ways: passes in sync,
still fails when a dependency is added to `pyproject.toml` without re-locking.

---

## Other known-deferred items

From the same devlog (lower priority):

- **Packaged-artifact smoke test** — build the installer in CI, then install and
  launch it headless in a clean runner (guide §7). Neither CTHarvester nor Modan2
  has this yet.
- **Upstream PyMCubes PR** — `mcubes/src/_mcubes.pyx` sets `ndarray.shape`
  directly (`verts.shape = (-1, 3)`), deprecated in NumPy 2.5. Currently worked
  around with a message-scoped `filterwarnings` ignore in `pyproject.toml`. Real
  fix is a one-line-per-site `reshape` PR upstream. Revisit if NumPy announces a
  removal version. See the pymcubes appendix in devlog 100.
- **Installer signing / notarization** — Windows Authenticode, macOS notarization
  (guide §7).

---

## Test-suite weak spots found during the F841 sweep (2026-07-26)

Enabling `F841` surfaced tests that compute a value and then never assert on it.
The unused bindings are gone, but the underlying thinness remains:

- `tests/test_edge_cases.py::test_single_image_sequence` /
  `::test_negative_sequence_numbers` assert only on the literal settings dict
  they just built (`settings["seq_end"] - settings["seq_begin"] == 0`). They
  instantiated a `ThumbnailGenerator` and never called it.
- `tests/test_error_recovery.py::test_missing_source_directory` /
  `::test_loading_from_nonexistent_directory` assert only
  `generator is not None` / `hasattr(...)`.
- `tests/integration/test_ui_workflows.py` captured `geometry1` and
  `initial_title` for a before/after comparison that was never written.
- `tests/test_basic.py` is excluded from CI (`--ignore=tests/test_basic.py` in
  `test.yml` and `test-full.yml`) yet passes locally, and now overlaps
  `tests/test_smoke.py` almost entirely. Decide: fold the unique parts into
  `test_smoke.py` and delete it, or drop the `--ignore`.
