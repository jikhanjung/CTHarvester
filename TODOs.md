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
| 1 | Cross-platform CI matrix + headless smoke test | ✅ | 3 OS x Python 3.12, `tests/test_smoke.py` |
| 2 | Lint + tests gating | ✅ | ruff, mypy, the test matrix and the docs build all gate. No `\|\| true` left in the lint job (mypy became gating 2026-07-27) |
| 3 | Expand the lint ruleset incrementally | ✅ | `E, F, I, N, UP, B, C4, LOG, DTZ, SIM, TRY, S, PTH, C901, RUF012`. All of the guide's groups landed 2026-07-27; individual waivers are argued in `pyproject.toml` |
| 4 | `filterwarnings = error` | ✅ | `pyproject.toml`, narrow documented ignores only |
| 5 | Lockfile + pip-audit + Dependabot | ✅ | 9 per-platform lockfiles with hashes, pip-audit gating on all three platforms, `.github/dependabot.yml`, and `dependabot-lock-refresh.yml` to keep the locks in step with Dependabot's range bumps |
| 6 | Coverage gate | ✅ | `--cov-fail-under=75` on the reference leg |
| 7 | Static type checking, scoped | ✅ | mypy per-module strict, gating in CI over `core/`, `utils/` and `ui/` (43 files, clean). Only `ui/widgets/` is still excluded. CI, `make type-check` and the pre-commit hook now run one identical command |
| 8 | Dead-code / complexity automation | ✅ | `C901` enforced at the guide's threshold of 15 (2026-07-26); the backlog of eight functions is cleared. vulture evaluated and rejected — 5 of its 6 findings were false positives; Modan2 does not use it either. |
| 9 | Packaged-artifact smoke test; signed installers | ⚠️ | Smoke test done (2026-07-26): `--self-test` entry point, run against the frozen build on all 3 OSes in `reusable_build.yml`. Installer signing/notarization still open |
| 10 | Property-based / fuzz tests | ⚠️ | `tests/property/test_image_properties.py` exists but its body is `pytest.skip("Template - to be implemented in Phase 4")` |

**Done 2026-07-27:** ~~adopt Modan2's per-platform lockfiles~~. Nine locks
(runtime / dev / build x linux, windows, macos), the `pyqt5-qt5` environment
markers removed, `pip-audit` extended to all three platform locks. See devlog
106. A per-platform lock cannot fork by Python version the way `--universal`
did, which briefly pinned the whole matrix to the 3.11-compatible resolution;
dropping 3.11 the same day made the question moot — the floor is 3.12 and the
locks carry numpy 2.5.1 / scipy 1.18.0. Keep `requires-python`, the CI matrix
and `LOCK_ARGS` in step.

**mypy is gating (2026-07-27).** Item #2's `|| true` was there because mypy
pinned `python_version = 3.11` while the numpy 2.5 stubs use 3.12 `type` syntax.
Dropping 3.11 moved the config to 3.12, `mypy --config-file pyproject.toml
core/ utils/` reports **Success: no issues found in 24 source files** against
the locked mypy 1.20.2, and the guard is gone.

**`ui/` joined the scope 2026-07-28.** `mypy --config-file pyproject.toml core/
utils/ ui/` reports **Success: no issues found in 43 source files**. It took six
fixes in `ui/` proper and four in `ui/dialogs/progress_dialog.py`, which came
off the exclude list at the same time.

What remains outside is **`ui/widgets/`** — 38 errors across `mcube_widget.py`
(27) and `object_viewer_2d.py` (11), still excluded in `pyproject.toml` and
still `ignore_errors = true`. Most are one mechanical class: `Qt.LeftButton`
and friends, which PyQt5 exposes on `Qt` at runtime but the stubs place on
`Qt.GlobalColor` / `Qt.MouseButton`. The rest are `union-attr` on
`QApplication.instance()`, a few `override` mismatches and three
`var-annotated`. Same approach: one file clean before it is added.

