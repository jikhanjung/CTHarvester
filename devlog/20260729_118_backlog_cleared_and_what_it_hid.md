# 백로그를 비우면서 드러난 것들 — 통과하던 테스트가 아무것도 검사하지 않던 문제

2026-07-29

## 배경

main이 빨간 상태였다. macOS 러너에서 `test_eta_calculation_with_speed` 하나가
깨졌고, 나머지는 전부 초록이었다. 그걸 고치는 김에 `TODOs.md`에 남아 있던
항목을 순서대로 비웠다 — mypy `ui/widgets/`, 속성 기반 테스트, bandit 존치
여부, F841 스윕이 남긴 얇은 테스트들.

**결과적으로 이 세션에서 고친 것 중 절반은 백로그가 예고한 작업이 아니라, 그
작업을 하다 드러난 결함이었다.** 공통점이 하나 있다: 전부 *무언가를 재보지
않고 있었기 때문에* 보이지 않았다.

## 1. ETA 테스트 — 상대비율도 기계 독립적이지 않다

세 번째 macOS 실패였고, 앞선 두 번의 수정이 모두 같은 이유로 틀렸다.

| 시도 | 단언 | 결과 |
|---|---|---|
| 최초 | `eta < 2` | macOS에서 4.83s로 실패 |
| 2차 | `approx(9 * elapsed, rel=0.5)` | macOS에서 2.77 vs 6.01로 실패 |

2차 수정의 주석은 "9배라는 관계는 기계가 어떤 속도로 돌든 성립한다"고 적었다.
성립하지 않는다. `SimpleProgressTracker`의 샘플은 **순간 속도가 아니라 누적
속도**(`completed / elapsed_since_start`)다. 따라서 첫 샘플은 `1/elapsed_1`이고,
이 값은 극단적으로 변동이 크다. 러너가 후반에 한 번 멈칫하면 그 초기 이상치가
여전히 smoothing window 안에 앉아 평균을 실제 속도 위로 끌어올리고, ETA가
짧아진다.

이건 트래커가 설계대로 동작한 결과다. **고정해야 할 변수는 비율이 아니라
시계였다.** 같은 파일의 `test_speed_averaging`이 이미 `monkeypatch`로
`time.perf_counter`를 주입하는 선례를 만들어 뒀는데, 그 선례를 이 테스트에
적용하지 않았던 것이다.

시계를 주입하니 숫자가 정확해진다 — 100 items/s 고정이면 speed 100,
elapsed 0.1s, ETA 0.9s. 허용오차가 `rel=0.5`에서 float 노이즈 수준으로 좁아졌다.
ETA 식에 1.3을 곱하는 프로브로 테스트가 실제 회귀를 잡는 것을 확인했다.

덤으로 `test_reset`의 `assert tracker.start_time <= time.time()`도 고쳤다.
`start_time`은 `perf_counter` 값이고 `time()`은 epoch이라 **두 시계가 무관해서
어떤 값이든 통과**하던 단언이었다.

## 2. `ui/widgets/` — exclude가 가리고 있던 결함 두 개

38건 중 절반은 예고대로 기계적이었다. PyQt5는 런타임에 `Qt`에 열거형 멤버를
노출하지만 스텁은 스코프 열거형에 두므로, `Qt.MouseButton.LeftButton` 식으로
이름을 정확히 쓰면 사라진다. 이 과정에서 `# type: ignore` 10개가 함께 없어졌고,
그중 하나는

```python
Qt.KeepAspectRatio,  # type: ignore[attr-defined],
```

**끝의 쉼표 때문에 형식이 깨져 있었다.** mypy는 이걸 무시 주석으로 인정하지
않고 syntax error로 보고하고 있었으므로, 이 무시는 처음부터 아무것도 억제하지
못했다.

나머지 둘은 타입 잡음이 아니라 결함이었다.

**`mcube_widget.py`의 `self.parent = parent`.** devlog 117에서
`progress_dialog.py`에 대해 지적한 것과 정확히 같은 결함이다 — `QWidget.parent()`
메서드를 인스턴스에서 덮어쓰므로 `widget.parent()`를 부르는 쪽은 부모 위젯 대신
2D 뷰어를 받는다. 파일 안에서만 읽히는 것을 확인하고 `parent_widget`으로 개명.

