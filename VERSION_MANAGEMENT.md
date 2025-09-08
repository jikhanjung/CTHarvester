# CTHarvester 버전 관리: 전략과 실전 가이드

## 개요

CTHarvester는 중앙 집중식 버전 관리 시스템을 사용합니다. 모든 버전 정보는 `version.py` 파일에서 관리되며, `manage_version.py` 스크립트를 통해 자동화된 방식으로 업데이트됩니다.

## 🎯 핵심 원칙

- **Single Source of Truth**: `version.py` 파일이 유일한 버전 정보 소스입니다.
- **Semantic Versioning**: [SemVer 2.0.0](https://semver.org/) 규칙을 엄격히 준수합니다.
- **자동화**: `manage_version.py` 스크립트를 통해 버전 업데이트와 관련 작업(CHANGELOG, Git commit/tag)을 자동화합니다.

## 📁 관련 파일

| 파일 | 설명 |
|--------------------|------------------------------------------------|
| `version.py` | 버전 정보를 저장합니다. (Single Source of Truth) |
| `manage_version.py` | 버전 업데이트 및 관련 작업을 자동화하는 스크립트입니다. |
| `CHANGELOG.md` | 각 버전별 변경 사항을 기록하는 문서입니다. |

## 🔧 버전 관리 명령어

`manage_version.py` 스크립트는 다음과 같은 명령어를 제공합니다.

### 1. 정식 버전 업데이트

안정된 정식 버전의 번호를 올립니다.

- **`major`**: `1.2.3` -> `2.0.0`
- **`minor`**: `1.2.3` -> `1.3.0`
- **`patch`**: `1.2.3` -> `1.2.4`

```bash
python manage_version.py minor
```

### 2. Pre-release 시작

다음 버전의 pre-release(사전 출시)를 시작합니다. 토큰(`alpha`, `beta`, `rc`)을 지정하지 않으면 `alpha`가 기본값입니다.

- **`premajor`, `preminor`, `prepatch`**

```bash
# 0.1.4 -> 0.2.0-alpha.1
python manage_version.py preminor

# 0.2.0-alpha.1 -> 1.0.0-beta.1
python manage_version.py premajor beta
```

### 3. Pre-release 번호 증가

현재 pre-release 버전의 번호를 1 올립니다.

- **`prerelease`**

```bash
# 0.2.0-alpha.1 -> 0.2.0-alpha.2
python manage_version.py prerelease
```

### 4. Pre-release 단계 전환

`alpha` -> `beta` -> `rc` 와 같이 pre-release 단계를 전환합니다. 번호는 1로 초기화됩니다.

- **`stage <alpha|beta|rc>`**

```bash
# 0.2.0-alpha.2 -> 0.2.0-beta.1
python manage_version.py stage beta
```

### 5. 정식 버전으로 출시

Pre-release 버전을 안정된 정식 버전으로 변경합니다.

- **`release`**

```bash
# 0.2.0-rc.3 -> 0.2.0
python manage_version.py release
```

## 🚀 일반적인 릴리스 워크플로우 예시

`v0.1.0` 버전 출시 이후, `v0.2.0` 버전을 출시하는 전체 과정 예시입니다.

1.  **v0.2.0 개발 시작 (alpha)**
    - `v0.1.0` 에서 `v0.2.0`의 `alpha` 버전을 시작합니다.
    ```bash
    python manage_version.py preminor alpha
    # 새 버전: 0.2.0-alpha.1. 스크립트 안내에 따라 커밋과 태그를 생성합니다.
    ```

2.  **alpha 버전 개발 및 업데이트**
    - 기능 개발 및 버그 수정을 진행하며 `prerelease`로 버전을 올립니다.
    ```bash
    python manage_version.py prerelease
    # 새 버전: 0.2.0-alpha.2
    ```

3.  **beta 단계로 전환**
    - 주요 기능 개발이 완료되면 `beta` 단계로 전환하여 안정성 테스트를 시작합니다.
    ```bash
    python manage_version.py stage beta
    # 새 버전: 0.2.0-beta.1
    ```

4.  **정식 버전 출시**
    - RC 단계를 거치거나, 베타 버전이 안정적이라고 판단되면 정식 버전으로 출시합니다.
    ```bash
    python manage_version.py release
    # 새 버전: 0.2.0
    ```

### ⚠️ 릴리스 태그에 대한 중요 노트

**릴리스 태그는 실제로 배포될 코드의 최종 버전을 가리켜야 합니다.**

`manage_version.py`를 실행하면 버전업과 태그 생성을 한 번에 처리해주는 것이 가장 이상적입니다. 하지만 만약 버전업 커밋을 한 직후, 태그를 생성하기 전에 긴급한 버그 수정이 필요하다면 다음 절차를 따라야 합니다.

1.  버그를 수정하고 새로운 커밋을 만듭니다. (예: `fix: Critical bug in build process`)
2.  `manage_version.py`의 자동 태그 생성 기능을 사용하지 않습니다.
3.  **가장 마지막 커밋(버그 수정 커밋)의 해시(ID)를 직접 지정하여** 수동으로 태그를 생성합니다. 이는 빌드될 코드에 버그 수정이 반드시 포함되도록 보장하기 위함입니다.

    ```bash
    # 1. 마지막 커밋의 해시 확인
    git log -n 1

    # 2. 해당 커밋 해시를 지정하여 태그 생성
    git tag -a v0.2.0 <commit-hash> -m "Release version 0.2.0"
    ```

## ⚙️ 설치 및 요구사항

새로운 버전 관리 스크립트는 `semver` 라이브러리를 사용합니다. 프로젝트 실행 전, 반드시 의존성을 설치해야 합니다.

```bash
pip install -r requirements.txt
```

---
*Last updated: 2025-09-07*
