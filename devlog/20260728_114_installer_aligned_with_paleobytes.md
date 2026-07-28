# 인스톨러 설정을 PaleoBytes 공통 규약에 맞춤

2026-07-28

`InnoSetup/CTHarvester.iss.template`을 `../Modan2`, `../PaperMeister`와 같은
모양으로 맞췄다. 세 프로젝트가 같은 스위트로 배포되는데 Windows 설치 동작만
서로 달랐다.

---

## 📋 출발점: 세 프로젝트 비교

| | CTHarvester (전) | Modan2 | PaperMeister |
|---|---|---|---|
| `AppId` | **없음** | GUID | GUID |
| `AppPublisher` | `Jikhanjung` | `PaleoBytes` | `PaleoBytes` |
| `PrivilegesRequired` | **없음 (관리자 승격)** | `lowest` | `lowest` |
| 설치 위치 | `{commonpf}\PaleoBytes\...` (관리자) | `{localappdata}\PaleoBytes\...` | `{localappdata}\PaleoBytes\...` |
| `UninstallDisplayIcon` | 없음 | 있음 | 없음 |
| `Compression` | `lzma` + solid | `lzma/normal`, solid 없음 | `lzma/normal`, solid 없음 |
| 시작 메뉴 | `PaleoBytes\CTHarvester` | `PaleoBytes\Modan2` | `PaleoBytes\PaperMeister` |
| `[Run]` 플래그 | `postinstall nowait skipifsilent` | `postinstall shellexec` | `postinstall shellexec nowait skipifsilent` |

재미있는 건 PaperMeister 쪽 커밋 메시지(`2cb5adf`)가 설치 위치를 옮기는 이유로
"to group with Modan2 and CTHarvester"라고 적고 있다는 점이다. 실제로는
CTHarvester가 `{commonpf}`(Program Files)를 쓰는 유일한 예외였다. 즉 규약은
이미 두 프로젝트에 있었고, 그 규약을 근거로 세 번째를 옮기면서 정작 어긋난
쪽을 확인하지 않았다. **"맞춰서 옮겼다"는 진술이 맞춰지는 대상을 검증하지
않고도 성립한다**는 것이 여기서 남는 교훈이다.

## ⚙️ 적용한 것

- **`AppId` 신규 부여** (`{{D08C5C2E-...}`). Inno는 `AppId`가 없으면 `AppName`
  에서 신원을 파생하므로, 지금까지의 업그레이드 감지와 제거 항목은 전부
  `CTHarvester_is1` 키에 매달려 있었다. 표시 이름을 바꾸는 순간 두 번째 사본이
  나란히 깔린다.
- **per-user 설치**: `PrivilegesRequired=lowest` +
  `DefaultDirName={userpf}\PaleoBytes\CTHarvester`. 승격이 없으므로 `{userpf}`와
  `{userprograms}`가 UAC에 동의한 사람이 아니라 실행한 사람으로 확실히 해석된다.
  Roaming이 아닌 Local인 이유는 Modan2의 근거를 그대로 따랐다 — onedir 페이로드가
  수백 MB라 도메인 가입 머신에서 프로필과 동기화된다.

  처음에는 형제 프로젝트를 따라 `{localappdata}\PaleoBytes\CTHarvester`로 갔다가
  `{userpf}`(= `%LOCALAPPDATA%\Programs`)로 다시 옮겼다. `%LOCALAPPDATA%` 바로 밑은
  캐시와 프로필 같은 **애플리케이션 데이터**가 사는 곳이고, 프로그램 자체가 그 사이에
  끼는 자리가 아니다. `{userpf}`가 Windows가 per-user 프로그램용으로 정해 둔
  위치다.

  이 결론은 Modan2가 `{userappdata}`(Roaming) → `{localappdata}` → `{userpf}`로 두 번
  옮기며 도달한 것이다. **위 비교표는 이 글을 쓰던 시점의 스냅샷이고, 세 프로젝트는
  같은 날 셋 다 `{userpf}\PaleoBytes\<App>`으로 정렬됐다** — 규약을 맞추던 도중에
  규약 자체가 한 번 더 움직인 셈이라, 표를 그대로 두면 형제 프로젝트가 아직
  `{localappdata}`인 것처럼 읽힌다.
