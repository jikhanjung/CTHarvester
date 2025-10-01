# 포괄적 프로젝트 개선 계획

**날짜**: 2025-10-01
**세션**: #053
**타입**: 분석 & 계획
**상태**: 📋 계획 중

## 개요

이 문서는 철저한 프로젝트 분석과 최근 버그 발견을 기반으로 한 포괄적인 개선 계획을 설명합니다. 계획은 우선순위별로 구성되며 즉각적인 수정과 장기적인 개선을 모두 포함합니다.

## 요약

**프로젝트 상태**: 양호 ✅
- 486개의 테스트로 강력한 기반 (~95% 핵심 커버리지)
- 잘 설계된 모듈식 구조
- 52개의 상세한 devlog 항목으로 활발한 개발

**개선이 필요한 영역**:
- 썸네일 생성 API의 치명적 버그
- 저장소 정리 필요
- 문서 불일치
- 테스트 구조 개선

---

## 🔴 치명적 이슈 (즉시 조치 필요)

### 이슈 1: 파이썬 썸네일 생성 API 손상

**우선순위**: 🔴 치명적
**예상 시간**: 2시간
**심각도**: 중대한 변경 - 공개 API 작동 불가

#### 문제 설명

최근 콜백 기반 접근을 제거하는 리팩토링 이후, 공개 `generate()` 메서드 시그니처가 새 내부 구현과 호환되지 않습니다:

**위치**: `core/thumbnail_generator.py:169-191`

```python
# 현재 (손상됨):
def generate(self, directory, use_rust_preference=True, progress_callback=None, cancel_check=None):
    if use_rust:
        return self.generate_rust(directory, progress_callback, cancel_check)
    else:
        return self.generate_python(directory, progress_callback, cancel_check)  # ❌ 잘못된 시그니처!

# generate_python은 이제 다음을 기대합니다:
def generate_python(self, directory, settings, threadpool, progress_dialog=None):
```

**영향**:
- `generate(..., use_rust_preference=False)`를 사용하는 호출자는 `TypeError` 발생
- 하위 호환성 손상
- Rust 경로는 작동하지만 Python 대체 경로는 손상됨

#### 해결 방안

**옵션 A: 공개 API 업데이트 (중대한 변경)**
```python
def generate(self, directory, settings, threadpool, use_rust_preference=True, progress_dialog=None):
    """사용 가능한 최상의 방법으로 썸네일 생성

    Args:
        directory (str): CT 이미지가 포함된 디렉토리
        settings (dict): 이미지 매개변수가 있는 설정 해시
        threadpool (QThreadPool): Qt 스레드 풀
        use_rust_preference (bool): 가능한 경우 Rust 선호
        progress_dialog (ProgressDialog, optional): 진행 상황 UI
    """
    if self.rust_available and use_rust_preference:
        return self.generate_rust(directory, progress_dialog)
    else:
        return self.generate_python(directory, settings, threadpool, progress_dialog)
```

**옵션 B: 하위 호환성 유지 (어댑터)**
```python
def generate(self, directory, use_rust_preference=True, progress_callback=None, cancel_check=None):
    """하위 호환성을 위한 레거시 래퍼"""
    # 컨텍스트에서 설정 추출하거나 호출자에게 업데이트 요구
    warnings.warn("기존 시그니처는 더 이상 사용되지 않습니다. generate_v2()를 사용하세요", DeprecationWarning)
    # 어댑터 로직 제공
```

**권장사항**: 옵션 A (깔끔한 단절, 마이그레이션 문서화)

**업데이트할 파일**:
1. `core/thumbnail_generator.py:169-191` - 시그니처 업데이트
2. `ui/main_window.py:817-891` - 이미 새 시그니처 사용 중 ✅
3. `tests/test_thumbnail_generator.py` - 테스트 케이스 업데이트
4. `docs/api/core.rst` - API 문서 업데이트

