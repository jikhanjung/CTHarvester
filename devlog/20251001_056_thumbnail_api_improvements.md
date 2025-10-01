# Thumbnail API 개선 - Rust/Python 통합 및 사용자 설정 존중

**날짜**: 2025-10-01
**세션**: 056
**관련 이슈**: API 일관성 및 사용자 설정 존중

## 개요

ThumbnailGenerator의 두 가지 API 불일치 문제를 발견하고 수정했습니다:
1. Rust 경로와 Python 경로의 반환 형식 불일치
2. 사용자 설정 `sample_size` 무시

## 발견된 문제

### 문제 1: Rust 경로 API 불일치

**위치**: `core/thumbnail_generator.py:195-203`

**문제점**:
```python
def generate(self, directory, settings, threadpool, use_rust_preference=True,
             progress_dialog=None):
    """Generate thumbnails using best available method"""
    use_rust = self.rust_available and use_rust_preference

    if use_rust:
        logger.info("Using Rust-based thumbnail generation")
        return self.generate_rust(directory, None, None)  # ❌ bool 반환
    else:
        logger.info("Using Python-based thumbnail generation")
        return self.generate_python(directory, settings, threadpool, progress_dialog)  # ✅ dict 반환
```

**문제 상세**:
- Rust 경로: `bool` 반환 (True/False)
- Python 경로: `dict` 반환 (`{'success', 'cancelled', 'data', 'error'}`)
- Rust 사용 시 `settings`, `threadpool`, `progress_dialog` 매개변수 완전히 무시
- 진행 상황 업데이트 없음
- 취소 기능 작동 안 함
- 향후 코드가 통합 API에 의존하면 조용히 실패

**영향**:
- 사용자가 Rust 모듈 사용 시 진행률 표시 안 됨
- 취소 버튼 작동 안 함
- 호출 코드가 반환 형식 확인 필요 (isinstance check)
- API 일관성 부족으로 유지보수 어려움

---

### 문제 2: 사용자 설정 sample_size 무시

**위치**: `core/thumbnail_generator.py:397-404` (이전 줄 번호)

**문제점**:
```python
# Initialize variables for multi-stage sampling
base_sample = max(20, min(30, int(total_work * 0.02)))  # ❌ 하드코딩
sample_size = base_sample
total_sample = base_sample * 3

logger.info(f"Multi-stage sampling: {base_sample} images per stage")
```

**문제 상세**:
- 항상 자동 계산: `total_work * 0.02`, 20-30 범위로 클램핑
- `config/settings.yaml`의 `thumbnails.sample_size` 완전히 무시
- 사용자가 ETA 정확도 조정 불가
- 문서화된 설정 옵션이 실제로 작동 안 함

**영향**:
- 대용량 데이터셋: 샘플이 너무 작아 부정확한 ETA
- 소용량 데이터셋: 샘플이 불필요하게 많아 오버헤드
- 사용자 설정 무시로 신뢰성 저하

---

## 해결 방안

### 해결 1: Rust 경로 통합 API 적용

**변경 내용**:

1. **progress_dialog에서 callback 생성**:
```python
if use_rust:
    logger.info("Using Rust-based thumbnail generation")
    # Create progress callback from progress_dialog
    progress_callback = None
    cancel_check = None

    if progress_dialog:
        def progress_callback(percentage):
            """Update progress dialog with percentage"""
            progress_dialog.lbl_text.setText(f"Generating thumbnails: {percentage:.1f}%")
            progress_dialog.pb_progress.setValue(int(percentage))
            progress_dialog.update()
            QApplication.processEvents()

        def cancel_check():
            """Check if user cancelled via progress dialog"""
            return progress_dialog.was_cancelled if hasattr(progress_dialog, 'was_cancelled') else False
```