**`object_viewer_2d.py`의 무방비 역참조.** `mousePressEvent`,
`mouseMoveEvent`, `mouseReleaseEvent`가 전부
`self.object_dialog.update_status()`로 끝나고, `resizeEvent`는
`object_dialog.mcube_widget`과 `threed_view`를 같은 방식으로 뚫고 들어갔다. 셋
다 `MainWindowSetup`이 생성 이후에 바깥에서 붙여 주는 값이다. 즉 **단독으로
생성된 뷰어 — 테스트의 모든 뷰어 — 에서 이 네 경로는 전부 `AttributeError`를
냈다.** 아무도 마우스 핸들러를 호출하는 테스트를 쓰지 않아서 드러나지 않았을
뿐이다.

가드를 넣고 회귀 테스트 6개를 붙였다. 가드를 다시 빼면 그중 4개가 원래의
`AttributeError`로 깨지는 것을 프로브로 확인했다.

오버레이 버튼의 `method-assign` 5건은 **남겼다.** 자기가 소유하고 기반
핸들러를 부르지 않는 자식 `QLabel`에 핸들러를 대입하는 것은 평범한 PyQt
관용구이고, 같은 에러 코드를 달고 있을 뿐 `self.parent`와 같은 결함이 아니다.

이걸로 mypy의 exclude 목록이 **비었다**. CI·`make type-check`·pre-commit이
devlog 117에서 이미 동일한 `core/ utils/ ui/` 명령으로 통일돼 있었으므로,
exclude 한 줄을 지우자 세 곳이 동시에 넓어졌다.

## 3. hypothesis는 읽지 않는 파일에 설정돼 있었다

속성 테스트를 실제로 쓰려고 보니 `pyproject.toml`에

```toml
[tool.hypothesis]
max_examples = 100
derandomize = true
deadline = 500
```

이 있었다. **hypothesis는 `pyproject.toml`을 읽지 않는다** — 설치된 패키지
어디에도 그 파일명이 나오지 않는다. 추정이 아니라 측정으로 확인했다:
`settings.default.derandomize`가 파일이 `true`라고 적은 자리에서 `False`를
돌려줬다.

셋 중 `derandomize`가 중요하다. 이게 없으면 CI 실행마다 다른 예제를 뽑으므로,
입력 공간의 얇은 조각에서만 깨지는 속성이 **어느 플랫폼에서 가끔 실패하고
재실행하면 통과한다** — 바로 이 날 아침에 고친 macOS ETA 플레이크와 같은
모양이다. 속성 테스트를 넣으면서 그 실패 양식을 다시 들여올 수는 없었다.

`tests/conftest.py`의 `settings.register_profile()`로 옮겼고, 프로파일이 실제로
적용되는지 프로브로 확인했다.

속성 자체는 14개를 썼다. 가장 값어치 있는 것은 `average_images`의 범위 속성이다
— 이 함수는 uint8 두 밝은 픽셀이 wrap하지 않도록 dtype을 넓혀서 더하는 것이
존재 이유인데, 200과 200을 골라야겠다고 생각한 사람이 없으면 예제 기반
테스트로는 고정되지 않는다. 홀수 길이 스택이 마지막 이미지를 자기 자신과
짝짓는다는 점에서 `average(x, x) == x`도 실제 입력이다.

넓히기를 뺀 프로브와 `set_roi_bounds`의 min/max를 뺀 프로브로 14개 중 6개가
반응하는 것을 확인했다.

## 4. bandit — 재보고 나서 남기기로 했다

백로그가 "지나가면서 결정할 일이 아니다"라고 미뤄 둔 건이다. ruff의
flake8-bandit이 bandit 1.9.4의 **75개 중 73개**를 구현하므로 질문 자체는
정당했다.

포팅되지 않은 4개 중 셋은 이 프로젝트가 쓰지 않는 라이브러리용이다 —
`B614`(torch.load), `B615`(HuggingFace), `B703`(Django XSS).

넷째가 결정한다. **`B613` `trojansource`** 는 양방향 유니코드 제어문자를
잡는다 — 소스가 렌더링되는 모습과 컴파일되는 모습이 달라지는 공격이다. HIGH
severity라 잡의 `-ll` 게이트를 통과하고, 나머지 셋과 달리 언어·의존성과
무관하다. 프로브로 확인했다: 주석에 `U+202E`가 든 파일을 bandit은 잡고
`ruff check --select S`는 통과시킨다.