**외부 호출자를 위한 마이그레이션 경로**:
```python
# 이전:
generator.generate(directory, use_rust_preference=False,
                   progress_callback=cb, cancel_check=cc)

# 이후:
generator.generate_python(directory, settings, threadpool, progress_dialog)
# 또는
generator.generate(directory, settings, threadpool,
                   use_rust_preference=False, progress_dialog=pd)
```

---

### 이슈 2: 진행 상황 샘플링 작동 안 함 (ETA가 "추정 중..."에 고정됨)

**우선순위**: 🔴 높음
**예상 시간**: 1시간
**심각도**: 사용자 경험 저하 - 정확한 ETA 없음

#### 문제 설명

**위치**: `core/thumbnail_generator.py:386-397`

계산된 `sample_size`가 `ThumbnailManager`에 전달되지 않아 기본값 0으로 남아 있어 진행 상황 샘플링이 시작되지 않습니다.

**현재 코드**:
```python
# 388-390번째 줄: 샘플 크기 계산
base_sample = max(20, min(30, int(total_work * 0.02)))
sample_size = base_sample
total_sample = base_sample * 3

# 492-497번째 줄: sample_size 없이 ThumbnailManager 생성
thumbnail_manager = ThumbnailManager(
    None,  # main_window
    progress_dialog,
    threadpool,
    shared_progress_manager
)
# ❌ sample_size가 설정되지 않음!
```

**영향**:
- `ThumbnailManager.sample_size = 0` (기본값)
- 샘플링이 시작되지 않음
- ETA가 계속 "추정 중..."으로 표시됨
- 사용자가 시간 예측을 볼 수 없음

#### 해결 방안

**옵션 A: 생성자를 통해 전달**
```python
class ThumbnailManager:
    def __init__(self, parent, progress_dialog, threadpool,
                 shared_progress_manager, sample_size=20):
        self.sample_size = sample_size
```

**옵션 B: 생성 후 설정 (빠른 수정)**
```python
thumbnail_manager = ThumbnailManager(...)
thumbnail_manager.sample_size = sample_size
```

**옵션 C: 설정에서 가져오기 (모범 사례)**
```python
# ThumbnailManager.__init__에서:
settings = SettingsManager()
self.sample_size = settings.get('thumbnails.sample_size', 20)
```

**권장사항**: B (즉시)와 C (적절한 수정)의 조합

**구현**:
1. `generate_python()`에서 빠른 수정:
   ```python
   thumbnail_manager = ThumbnailManager(...)
   thumbnail_manager.sample_size = sample_size  # 498번째 줄
   ```

2. `ThumbnailManager.__init__`에서 적절한 수정:
   ```python
   # 사용 가능한 경우 설정에서 읽기
   if hasattr(parent, 'settings'):
       self.sample_size = parent.settings.get('thumbnails.sample_size', 20)
   else:
       self.sample_size = 20  # 기본값
   ```

**업데이트할 파일**:
1. `core/thumbnail_generator.py:497` - `thumbnail_manager.sample_size = sample_size` 추가
2. `core/thumbnail_manager.py:__init__` - 설정에서 읽기
3. `tests/test_thumbnail_generator.py` - 샘플링 작동 확인
4. `tests/test_thumbnail_manager.py` - sample_size 처리 테스트

**검증**:
- Python 대체로 썸네일 생성
- 샘플링 완료 후 ETA가 실제 시간을 표시하는지 확인
- 로그에서 "Sampling complete: X.XX weighted units/s" 확인

---

### 이슈 3: 실패한 썸네일 생성이 제대로 처리되지 않음

**우선순위**: 🔴 높음
**예상 시간**: 30분
**심각도**: 실패 시 UI 손상

#### 문제 설명

**위치**: `ui/main_window.py:900+`

Python 썸네일 생성이 `success=False`를 반환하지만 `cancelled=False`일 때, 코드는 디스크에서 로드하고 빈/유효하지 않은 데이터로 UI를 초기화하는 작업을 계속합니다.

