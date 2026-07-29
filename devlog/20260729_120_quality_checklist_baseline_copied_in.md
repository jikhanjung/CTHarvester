# 120 — 품질 상태표의 기준을 저장소 안으로 (Modan2 가이드 Appendix A 사본)

2026-07-29. 코드 변경 없음. 119가 "열어 둔 것"으로 남긴 항목을 닫는다.

## 무엇이 문제였나

`TODOs.md`의 "Code quality guide status" 표는 이렇게 시작하고 있었다:

    Live status against `../Modan2/docs/CODE_QUALITY_GUIDE.md` (v1.0, 2026-07-23),
    Appendix A's prioritised adoption checklist.

10행짜리 표의 **기준이 이 저장소 안에 없다.** 형제 저장소가 옆에 체크아웃돼
있어야만 풀리는 상대경로이고, 없으면 표의 1~10번이 무엇을 세는 번호인지 알
길이 없다. 같은 파일이 `guide §7`, `the guide's threshold` 처럼 절 번호로
가리키는 곳도 세 군데 더 있었다.

## 119는 "복사하지 말라"고 했는데 왜 복사하나

119의 논거는 **살아 있는 공유 표준**에 대한 것이었다 — 상류가 개정되면 사본은
조용히 낡고, 사본은 자기가 낡았다고 알려 주지 않는다. 그래서 `.guides/`는
심볼릭 링크다.

여기 필요한 것은 성질이 반대다. 표가 추적하는 것은 *현재 최선의 권고*가 아니라
**2026-07-23의 v1.0 체크리스트 대비 지금 어디까지 왔는가**이다. 기준선이 움직이면
추적이 깨진다 — **갱신되지 않는 것이 결함이 아니라 요건**이다. 스냅샷은 스냅샷
답게 고정돼야 하고, 고정된 스냅샷이 있을 곳은 계획(`TODOs.md`)이 아니라
기록(`devlog/`)이다.

## 공유 가이드(`.guides/desktop/code-quality.md`)로 옮기지 않은 이유

119가 표로 정리해 둔 그대로다 — 같은 계보지만 같은 문서가 아니고, 공유본에는
표가 추적하는 체크리스트 자체가 없다. 이번에 하나 더 확인했는데, **절 번호가
서로 다른 것을 가리킨다**:

| | Modan2 원본 §7 | 공유 가이드 §7 |
|---|---|---|
| 제목 | Packaging & release verification | Dead code, complexity & duplication |

`TODOs.md`가 두 곳에서 쓰는 `guide §7`(패키지 산출물 스모크 테스트, 설치본
서명)은 전자다. 기준 문서만 조용히 바꿔 달았다면 **링크는 안 깨진 채로 뜻만
틀리는** 형태가 됐을 것이다. 아래 사본의 절 번호가 정본이다.

---

# 사본 — CODE_QUALITY_GUIDE.md (Modan2, v1.0, 2026-07-23)

출처: `jikhanjung/Modan2` (공개 저장소) `docs/CODE_QUALITY_GUIDE.md`. 원문 그대로
옮긴 것이며, 이 저장소에서는 **갱신하지 않는다**(위 참조). 상류의 이후 판이
궁금하면 원본을 보되, 아래 표의 기준으로 삼지는 말 것.

## 절 목록 — `§n` 참조의 정본

| § | 제목 |
|---|---|
| 0 | Why desktop multi-platform is different |
| 1 | Formatting & Linting (static, cheap, always-on) |
| 2 | Type checking (static, high-value, incremental) |
| 3 | Testing strategy |
| 4 | Test coverage |
| 5 | Cross-platform CI — the keystone for desktop |
| 6 | Dependencies & reproducible environments |
| 7 | Packaging & release verification |
| 8 | Runtime robustness & error handling |
| 9 | Resource & memory management |
| 10 | Internationalization, encoding & rendering |
| 11 | Performance |
| 12 | Security (for a file-ingesting desktop app) |
| 13 | Dead code & complexity |
| 14 | Developer workflow & gating |

## Appendix A — Prioritized adoption checklist

> For a mature codebase that already has linting + a test suite (like this one),
> adopt in this order — cheapest and highest-leverage first:
>
> 1. [ ] **Cross-platform CI matrix** (OS × min/max runtime) + a headless **import/smoke test**. *Catches the biggest class of user-only crashes.*
> 2. [ ] **Make lint + tests gating** (remove `|| true`; branch protection).
> 3. [ ] **Expand the lint ruleset** incrementally — start with `DTZ`, `RUF012`, `S`, zero-violation groups; auto-fix the safe ones.
> 4. [ ] **`filterwarnings = error`** in tests (missing-glyph, Deprecation, numpy).
> 5. [ ] **Dependency hygiene:** lockfile + `pip-audit` + Dependabot; documented clean rebuild.
> 6. [ ] **Coverage gate** (floor + no-regression on PRs).
> 7. [ ] **Static type checking** (mypy/pyright), scoped to core modules, expanding.
> 8. [ ] **Dead-code / complexity automation** (`vulture`, `C901`/`radon`).
> 9. [ ] **Packaged-artifact smoke test** in a clean runner; sign installers.
> 10. [ ] **Property-based/fuzz tests** for parsers and numeric code.

