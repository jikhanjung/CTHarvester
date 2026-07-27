# Devlog 109: Four Backlog Items, One of Which Was Already Broken

**Date:** 2026-07-27
**Current Version:** 0.2.3-beta.2
**Status:** ✅ Dependabot unblocked, mypy gating, `SIM` + `TRY` enabled, doc links fixed and tested
**Previous:** [devlog 108 - One Python Version](./20260727_108_python_312_only.md)

---

## 🎯 Overview

Four items off the backlog. They were picked as separate chores; one of them
turned out not to be a chore at all.

---

## 🚧 Dependabot could not merge anything, and nobody noticed

Four Dependabot PRs were open, the oldest from October. The reason they sat
there is structural: **Dependabot edits version ranges in `pyproject.toml` and
never touches the lockfiles.** With a gating `dependency-lock` job, that means
every Dependabot PR fails by construction, and the fix is to regenerate nine
lockfiles by hand on someone else's branch. So nobody did.

Modan2 already had `dependabot-lock-refresh.yml`; it is now here too, adapted:
`pull_request_target` (a Dependabot-triggered `pull_request` run gets a
read-only token and cannot push), gated on the `dependabot[bot]` actor, running
`make lock` and pushing the result to the PR branch.

Two things stated differently from the original:

- **The security argument.** Modan2's comment says `uv pip compile` "does not
  execute package code". That is nearly true and not quite: resolution can build
  a source distribution to read its metadata. The honest version is that the
  **actor gate** is what makes this safe, not the inertness of the command — the
  diff comes from Dependabot, and a hostile upstream release would compromise a
  local `make lock` just as well.
- **No `LOCK_REFRESH_TOKEN` is configured**, so the push uses `GITHUB_TOKEN` and
  GitHub's loop prevention means the PR's checks do not re-run on the pushed
  commit. The locks are still refreshed; the checks need a manual re-run. Worth
  a fine-grained PAT if this gets used often.

### Then the PRs themselves

Reading them rather than merging them:

| PR | Verdict |
|---|---|
| #7 black, #4 pylint | Target dependencies **ruff replaced**. Nothing left to bump. Closed. |
| #5 pillow | Proposes `>=11.0.0,<13.0.0`. The declared floor is `>=12.3.0`, raised deliberately because Pillow 11.3.0 carries 18 CVEs. **Merging it would re-admit the vulnerable range.** Closed. |
| #6 pytest | The only live one. Left open. |

A bot's PR is a suggestion, not a work order. Three of four should never land,
and one of those is a security regression wearing a routine-update title.

---

## ✅ mypy is gating

The `|| true` came off. Devlog 108 verified it passes at `python_version = 3.12`
and left it advisory on purpose — enabling a gate inside a matrix change would
have tangled any later type failure with that commit. Its own commit now.

Scope is unchanged: `core/` and `utils/`. mypy reports the `ui.*` strict
sections as unused because nothing passes those paths to it — widening is the
next job, a directory at a time.

That completes item #2 of the code-quality guide checklist: no advisory steps
left in the lint job.

---

## 🔗 11 of 15 documentation links were broken

Devlog 107 spotted four references to `docs/user_guide/troubleshooting.rst`, a
path that has never existed. Counting properly across all Markdown under
`docs/`: **11 of the 15 relative links were broken**, including links to
`docs/developer_guide/index.rst` and `.../testing.rst`, neither of which exists
either.

The ratio is the finding. The Sphinx build validates the manual — a bad toctree
entry fails `make docs`, which gates CI — and **nothing at all** validated the
notes. Unchecked links do not decay slowly; they were mostly wrong from the day
they were written.

So `tests/test_docs_links.py` parametrises over every relative Markdown link
under `docs/` and asserts the target exists. Deliberately narrow: external URLs
are not fetched, because a suite that fails when someone else's website is down
is a suite people learn to ignore.

Two mentions were left wrong on purpose — a published changelog entry and an
archived release note describing a past release in prose. Rewriting a released
changelog is worse than letting it be wrong about a path.

---

## 🧹 `SIM` and `TRY`

**`SIM` — 37 findings, all addressed.** Most were mechanical. The ones worth
naming:

- `SIM117` merged 15 nested `with patch(...)` blocks into parenthesized context
  lists, which read better than nesting on 3.12. Fourteen scripted, one by hand.
- `SIM114` merged branches whose bodies were already identical. Two merges put
  `and` inside `or`; they got explicit parentheses, because operator precedence
  is not the reader's job. One merge also falsified its own comment — the
  condition now covers two cases — so the comment was rewritten.
- Two suppressions, both deliberate: `SIM115` in `test_stress.py`, where holding
  the file handles open **is** the test, and `SIM108` in `image_utils.py`, where
  a `type: ignore` has to sit on the line mypy reports.

**`TRY` — the one with teeth is `TRY400`.** 49 `except` blocks called
`logger.error`, which records the message and throws the traceback away. The
stack that explains the failure never reached the log. They call
`logger.exception` now.

That cascaded, and the cascade is the interesting part:

```
logger.error(f"Failed to load settings: {e}")   →  TRY400
logger.exception(f"Failed to load settings: {e}")  →  TRY401 (1 → 40)
logger.exception("Failed to load settings")     →  27 unused `as e` bindings (F841)
except Exception:
```

One rule's fix created the next rule's finding, twice. The end state says what
failed in the message and why in the traceback, with nothing duplicated.

Three `TRY` rules are off, each argued in `pyproject.toml`: `TRY003` (65) wants
bespoke exception classes for messages that name the specific file or setting;
`TRY301` (2) would extract functions purely to relocate a `raise`; `TRY300` (20)
is worth doing, has no autofix, and is **deferred rather than waived** — the
ignore entry points at `TODOs.md` and should be deleted when the sites are
converted.

---

## 🧪 Verification

- `ruff check` / `ruff format --check` clean; `mypy` clean
- **1,311 passed, 5 skipped** — the full suite including slow and benchmark
  tests, run because production logging and test-file handles both changed
- No test asserted on the `: {e}` text that came out of 40 log messages
- The stress benchmarks specifically, since one of them was edited
- Workflow YAML parses; the previous push's five CI workflows were all green

---

## 💡 Lessons

1. **A gate with no path through it is a closed door.** The `dependency-lock`
   job is correct and the lockfiles are correct; together they made every
   Dependabot PR unmergeable, and the symptom was silence — four PRs quietly
   ageing, not a red build anyone owned.

2. **Read the bot's PRs.** Three of four should never merge, and one would have
   walked 18 CVEs back in under the title "update pillow requirement".

3. **The ratio matters more than the count.** Four broken links looks like drift.
   11 of 15 says the category was never checked at all — which is a different
   problem with a different fix, and the fix is a test, not an edit.

4. **Fixing one lint rule can create the next one's findings.** TRY400 → TRY401
   → F841 was a chain, not three independent cleanups. Enabling a rule group and
   running `--fix` once would have left the tree in the middle of that chain.

5. **Deferred and waived are different, and the config should say which.**
   `TRY300` is ignored today and should not be ignored forever; the entry says so
   and names where the follow-up lives. `TRY003` is ignored on the merits. Both
   are one line of `ignore`, and only a comment distinguishes them.

---

**Next:** `TRY300`'s 20 sites, then the two large rule groups — `PTH` (499) and
`S` (2166, most of them `S101` in tests and needing a per-file ignore before the
real findings show). Property-based tests and installer signing are still the
open guide items.