**현재 코드**:
```python
result = self.thumbnail_generator.generate_python(...)

if result:
    if result.get('cancelled'):
        # 취소 처리
        pass
    else:
        # ❌ success=False인 경우에도 계속됨!
        self.minimum_volume = result.get('minimum_volume')
        self.level_info = result.get('level_info')
        self.load_thumbnail_data_from_disk()
        self.initializeComboSize()  # 데이터가 유효하지 않으면 빈 콤보
```

**영향**:
- UI에 빈 콤보 박스 표시
- 3D 뷰가 충돌하거나 아무것도 표시하지 않을 수 있음
- 사용자에게 오류 메시지 없음
- 혼란스러운 사용자 경험

#### 해결 방안

**구현**:
```python
result = self.thumbnail_generator.generate_python(...)

if not result:
    # Null 결과
    self.show_error("썸네일 생성 실패", "알 수 없는 오류가 발생했습니다")
    QApplication.restoreOverrideCursor()
    return

if result.get('cancelled'):
    # 사용자 취소
    self.show_info("썸네일 생성 취소됨", "사용자가 작업을 취소했습니다")
    QApplication.restoreOverrideCursor()
    return

if not result.get('success'):
    # 생성 실패
    error_msg = result.get('error', '썸네일 생성 실패')
    self.show_error("썸네일 생성 실패", error_msg)
    QApplication.restoreOverrideCursor()
    return

# 성공한 경우에만 계속
self.minimum_volume = result.get('minimum_volume')
self.level_info = result.get('level_info')
# ... 나머지 성공 처리
```

**업데이트할 파일**:
1. `ui/main_window.py:900-950` - 실패 처리 추가
2. `core/thumbnail_generator.py:621-641` - 결과 딕셔너리에 오류 정보 보장
3. `tests/test_integration_thumbnail.py` - 실패 시나리오 테스트

**추가 개선 사항**:
- `generate_python()`의 결과 딕셔너리에 'error' 필드 추가
- 상세한 오류 정보 로깅
- 제안이 포함된 사용자 친화적 오류 다이얼로그 표시

---

## 🟡 높은 우선순위 이슈 (이번 주)

### 이슈 4: 저장소 정리

**우선순위**: 🟡 높음
**예상 시간**: 1시간
**영향**: 저장소 위생, 명확성

#### 제거/이동할 파일

**루트의 테스트 데이터 파일** (test_data/에 있어야 하거나 무시되어야 함):
```bash
# 제거하거나 test_data/로 이동:
Estaingia_rough_1.tps
Estaingia_rough_2.tps
Phacops_flat_20230619.tps
Tf-20230619.x1y1
M2Preferences_1.png
M2Preferences_2.png
CTHarvester_48.png
CTHarvester_48_2.png
CTHarvester_64.png
CTHarvester_64_2.png
expand.png
shrink.png
move.png
info.png
```

**고아 파일**:
```bash
# 제거:
CTScape.spec  # 존재하지 않는 CTScape.py 참조
src/lib_final_backup_20250927.rs  # 백업 파일
check_user_settings.py  # 임시 디버그 스크립트
```

**실행 계획**:
1. 테스트 데이터 패턴에 대한 `.gitignore` 항목 생성
2. 추적된 테스트 파일 `git rm`
3. 유용한 테스트 데이터를 `test_data/` 디렉토리로 이동
4. 백업 및 임시 파일 제거
5. 필요한 경우 문서 업데이트

#### 명령어 순서:
```bash
# test_data 디렉토리 생성
mkdir -p test_data/samples

# 테스트 데이터 이동
mv *.tps test_data/samples/
mv *.x1y1 test_data/samples/
mv *Preferences*.png test_data/samples/

# 고아 파일 제거
git rm CTScape.spec
git rm src/lib_final_backup_20250927.rs
git rm check_user_settings.py

# .gitignore 업데이트
echo "test_data/" >> .gitignore
echo "check_*.py" >> .gitignore

# 커밋
git commit -m "chore: 저장소 정리 - 테스트 데이터 이동 및 고아 파일 제거"
```

---

### 이슈 5: 문서 불일치

**우선순위**: 🟡 높음
**예상 시간**: 45분
**영향**: 사용자 혼란, 잘못된 설정