2. **Rust 호출 및 결과 변환**:
```python
    # Use unified return format
    rust_success = self.generate_rust(directory, progress_callback, cancel_check)

    # Convert legacy bool to unified dict format
    if rust_success:
        return {
            'success': True,
            'cancelled': False,
            'data': None,  # Rust doesn't return thumbnail data
            'error': None
        }
    else:
        # Check if it was cancelled or failed
        cancelled = cancel_check() if cancel_check else False
        return {
            'success': False,
            'cancelled': cancelled,
            'data': None,
            'error': 'Rust thumbnail generation failed' if not cancelled else None
        }
```

3. **필요한 import 추가**:
```python
from PyQt5.QtWidgets import QApplication
```

**개선 효과**:
- ✅ Rust/Python 경로 모두 동일한 dict 형식 반환
- ✅ 진행 상황 업데이트 작동 (progress_dialog 통합)
- ✅ 취소 기능 정상 작동
- ✅ 미래 코드에서 일관된 API 사용 가능
- ✅ 호출 코드에서 타입 체크 불필요

---

### 해결 2: 사용자 설정 sample_size 존중

**변경 내용**:

```python
# Initialize variables for multi-stage sampling
# Read sample_size from settings, with fallback calculation if not configured
user_sample_size = None
if settings and isinstance(settings, dict):
    # Try to get sample_size from settings dict
    user_sample_size = settings.get('sample_size')

if user_sample_size is not None:
    # User has configured sample_size in settings
    base_sample = max(1, min(100, int(user_sample_size)))  # Clamp to reasonable range
    logger.info(f"Using user-configured sample_size: {base_sample}")
else:
    # Fallback: auto-calculate based on total work
    base_sample = max(20, min(30, int(total_work * 0.02)))
    logger.info(f"Auto-calculated sample_size: {base_sample} (2% of {total_work} work)")

sample_size = base_sample
total_sample = base_sample * 3
```

**로직**:
1. `settings` dict에서 `sample_size` 읽기
2. 값이 있으면 사용 (1-100 범위로 클램핑)
3. 없으면 기존 자동 계산 로직 사용
4. 로그에 어떤 값 사용했는지 명시

**안전장치**:
- `isinstance(settings, dict)` 체크로 None 방지
- `max(1, min(100, ...))` 로 1-100 범위 강제
- 자동 계산 로직 유지로 하위 호환성 보장

**개선 효과**:
- ✅ 사용자 설정 `thumbnails.sample_size` 존중
- ✅ 설정 없으면 자동 계산 (기존 동작 유지)
- ✅ 1-100 범위로 안전하게 제한
- ✅ 로그에서 설정 출처 추적 가능
- ✅ 대용량/소용량 데이터셋 맞춤 최적화 가능

---

## 기술적 세부사항

### 통합 API 형식

**반환 딕셔너리 구조**:
```python
{
    'success': bool,      # 생성 성공 여부
    'cancelled': bool,    # 사용자가 취소했는지
    'data': dict | None,  # 썸네일 데이터 (Python만, Rust는 None)
    'error': str | None   # 오류 메시지 (실패 시)
}
```

**케이스별 반환값**:

| 상황 | success | cancelled | data | error |
|-----|---------|-----------|------|-------|
| 성공 (Python) | True | False | {...} | None |
| 성공 (Rust) | True | False | None | None |
| 사용자 취소 | False | True | None | None |
| 실패 | False | False | None | "error message" |

### settings 딕셔너리 구조

**main_window.py에서 전달**:
```python
result = self.thumbnail_generator.generate_python(
    directory=self.edtDirname.text(),
    settings=self.settings_hash,  # dict 형식
    threadpool=self.threadpool,
    progress_dialog=self.progress_dialog
)
```

**settings_hash 예시**:
```python
{
    'sample_size': 50,      # thumbnails.sample_size
    'max_size': 500,        # thumbnails.max_size
    'compression': True,    # thumbnails.compression
    'format': 'tif',        # thumbnails.format
    # ... 기타 설정
}
```

### 코드 변경 통계

