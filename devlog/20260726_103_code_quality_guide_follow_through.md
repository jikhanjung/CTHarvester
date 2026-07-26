# Devlog 103: Code Quality Guide Follow-Through — DTZ, Gating, a Packaged Smoke Test That Found a Broken Build

**Date:** 2026-07-26
**Current Version:** 0.2.3-beta.2
**Status:** ✅ Four checklist items closed; all CI green
**Previous:** [devlog 102 - Automatic Threshold and ROI Detection](./20260726_102_auto_threshold_and_roi_detection.md)

---

## 🎯 Overview

Prompted by the question "is the code quality guide actually applied to this
repo?", the tree was audited against `../Modan2/docs/CODE_QUALITY_GUIDE.md`
Appendix A — its prioritised adoption checklist — item by item, verified against
the code rather than against devlog 100's record of what was intended.

Result at the start: **5 of 10 done, 3 partial, 2 not started.** Four items were
then worked in the guide's own order, cheapest first.

The audit table now lives in `TODOs.md` as a living document. Devlog 100's table
stays as the snapshot from the original audit.

| # | Item | Before | After |
|---|---|---|---|
| 3 | Expand the lint ruleset | ⚠️ | ⚠️ `DTZ` added; `SIM`/`TRY`/`PTH`/`S` remain |
| 2 | Lint + tests gating | ⚠️ | ⚠️ docs build now gates; only mypy remains advisory |
| 9 | Packaged-artifact smoke test | ❌ | ⚠️ smoke test on 3 OSes; signing remains |
| 8 | Dead-code / complexity | ❌ | ⚠️ `C901` ratchet; vulture rejected |

---

## 🔧 Work Completed

### Item 3 — `DTZ`: 17 naive datetimes

The smallest rule group, and the guide's advice is to start with the small ones.

Thirteen were `datetime.now()` feeding a log line, a changelog date or a metrics
record. They became `datetime.now().astimezone()`: the rendered value is
identical — these are meant to be local time and still are — but the result now
carries its offset instead of leaving a reader to guess which machine's clock
produced it.

Two needed more than a mechanical change:

- **`scripts/bump_version.py`** used `date.today()` for the changelog entry. Now
  derived from an aware local datetime, so the release date is stated in the
  releaser's timezone rather than inherited from whatever the process locale
  happens to be.

- **`scripts/generate_release_notes.py`** reinterpreted a git commit's epoch
  seconds in the local zone via `fromtimestamp(commit.committed_date)`, which
  can shift the reported date by a day. GitPython already exposes
  `commit.committed_datetime`, aware and carrying the committer's own offset.

### Item 2 — the docs build gates now

The docs job carried `continue-on-error: true`, so it reported success
unconditionally. That is exactly how the documentation build stayed broken for
weeks (fixed in devlog 101) with a green tick next to it the whole time.

Removing the flag alone would have turned it red immediately: the job installed
`sphinx sphinx-rtd-theme` **by name**, and `conf.py` imports `version.py`, which
needs semver. So it now installs `docs/requirements.txt` — the same list
`docs.yml` uses, and the one semver was added to. Naming a subset inline is what
let the two diverge in the first place.

The summary job's verdict counts docs alongside lint, smoke and test rather than
reporting it and ignoring it.

Verified by running the job's exact commands in a fresh 3.12 venv before pushing.

mypy stays advisory; the numpy 2.5 stub issue is unchanged and does not
reproduce locally.

### Item 9 — a packaged smoke test, and the bug it found on first run ⚠️

`CTHarvester.py` gains `--self-test`: boot the app headless, let the event loop
turn over so deferred initialisation runs, close top-levels, exit 0.
`reusable_build.yml` runs the **frozen executable** with it on Windows, macOS and
Linux after each build.

The first local run failed:

```
File "OpenGL/platform/__init__.py", line 52, in _load
TypeError: 'NoneType' object is not callable
[PYI-460544:ERROR] Failed to execute script 'CTHarvester'
```

**The packaged Linux build could not start at all.**

Source and frozen were compared in an identical environment — same `DISPLAY`,
same `QT_QPA_PLATFORM` — which is what turned this from "probably my machine"
into a diagnosis:

| | exit code |
|---|---|
| `python CTHarvester.py --self-test` | 0 |
| `./dist/CTHarvester/CTHarvester --self-test` | 1 |

PyOpenGL chooses its backend at runtime through `OpenGL.plugins`, importing the
module by dotted name:

```
nt      -> OpenGL.platform.win32.Win32Platform
darwin  -> OpenGL.platform.darwin.DarwinPlatform
linux   -> OpenGL.platform.glx.GLXPlatform
egl     -> OpenGL.platform.egl.EGLPlatform
osmesa  -> OpenGL.platform.osmesa.OSMesaPlatform
```

PyInstaller's static analysis cannot see a dotted-name import, so **no backend
was bundled** and `_load()` returned None. All five are now declared in
`hiddenimports` across all three spec files — one spec builds every OS, and
`CTHarvester.spec` is still reachable via `build_cross_platform.py` and
`build.py`'s onefile fallback.

Verified end to end on Linux: clean rebuild, frozen executable reaches its main
window, exits 0. Windows and macOS confirmed in CI on the next push — all three
smoke steps green.