#### 5.1. Python 버전 요구사항 충돌

**현재 상태**:
- `README.md`: "Python 3.12+" (배지 및 설치 지침)
- `pyproject.toml:13`: `requires-python = ">=3.8"`
- `pytest.ini:2`: `minversion = 3.12`
- CI 워크플로우는 Python 3.11 사용

**결정**: Python 3.11+를 최소 버전으로 사용
- 타입 힌트 및 비동기 기능에 충분히 현대적
- CI 구성과 일치
- 새 사용자에게 합리적인 요구사항

**필요한 업데이트**:
1. `pyproject.toml:13`: `requires-python = ">=3.11"`
2. `README.md:8`: 배지를 `python-3.11%2B`로 업데이트
3. `README.md:45`: "Python 3.11 이상"
4. `pytest.ini:2`: `minversion = 3.11`
5. `docs/installation.rst`: Python 버전 업데이트

#### 5.2. 플레이스홀더가 있는 GitHub URL

**위치**: `pyproject.toml:62-65`

```toml
# 현재:
[project.urls]
Homepage = "https://github.com/yourusername/CTHarvester"
Documentation = "https://github.com/yourusername/CTHarvester/wiki"
Repository = "https://github.com/yourusername/CTHarvester"
Issues = "https://github.com/yourusername/CTHarvester/issues"
```

**다음으로 업데이트**:
```toml
[project.urls]
Homepage = "https://github.com/jikhanjung/CTHarvester"
Documentation = "https://jikhanjung.github.io/CTHarvester"
Repository = "https://github.com/jikhanjung/CTHarvester"
Issues = "https://github.com/jikhanjung/CTHarvester/issues"
```

#### 5.3. README가 잘못된 스크립트 참조

**위치**: `README.md:115-123`

존재하지 않는 `bump_version.py` 참조. 실제 파일은 `manage_version.py`.

**업데이트**:
```bash
# 이전:
python bump_version.py patch

# 이후:
python manage_version.py bump patch
```

**업데이트할 파일**:
1. `README.md` - 모든 `bump_version.py` 참조 업데이트
2. `README.ko.md` - 한국어 버전에서 동일한 업데이트
3. `docs/developer_guide.rst` - 버전 관리 섹션 업데이트

---

### 이슈 6: 테스트 구조 및 마커

**우선순위**: 🟡 높음
**예상 시간**: 2시간
**영향**: 더 나은 테스트 선택, 더 빠른 CI

#### 문제

**현재 상태**:
- 수집된 테스트 486개
- Unit 마커: 0개 테스트 선택됨
- Integration 마커: 9개 테스트 선택됨
- 대부분의 테스트에 마커 없음

**목표**: 선택적 실행을 위해 모든 테스트에 마커 적용

#### 구현 계획

**마커 전략**:
```python
# Unit 테스트 - 빠름, 외부 종속성 없음
@pytest.mark.unit
def test_settings_manager_get():
    ...

# Integration 테스트 - 여러 구성 요소
@pytest.mark.integration
def test_thumbnail_generation_workflow():
    ...

# UI 테스트 - Qt 애플리케이션 필요
@pytest.mark.ui
def test_settings_dialog_save():
    ...

# Slow 테스트 - 장기 실행 (>1초)
@pytest.mark.slow
def test_full_pipeline():
    ...

# 선택적 종속성 필요
@pytest.mark.skipif(not HAS_PYMCUBES, reason="pymcubes not installed")
def test_mesh_generation():
    ...
```

**업데이트할 파일** (31개 테스트 파일):

**Unit 테스트** (`@pytest.mark.unit` 추가):
- `tests/test_settings_manager.py`
- `tests/test_file_utils.py`
- `tests/test_common.py`
- `tests/test_image_utils.py`
- `tests/test_worker.py`
- `tests/test_error_message_builder.py`
- `tests/test_progress_manager.py`
- `tests/test_progress_tracker.py`