```
core/thumbnail_generator.py
- 라인 추가: 52
- 라인 삭제: 4
- 순 증가: +48 라인
```

**변경 위치**:
1. Import 섹션 (QApplication 추가)
2. `generate()` 메서드 - Rust 경로 (195-235줄)
3. `generate_python()` 메서드 - sample_size 로직 (431-449줄)

---

## 테스트 결과

### ThumbnailGenerator 테스트
```bash
pytest tests/test_thumbnail_generator.py -v
```

**결과**: 18/18 통과 ✅

**주요 테스트**:
- `test_initialization`: 초기화 정상
- `test_calculate_total_thumbnail_work_*`: 작업량 계산 정확
- `test_generate_method_routing`: Rust/Python 라우팅 정상
- `test_full_workflow_python`: Python 경로 end-to-end
- `test_full_workflow_rust`: Rust 경로 end-to-end

### 전체 테스트 스위트
```bash
pytest tests/ -v --tb=no -q
```

**결과**: 485 passed, 1 skipped, 1 warning ✅

**실행 시간**: 8.87초

---

## Before/After 비교

### Rust 경로 사용 시

#### Before (문제 상황)
```python
# 호출
result = generator.generate(
    directory="/path/to/images",
    settings={'sample_size': 50},
    threadpool=pool,
    progress_dialog=dialog
)

# 반환값
result = True  # ❌ bool 타입

# 문제점
- progress_dialog 무시 → 진행률 표시 안 됨
- settings 무시 → 설정 적용 안 됨
- 취소 불가
- dict 형식 기대하는 코드는 에러
```

#### After (해결 상황)
```python
# 호출
result = generator.generate(
    directory="/path/to/images",
    settings={'sample_size': 50},
    threadpool=pool,
    progress_dialog=dialog
)

# 반환값
result = {
    'success': True,
    'cancelled': False,
    'data': None,
    'error': None
}  # ✅ 통합 dict 형식

# 개선점
- progress_dialog 사용 → 진행률 표시됨
- 취소 버튼 작동
- Python 경로와 동일한 형식
- 일관된 에러 처리 가능
```

---

### sample_size 설정 시

#### Before (문제 상황)
```yaml
# config/settings.yaml
thumbnails:
  sample_size: 50  # ❌ 무시됨
```

```python
# 로그
INFO: Auto-calculated sample_size: 25 (2% of 1250 work)
# 50을 설정했지만 25 사용됨
```

#### After (해결 상황)
```yaml
# config/settings.yaml
thumbnails:
  sample_size: 50  # ✅ 존중됨
```

```python
# 로그
INFO: Using user-configured sample_size: 50
# 설정한 대로 50 사용됨
```

---

## 사용 예시

### 예시 1: Rust 모듈 사용 (진행률 표시)

```python
generator = ThumbnailGenerator()

# Rust 사용 가능하고 선호
result = generator.generate(
    directory="/data/ct_scans",
    settings={'sample_size': 30},
    threadpool=QThreadPool.globalInstance(),
    use_rust_preference=True,
    progress_dialog=progress_dialog  # ✅ 이제 작동함
)

# 통합 형식으로 결과 처리
if result['success']:
    print("✅ 썸네일 생성 완료")
elif result['cancelled']:
    print("⏸️ 사용자가 취소함")
else:
    print(f"❌ 오류: {result['error']}")
```

### 예시 2: 사용자 설정 sample_size 사용

```python
# 대용량 데이터셋 - 많은 샘플로 정확한 ETA
settings = {
    'sample_size': 100,  # ✅ 100개 이미지 샘플링
    'max_size': 256,
    'compression': True
}

result = generator.generate_python(
    directory="/data/large_dataset",  # 5000+ images
    settings=settings,
    threadpool=pool,
    progress_dialog=dialog
)
# 로그: "Using user-configured sample_size: 100"
```

