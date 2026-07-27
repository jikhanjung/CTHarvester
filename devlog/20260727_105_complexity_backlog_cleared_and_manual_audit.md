# Devlog 105: Complexity Backlog Cleared, and a Manual That Described Features Nobody Built

**Date:** 2026-07-27
**Current Version:** 0.2.3-beta.2
**Status:** ✅ `C901` at the guide's threshold; documentation reconciled with the code
**Previous:** [devlog 104 - Rust Default and Complexity Backlog](./20260726_104_rust_default_and_complexity_backlog.md)

---

## 🎯 Overview

Two halves. The first finished the `C901` backlog started in devlog 104 — six
more functions, taking the ratchet from 20 to the guide's threshold of 15. The
second answered "does the manual cover what is actually there?", which turned
out to be a much bigger question than expected.

---

## 🔧 Part 1 — the complexity backlog, cleared

Six functions, in the order coverage allowed rather than strictly by score.

| Function | Before | After | Extracted |
|---|---|---|---|
| `thumbnail_generator.load_thumbnail_data` | 20 | 11 | `_find_thumbnail_levels`, `_select_thumbnail_level`, `_normalize_to_8bit` |
| `progress_dialog._calculate_eta` | 20 | 5 | `_format_eta`, `_record_velocity`, `_eta_from_step_times`, `_eta_from_elapsed`, `_eta_from_velocity`, `_smooth_eta` |
| `thumbnail_creation_handler.create_thumbnail_rust` | 18 | 12 | `_open_rust_progress_dialog`, `_format_rust_progress`, `_report_rust_outcome` |
| `build.py::main` | 17 | 10 | `parse_build_types`, `build_onefile_executable` |
| `file_handler.sort_file_list_from_dir` | 17 | 12 | `_most_common`, `_most_common_supported_extension` |
| `sequential_processor.process_level` | 16 | 11 | `_source_filenames`, `_maybe_finish_sampling` |

**Ratchet: 32 → 28 → 20 → 18 → 15.** Eight functions across two sessions;
nothing is above the guide's threshold now, and the comment in
`[tool.ruff.lint.mccabe]` says to keep treating the number as a ratchet.

### `_calculate_eta`: tests first, on purpose

This one had **zero** coverage — its whole body was untested — so 26
characterization tests were written before touching it, describing what it does
rather than what it should. Two things fell out of writing them:

- **A value of exactly `0.0` reads as "no estimate".** The throttled branch
  guards with `if self.smoothed_eta:`, a truthiness test, so a smoothed ETA of
  zero is indistinguishable from `None` and the caller is told there is no
  estimate instead of `"0s"`. **Pinned as existing behaviour and left alone.**
  Fixing it in the same change as a refactor is how a refactor stops being one.
- **The three-way duration format existed twice**, once per branch.

All 26 tests passed unmodified against the refactored code, which is the entire
point of having written them first. The method's body went from 0% to fully
covered.

### Smaller things worth naming

- `_most_common_supported_extension` previously interleaved "is this format
  supported" with "which is most common" in one loop, leaving the rule — *a
  directory of TIFFs with a pile of stray `.txt` logs is still a TIFF stack* —
  implicit. It now filters, then takes the maximum.
- `_source_filenames` pulls out naming that **must** agree with
  `ThumbnailWorker`'s, a coupling that deserves a name and a docstring.
- `parse_build_types` was verified directly rather than by running a full build:
  all four argument shapes produce the same result as before.

---

## 📖 Part 2 — auditing the manual against the code

### Documentation described features that do not exist

`docs/advanced_features.rst` had "Keyboard Power User Shortcuts" and "Hidden
Features" sections describing:

| Documented | Reality |
|---|---|
| `Ctrl+Home` / `Ctrl+End` — first/last slice | Actually `Home` / `End` |
| `Ctrl+0` — "reset threshold to 128" | `Ctrl+0` is **fit-to-window** |
| `Shift+Left/Right` — jump 100 slices | Does not exist |
| `Shift+Up/Down` — coarse threshold | Does not exist |
| `F11` fullscreen, `Ctrl+W` wireframe, `Ctrl+B` bounding box | None exist |
| 3 double-click behaviours, 2 middle-click actions, 3 context menus, drag-and-drop | **No `mouseDoubleClickEvent`, `contextMenu` or `dropEvent` handler exists anywhere in `ui/`** |

Checked by comparing every documented key against `config/shortcuts.py` and
grepping the UI for the handlers. The other 23 of 24 shortcuts were documented
correctly in the user guide and index; this was one section that had drifted
into fiction.

`docs/changelog.rst`'s v0.2.3-beta.2 entry describes a different scheme again —
"Screenshot (F12)", "Load/Save crop (Ctrl+Shift+L/S)", "Reset threshold
(Ctrl+T)" when `Ctrl+T` generates thumbnails. Left as published, with a note
pointing at the real list: rewriting a released changelog seemed worse than
annotating it.

### Numbers that had drifted

| Claim | Documented | Actual |
|---|---|---|
| Test count | 1,150 | **1,295** |
| Coverage | ~91% | **~79%** |
| Rust speedup | "10-50x" in 9 places, "~2-3x" in one | measured 3-10x |