**Integration 테스트** (`@pytest.mark.integration` 추가):
- `tests/test_integration_thumbnail.py` ✅ (이미 있음)
- `tests/test_thumbnail_generator.py` - 일부 테스트
- `tests/test_thumbnail_manager.py` - 일부 테스트

**UI 테스트** (`@pytest.mark.ui` 추가):
- `tests/ui/test_dialogs.py`
- `tests/ui/test_interactive_dialogs.py`
- `tests/ui/test_mcube_widget.py`
- `tests/ui/test_object_viewer_2d.py`
- `tests/ui/test_vertical_timeline.py`

**pytest.ini 업데이트**:
```ini
[pytest]
markers =
    unit: Unit 테스트 - 빠름, 격리됨
    integration: Integration 테스트 - 여러 구성 요소
    ui: UI 테스트 - Qt 애플리케이션 필요
    slow: Slow 테스트 - 1초 이상 걸릴 수 있음
```

**CI 업데이트** (`.github/workflows/test.yml`):
```yaml
# 빠른 테스트 (unit만)
- name: Run unit tests
  run: pytest -m unit -v

# Slow를 제외한 모든 테스트
- name: Run integration tests
  run: pytest -m "integration and not slow" -v

# UI 테스트
- name: Run UI tests
  run: pytest -m ui -v
```

---

### 이슈 7: 종속성 관리 통합

**우선순위**: 🟡 높음
**예상 시간**: 1시간
**영향**: 일관된 환경, 더 쉬운 설정

#### 문제

세 파일이 불일치로 종속성을 정의합니다:
- `requirements.txt` - 런타임 종속성
- `requirements-dev.txt` - 개발 종속성
- `pyproject.toml` - 프로젝트 메타데이터 및 빌드 종속성

**불일치 예**:
```
# requirements.txt
maturin>=1.4.0,<2.0.0

# pyproject.toml build-system
maturin>=1.3.0
```

#### 해결 방안

**옵션 A: pyproject.toml을 단일 진실 소스로 사용 (현대적)**
```toml
[project]
dependencies = [
    "PyQt5>=5.15.0",
    "numpy>=1.24.0",
    "Pillow>=10.0.0",
    # ... 모든 런타임 종속성
]

[project.optional-dependencies]
dev = [
    "pytest>=7.4.0",
    "black>=23.0.0",
    "flake8>=6.0.0",
    # ... 모든 개발 종속성
]

rust = [
    "maturin>=1.4.0,<2.0.0",
]
```

**옵션 B: requirements.txt 유지, pyproject.toml에서 생성**
```bash
# 도구 설치
pip install pip-tools

# pyproject.toml에서 requirements.txt 생성
pip-compile pyproject.toml -o requirements.txt
pip-compile --extra dev pyproject.toml -o requirements-dev.txt
```

**권장사항**: 옵션 A (현대적 Python 패키징)

**마이그레이션 경로**:
1. 모든 종속성을 `pyproject.toml`로 이동
2. 하위 호환성을 위해 `requirements.txt` 유지 (pyproject.toml에서 생성)
3. 설치 문서 업데이트

**업데이트할 파일**:
1. `pyproject.toml` - 완전한 종속성 목록 추가
2. `requirements.txt` - 간소화 또는 생성
3. `requirements-dev.txt` - 간소화 또는 생성
4. `README.md` - 설치 지침 업데이트
5. `docs/installation.rst` - 설치 가이드 업데이트

---

## 🟢 중간 우선순위 이슈 (이번 달)

### 이슈 8: main_window.py 리팩토링 계속

**우선순위**: 🟢 중간
**예상 시간**: 4시간
**현재**: 1,225줄 (4,840줄에서 감소 - 이미 96.6% 감소!)

**추출 대상**:

1. **메뉴 및 액션 설정** (200줄) → `ui/setup/menu_setup.py`
2. **툴바 설정** (100줄) → `ui/setup/toolbar_setup.py`
3. **자르기 핸들러** (150줄) → `ui/handlers/crop_handler.py`
4. **볼륨 핸들러** (200줄) → `ui/handlers/volume_handler.py`
5. **이미지 로딩** (100줄) → `ui/handlers/image_handler.py`

