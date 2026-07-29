# TODOs

Deferred work, with enough context to pick up later. Newest first.

---

## Code quality guide status

Live status against the prioritised adoption checklist (Appendix A) of the code
quality guide, v1.0 of 2026-07-23. **The checklist and the section numbering it
uses are copied into [devlog 120](devlog/20260729_120_quality_checklist_baseline_copied_in.md)**
— that copy is the baseline this table scores against, and it is deliberately
frozen at v1.0. Verified 2026-07-26. The table in devlog 100 is the snapshot
from the original audit; this one is the current state and should be updated as
items land.

| # | Item | Status | Where it stands |
|---|---|---|---|
| 1 | Cross-platform CI matrix + headless smoke test | ✅ | 3 OS x Python 3.12, `tests/test_smoke.py` |
| 2 | Lint + tests gating | ✅ | ruff, mypy, the test matrix and the docs build all gate. No `\|\| true` left in the lint job (mypy became gating 2026-07-27) |
| 3 | Expand the lint ruleset incrementally | ✅ | `E, F, I, N, UP, B, C4, LOG, DTZ, SIM, TRY, S, PTH, C901, RUF012`. All of the guide's groups landed 2026-07-27; individual waivers are argued in `pyproject.toml` |
| 4 | `filterwarnings = error` | ✅ | `pyproject.toml`, narrow documented ignores only |
| 5 | Lockfile + pip-audit + Dependabot | ✅ | 9 per-platform lockfiles with hashes, pip-audit gating on all three platforms, `.github/dependabot.yml`, and `dependabot-lock-refresh.yml` to keep the locks in step with Dependabot's range bumps |
| 6 | Coverage gate | ✅ | `--cov-fail-under=75` on the reference leg |
| 7 | Static type checking, scoped | ✅ | mypy per-module strict, gating in CI over `core/`, `utils/` and `ui/` — **nothing excluded** as of 2026-07-29 (49 files, clean). CI, `make type-check` and the pre-commit hook run one identical command |
| 8 | Dead-code / complexity automation | ✅ | `C901` enforced at 15 (2026-07-26); the backlog of eight functions is cleared. vulture evaluated and rejected — 5 of its 6 findings were false positives. |
| 9 | Packaged-artifact smoke test; signed installers | ⚠️ | Smoke test done (2026-07-26): `--self-test` entry point, run against the frozen build on all 3 OSes in `reusable_build.yml`. Installer signing/notarization still open |
| 10 | Property-based / fuzz tests | ✅ | `tests/property/test_image_properties.py` holds 14 real properties over `downsample_image`, `average_images` and `ROIManager` (2026-07-29). The hypothesis profile moved to `tests/conftest.py`, because the `[tool.hypothesis]` table in `pyproject.toml` had never been read |

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

**`ui/widgets/` joined 2026-07-29, and the exclude list is now empty.** The 38
errors came out as predicted in kind but not in weight: about half really were
the mechanical `Qt.LeftButton` class, fixed by naming the scoped enum
(`Qt.MouseButton.LeftButton`, `Qt.CursorShape.ArrowCursor`,
`Qt.AspectRatioMode.KeepAspectRatio`), which also let ten `# type: ignore`
comments go — one of which, `# type: ignore[attr-defined],` with a trailing
comma, was malformed and had never suppressed anything.

Two were real defects rather than typing noise, both of the kind that only
surfaces because nothing had ever measured the file:

- `mcube_widget.py` did `self.parent = parent`, overwriting `QWidget.parent()`
  for the instance — the same defect `progress_dialog.py` had (devlog 117).
  Renamed to `parent_widget`; it is read only inside that file.
- `object_viewer_2d.py` ended every mouse handler with an unguarded
  `self.object_dialog.update_status()`, and `resizeEvent` reached through both
  `object_dialog` and `threed_view` the same way. Both are attached from
  outside by `MainWindowSetup`, so all four paths raised `AttributeError` on a
  standalone viewer. Guarded, and six regression tests added — verified by
  probe: removing the guards fails four of them.

The `method-assign` errors on the overlay buttons were kept and waived
in place: assigning a handler onto a child `QLabel` you own is the ordinary
PyQt idiom, not the `self.parent` defect.

**Working order** (cheapest first, per the guide's own ordering): ~~#3 `DTZ`~~,
~~#2 docs build gating~~, ~~#9 packaged smoke test~~, ~~#8 complexity ratchet~~,
~~per-platform locks~~, ~~mypy gating~~ and ~~the full lint ruleset~~ (all done
2026-07-26/27), ~~widening mypy to `ui/`~~ (2026-07-28) and ~~`ui/widgets/`~~
(2026-07-29) and ~~#10 property tests~~ (2026-07-29). Remaining: **installer
signing**, which needs a Windows Authenticode certificate and an Apple
Developer ID — credentials, not code, so it cannot be finished from here.

### Hypothesis was configured in a file it does not read (2026-07-29)

`pyproject.toml` carried a `[tool.hypothesis]` table setting `max_examples`,
`derandomize` and `deadline`. **Hypothesis has no pyproject.toml support** —
there is no reference to the filename anywhere in the installed package — so
all three were inert, confirmed by reading `settings.default.derandomize` as
`False` against a file that said `true`. The values now live in a profile
registered in `tests/conftest.py`.

`derandomize` was the one that mattered: without it each CI run draws
different examples, so a property holding for all but a sliver of the input
space fails on one platform, once in a while, and passes on rerun — the same
shape as the macOS ETA flake fixed the same day.

### Complexity backlog (`C901`) ✅ cleared 2026-07-26

`max-complexity` is at **15**, this project's own long-standing value (it was
already 15 in 2025-09-30, devlog 038; the guide sets no number — see devlog 120).
It began as a ratchet at
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
- **The `bandit` job overlaps ruff almost entirely — and stays. ✅ decided
  2026-07-29.** ruff's flake8-bandit implements **73 of bandit 1.9.4's 75**
  checks, so the question was fair. Diffing the two leaves **four** bandit
  checks with no ruff port, three of which are for libraries this project does
  not use: `B614` (`torch.load`), `B615` (HuggingFace downloads), `B703`
  (Django XSS).

  The fourth decides it. **`B613` `trojansource`** flags bidirectional Unicode
  control characters — the class of attack where a file renders differently
  from how it compiles. It is HIGH severity, so it clears the job's `-ll`
  gate, and it is language- and project-agnostic. Verified by probe: a file
  with `U+202E` in a comment is caught by bandit and passes
  `ruff check --select S` clean.

  The invocation was left broad rather than narrowed to `-t B613`, so a future
  bandit check ruff has not ported arrives on its own. The reasoning is now in
  `security.yml` next to the command. Worth knowing: bandit reports **nothing**
  at this threshold today (12 findings, all below `-ll`) — like the ruff `S`
  rules, its value is prospective.

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
  launch it headless in a clean runner (guide §7, copied into devlog 120).
  Neither CTHarvester nor Modan2 has this yet.
