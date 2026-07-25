# TODOs

Deferred work, with enough context to pick up later. Newest first.

---

## Lint hardening: restore dangerous flake8 rules + migrate to Ruff

**Status:** part 1 done (2026-07-26); part 2 still open
**Context:** item 4 of the code-quality-guide adoption
(`devlog/20260724_100_code_quality_guide_adoption.md`). Deliberately skipped at
the time — the CI structure was aligned with Modan2 but the lint *tooling* was
left as-is.

### 1. Restore dangerous flake8 rules ✅ done

Re-enabled in `.pre-commit-config.yaml` and now clean tree-wide: `F821`, `F811`,
`F841`, `E722`, `E712`, `B001`, `B006`, `B008`, `B011`, `B014`, `B017`, `F403`,
`F405`. Two `# noqa: F841` remain, both in profiling code where the binding *is*
the work being measured.

Still ignored on purpose, and worth revisiting with Ruff rather than one at a
time:

- `C901` (11 functions over complexity 15) — refactor-sized, not a lint fix.
- `F541` (32 f-strings with no placeholders), `E228` (10), `B007` (10 unused
  loop variables) — cosmetic; `ruff format`/`ruff --fix` handles these in bulk.

### 2. Migrate black + isort + flake8 + pylint → Ruff

Consolidate four tools into one, matching Modan2 (`ruff` + `ruff format`).

- Replace in `.pre-commit-config.yaml`, `pyproject.toml`, `requirements-dev`
  (and the lockfiles — re-run `make lock`), and the `lint` job in
  `.github/workflows/test.yml`.
- Pin the ruff version in CI and pre-commit to the same rev (Modan2 learned this
  the hard way — a newer ruff reformatted markdown code blocks).
- Start from Modan2's `select` (`E, F, I, N, UP, B, C4, LOG, RUF012`) and add
  the guide's high-value groups incrementally: `DTZ` (naive datetime — CTHarvester
  has ~7 `datetime.now()` sites), `S` (bandit — replaces the standalone bandit
  job in `security.yml`), `PTH`, `TRY`, `SIM`.
- Expect a large first-pass reformat + a batch of findings to triage.

**Once done:** flip the `lint` job's flake8/mypy steps from advisory to gating
(remove the `|| true`), and resolve the mypy-vs-numpy-2.5 stub issue
(`python_version=3.11` rejects the stubs' 3.12 `type` syntax — either bump
`python_version` or scope-exclude numpy).

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
