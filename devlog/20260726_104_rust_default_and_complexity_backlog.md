# Devlog 104: The Rust Generator Was Never Running — and the First C901 Refactor

**Date:** 2026-07-26
**Current Version:** 0.2.3-beta.2
**Status:** ✅ Rust default fixed; complexity ratchet 32 → 28
**Previous:** [devlog 103 - Code Quality Guide Follow-Through](./20260726_103_code_quality_guide_follow_through.md)

---

## 🎯 Overview

Started as the C901 refactoring backlog from devlog 103. The first target was
`ThumbnailManager.process_level` — complexity 32, the function pinning the
ratchet. A question asked before touching it ("isn't thumbnail generation Rust
code?") turned out to matter more than the refactor.

**It is not.** The Rust module shipped disabled, and every install ran the
pure-Python path.

---

## 🐛 The Rust thumbnail generator was never used

`config/settings.yaml` shipped:

```yaml
use_rust_module: false  # false to force Python fallback
```

The comment reads like a debugging override that got committed
(commit `062156a`, 2025-10-01). The consequence: the compiled Rust module —
built by CI, bundled into the installer, and the reason the thumbnail pipeline
is fast — was skipped on every run.

### Why reading the code was not enough

The natural mental model is "it looks for the Rust module, and falls back if it
isn't there". The code does the opposite ordering:

```python
use_rust_preference = getattr(self.window.m_app, "use_rust_thumbnail", True)

if use_rust_preference:          # checked FIRST
    try:
        from ct_thumbnail import build_thumbnails
        use_rust = True
    except ImportError:          # the fallback everyone reasons about
        use_rust = False
else:
    use_rust = False             # taken in practice — import never attempted
```

With the preference off, the module is never even looked for. The
`except ImportError` path — the one that makes "it'll fall back" true — only
runs when the preference is already on.

### Confirmed by construction, not by reading

The real main window was built against an isolated `HOME`:

| | value |
|---|---|
| `processing.use_rust_module` | `False` |
| `m_app.use_rust_thumbnail` | `False` |
| `ct_thumbnail` importable | **`True`** |
| branch taken | **PYTHON** |

The module was present and skipped.

### Three defaults disagreed with one file

| Source | Default |
|---|---|
| `ui/ctharvester_app.py:55` | `True` |
| `ui/handlers/settings_handler.py:181` | `True` |
| `ui/dialogs/settings_dialog.py:319` | `True` |
| `config/settings.yaml:26` | **`false`** ← wins |

`.get(key, True)` cannot fall back on a key that is *present*. Three code paths
agreeing on `True` bought nothing.

### The fix, and its limit

`use_rust_module: true`, with a comment saying why `false` is not needed to
survive a missing module. `docs/configuration.md` updated — it had documented
the default as `false`, so the docs were consistent with the bug.

Verified in both directions with an isolated `HOME`:

| scenario | branch |
|---|---|
| fresh install | **RUST** |
| existing `settings.yaml` holding `false` | PYTHON |

**Existing installations keep their stored value** — a saved setting beats a
shipped default, which is correct behaviour for a settings file but means the
fix only reaches new installs. Recorded in the changelog: change it in Settings,
or delete the settings file.

---

## 🔧 C901 backlog: `process_level`, 32 → 9

The function pinning the ratchet. 290 lines doing six unrelated jobs. Four are
now their own methods:

| Method | Responsibility |
|---|---|
| `_resolve_level_weight` | Set `self.level_weight` from the parent's work distribution; 1.0 when absent or in the older list-of-ints form |
| `_submit_workers` | One worker per image pair, stopping early on cancellation |
| `_wait_for_completion` | Event-loop pump with stall detection; returns the start time the caller needs for statistics |
| `_drain_after_cancel` | Bounded wait for in-flight workers |

What remains in `process_level` is the sequence itself: count tasks, configure
sampling, size the pool, submit, wait, collect, report.

No behaviour change intended. Two incidental differences, both recorded in the
commit rather than left for someone to discover:

- The "starting main wait loop" line is logged unconditionally instead of behind
  a `first_log` flag, so it appears even when every task finished during
  submission.
- The stalled-queue warning is one message instead of three; the three always
  fired together.

**Ratchet lowered 32 → 28**, now pinned by `thumbnail_generator.generate_python`.

### Coverage was checked before cutting

| Module | Coverage |
|---|---|
| `ui/handlers/thumbnail_creation_handler.py` | 96.8% |
| `core/file_handler.py` | 90.3% |
| `core/sequential_processor.py` | 81.1% |
| `core/thumbnail_generator.py` | 75.0% |
| `core/thumbnail_manager.py` | 68.3% |
| `ui/dialogs/progress_dialog.py` | **51.4%** |

`progress_dialog._calculate_eta` (complexity 20) has **zero** coverage — its
whole body, lines 210–319, is untested. That one needs characterization tests
written before it is touched, and is deliberately not next.

---

## 📁 Files Changed

6 files, +230 / −189 across 2 commits.

| File | Change |
|---|---|
| `config/settings.yaml` | `use_rust_module: true` |
| `docs/configuration.md` | Documented default corrected |
| `CHANGELOG.md` | User-visible behaviour change |
| `core/thumbnail_manager.py` | Four methods extracted |
| `pyproject.toml` | Ratchet 32 → 28 |
| `TODOs.md` | Backlog updated |

---

## 🧪 Verification

- Full suite including slow and benchmark tests: **1269 passed, 5 skipped**
- `ruff check` / `ruff format --check` clean; mypy clean
- Rust branch selection verified empirically in both directions
- `process_level` complexity measured before and after: 32 → 9

---

## 💡 Lessons

1. **A question about the code beat reading the code.** The refactor was already
   underway when "isn't this the Rust path?" was asked. Answering it properly —
   by constructing the objects rather than tracing the source — found a shipped
   feature that had been switched off for months.

2. **`get(key, default)` is not a default when the key exists.** Three call
   sites specifying `True` looked like three votes. They were zero: the shipped
   YAML had the key, so no fallback ever applied. Defaults belong in one place.

3. **A comment explaining a debugging override is not the same as removing it.**
   `# false to force Python fallback` documented the switch perfectly, and the
   switch stayed on for months. Worse, `docs/configuration.md` then documented
   the wrong default as intended behaviour, making the bug look like a decision.

4. **Check coverage before refactoring, not after.** It reordered the backlog:
   the second-worst function by complexity has no tests at all, so it is not the
   second one to touch.

5. **Name the incidental differences.** "No behaviour change" is rarely exactly
   true after a 290-line split. Two log lines changed; saying so in the commit
   costs a sentence and saves a bisect.

---

**Next:** `generate_python` (28), the function now pinning the ratchet. Then
characterization tests for `_calculate_eta` before splitting it. Backlog in
`TODOs.md`.
