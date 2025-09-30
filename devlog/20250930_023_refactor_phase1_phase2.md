# 리팩토링 Phase 1-2 완료

날짜: 2025-09-30
브랜치: refactor/code-structure
작성자: Code Refactoring

## 개요

CTHarvester의 모듈화를 위한 리팩토링을 시작했습니다.
Phase 1-2를 완료하여 기본 구조를 생성하고 import 경로를 업데이트했습니다.

---

## Phase 1: 모듈 구조 생성 ✅

### 1.1 디렉토리 구조

```
CTHarvester/
├── config/          # 전역 설정 및 상수
│   ├── __init__.py
│   └── constants.py
├── core/            # 핵심 비즈니스 로직 (준비됨)
│   └── __init__.py
├── ui/              # UI 컴포넌트 (준비됨)
│   ├── __init__.py
│   └── widgets/
│       └── __init__.py
├── utils/           # 유틸리티 함수
│   ├── __init__.py
│   ├── image_utils.py
│   └── file_utils.py
└── security/        # 보안 모듈
    ├── __init__.py
    └── file_validator.py (moved from file_security.py)
```

### 1.2 생성된 모듈

#### config/constants.py
전역 상수 정의:
- 애플리케이션 정보 (APP_NAME, PROGRAM_VERSION, COMPANY_NAME)
- 파일 확장자 (SUPPORTED_IMAGE_EXTENSIONS, THUMBNAIL_EXTENSION)
- 썸네일 생성 파라미터 (DEFAULT_THUMBNAIL_MAX_SIZE)
- 스레드 설정 (MIN_THREADS, MAX_THREADS, DEFAULT_THREADS)
- 메모리 설정 (MEMORY_THRESHOLD_MB)
- UI 설정 (DEFAULT_WINDOW_WIDTH, DEFAULT_WINDOW_HEIGHT)
- 3D 렌더링 (DEFAULT_THRESHOLD, DEFAULT_ISO_VALUE)
- 로깅 (LOG_DIR_NAME, DEFAULT_LOG_LEVEL)
- 환경변수 (ENV_LOG_LEVEL, ENV_CONSOLE_LEVEL, ENV_LOG_DIR)

#### utils/image_utils.py
이미지 처리 유틸리티 함수:
- `detect_bit_depth()`: 이미지 비트 깊이 감지 (8/16)
- `load_image_as_array()`: 이미지를 numpy 배열로 로드
- `downsample_image()`: 이미지 다운샘플링 (subsample/average)
- `average_images()`: 두 이미지 평균화 (오버플로우 안전)
- `save_image_from_array()`: numpy 배열을 이미지 파일로 저장
- `get_image_dimensions()`: 이미지 크기 조회 (전체 로드 없이)

#### utils/file_utils.py
파일 시스템 유틸리티 함수:
- `find_image_files()`: 디렉토리에서 이미지 파일 찾기
- `parse_filename()`: 파일명 파싱 (prefix, number, extension)
- `create_thumbnail_directory()`: 썸네일 디렉토리 생성
- `get_thumbnail_path()`: 썸네일 파일 경로 생성
- `clean_old_thumbnails()`: 이전 썸네일 디렉토리 삭제
- `get_directory_size()`: 디렉토리 전체 크기 계산
- `format_file_size()`: 파일 크기를 사람이 읽기 쉬운 형식으로

#### security/file_validator.py
`file_security.py`를 `security/` 모듈로 이동:
- `SecureFileValidator` 클래스
- `FileSecurityError` 예외
- `safe_open_image()` 함수

---

## Phase 2: Import 경로 업데이트 ✅

### 2.1 CTHarvester.py 수정

#### 기존 import
```python
from file_security import SecureFileValidator, FileSecurityError, safe_open_image

COMPANY_NAME = "PaleoBytes"
PROGRAM_NAME = "CTHarvester"
try:
    from version import __version__ as PROGRAM_VERSION
except ImportError:
    PROGRAM_VERSION = "0.2.0"
```

#### 변경 후 import
```python
# Project modules
from security.file_validator import SecureFileValidator, FileSecurityError, safe_open_image
from config.constants import (
    PROGRAM_NAME as CONST_PROGRAM_NAME,
    PROGRAM_VERSION as CONST_PROGRAM_VERSION,
    COMPANY_NAME as CONST_COMPANY_NAME,
    SUPPORTED_IMAGE_EXTENSIONS,
    THUMBNAIL_DIR_NAME,
    DEFAULT_LOG_LEVEL
)

# Use constants from config module
COMPANY_NAME = CONST_COMPANY_NAME
PROGRAM_VERSION = CONST_PROGRAM_VERSION
PROGRAM_NAME = CONST_PROGRAM_NAME
PROGRAM_AUTHOR = "Jikhan Jung"
```

### 2.2 변경 사항
- `file_security` → `security.file_validator`로 import 경로 변경
- 상수 정의를 `config.constants`에서 import
- 기존 변수명 유지하여 하위 호환성 보장

---

## Phase 3-4: 향후 작업 (보류)

### Phase 3: ThumbnailWorker 클래스 추출
**상태**: 보류
**이유**:
- ThumbnailWorker 클래스가 매우 큼 (400+ 줄)
- ThumbnailManager와 밀접하게 연결됨
- 큰 변경이 필요하며, 신중한 테스트 필요

**계획**:
- `core/thumbnail_worker.py` 생성
- `ThumbnailWorker`, `ThumbnailWorkerSignals` 클래스 이동
- CTHarvester.py에서 import

### Phase 4: UI 컴포넌트 분리
**상태**: 보류
**이유**:
- PreferencesDialog, ProgressDialog 등 분리 필요
- 큰 작업이며 Phase 3 완료 후 진행 권장