**Working order** (cheapest first, per the guide's own ordering): ~~#3 `DTZ`~~,
~~#2 docs build gating~~, ~~#9 packaged smoke test~~, ~~#8 complexity ratchet~~,
~~per-platform locks~~, ~~mypy gating~~ and ~~the full lint ruleset~~ (all done
2026-07-26/27) and ~~widening mypy to `ui/`~~ (2026-07-28). Remaining: **#10
property tests**, **installer signing**, and mypy over `ui/widgets/`.

### Complexity backlog (`C901`) ✅ cleared 2026-07-26

`max-complexity` is at **15**, the guide's threshold. It began as a ratchet at
32 — the then-worst function — and came down as each of eight functions was
split. Nothing is above the limit now.

| Function | Before | After |
|---|---|---|
| `core/thumbnail_manager.py::process_level` | 32 | 9 |
| `core/thumbnail_generator.py::generate_python` | 28 | 13 |
| `core/thumbnail_generator.py::load_thumbnail_data` | 20 | 11 |
| `ui/dialogs/progress_dialog.py::_calculate_eta` | 20 | 5 |
| `ui/handlers/thumbnail_creation_handler.py::create_thumbnail_rust` | 18 | 12 |
| `build.py::main` | 17 | 10 |
| `core/file_handler.py::sort_file_list_from_dir` | 17 | 12 |
| `core/sequential_processor.py::process_level` | 16 | 11 |

`_calculate_eta` had no test coverage at all, so 26 characterization tests were
written before it was touched; they still pass unmodified. Its body went from
0% covered to fully covered.

Keep treating the number as a ratchet: lower it when the tree allows, never
raise it.

---

## Lint ruleset: what is left after `SIM` and `TRY` (2026-07-27)

**`TRY300` ✅ done 2026-07-27.** All 20 sites converted and the rule is enabled.
It was not purely cosmetic: `performance_logger`'s decorator had its success
logging inside the `try`, so an exception raised while logging would have been
caught and reported as the *wrapped function* failing. Splitting the block put
that right. One knock-on — the extra `else` branch pushed
`create_thumbnail_python` to complexity 16, over the `C901` limit, so its three
near-identical failure blocks were extracted into `_fail_python_generation` and
`_close_python_progress`.

The `C901` ratchet stays at 15: measured after this change, the worst function
in the tree is exactly 15, so it cannot be lowered yet.

**`TRY003` (65) and `TRY301` (2) are waived on the merits**, with the reasoning
in `pyproject.toml` next to each. Revisit only if the reasoning stops holding.

**`PTH` ✅ done 2026-07-27**, in five stages — `security`/`config`/`CTLogger`,
`utils`, `core`, `ui`, `scripts` — each verified against the full suite before
the next. Shipped code is fully converted; `tests/**` (322 sites) is waived
permanently, with the argument in `pyproject.toml`. See devlog 111.

The rule the conversion followed, worth keeping if anything else touches paths:
**public signatures keep returning `str`; `Path` is an internal detail converted
back at the boundary.** mypy caught the one place it slipped.

**`S` ✅ done 2026-07-27.** The 2,166 count was almost entirely `S101` (assert)
in the test tree. After per-file ignores for `tests/**` (`S101`, plus `S108` for
`/tmp` strings fed to the path validator and `S103` for permission-restoring
teardown) and waiving the subprocess trio `S603`/`S607`/`S606`, the real work was
three `try`/`except`/`pass` blocks.

Two things worth remembering about it:

- **It found nothing.** `bandit` already runs in `security.yml` over the same
  code. The value is prospective — `eval`, `pickle`, `shell=True`, weak hashes
  and hardcoded secrets now fail at lint time, in the PR, rather than in a
  separate workflow. Verified by probe rather than assumed: a scratch file using
  all five was flagged (S307, S301, S324, S602, S105) with the waivers in place.
- **The `bandit` job now overlaps ruff substantially.** Removing it would be a
  reasonable simplification, but dropping a security scanner is not a call to
  make in passing — decide it on its own, checking which bandit checks ruff has
  no port of.

---

## Broken doc links ✅ fixed 2026-07-27

Found during the `docs/manual/` move. It was worse than the four references
spotted then: **11 of the 15 relative links** in the Markdown under `docs/` were
broken, mostly pointing into `docs/user_guide/`, a directory that has never
existed in this repository. All repointed, and `tests/test_docs_links.py` now
parametrises over every relative Markdown link under `docs/` so the class cannot
come back silently.

Two mentions were left alone on purpose, because they are records rather than
links: `docs/manual/changelog.rst:196` and a file listing in
`docs/release-notes/v0.2.3-beta.1-enhanced.md` both name
``docs/user_guide/troubleshooting.rst`` as prose describing a past release.
Rewriting a published changelog is worse than letting it be wrong about a path.

Still open, if wanted: nothing checks **external** URLs. `sphinx-build -b
linkcheck` would cover the manual's; the notes would need a separate tool. Not
obviously worth a network-dependent CI job.

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
