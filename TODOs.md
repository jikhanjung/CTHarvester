# TODOs

Deferred work, with enough context to pick up later. Newest first.

---

## Lint hardening: restore dangerous flake8 rules + migrate to Ruff

**Status:** deferred (2026-07-24)
**Context:** item 4 of the code-quality-guide adoption
(`devlog/20260724_100_code_quality_guide_adoption.md`). Deliberately skipped so
far — the CI structure was aligned with Modan2 but the lint *tooling* was left
as-is.

Two parts:

### 1. Restore dangerous flake8 rules

`.pre-commit-config.yaml`'s flake8 `extend-ignore` currently disables rules that
catch real bugs. Highest priority to re-enable:

- **`F821` (undefined name)** — catches `NameError` statically. Should never be
  off.
- `F811` (redefinition of unused name), `F841` (unused local variable)
- `E722` (bare `except:`)
- `B006`/`B008` (mutable/call default args), `C901` (complexity)

Approach: turn them on one at a time, fix or `# noqa: <code>` with a reason each
finding (never bulk-ignore), run the suite after each.

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