**계획**:
- `ui/preferences_dialog.py`
- `ui/progress_dialog.py`
- `ui/main_window.py` (일부)

---

## 커밋 내역

### Commit 1: Phase 1
```
refactor: Create modular directory structure (Phase 1)

- config/: Global constants
- utils/: Utility functions (image, file)
- security/: file_validator.py (moved)
- core/, ui/: Prepared for future extraction
```

### Commit 2: Phase 2 (예정)
```
refactor: Update import paths (Phase 2)

- CTHarvester.py: Updated imports to use new modules
- Backward compatible: Kept existing variable names
```

---

## 테스트 권장사항

### 기능 테스트
```bash
# 프로그램 실행
python CTHarvester.py

# 확인 사항:
1. 프로그램이 정상 시작되는지
2. 디렉토리 열기가 작동하는지
3. 썸네일 생성이 작동하는지
4. 3D 뷰가 작동하는지
5. 설정 저장/로드가 작동하는지
```

### Import 테스트
```python
# Python 인터프리터에서
from config.constants import PROGRAM_NAME, PROGRAM_VERSION
from security.file_validator import SecureFileValidator
from utils.image_utils import detect_bit_depth
from utils.file_utils import find_image_files

print(PROGRAM_NAME, PROGRAM_VERSION)
```

---

## 장점

### 1. 코드 구조 개선
- 관심사 분리 (Separation of Concerns)
- 모듈별 책임 명확화
- 재사용성 향상

### 2. 유지보수성 향상
- 기능별로 파일이 나뉘어 코드 찾기 쉬움
- 수정 시 영향 범위 축소
- 테스트 작성 용이

### 3. 확장성
- 새로운 기능 추가 시 적절한 모듈에 배치
- 의존성 관리 명확

### 4. 문서화
- 각 모듈별 docstring 작성
- 함수별 명확한 역할 정의

---

## 단점 및 제약

### 1. Import 경로 길이 증가
```python
# 기존
from file_security import SecureFileValidator

# 변경 후
from security.file_validator import SecureFileValidator
```

### 2. 일부 순환 import 가능성
- config에서 version import
- 주의 필요

### 3. 점진적 리팩토링 필요
- 한 번에 모두 변경하면 위험
- 단계별 테스트 필수

---

## 다음 단계

### 단기 (1주일)
1. **Phase 2 완료 및 테스트**
   - CTHarvester.py 실행 테스트
   - 모든 기능 회귀 테스트
   - 발견된 버그 수정

2. **Phase 2 커밋**
   - 테스트 완료 후 커밋
   - Pull Request 생성 (선택)

### 중기 (2-4주)
1. **Phase 3: ThumbnailWorker 추출**
   - `core/thumbnail_worker.py` 생성
   - 테스트 작성
   - 메모리 사용량 확인

2. **Phase 4: UI 컴포넌트 분리**
   - PreferencesDialog 추출
   - ProgressDialog 추출
   - 다이얼로그별 독립 파일

### 장기 (1-2개월)
1. **전체 리팩토링 완료**
   - CTHarvesterMainWindow 분리
   - ObjectViewer2D, MCubeWidget 분리
   - 테스트 커버리지 70% 이상

2. **main 브랜치 머지**
   - 모든 테스트 통과 후
   - 문서 완성 후
   - 팀 리뷰 후 (해당되는 경우)

---

## 호환성

### 이전 버전과의 호환성
- ✅ 기존 변수명 유지 (PROGRAM_NAME, PROGRAM_VERSION 등)
- ✅ 기존 함수 호출 방식 유지
- ✅ 설정 파일 호환

### 위험 요소
- ⚠️ Python 경로 설정 필요 (프로젝트 루트를 PYTHONPATH에 추가)
- ⚠️ 순환 import 가능성 (config ↔ 다른 모듈)
- ⚠️ 대규모 변경으로 인한 예상치 못한 버그

---

## 성공 기준

| 항목 | 목표 | 현재 상태 |
|------|------|----------|
| 모듈 구조 생성 | 5개 디렉토리 | ✅ 완료 |
| 유틸리티 함수 분리 | 2개 파일 | ✅ 완료 (image, file) |
| 보안 모듈 분리 | 1개 파일 | ✅ 완료 (file_validator) |
| config 모듈 | 1개 파일 | ✅ 완료 (constants) |
| Import 경로 업데이트 | CTHarvester.py | ✅ 완료 |
| ThumbnailWorker 추출 | core/ 모듈 | ⏳ 보류 |
| UI 컴포넌트 분리 | ui/ 모듈 | ⏳ 보류 |
| 테스트 통과 | 회귀 없음 | ⏳ 테스트 필요 |

---

## 참고 자료

- `devlog/20250930_014_important_improvements_plan.md` - 원래 개선 계획
- `devlog/20250930_022_daily_work_summary.md` - 오늘 작업 요약
- Python Packaging Guide: https://packaging.python.org/
- Clean Code in Python: https://realpython.com/python-clean-code/

---

## 결론

Phase 1-2를 성공적으로 완료하여:
- ✅ 모듈 구조 생성 (config, core, ui, utils, security)
- ✅ 유틸리티 함수 분리 (image_utils, file_utils)
- ✅ 보안 모듈 정리 (file_validator)
- ✅ Import 경로 업데이트

**다음**: Phase 2 테스트 후 커밋, Phase 3-4는 별도 작업으로 진행

**브랜치**: `refactor/code-structure`에서 작업 진행 중
**상태**: 진행 중 (Phase 2 완료, 테스트 필요)