`-t B613`으로 좁히지 않고 넓은 호출을 유지했다. 그래야 ruff가 아직 포팅하지
않은 미래의 검사가 이 비교를 다시 돌리지 않고도 들어온다. 기록해 둘 것:
**bandit은 지금 이 임계값에서 아무것도 보고하지 않는다**(12건, 전부 `-ll`
아래). ruff `S`를 켤 때와 같은 논리로, 가치는 예방적이다.

## 5. 얇은 테스트 — 그리고 그중 하나가 진짜였다

F841 스윕이 남긴 항목들은 예상대로 리터럴에 대한 단언이나 `hasattr` 확인이었고,
실제 호출로 바꾸면 되는 일이었다.

**하나만 달랐다.** `test_settings_persistence`는 서로를 가려 주는 결함 두 개를
품고 있었다.

1. 양쪽 절반이 `if hasattr(window, "settings")`로 가드돼 있었다. 속성 이름은
   **`settings_manager`** 다. 즉 가드가 항상 False라 쓰기와 검사가 함께
   건너뛰어졌고, **이 테스트는 통과 외의 결과를 낼 수 없었다.**
2. 격리를 `CTHARVESTER_SETTINGS_DIR`로 걸고 있었다. **애플리케이션이 한 번도
   읽은 적 없는 이름이다** — `utils.paths`는 `CTHARVESTER_CONFIG_DIR`에서
   설정 루트를 해석한다. 틀린 이름이 공유 `main_window` fixture를 포함해 세
   곳에 있었다.

`closeEvent()`가 `save_settings()`를 부르고 그 fixture가 teardown에서 창을
닫으므로, **통합 테스트는 실행할 때마다 개발자의 진짜 `preferences.json`에 쓰고
있었다.** 언어 키까지 덮어쓰이지 않은 것은 오직 결함 1 덕분이었다.

세 곳 모두 `monkeypatch.setenv`로 올바른 이름을 쓰게 했다 — `os.environ`이
아니라 `monkeypatch`인 것은 세션 나머지로 새지 않고 teardown에서 되돌리기
위해서다. 그리고 설정 경로가 정말 `tmp_path` 아래인지 단언하게 했다. 이름이
다시 틀리면 시끄럽게 실패한다.

**`tests/test_basic.py`는 지웠다.** CI에서 `--ignore` 되면서 로컬에서는
통과하던 파일인데, 어느 쪽으로 정리하든 이상한 상태였다. 지우기 전에
가정하지 않고 확인했다: `test_smoke.py::test_module_imports`가
`config`/`core`/`security`/`ui`/`utils` 전 모듈을 순회하고
`::test_third_party_native_extensions_load`가 컴파일된 서브모듈을 직접
건드리므로 앞의 둘을 포섭하고, 나머지 넷은 전용 파일이 같은 호출을 — 일부는 더
엄격하게 — 덮고 있었다.

## 남은 것

체크리스트에서 남은 항목은 **인스톨러 서명/공증** 하나다. Windows
Authenticode 인증서와 Apple Developer ID가 필요하므로 코드가 아니라 자격
증명의 문제이고, 여기서 끝낼 수 있는 일이 아니다.

`[Unreleased]`에 사용자에게 보이는 변경이 쌓여 있어 beta.4를 낼 시점으로
보인다.

## 배운 것

**"이 단언은 무엇이 깨지면 실패하는가"를 물어야 한다.** 이 세션에서 나온 결함은
전부 통과하는 테스트나 통과하는 게이트 뒤에 있었다. `hasattr` 가드가 항상
False인 테스트, 형식이 깨져 억제하지 못하던 `type: ignore`, 읽히지 않는 파일의
설정, 무관한 두 시계를 비교하던 단언 — 넷 다 초록이었다. 초록은 검사했다는
뜻이 아니라 실패하지 않았다는 뜻뿐이다.

**그래서 이번에는 전부 프로브로 확인했다.** 고의로 결함을 주입하고 테스트가
정말 깨지는지 본 뒤 원복하는 절차를 다섯 번 돌렸다(ETA 식, object_dialog 가드,
average_images의 dtype 넓히기, set_roi_bounds의 정규화, 환경변수 이름). 재보지
않으면 exclude 사유가 유통기한을 넘기듯, 단언도 조용히 아무것도 검사하지 않게
된다.