```python
# 소용량 데이터셋 - 적은 샘플로 빠른 시작
settings = {
    'sample_size': 10,  # ✅ 10개 이미지만 샘플링
    'max_size': 512
}

result = generator.generate_python(
    directory="/data/small_dataset",  # ~100 images
    settings=settings,
    threadpool=pool,
    progress_dialog=dialog
)
# 로그: "Using user-configured sample_size: 10"
```

### 예시 3: 설정 없이 자동 계산

```python
# settings에 sample_size 없음
settings = {
    'max_size': 500,
    'compression': True
}

result = generator.generate_python(
    directory="/data/ct_scans",
    settings=settings,  # sample_size 없음
    threadpool=pool,
    progress_dialog=dialog
)
# 로그: "Auto-calculated sample_size: 25 (2% of 1250 work)"
# ✅ 기존 동작 유지
```

---

## 영향 및 이점

### 코드 품질
- ✅ API 일관성 향상
- ✅ 타입 안정성 개선 (단일 반환 형식)
- ✅ 에러 처리 통일
- ✅ 문서화된 설정 실제 작동

### 사용자 경험
- ✅ Rust 사용 시에도 진행률 표시
- ✅ 취소 버튼 모든 경로에서 작동
- ✅ 사용자 설정 존중 (예측 가능한 동작)
- ✅ 대용량/소용량 데이터셋 맞춤 조정 가능

### 유지보수성
- ✅ 호출 코드에서 타입 체크 불필요
- ✅ 향후 기능 추가 시 일관된 패턴
- ✅ 로그에서 설정 출처 추적 용이
- ✅ 테스트 작성 더 쉬움

---

## 향후 개선 가능성

### 1. 타입 힌팅 추가
```python
from typing import TypedDict, Optional

class ThumbnailResult(TypedDict):
    success: bool
    cancelled: bool
    data: Optional[dict]
    error: Optional[str]

def generate(...) -> ThumbnailResult:
    ...
```

### 2. Rust 경로에서도 thumbnail_array 반환
현재 Rust는 파일만 생성하고 `data: None` 반환. 메모리에 로드하여 Python 경로와 완전히 동일하게 만들 수 있음.

### 3. SettingsManager 직접 사용
현재는 dict로 전달받지만, SettingsManager 객체를 직접 주입하면 더 타입 안전:
```python
def generate_python(self, directory, settings: SettingsManager, ...):
    sample_size = settings.get('thumbnails.sample_size', 20)
```

### 4. Progress 콜백 표준화
현재 Rust/Python이 다른 progress 인터페이스 사용. 표준 Progress 프로토콜 정의 가능.

---

## 교훈

### API 설계
- **일관성이 핵심**: 같은 기능은 같은 인터페이스로
- **레거시 호환성**: 기존 동작 유지하면서 개선
- **명시적 로깅**: 어떤 경로/설정 사용하는지 명확히

### 설정 관리
- **사용자 설정 존중**: 문서화된 옵션은 실제 작동해야
- **합리적 기본값**: 설정 없어도 잘 작동해야
- **안전 장치**: 극단적 값 방지 (1-100 클램핑)

### 점진적 개선
- **기존 코드 깨지 않기**: Python 경로 그대로, Rust 경로만 개선
- **테스트로 검증**: 485개 테스트 모두 통과 확인
- **로그로 추적**: 변경 사항 관찰 가능하게

---

## 관련 문서

- [053_comprehensive_improvement_plan.md](20251001_053_comprehensive_improvement_plan.md) - 원래 계획
- [055_comprehensive_plan_implementation.md](20251001_055_comprehensive_plan_implementation.md) - 구현 보고서
- [docs/configuration.md](../docs/configuration.md) - 설정 가이드
- [core/thumbnail_generator.py](../core/thumbnail_generator.py) - 수정된 소스

---

**작성자**: Claude Code
**날짜**: 2025-10-01
**세션**: 056
**커밋**: 7e44d3f
