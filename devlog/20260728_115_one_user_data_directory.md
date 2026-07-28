# 사용자 데이터를 한 디렉토리로: preferences.json

2026-07-28

devlog 114에서 인스톨러를 맞추다가 매뉴얼의 로그 경로가 코드와 다른 것을 발견했고,
확인해 보니 문제는 문서가 아니었다. **레이아웃을 아는 곳이 네 군데였고 서로 달랐다.**

---

## 🔍 네 명의 소유자

| 위치 | 무엇을 알고 있었나 |
|---|---|
| `utils/settings_manager.py` | `%APPDATA%/CTHarvester/settings.yaml` (Win) / `~/.config/CTHarvester/settings.yaml` |
| `utils/log_helper.py` | `~/PaleoBytes/CTHarvester/logs` |
| `CTLogger.py` | `~/PaleoBytes/<name>/logs` — 인자에서 파생 |
| `config/constants.py` | `~/PaleoBytes/CTHarvester` + `data/`, `logs/`, `backups/` |

즉 **설정과 로그가 플랫폼마다 서로 다른 곳에** 있었다. 매뉴얼이 로그 위치를
`%APPDATA%\PaleoBytes\...`로 적은 것은 이 둘을 헷갈린 결과로 보인다 — 설정은
`%APPDATA%`에 있었고 로그는 `PaleoBytes`에 있었으니, 둘을 합치면 존재하지 않는
경로가 된다.

`config/constants.py`의 `DEFAULT_DB_DIRECTORY`·`DEFAULT_STORAGE_DIRECTORY`·
`DB_BACKUP_DIRECTORY`는 Modan2에서 그대로 옮겨온 상수였다. Modan2에는 데이터베이스가
있고 CTHarvester에는 없다. 그런데 `CTHarvester.py`는 시작할 때마다 이 넷을 다
만들었다 — **`data/`와 `backups/`는 매 실행마다 사용자 프로필에 생성되고 아무도 읽지
않는 빈 디렉토리였다.** grep으로 확인: 두 상수는 constants.py와 그 생성 호출
외에는 어디에도 등장하지 않는다.

## ⚙️ 결과

`utils/paths.py` 하나가 레이아웃을 안다:

```
~/PaleoBytes/CTHarvester/
    preferences.json
    logs/CTHarvester.log
```

- 설정 파일은 **`preferences.json`** (Modan2와 동일한 이름·형식), 로그와 같은
  디렉토리. 프로필 백업이 디렉토리 하나 복사로 끝나는 것이 이 배치의 이유다.
- `CTHARVESTER_DATA_DIR`로 루트를 바꿀 수 있다. PaperMeister의
  `PAPERMEISTER_DATA_DIR`과 같은 용도 — 테스트가 실제 홈 디렉토리를 건드리지 않고
  해석 순서를 고정할 수 있다.
- 기존 `CTHARVESTER_LOG_DIR`의 처리도 `paths.py`로 옮겼다. 전에는 `CTLogger`만
  이 변수를 봤기 때문에 **로그 파일은 옮겨 가는데 UI의 "로그 디렉토리 열기"와 로그
  뷰어는 기본 위치를 계속 봤다.** 소유자가 둘이면 오버라이드에서 갈라진다는, 이
  변경이 없애려는 문제의 축소판. 명시적 `log_dir` 인자가 환경변수보다 우선하도록
  순서도 바로잡았다(전에는 환경변수가 인자를 덮었다).
- 나머지 세 곳은 전부 이 모듈에 위임. `config/constants.py`의 상수 5개는 삭제하고
  `CTHarvester.py`는 `user_directories()`가 주는 두 개만 만든다.

`ensure_directories`를 `paths.py`에 또 만들지 않았다. `utils/common.py`에 이미
있고 자체 테스트도 있다 — **같은 이름의 함수를 둘 만드는 것이 방금 없앤 문제의
재발이다.**

## 🤔 defaults: YAML을 남기려다 지웠다

처음에는 `config/settings.yaml`을 남길 생각이었다. 근거는 **JSON은 주석을 실을 수
없다**는 것 — 이 파일의 값들에는 설명이 붙어 있고, 그중에는 devlog 104에서 문제가
됐던 `use_rust_module`의 "false로 두면 어떻게 되는지"도 있다.

그 근거가 두 가지 사실 앞에서 무너졌다.

**하나. 릴리스 빌드에는 이 파일이 없다.** CI가 쓰는 `CTHarvester_onedir.spec`의
`datas`에는 아이콘과 번역뿐이다(`build_cross_platform.py`만 포함시킨다). 즉
`_load_default_settings()`는 프리즈된 빌드에서 항상 실패하고
`_get_hardcoded_defaults()`로 떨어졌다. **출하된 모든 버전은 이미 파이썬 dict로
동작하고 있었고, 매뉴얼만 YAML 파일을 가리키고 있었다.** 주석을 지키려던 파일이
정작 사용자에게 도달한 적이 없다.

**둘. 이미 어긋나 있었다.** 두 사본을 키 단위로 대조했더니:

| | 내용 |
|---|---|
| YAML에만 있고 아무도 안 읽음 | `rendering.background_color`, `logging.backup_count`, `paths.export_directory` 등 |
| 앱이 쓰는데 YAML에 없음 | `application.default_directory`, `window.main_geometry`, `window.mcube_geometry` |