**목표**: 800줄 미만으로 감소, 각 핸들러는 300줄 미만

---

### 이슈 9: CI/CD 개선

**우선순위**: 🟢 중간
**예상 시간**: 2시간

#### 9.1. Pre-commit 훅 검증

`.github/workflows/test.yml`에 추가:
```yaml
- name: Verify pre-commit hooks
  run: |
    pip install pre-commit
    pre-commit run --all-files
```

#### 9.2. 문서 빌드 확인

`.github/workflows/test.yml`에 추가:
```yaml
- name: Verify documentation builds
  run: |
    pip install sphinx sphinx-rtd-theme
    cd docs && make html
```

#### 9.3. 코드 커버리지 임계값

`pytest.ini` 업데이트:
```ini
[tool:pytest]
addopts =
    --cov=core
    --cov=ui
    --cov=utils
    --cov-report=html
    --cov-report=term
    --cov-fail-under=90
```

---

### 이슈 10: 보안 개선

**우선순위**: 🟢 중간
**예상 시간**: 3시간

#### 10.1. 보안 테스트 커버리지 증가

**현재**: `security/file_validator.py`가 40.51% 커버리지

**목표**: 90%+ 커버리지

**누락된 테스트**:
- 심볼릭 링크 처리
- 유니코드 경로 처리
- 매우 긴 경로 이름
- 파일 이름의 특수 문자
- 대소문자 구분 엣지 케이스

#### 10.2. 파일 작업 감사

**작업**: 모든 파일 작업이 `FileValidator`를 사용하는지 확인

**감사할 파일**:
- `core/thumbnail_generator.py`
- `ui/handlers/export_handler.py`
- `utils/file_utils.py`
- `core/thumbnail_manager.py`

**확인할 패턴**:
```python
# 나쁨:
with open(user_provided_path) as f:
    ...

# 좋음:
from security.file_validator import FileValidator
validator = FileValidator()
if validator.validate_path(user_provided_path):
    with open(user_provided_path) as f:
        ...
```

---

## 🔵 낮은 우선순위 이슈 (시간이 허락할 때)

### 이슈 11: 코드 품질 개선

**우선순위**: 🔵 낮음
**예상 시간**: 4-6시간

#### 11.1. Print 문을 로깅으로 교체

**발견**: 25개 파일에 322개 print 문

**주요 파일**:
- `ui/main_window.py` (5개 발생)
- `core/thumbnail_manager.py` (1개 발생)
- `core/thumbnail_generator.py` (1개 발생)

**패턴**:
```python
# 이전:
print(f"Processing {count} images")

# 이후:
logger.info(f"Processing {count} images")
```

#### 11.2. 와일드카드 import 교체

**위치**: `ui/widgets/mcube_widget.py:22-23`

```python
# 이전:
from OpenGL.GL import *
from OpenGL.GLU import *

# 이후:
from OpenGL.GL import (
    glClear, glClearColor, glEnable, glDisable,
    glBegin, glEnd, glVertex3f, glColor3f,
    GL_COLOR_BUFFER_BIT, GL_DEPTH_BUFFER_BIT,
    GL_DEPTH_TEST, GL_LIGHTING, GL_LIGHT0,
    # ... 실제로 사용되는 것만
)
```

#### 11.3. 모듈 docstring 추가

다음에 포괄적인 모듈 docstring 추가:
- `config/` 모듈
- `utils/` 모듈
- `security/` 모듈

**템플릿**:
```python
"""모듈 간단한 설명.

모듈 목적 및 내용에 대한 자세한 설명.

예제:
    >>> from module import Class
    >>> obj = Class()
    >>> obj.method()

속성:
    MODULE_CONSTANT: 설명

참고:
    사용법에 대한 추가 참고 사항
"""
```

---

### 이슈 12: 문서 개선

**우선순위**: 🔵 낮음
**예상 시간**: 3시간

#### 12.1. Devlog 색인 생성

**파일**: `devlog/README.md`

