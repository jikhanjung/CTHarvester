# Devlog 110: pytest 9, and What the Day Added Up To

**Date:** 2026-07-27
**Current Version:** 0.2.3-beta.2
**Status:** ✅ pytest 9.1.1; ten commits pushed, all CI green
**Previous:** [devlog 109 - Four Backlog Items](./20260727_109_backlog_sweep.md)

---

## 🎯 Part 1 — pytest 9

The last open Dependabot PR proposed widening the ceiling from `<9.0.0` to
`<10.0.0`. It was closed, not merged, because **it would have changed nothing.**

The lockfiles pin pytest 8.4.2. That pin stays valid inside the wider range, and
`uv pip compile` prefers the version already written in its output file. So the
declared range would have moved and the version actually installed would not —
the PR's title promises an upgrade it cannot deliver.

Raising the **floor** is what moves a pinned lock:

```toml
"pytest>=9.0.0,<10.0.0",
```

8.4.2 falls out of range, the resolver has to move, and `make lock` produced
9.1.1 across all nine files with no `--upgrade-package` needed.

This is the second time in one day the same property mattered. Devlog 108 has it
from the other direction: raising the Python floor from 3.11 to 3.12 *allowed*
numpy 2.5.1 and the pins stayed at 2.4.6 anyway, because relaxing a constraint
never moves anything on its own. **A ceiling is permission; a floor is force.**
The reasoning is now a comment next to the constraint rather than a lesson in a
devlog nobody re-reads.

### What was checked before touching the declaration

The five pytest plugins were resolved against pytest 9 first, on a scratch
requirements file — `pytest-cov`, `pytest-qt`, `pytest-timeout` and
`pytest-xdist` all resolve within their **existing** ranges, so no other
declaration had to move. Only `pytest==8.4.2 → 9.1.1` appears in the lock diff.

### Nothing needed adjusting, which is worth saying out loud

No test and no configuration changed. That deserves stating rather than passing
over, because this project runs `filterwarnings = error`: a major pytest release
is exactly the kind of change that turns fresh deprecation warnings into
failures, and none appeared. Full suite including slow and benchmark tests:
**1,311 passed, 5 skipped.**

---

## 📊 Part 2 — the day's ledger

Ten commits, 102 files, +6,685 / −1,073, from `633938d` to `a732753`. All four
CI workflows green on the final push, including the three-platform frozen build.

### What actually got better

| | Before | After |
|---|---|---|
| Lockfiles | 3 universal | 9 per-platform |
| pip-audit coverage | 1 lock (Linux) | 3 locks |
| `logger.exception` in the tree | 11 | 56 |
| mypy in CI | advisory (`\|\| true`) | gating |
| ruff rule groups | 10 | 12 (`SIM`, `TRY`) |
| CI matrix jobs (test.yml) | 13 | 6 |
| Open Dependabot PRs | 4, none mergeable | 0 |
| Broken relative doc links | 11 of 15 | 0, and tested |

The four that matter operationally:

1. **A Windows install can no longer be wrong by construction.** Per-platform
   resolution removed both the defect and the hand-written marker patching it.
2. **Failures can be diagnosed.** 49 `except` blocks logged a message and threw
   the traceback away.
3. **A security regression was stopped at review.** The pillow PR would have
   walked the floor back from `>=12.3.0` to `>=11.0.0`, re-admitting 18 CVEs,
   under the title "update pillow requirement".
4. **Dependency updates can land again.** The gate and the lockfiles were each
   correct and jointly made every Dependabot PR unmergeable. The symptom was
   silence, not a red build.

### What was given up, and what was not touched

- **Python 3.11 and 3.13 are no longer tested.** Deliberate, argued, and still a
  trade: CI cost bought with coverage.
- **Three `TRY` rules are off.** `TRY300` (20 sites) is deferred, not waived —
  the `ignore` entry says so and names where the follow-up lives.
- **mypy still only sees `core/` and `utils/`.** The `ui.*` strict sections in
  `pyproject.toml` are read by nothing.
- **Coverage is unchanged at ~79%.** Nothing here improved the tests' reach.
- **No user-facing behaviour changed at all.** This was a day of infrastructure.

### One number that lies

The test count went 1,295 → 1,311. **All 16 are documentation-link tests.** Not
one line of additional product code is under test than this morning. A badge
that goes up is not the same as a codebase that is better checked, and the
distinction is worth keeping in view the next time that number is quoted at
someone — including in this project's own README, which had already drifted to
claiming 1,150 tests and ~91% coverage against an actual ~79%.

---

## 💡 Lessons

1. **A ceiling is permission; a floor is force.** Twice today, on numpy and on
   pytest. Any tool that prefers its existing pins behaves this way, so a PR that
   only widens an upper bound is a no-op wearing an upgrade's title.

2. **Check the plugins before moving the framework.** Resolving the five pytest
   plugins against 9 first turned "does this break the suite?" into a question
   already answered before any file was edited.

3. **"Nothing needed to change" is a result, not an absence of one** — under
   `filterwarnings = error` it is a real signal about the upgrade, and it is
   worth writing down so the next person knows it was checked rather than
   assumed.

4. **Count what improved and what was spent.** A day that only lists wins is a
   day that was not measured. Version coverage, three lint rules, and mypy's
   scope are all on the other side of this ledger.

---

**Next:** `TRY300`'s 20 sites, `PTH` (499), `S` (2,166 — mostly `S101` in tests,
needing a per-file ignore before the real findings show), widening mypy to
`ui/`, property-based tests, and installer signing. All in `TODOs.md`.