devlog 113의 "손으로 관리되는 두 번째 사본은 반드시 어긋난다"가 또 한 번 확인됐다.
이번엔 예측이 아니라 측정이다.

그래서 YAML을 지우고 파이썬 dict를 유일한 정의로 삼았다. **주석은 형식이 아니라
파일이 문제였다** — 파이썬 주석으로 옮기니 그대로 살아 있고, 이쪽은 프리즈된
빌드에도 실제로 들어간다.

키 집합 자체는 건드리지 않았다. 안 읽히는 키를 지우면 사용자 파일의 내용이
바뀌고, 그건 별개의 판단이다.

## 🧯 읽을 수 없는 파일

Modan2를 따라, 깨진 설정 파일은 defaults로 조용히 덮지 않고 `.bak`으로 옮긴 뒤
로그에 남긴다. 기존 동작은 예외를 잡아 defaults를 쓰는 것뿐이었다 — 사용자가 설정한
모든 값이 사라지는데 원인 파일도 함께 사라졌다.

## 🔍 검증

- 새 테스트 17개 (`tests/test_paths.py`). 핀으로 박아 둘 가치가 있는 것은 개별
  문자열이 아니라 **소비자들이 같은 곳을 가리킨다는 사실**이므로,
  `log_helper`·`CTLogger`·`SettingsManager` 각각이 `paths`와 일치하는지를 보고,
  `CTHARVESTER_LOG_DIR`을 걸었을 때도 여전히 일치하는지를 따로 본다(이게 실제로
  깨져 있던 지점이다). `SettingsManager`에는 그때까지 직접 테스트가 아예 없었다.
- `test_import_settings`는 YAML을 써 놓고 버튼 존재만 검사하고 있었다 — import가
  파싱조차 못 하는데 통과했다. JSON으로 바꾸고 값이 실제로 반영됐는지 검사하도록
  고쳤다(`TODOs.md`가 적어 둔 "값을 만들고 검사하지 않는 테스트" 부류).
- 전체 스위트 1323 passed.
- **`--self-test`로 실제 부팅**해 프로필에 무엇이 생기는지 확인: `preferences.json`과
  `logs/CTHarvester.log` 둘뿐. `data/`와 `backups/`는 없다. 상수를 지웠다는 것과
  실제로 안 만들어진다는 것은 다른 주장이라서, 후자를 봤다.
- 매뉴얼 경고를 **세기 대신 diff**했다(devlog 113의 교훈): 4개 → 4개, 집합이 동일.
  새로 생긴 것도, 사라진 것도 없다.

## 🧹 문서에서 드러난 것

경로를 훑다 보니 매뉴얼이 실제와 다른 곳이 상당했다. 이번 변경으로 어차피 손대야
하는 범위 안에서 정리했다:

- 로그 경로가 **세 가지 방식으로** 틀려 있었다: `%APPDATA%\PaleoBytes\...`,
  `~/.local/share/PaleoBytes/...`, 그리고 존재하지 않는 `ctharvester_*.log`
  파일명(실제는 `CTHarvester.log`).
- `advanced_features.rst`의 설정 예시가 **실제로 없는 키 이름**을 쓰고 있었다
  (`general:`, `worker_threads`, `max_pyramid_level`, `advanced:`, 그리고 아예
  존재하지 않는 `priority`/`backface_culling`/`wireframe_mode`). 세 번째 스키마
  사본을 유지하는 대신, 짧고 정확한 예시 + `configuration.rst` 참조로 바꿨다.
- **`cache.db` SQLite 캐시 "복구" 절이 있었다.** 프로젝트 전체에 sqlite는 한 줄도
  없다. 삭제.
- `tests/ui/conftest.py`의 `temp_settings_file` 픽스처는 아무도 요청하지 않는
  죽은 픽스처였고, 내용도 실제 스키마와 무관한 키를 쓰는 YAML이었다. 삭제.

## 💡 교훈

1. **문서가 코드와 다를 때, 먼저 의심할 것은 코드가 하나인지 여부다.** "매뉴얼이
   틀렸다"로 끝냈다면 네 개의 소유자는 그대로 남았다.
2. **상수를 물려받으면 그 상수가 전제하는 것도 물려받는다.** Modan2의 디렉토리
   상수를 복사한 대가는 데이터베이스 없는 프로그램이 매 실행마다 만드는 빈
   `backups/`였다.
3. **어떤 파일을 지킬지 정하기 전에 그 파일이 사용자에게 도달하는지 확인해라.**
   `config/settings.yaml`을 남길 근거(주석)는 그럴듯했지만, 그 파일은 릴리스
   빌드에 들어간 적이 없었다. 근거를 검토하는 것보다 전제를 확인하는 것이 빨랐다.
4. **지운 것이 실제로 안 생기는지 봐라.** 상수 삭제는 코드의 주장이고, 빈
   디렉토리가 안 생긴다는 것은 실행의 사실이다.
5. **오버라이드는 소유자가 갈라지는 곳에서 먼저 깨진다.** `CTHARVESTER_LOG_DIR`은
   기본 경로에서는 두 모듈이 우연히 같은 값을 만들어 냈기 때문에 멀쩡해 보였고,
   변수를 걸었을 때만 어긋났다. 통합의 이득은 기본 경로가 아니라 여기에 있다.