```markdown
# 개발 로그 색인

모든 개발 세션의 시간순 색인.

## 최근 세션 (2025년 10월)

- [053](20251001_053_comprehensive_improvement_plan.md) - 포괄적 개선 계획
- [052](20251001_052_python_thumbnail_progress_fix.md) - Python 썸네일 진행 상황 수정
- [051](20251001_051_phase2_python_thumbnail_completion.md) - Phase 2 완료
...

## 주제별

### 아키텍처 & 리팩토링
- 세션 044, 043, 041

### 테스트
- 세션 042, 040, 039

### 문서
- 세션 045, 038
```

#### 12.2. 구성 가이드

**파일**: `docs/configuration.md`

`config/settings.yaml`의 모든 설정을 다음과 함께 문서화:
- 기본값
- 유효한 범위
- 사용 사례
- 예제

#### 12.3. API 문서 배포

1. Sphinx 빌드 작동 확인
2. GitHub Pages 활성화 (이미 워크플로우 있음)
3. README에 문서 링크 업데이트

---

## 구현 일정

### 1주차: 치명적 수정

**1-2일차**:
- ✅ 이슈 1: 썸네일 생성 API 수정
- ✅ 이슈 2: 진행 상황 샘플링 수정
- ✅ 이슈 3: 실패 처리 추가

**3일차**:
- ✅ 이슈 4: 저장소 정리
- ✅ 이슈 5: 문서 수정
- ✅ 포괄적 테스트 작성

**4-5일차**:
- ✅ 이슈 6: 테스트 마커 추가
- ✅ 이슈 7: 종속성 통합
- ✅ 모든 테스트 통과 확인

### 2주차: 높은 우선순위

**1-2일차**:
- 이슈 8: main_window.py 리팩토링 계속
- 2-3개 핸들러 추출

**3-4일차**:
- 이슈 9: CI/CD 개선
- 이슈 10: 보안 개선

**5일차**:
- 테스트 및 검증
- 문서 업데이트

### 1개월차: 중간 우선순위

- 이슈 8 완료 (main_window 리팩토링)
- 이슈 9 완료 (CI/CD)
- 이슈 10 완료 (보안)

### 지속적: 낮은 우선순위

- 이슈 11: 코드 품질 (시간이 허락할 때)
- 이슈 12: 문서 (지속적 개선)

---

## 성공 지표

### 1주차 목표:
- ✅ 모든 치명적 버그 수정
- ✅ 테스트 스위트 100% 통과
- ✅ 저장소 정리
- ✅ 문서 정확성

### 2주차 목표:
- ✅ 테스트 마커 적용 (100% 커버리지)
- ✅ pre-commit 및 문서 확인으로 CI/CD 개선
- ✅ 보안 커버리지 >90%

### 1개월차 목표:
- ✅ main_window.py <800줄
- ✅ 모든 핸들러 <300줄
- ✅ 모든 모듈에서 코드 커버리지 >90%

---

## 위험 완화

### 위험:

1. **중대한 변경**: API 시그니처 변경이 외부 코드를 손상시킬 수 있음
   - 완화: 버전 업 (0.2.3 → 0.3.0), 마이그레이션 문서화

2. **테스트 실패**: 리팩토링이 회귀를 도입할 수 있음
   - 완화: 각 변경 후 전체 테스트 스위트 실행

3. **시간 초과**: 일부 작업이 예상보다 오래 걸릴 수 있음
   - 완화: 치명적 수정을 먼저 우선순위로 지정, 낮은 우선순위 연기

---

## 참고 사항

- 이것은 살아있는 문서입니다 - 작업이 진행됨에 따라 업데이트
- 완료된 항목에 ✅ 표시
- 발견된 대로 새 이슈 추가
- 관련 커밋/PR에 링크

---

## 참고 자료

- 원본 분석: 세션 #053 포괄적 검토
- 최근 커밋: 5425d76, e4e7d57, d2c74d7
- 관련 이슈: GitHub Issues 트래커
- 테스트 커버리지 리포트: `htmlcov/index.html`