`TODOs.md`의 상태표 1~10번이 이 번호다.

## §7 Packaging & release verification — `TODOs.md`가 두 번 가리키는 절

> **Goal:** the thing you ship actually starts on a clean machine.
>
> - **Build the installer per-OS in CI** (matrix), not just on the maintainer's laptop.
> - **Smoke-test the *built artifact*, not just the source.** Install the produced package in a clean VM/runner and launch it headless. Source tests passing does not prove the frozen/packaged app (PyInstaller/py2app/MSIX) bundles every dependency and data file.
> - **Verify data files, icons, translations, and native libs are bundled** — these are the usual "works from source, broken when frozen" gaps.
> - **Sign** installers (Windows Authenticode, macOS notarization) so users aren't blocked by OS gatekeepers.
> - Keep a written **release checklist** and version single-sourced.

## §1의 린트 규칙군 표 — 상태표 3번의 근거

> | Rule group | Catches | Why it matters here |
> |---|---|---|
> | `DTZ` | naive datetime / missing tzinfo | The `datetime.UTC` / timezone class of bugs |
> | `RUF012` | mutable class-level defaults | Shared-state-across-instances bugs (a real past defect) |
> | `S` (bandit) | eval/exec, `shell=True`, weak hash, unsafe yaml, path issues | Untrusted file parsing / process launching |
> | `TRY`, `LOG`, `G` | exception & logging anti-patterns | Silent failures, f-strings in logging |
> | `SIM`, `RET`, `PIE`, `PERF`, `A` | simplifications, dead returns, shadowed builtins | General rot |
> | `PTH` | `os.path` → `pathlib` | Path handling correctness across separators |
> | `C901` | function complexity (mccabe) | Flags mega-methods that hide bugs |
>
> - **Adopt incrementally.** … Turn on the zero-violation groups immediately;
>   auto-fix the safe ones (`ruff check --select GRP --fix`, then run the test
>   suite); for the noisy groups (`S`, `PTH`, `G`), either fix in a dedicated pass
>   or scope to specific high-value rules. **Never bulk-`# noqa`; fix or
>   deliberately ignore with a reason.**

**옮겨 놓고 보니 틀렸던 것 하나 — "the guide's threshold of 15".**
`TODOs.md`와 devlog 103·105는 `C901` 임계값 15를 가이드가 정한 값처럼 적어
왔는데, **원문에는 숫자가 없다.** §1은 `C901`을 규칙군으로만 들고, §13도
`vulture`/`radon`과 함께 도구로만 언급한다. 가이드 파일의 커밋은 둘뿐이고 어느
판에도 임계값이 없었다. 게다가 **Modan2 자신의 `max-complexity`는 19다.**

15는 이 저장소가 원래 쓰던 값이다 — 가이드가 쓰이기 열 달 전인 2025-09-30에
이미 `max-complexity = 15`였다(devlog 038). 103이 래칫을 32로 올릴 때 돌아갈
목표로 삼은 것이 그 원래 값이었고, 어느 시점엔가 그 출처가 가이드로 잘못
붙었다. **끄집어내 옆에 놓으니 보였다** — 옆 저장소를 열어야만 확인되는 인용은
아무도 확인하지 않는다. 문구는 이번에 바로잡았다.

## Appendix B — Tooling quick reference

> | Concern | Tool(s) |
> |---|---|
> | Lint + format | Ruff |
> | Type check | mypy, pyright |
> | Test | pytest, pytest-qt, pytest-xvfb, pytest-cov, pytest-benchmark |
> | Property/fuzz | hypothesis |
> | Coverage gate | coverage.py `--fail-under`, diff-cover |
> | Security (code) | bandit / Ruff `S` |
> | Security (deps) | pip-audit, Dependabot / Renovate |
> | Env / lock | pip-tools, uv, Poetry |
> | Dead code / complexity | vulture, radon, Ruff `F401/F841/C901` |
> | Profiling | line_profiler, memory_profiler, snakeviz |
> | CI | GitHub Actions matrix; pre-commit; branch protection |
> | Packaging | PyInstaller / py2app / briefcase; code signing + notarization |

---

## 바꾼 것

`TODOs.md`의 Modan2 참조 네 곳이 이 devlog를 가리킨다 — 표 머리말, `C901`
임계값 문장(위 주의 사항 반영), `guide §7` 두 곳.

## 그대로 둔 것

**devlog 100·103의 `../Modan2/docs/CODE_QUALITY_GUIDE.md` 참조는 손대지
않았다.** 그 둘은 *그때 무엇을 보고 감사했는가*의 기록이고, 경로를 지금 것으로
바꾸면 사실관계가 틀어진다. 기록은 낡을 권리가 있고, 낡지 말아야 하는 것은
계획 쪽이다. 이 저장소에서 형제 저장소로 나가는 **살아 있는** 의존은 이제 없다.
