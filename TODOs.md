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
| 8 | Dead-code / complexity automation | ✅ | `C901` enforced at the guide's threshold of 15 (2026-07-26); the backlog of eight functions is cleared. vulture evaluated and rejected — 5 of its 6 findings were false positives; Modan2 does not use it either. |
| 9 | Packaged-artifact smoke test; signed installers | ⚠️ | Smoke test done (2026-07-26): `--self-test` entry point, run against the frozen build on all 3 OSes in `reusable_build.yml`. Installer signing/notarization still open |
| 10 | Property-based / fuzz tests | ⚠️ | `tests/property/test_image_properties.py` exists but its body is `pytest.skip("Template - to be implemented in Phase 4")` |

**Working order** (cheapest first, per the guide's own ordering): ~~#3 `DTZ`~~,
~~#2 docs build gating~~, ~~#9 packaged smoke test~~ and ~~#8 complexity
ratchet~~ (all done 2026-07-26). Remaining: the complexity backlog below,
#10 property tests, mypy gating, installer signing.

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