`tests/test_smoke.py` pins the flag itself, since the release gate now depends on
its exit code.

### Item 8 — a complexity ratchet, and vulture rejected

**vulture was evaluated and not adopted.** Five of its six findings on the
shipped code were false positives:

| Finding | Verdict |
|---|---|
| `config/constants.py` unused import `__version_info__` | deliberate re-export |
| `utils/performance_logger.py` `exc_val`, `exc_tb` | required `__exit__` signature |
| `ui/widgets/mcube_widget.py` `n` | Qt callback signature |
| `ui/errors.py` `show_details` | public function parameter |
| `utils/file_utils.py` `recursive` | **real** |

A checker wrong five times out of six trains people to ignore it. Modan2 does not
use it either.

Its one real finding is fixed: `find_image_files()` took a `recursive` parameter,
documented as "include subdirectories", that neither code path implemented.
Passing `recursive=True` silently returned the same non-recursive list. Removed
rather than implemented — no caller wanted it, a CT image stack is a flat
directory by construction, and a `TypeError` is a better answer than a quietly
wrong one.

For complexity, `C901` is enabled with `max-complexity = 32` — the current worst
function. That is a **ratchet, not a target**: the tree passes today and nothing
is allowed to get worse. The distribution:

| threshold | functions over |
|---|---|
| 10 | 31 |
| 15 (guide's) | 8 |
| 20 | 2 |
| 32 | 0 |

The eight above the guide's threshold are recorded in `TODOs.md` with their
scores, to be worked down. The rule is: lower the number as functions are split,
never raise it.

### Also: a flaky test finally made deterministic

`test_speed_averaging` failed again on macOS. The previous attempt (devlog 101)
widened its sleep ratio from 10x to 20x, which treated the symptom — the test was
never measuring the tracker. It drove "fast" and "slow" phases with
`time.sleep()`, and on a loaded runner a 1 ms sleep overshoots by an order of
magnitude, so the half meant to be faster genuinely ran slower.

The clock is now injected via monkeypatch. The phases differ by exactly the
intended 20x, the result is identical on every machine, and the assertion is
exact (`avg_second > avg_first`) rather than carrying an 0.8 fudge factor chosen
to survive noise. Verified deterministic over 20 consecutive runs.

---

## 📁 Files Changed

21 files, +280 / −48 across 5 commits.

| Area | Files |
|---|---|
| Lint config | `pyproject.toml` (`DTZ`, `C901`, `[tool.ruff.lint.mccabe]`) |
| CI | `.github/workflows/test.yml`, `reusable_build.yml` |
| Packaging | `CTHarvester.spec`, `CTHarvester_onedir.spec`, `CTHarvester_onefile.spec` |
| Entry point | `CTHarvester.py` (`--self-test`) |
| Timestamps | `build.py`, `manage_version.py`, `core/thumbnail_generator.py`, `ui/handlers/thumbnail_creation_handler.py`, `scripts/*` |
| Code | `utils/file_utils.py` |
| Tests | `tests/test_smoke.py`, `tests/test_progress_tracker.py` |
| Docs | `TODOs.md` (live guide status + complexity backlog) |

---

## 🧪 Verification

- Full suite including slow and benchmark tests: **1269 passed, 5 skipped**
- `ruff check` / `ruff format --check` clean; mypy clean
- Frozen build smoke test: verified locally on Linux (before/after), and in CI on
  all three platforms
- Docs job verified by running its exact commands in a fresh venv
- All four CI workflows green

---

## 💡 Lessons

1. **A non-gating check is not a check.** The docs build was broken for weeks
   behind a green tick, because `continue-on-error` made the result
   unconditional. The same shape as devlog 101's `lock-check`, which failed
   100% of the time and was equally uninformative.

2. **Verify the audit, do not read it.** Devlog 100 recorded what was intended.
   Three of the ten items had moved since — in both directions — and only
   checking the tree showed which.

3. **A smoke test earns its keep on the first run, or it was not needed.** This
   one found that the shipped Linux build could not start. No source-level test
   could have: the defect lives in the boundary between the code and the way it
   is packaged.

4. **Compare two environments to turn "probably my machine" into a diagnosis.**
   Source at exit 0 and frozen at exit 1, with every variable held equal, is a
   bug report. Either one alone is a shrug.

5. **A linter with a five-in-six false-positive rate is worse than none.** It
   costs review attention on every run and teaches people to skim. Rejecting
   vulture and keeping the one finding it earned was the better trade.

6. **Ratchet what you cannot fix today.** Pinning `max-complexity` at the current
   worst value gets the rule enforced immediately, at zero refactoring cost, and
   makes every future increase visible. A threshold nobody can meet just gets
   disabled.

7. **Injecting the clock beats widening the tolerance.** Two rounds were spent
   tuning sleep durations for a test that could never be reliable. Controlling
   time made it exact and free.

---

**Next:** the `C901` backlog (eight functions, worst at 32), the remaining rule
groups (`SIM` 40, `TRY` 138, `PTH` 502, `S` 2083), mypy gating once the numpy 2.5
stubs are resolved, property-based tests (still a skipped template), and
installer signing. All in `TODOs.md`.