The coverage figure was overstated by 12 points. The speedup figure is more
interesting: "10-50x" traces to an aspirational docstring in devlog 037, while
the project's own measurements say otherwise — devlog 065 recorded 9-10 minutes
in Python against 2-3 minutes in Rust on a real dataset, and devlog 089 verified
5-10x. Unified on **3-10x**, with the measured figures quoted.

Also: the FAQ, troubleshooting guide and user guide all advised *enabling* the
Rust module, which became the default in devlog 104.

### The auto-setup feature was undocumented

The automatic threshold/ROI/slice-range detection added in devlog 102 had no
user-facing documentation at all. From a user's point of view the threshold
slider and crop box moved by themselves with no explanation. `user_guide.rst`
now has an "Automatic Initial Setup" section, including the case where detection
declines, so an absent proposal reads as expected behaviour rather than failure.

---

## 🚨 The finding underneath: markdown under `docs/` is not published

Prompted by a question about how Modan2's documentation tooling compares. The
answer is that it does not differ — both use Sphinx with `sphinx_rtd_theme` and
the same six extensions — but checking turned up something else.

**Sphinx reads `.rst` only.** Neither project has `myst_parser` in `conf.py`, so
every `.md` file under `docs/` builds into nothing: readable on GitHub, invisible
on the documentation site.

Which meant `docs/configuration.md` — the 457-line reference for every settings
key, audited an hour earlier and found complete — **had never been published at
all.** Nine files were in that state, including 1,500 lines of developer
references under `docs/developer_guide/` that were neither published nor linked
from anywhere.

The split is now explicit rather than accidental:

- **`.rst`** — the published manual, in `index.rst`'s toctree.
- **`.md`** — repository-only notes for people working on CTHarvester.

`docs/README.md` states the convention, lists which file is which, and says that
a user-facing document written as `.md` will not reach anyone.
`configuration.md` became `configuration.rst` and is now in the toctree — its
hand-written anchor table of contents became a `.. contents::` directive, which
Sphinx keeps correct on its own. The orphaned developer references are linked
from `developer_guide.rst` as GitHub links, under a section explaining why they
are not part of the site.

---

## 🤝 Reported to Modan2

An addendum to `docs/CI_RECOMMENDATIONS_FOR_MODAN2.md`, checked against the
Modan2 tree rather than assumed:

1. **The markdown gap applies there too** — 12 files, same cause. The one item
   worth acting on.
2. **PyOpenGL hidden imports** — informational. Modan2 uses PyOpenGL and passes
   no `--hidden-import`, but its packaged smoke test passes on all three
   platforms, so its bundle is fine as built.
3. **Two things Modan2 is still ahead on**, found while looking for
   recommendations:
   - **Per-platform lockfiles** cannot hit the defect CTHarvester's universal
     lock did, where `pyqt5-qt5`'s missing Windows wheels broke every Windows CI
     job.
   - **`lock-check` seeding** — Modan2's Makefile already copies the committed
     lock before recompiling, with a comment explaining why. CTHarvester's did
     not, and its gating job failed on every upstream release for weeks.
4. **The `C901` ratchet technique**, with Modan2's distribution measured (12
   functions over 15, one over 20) so the tradeoff is concrete.

`sphinx-autobuild`, which Modan2 has and CTHarvester did not, is now `make
docs-watch`. It lives in pyproject's `docs` extra rather than
`docs/requirements.txt` — that file is what CI installs to *build* the docs, and
an authoring tool does not belong in it.

---

## 📁 Files Changed

24 files, +1509 / −903 across 5 commits.

---

## 🧪 Verification

- Full suite including slow and benchmark tests: **1,295 passed, 5 skipped**
- `ruff check` / `ruff format --check` clean; mypy clean
- Docs build verified after every documentation change; `configuration.html` now
  exists and the two remaining warnings are the pre-existing ones
- All four CI workflows green

---

## 💡 Lessons

1. **An audit finds what it is looking for.** Checking "is every feature
   documented?" found a missing section. Checking the reverse — "is every
   documented feature real?" — found a whole page of fiction. The second
   direction is the one nobody runs.

2. **Write the characterization tests first, and then leave the bugs alone.**
   `_calculate_eta`'s zero-is-falsy quirk was found *because* tests were written
   before refactoring. Fixing it in the same commit would have meant no longer
   being able to say the refactor changed nothing.

3. **Documentation drift is not uniform.** The settings reference was perfect —
   every key documented, no phantom keys. The shortcuts page was largely
   invented. Sampling one page tells you nothing about the next.

4. **A number repeated in nine places is not nine confirmations.** "10-50x"
   looked authoritative by repetition and was contradicted by the project's own
   benchmarks, sitting in its own devlogs.

5. **"Complete" means nothing without asking where it is published.**
   `configuration.md` was audited and passed, and was unreachable the whole time.
   Coverage of content and coverage of delivery are different questions.

6. **Looking for advice to give is a good way to receive some.** Two of the four
   items for Modan2 turned out to run the other way.

---

**Next:** the remaining guide items — additional ruff rule groups (`SIM` 40,
`TRY` 138, `PTH` 502, `S` 2083), mypy gating once the numpy 2.5 stubs allow it,
property-based tests (still a skipped template), and installer signing. Adopting
Modan2's per-platform lockfiles is now on the list too. All in `TODOs.md`.