- **Upstream PyMCubes PR** — `mcubes/src/_mcubes.pyx` sets `ndarray.shape`
  directly (`verts.shape = (-1, 3)`), deprecated in NumPy 2.5. Currently worked
  around with a message-scoped `filterwarnings` ignore in `pyproject.toml`. Real
  fix is a one-line-per-site `reshape` PR upstream. Revisit if NumPy announces a
  removal version. See the pymcubes appendix in devlog 100.
- **Installer signing / notarization** — Windows Authenticode, macOS notarization
  (guide §7, copied into devlog 120).

---

## Test-suite weak spots found during the F841 sweep ✅ fixed 2026-07-29

Enabling `F841` surfaced tests that compute a value and then never assert on
it. The unused bindings went in 2026-07-26; the thinness underneath is now
fixed too.

- `tests/test_edge_cases.py::test_single_image_sequence` now writes one file
  and calls `get_file_list`, which is the boundary of that function's
  inclusive `range(seq_begin, seq_end + 1)`. `::test_negative_sequence_numbers`
  was **deleted**: it asserted `isinstance(settings["seq_begin"], int)` on a
  literal it had just written, and the behaviour it was named for is covered
  for real in `test_error_recovery.py`.
- `tests/test_error_recovery.py::test_loading_from_nonexistent_directory` now
  calls `load_thumbnail_data` and asserts the `(None, {})` contract that
  callers unpack, plus a second case for a `.thumbnail` directory with no
  levels — the state a cancelled generation run leaves behind.
  `::test_thumbnail_generation_with_missing_directory` asserts the
  `FileNotFoundError` its own comment claimed without testing. (The backlog
  called this one `test_missing_source_directory`; no test by that name
  exists.)
- `tests/integration/test_ui_workflows.py::test_window_state_after_operations`
  captures geometry and title and compares them across the operation, which is
  the test the discarded `geometry1` / `initial_title` bindings were for.

### The isolation these tests promised did not exist ★

Fixing `test_settings_persistence` turned up a real defect rather than a thin
assertion. Two independent faults hid each other:

1. Both halves were guarded by `if hasattr(window, "settings")`. The attribute
   is **`settings_manager`**, so the guards were always False — the write and
   the assertion were skipped together, and the test could only pass.
2. Isolation was set with **`CTHARVESTER_SETTINGS_DIR`, which the application
   has never read.** `utils.paths` resolves the config root from
   `CTHARVESTER_CONFIG_DIR`. The wrong name appeared in three places,
   including the shared `main_window` fixture in
   `tests/integration/conftest.py`.

Because `closeEvent()` calls `save_settings()`, and the `main_window` fixture
closes its window at teardown, **the integration tests were writing the
developer's real `preferences.json` on every run.** Only fault 1 kept the
language key from being clobbered as well.

All three sites now use `monkeypatch.setenv("CTHARVESTER_CONFIG_DIR", ...)` —
`monkeypatch` rather than `os.environ` so the override is undone at teardown
instead of leaking through the rest of the session. The test asserts the
config path really is under `tmp_path`, which is what makes the name wrong
again fail loudly; verified by probe.

### `tests/test_basic.py` deleted, and the CI `--ignore` with it

It was excluded from CI in `test.yml` and `test-full.yml` yet passed locally —
an anomaly either way. Checked before deleting rather than assumed: every one
of its six tests is subsumed.

| test_basic.py | subsumed by |
|---|---|
| `test_import`, `test_requirements` | `test_smoke.py::test_module_imports` walks **every** module under `config`/`core`/`security`/`ui`/`utils` plus `CTHarvester`; `::test_third_party_native_extensions_load` touches the compiled submodules, not just the names |
| `test_security_module_basic` | `test_security.py` (including the null-byte case, `:74`) |
| `test_image_utils_basic` | `test_image_utils.py`, `test_image_utils_error_paths.py` |
| `test_progress_manager_basic` | `test_progress_manager.py` |
| `test_file_utils_basic` | `test_file_utils.py` (`parse_filename` at `:117`, in a stronger form) |

`docs/CI_CD_AUDIT.md` still shows `--ignore=tests/test_basic.py` in three code
blocks. Left alone deliberately: it is a dated audit report (2025-10-08), a
record of the commands at that time, and its snippets are already stale in
other ways (`--cov-fail-under=85`, now 75).