- `AppPublisher=PaleoBytes`, `UninstallDisplayIcon`, `Compression=lzma/normal` +
  `SolidCompression=no` (Modan2가 먼저 겪은 AV 오탐 완화), `[Run]`에 `shellexec`,
  데스크톱 아이콘을 `{autodesktop}` → `{userdesktop}`(권한이 `lowest`로 고정된
  뒤에는 `autodesktop`의 간접성이 아무 것도 사지 못한다).

## 🗑️ 같이 정리한 두 가지

**`InnoSetup/CTHarvester.iss` 삭제.** 템플릿과 별개로 `AppVersion "0.2.0"`을
하드코딩한 사본이 남아 있었다. `build.py`는 `.iss.template`만 읽으므로 죽은
파일이었지만, ISCC를 직접 여기에 겨누면 버전이 틀린 인스톨러가 조용히 나온다.
Modan2와 PaperMeister에는 템플릿만 있다. 이력 단일화(devlog 113)와 같은
구조의 문제 — **손으로 관리되는 두 번째 사본은 반드시 어긋난다.**

**`[Code] InitializeSetup` 제거.** 시작 메뉴 그룹 디렉토리를 `CreateDir`로 만드는
블록이었는데, Inno는 `[Icons]` 항목의 부모 디렉토리를 자동으로 만든다. 게다가
`InitializeSetup`은 사용자가 설치를 확인하기 *전에* 실행되므로, 마법사를 취소해도
빈 디렉토리가 남는다. PaperMeister에는 없고 Modan2에는 아직 있다 — 규약이 갈리는
유일한 항목이라 더 새 쪽을 택했다.

## 🔍 검증

Windows가 없으니 ISCC를 돌릴 수는 없다. 대신 `build.py`의 치환을 그대로
재연했다:

- `{{VERSION}}` 및 `..\` 상대 경로 전부 해소, 남은 것 없음
- **남은 이중 중괄호는 `AppId` 한 줄뿐** — Inno의 리터럴 `{` 이스케이프가
  `{{VERSION}}`류 플레이스홀더로 오인되지 않는지 확인하는 것이 목적
- 치환된 `LicenseFile` / `SetupIconFile` / `OutputDir`이 실제 존재하는 경로로
  해석되는지 확인

이 과정에서 **`SetupIconFile=..\icon.ico`가 존재하지 않는 경로**였음이 드러났다.
`build.py`가 이 문자열을 `resources/icons/icon.ico`로 치환해 주고 있었기 때문에
동작에는 문제가 없었지만, 템플릿만 읽으면 있지도 않은 루트 `icon.ico`를 가리키는
것으로 보인다. 템플릿을 실제 경로로 고치고 `build.py`의 치환 대상도 같이 옮겼다.

## ⚠️ 신원과 위치가 함께 바뀐다

기존 설치는 `C:\Program Files\PaleoBytes\CTHarvester`에 있고, per-user
인스톨러는 이것을 제자리 업그레이드할 수 없다. `AppId`가 새로 생긴 것까지
겹치므로 신원도 다르다.

`AppId`를 레거시 파생값(`CTHarvester`)으로 고정하면 신원은 이을 수 있지만, 설치
위치가 바뀌는 이상 어차피 제자리 업그레이드는 불가능하다. **어차피 한 번
끊어지는 지점이라면, 이름에서 파생된 신원을 영구히 물려받는 대신 지금 GUID로
갈아타는 것이 싸다.** PaperMeister가 v0.1.2에서 같은 판단을 했다.

처음에는 CHANGELOG와 매뉴얼에 "먼저 구 버전을 제거하라"를 적었는데, 현재 사용자가
없다는 것이 확인되어 걷어냈다. **마이그레이션 안내는 공짜가 아니다** — 아무도
해당되지 않는 경고는 영구히 남아 문서를 낡아 보이게 만든다.

## 💡 남은 것

- **인스톨러 서명**이 되면 `Compression`을 다시 solid/max로 돌릴 근거가 생긴다.
  지금 보수적으로 두는 이유는 서명이 없어서다 (`TODOs.md` #9).
- Modan2의 `[Code] InitializeSetup`도 같은 이유로 지울 수 있다.
- 매뉴얼이 로그 위치를 `%APPDATA%\PaleoBytes\CTHarvester\logs`로 적고 있는데
  `utils/log_helper.py`는 `~/PaleoBytes/CTHarvester/logs`를 쓴다 → 같은 세션에
  이어서 처리했다. devlog 115.
