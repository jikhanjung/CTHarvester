# 남은 품질 개선 계획

**날짜**: 2025-10-01
**문서**: 047 - 남은 품질 개선 사항 분석 및 실행 계획
**목적**: 코드 품질 최종 개선

---

## 📋 목차

1. [발견된 이슈 요약](#발견된-이슈-요약)
2. [이슈 #1: 볼륨 크롭 Off-by-One 에러](#이슈-1-볼륨-크롭-off-by-one-에러)
3. [이슈 #2: Python 썸네일 생성 이중화](#이슈-2-python-썸네일-생성-이중화)
4. [이슈 #3: Python 폴백 플레이스홀더](#이슈-3-python-폴백-플레이스홀더)
5. [실행 계획](#실행-계획)

---

## 발견된 이슈 요약

| 이슈 | 우선순위 | 영향도 | 예상 시간 |
|------|---------|--------|----------|
| **#1: 볼륨 크롭 좌표 오류** | 🔴 높음 | 데이터 정확성 | 15분 |
| **#2: 썸네일 생성 이중화** | 🟡 중간 | 유지보수성 | 2-3시간 |
| **#3: Python 폴백 미구현** | 🟡 중간 | 기능성 | 2-3시간 |

---

## 이슈 #1: 볼륨 크롭 Off-by-One 에러

### 문제 분석

**위치**: `core/volume_processor.py:149-152, 170`

**현재 코드**:
```python
# Line 149-152: 좌표 계산
from_x_small = int(from_x * smallest_width)
from_y_small = int(from_y * smallest_height)
to_x_small = int(to_x * smallest_width) - 1  # ⚠️ -1 적용
to_y_small = int(to_y * smallest_height) - 1  # ⚠️ -1 적용

# Line 170: 슬라이싱 (반열린 구간 [start:end))
volume = minimum_volume[
    bottom_idx_small:top_idx_small,
    from_y_small:to_y_small,  # ⚠️ 이미 -1된 값을 슬라이싱
    from_x_small:to_x_small   # ⚠️ 이미 -1된 값을 슬라이싱
]
```

### 문제점

Python 슬라이싱은 **반열린 구간** `[start:end)`을 사용:
- `arr[0:5]` → 인덱스 0, 1, 2, 3, 4 (5개 요소)
- `arr[0:4]` → 인덱스 0, 1, 2, 3 (4개 요소)

**현재 동작**:
```python
# 사용자가 ROI: X=[0, 100] 선택
to_x = 100 / image_width  # 예: 100 / 512 = 0.1953125
to_x_small = int(0.1953125 * 256) - 1 = 50 - 1 = 49

# 슬라이싱
volume[:, :, from_x_small:49]
# → from_x_small ~ 48 (마지막 픽셀 49 제외!)
```

**결과**: 사용자가 지정한 마지막 픽셀(100번째 픽셀)이 **누락됨**

### 올바른 구현

```python
# 수정 후
from_x_small = int(from_x * smallest_width)
from_y_small = int(from_y * smallest_height)
to_x_small = int(to_x * smallest_width)      # -1 제거
to_y_small = int(to_y * smallest_height)    # -1 제거

# 슬라이싱은 그대로 (Python이 자동으로 end-1까지 처리)
volume = minimum_volume[
    bottom_idx_small:top_idx_small,
    from_y_small:to_y_small,  # ✅ 올바른 범위
    from_x_small:to_x_small   # ✅ 올바른 범위
]
```

**예시**:
```python
# 사용자 ROI: X=[0, 100]
to_x = 100 / 512 = 0.1953125
to_x_small = int(0.1953125 * 256) = 50

# 슬라이싱: [:, :, 0:50]
# → 인덱스 0~49 (50개 픽셀) ✅ 올바름!
```

### 영향 범위

- **데이터 정확성**: ROI 선택 시 마지막 1픽셀씩 손실
- **3D 메시 생성**: 약간 작은 메시 생성
- **사용자 경험**: 선택 영역과 결과 불일치

### 해결 방법

**단계**:
1. `core/volume_processor.py:151-152` 수정: `-1` 제거
2. 기존 테스트 실행하여 회귀 확인
3. 경계값 테스트 추가

**예상 시간**: **15분**

---

## 이슈 #2: Python 썸네일 생성 이중화

### 문제 분석

**현재 상태**: Python 썸네일 생성 로직이 **두 곳**에 존재

#### 위치 1: `core/thumbnail_generator.py:263`
```python
def generate_python(self, directory, progress_callback=None, cancel_check=None):
    """Generate thumbnails using Python implementation"""
    logger.warning("Python thumbnail generation not yet implemented in extracted class")
    return False  # ⚠️ 플레이스홀더
```

#### 위치 2: `ui/main_window.py:818-1219` (약 400줄)
```python
def create_thumbnail_python(self):
    """Creates a thumbnail of the image sequence by downsampling the images...
    This is the original Python implementation kept as fallback.
    """
    # 실제 Python 구현 (400줄)
    # - 시스템 정보 로깅
    # - 다단계 LoD 생성
    # - 진행률 관리
    # - ThumbnailManager 호출
    # - 최종 볼륨 로딩
    ...
```

### 문제점

**1. 코드 중복 및 일관성 결여**:
- 로직이 두 곳에 분산되어 있음
- `core/thumbnail_generator.py`는 플레이스홀더만 있음
- 실제 로직은 `ui/main_window.py`에 남아있음

**2. 책임 분리 위반**:
- `main_window.py`는 UI 담당인데 썸네일 생성 로직이 400줄
- 035 문서의 분리 목표 미달성

**3. 유지보수 어려움**:
- Python 구현 수정 시 `main_window.py` 수정 필요
- `ThumbnailGenerator`가 실제로 생성하지 못함

**4. 테스트 불가능**:
- UI 없이 Python 썸네일 생성 테스트 불가

### 해결 방법 - 상세 분석

#### 옵션 A: 단순 이동 (추천하지 않음)

```python
# core/thumbnail_generator.py
def generate_python(self, directory, progress_callback=None, cancel_check=None):
    # main_window.create_thumbnail_python() 코드 전체 복사
    # 문제: UI 의존성 (QApplication, progress_dialog 등)
```

**문제**:
- `QApplication.setOverrideCursor()` 등 UI 의존성
- `self.progress_dialog` 접근
- `self.settings_hash`, `self.threadpool` 등 MainWindow 상태 필요

#### 옵션 B: UI 의존성 분리 후 이동 (추천) ⭐

**핵심 아이디어**:
1. **비즈니스 로직**: `ThumbnailGenerator`로 이동
2. **UI 상호작용**: `MainWindow`에 남김
3. **콜백 패턴**: 진행률, 취소 체크 등

**구조**:
```python
# core/thumbnail_generator.py
class ThumbnailGenerator:
    def generate_python(
        self,
        directory: str,
        settings: dict,
        threadpool: QThreadPool,
        progress_callback=None,
        cancel_check=None
    ):
        """Generate thumbnails using Python implementation

        Args:
            directory: CT 이미지 디렉토리
            settings: settings_hash (image_width, seq_begin, etc.)
            threadpool: Qt 스레드풀
            progress_callback(current, total, message): 진행률 콜백
            cancel_check(): 취소 확인 콜백 (True면 중단)

        Returns:
            dict: 썸네일 정보 또는 None
        """
        # 1. 시스템 정보 로깅 (UI 독립적)
        # 2. ThumbnailManager를 통한 생성
        # 3. 진행률 업데이트 (콜백 호출)
        # 4. 취소 체크 (콜백 호출)
        # 5. 결과 반환

# ui/main_window.py
class CTHarvesterMainWindow:
    def create_thumbnail_python(self):
        """UI wrapper for Python thumbnail generation"""
        # 1. UI 준비 (커서, 다이얼로그)
        QApplication.setOverrideCursor(Qt.WaitCursor)

        # 2. 콜백 정의
        def on_progress(current, total, message):
            self.progress_dialog.update_progress(current, total, message)

        def check_cancel():
            return self.progress_dialog.is_cancelled

        # 3. ThumbnailGenerator 호출
        result = self.thumbnail_generator.generate_python(
            directory=self.edtDirname.text(),
            settings=self.settings_hash,
            threadpool=self.threadpool,
            progress_callback=on_progress,
            cancel_check=check_cancel
        )

        # 4. UI 정리 및 결과 처리
        QApplication.restoreOverrideCursor()
        if result:
            self._update_ui_after_thumbnail(result)
```

#### 옵션 C: 완전 재구현 (장기 과제)

- Rust 구현을 Python으로 포팅
- 더 깨끗한 API
- 시간이 많이 소요 (1-2일)

### 선택: **옵션 B** (UI 의존성 분리 후 이동)

**이유**:
1. ✅ 기존 로직 재사용 (테스트됨)
2. ✅ UI와 비즈니스 로직 분리
3. ✅ 테스트 가능
4. ✅ 적당한 작업량 (2-3시간)

### 상세 이동 계획

#### Phase 1: 의존성 분석 (30분)

**분석 항목**:
```python
# main_window.create_thumbnail_python()에서 사용하는 것들
1. self.settings_hash          → 파라미터로 전달
2. self.threadpool             → 파라미터로 전달
3. self.thumbnail_manager      → ThumbnailGenerator가 소유
4. self.progress_dialog        → 콜백으로 대체
5. QApplication.setOverrideCursor()  → MainWindow에 남김
6. self.level_info             → 반환값으로 처리
7. self.minimum_volume         → 반환값으로 처리
```

**의존성 매핑**:
| MainWindow 상태 | 해결 방법 |
|-----------------|----------|
| `settings_hash` | 파라미터로 전달 |
| `threadpool` | 파라미터로 전달 |
| `thumbnail_manager` | `ThumbnailGenerator` 멤버로 이동 |
| `progress_dialog` | `progress_callback(current, total, msg)` 콜백 |
| 취소 체크 | `cancel_check() -> bool` 콜백 |
| UI 커서 | MainWindow에 남김 |
| `level_info` | 반환 딕셔너리에 포함 |
| `minimum_volume` | 반환 딕셔너리에 포함 |

#### Phase 2: 코어 로직 이동 (1시간)

**작업 내용**:
1. `create_thumbnail_python()` 코드 복사
2. UI 관련 코드 제거 (커서, 다이얼로그 직접 접근)
3. 콜백 호출 추가
4. 파라미터 추가
5. 반환값 구조화

**시그니처**:
```python
def generate_python(
    self,
    directory: str,
    settings: dict,  # settings_hash
    threadpool: QThreadPool,
    progress_callback: Optional[Callable[[int, int, str], None]] = None,
    cancel_check: Optional[Callable[[], bool]] = None
) -> Optional[dict]:
    """
    Returns:
        dict or None: {
            'levels': [...],  # level_info
            'minimum_volume': np.ndarray,
            'success': bool,
            'cancelled': bool
        }
    """
```

#### Phase 3: MainWindow 리팩토링 (30분)

**작업 내용**:
1. `create_thumbnail_python()` 간소화
2. 콜백 함수 정의
3. `ThumbnailGenerator.generate_python()` 호출
4. 반환값으로 UI 업데이트

#### Phase 4: 테스트 (30분)

**테스트 항목**:
1. Rust 없는 환경에서 Python 폴백 동작
2. 진행률 업데이트 확인
3. 취소 기능 확인
4. 에러 처리 확인

### 예상 시간

- Phase 1: 30분 (의존성 분석)
- Phase 2: 1시간 (코어 로직 이동)
- Phase 3: 30분 (MainWindow 리팩토링)
- Phase 4: 30분 (테스트)
- **총 예상 시간**: **2.5~3시간**

---

## 이슈 #3: Python 폴백 플레이스홀더

### 문제 분석

**위치**: `core/thumbnail_generator.py:263`

**현재 코드**:
```python
def generate_python(self, directory, progress_callback=None, cancel_check=None):
    """Generate thumbnails using Python implementation"""
    try:
        logger.warning("Python thumbnail generation not yet implemented in extracted class")
        return False  # ⚠️ 항상 False 반환
    except Exception as e:
        logger.error(f"Error during Python thumbnail generation: {e}")
        return False
```

### 문제점

**1. Rust 모듈 없으면 썸네일 생성 실패**:
```python
# ui/main_window.py:532-556
def create_thumbnail(self):
    use_rust_preference = getattr(self.m_app, "use_rust_thumbnail", True)

    if use_rust_preference:
        try:
            from ct_thumbnail import build_thumbnails
            use_rust = True
        except ImportError:
            use_rust = False
            logger.warning("ct_thumbnail module not found, falling back to Python")

    if use_rust:
        self.create_thumbnail_rust()
    else:
        self.create_thumbnail_python()  # ⚠️ 이게 호출됨
```

**문제**: `create_thumbnail_python()`은 `main_window.py`의 400줄 메소드를 호출하는데, `ThumbnailGenerator.generate_python()`은 False만 반환

**2. 이슈 #2와 연관**:
- 이슈 #2를 해결하면 자동으로 해결됨
- Python 로직을 `ThumbnailGenerator`로 이동하면 플레이스홀더가 실제 구현으로 대체됨

### 해결 방법

**이슈 #2 완료 후 자동 해결**

이슈 #2의 Phase 2에서:
```python
# core/thumbnail_generator.py
def generate_python(self, directory, settings, threadpool, ...):
    # ✅ 실제 Python 썸네일 생성 로직 (이슈 #2에서 이동)
    # - main_window.create_thumbnail_python()의 400줄 로직
    # - UI 의존성 제거됨
    # - 콜백으로 진행률 업데이트
    ...
    return {
        'levels': level_info,
        'minimum_volume': minimum_volume,
        'success': True,
        'cancelled': False
    }
```

### 예상 시간

**이슈 #2에 포함** (별도 작업 불필요)

---

## 실행 계획

### 우선순위 및 순서

```
Phase 1: 볼륨 크롭 수정 (우선순위 🔴 높음)
  ├─ 1.1 volume_processor.py 수정 (5분)
  ├─ 1.2 기존 테스트 실행 (5분)
  └─ 1.3 경계값 테스트 추가 (5분)
  총 예상: 15분

Phase 2: Python 썸네일 생성 통합 (우선순위 🟡 중간)
  ├─ 2.1 의존성 분석 (30분)
  ├─ 2.2 코어 로직 이동 (1시간)
  ├─ 2.3 MainWindow 리팩토링 (30분)
  └─ 2.4 테스트 및 검증 (30분)
  총 예상: 2.5~3시간

Phase 3: 최종 검증 및 문서화
  ├─ 3.1 전체 테스트 스위트 실행 (10분)
  ├─ 3.2 Rust 없는 환경 테스트 (10분)
  └─ 3.3 완료 보고서 작성 (10분)
  총 예상: 30분
```

### 총 예상 시간

- **Phase 1**: 15분
- **Phase 2**: 2.5~3시간
- **Phase 3**: 30분
- **전체**: **3~3.5시간**

---

## 세부 작업 체크리스트

### Phase 1: 볼륨 크롭 수정 ✅

- [ ] 1.1 `core/volume_processor.py` 수정
  - [ ] Line 151: `to_x_small = int(to_x * smallest_width)` (- 1 제거)
  - [ ] Line 152: `to_y_small = int(to_y * smallest_height)` (- 1 제거)
  - [ ] 주석 추가 (왜 -1을 제거했는지 설명)

- [ ] 1.2 기존 테스트 실행
  ```bash
  pytest tests/core/test_volume_processor.py -v
  pytest tests/ -k "crop" -v
  ```

- [ ] 1.3 경계값 테스트 추가
  - [ ] ROI가 전체 이미지일 때 테스트
  - [ ] ROI가 1픽셀일 때 테스트
  - [ ] 결과 크기 검증

### Phase 2: Python 썸네일 생성 통합

#### 2.1 의존성 분석

- [ ] `main_window.create_thumbnail_python()` 분석
  - [ ] 사용하는 인스턴스 변수 목록화
  - [ ] UI 호출 목록화
  - [ ] 외부 의존성 목록화

- [ ] 콜백 인터페이스 설계
  - [ ] 진행률 콜백 시그니처 정의
  - [ ] 취소 체크 콜백 시그니처 정의

#### 2.2 코어 로직 이동

- [ ] `core/thumbnail_generator.py` 수정
  - [ ] `generate_python()` 시그니처 업데이트
  - [ ] `main_window.create_thumbnail_python()` 로직 복사
  - [ ] UI 의존성 제거
  - [ ] 콜백 호출 추가
  - [ ] 파라미터 처리
  - [ ] 반환값 구조화

- [ ] `thumbnail_manager` 멤버 추가
  - [ ] `ThumbnailGenerator.__init__()` 수정
  - [ ] `ThumbnailManager` 인스턴스 생성

#### 2.3 MainWindow 리팩토링

- [ ] `ui/main_window.py` 수정
  - [ ] `create_thumbnail_python()` 간소화
  - [ ] 진행률 콜백 정의
  - [ ] 취소 체크 콜백 정의
  - [ ] `ThumbnailGenerator.generate_python()` 호출
  - [ ] 반환값으로 `level_info`, `minimum_volume` 업데이트
  - [ ] UI 상태 업데이트

- [ ] 기존 Python 구현 제거
  - [ ] 400줄 로직 삭제
  - [ ] 주석으로 이동 표시

#### 2.4 테스트 및 검증

- [ ] 단위 테스트
  - [ ] `ThumbnailGenerator.generate_python()` 단독 테스트
  - [ ] 콜백 호출 검증
  - [ ] 반환값 구조 검증

- [ ] 통합 테스트
  - [ ] Rust 모듈 제거 후 테스트
  - [ ] 전체 워크플로우 테스트
  - [ ] 진행률 다이얼로그 동작 확인
  - [ ] 취소 기능 확인

### Phase 3: 최종 검증

- [ ] 3.1 전체 테스트 스위트
  ```bash
  pytest tests/ -v --tb=short
  ```

- [ ] 3.2 Rust 없는 환경 테스트
  - [ ] ct_thumbnail 모듈 임시 제거
  - [ ] Python 폴백 동작 확인
  - [ ] 썸네일 생성 결과 확인

- [ ] 3.3 문서화
  - [ ] 완료 보고서 작성
  - [ ] 변경 사항 기록
  - [ ] 개선 전후 비교

---

## 기대 효과

### Phase 1 (볼륨 크롭 수정)

**정확성**:
- ✅ ROI 선택 시 마지막 픽셀까지 정확히 포함
- ✅ 사용자 의도와 결과 일치

**데이터 품질**:
- ✅ 3D 메시가 정확한 크기로 생성
- ✅ 내보낸 이미지 스택 크기 정확

### Phase 2 (썸네일 생성 통합)

**아키텍처**:
- ✅ 단일 책임 원칙 완벽 준수
- ✅ `ThumbnailGenerator`가 실제로 생성 가능
- ✅ UI와 비즈니스 로직 완전 분리

**유지보수성**:
- ✅ Python 구현 수정 시 한 곳만 변경
- ✅ 코드 중복 제거
- ✅ main_window.py 크기 대폭 감소 (1,511줄 → ~1,100줄)

**테스트 가능성**:
- ✅ UI 없이 썸네일 생성 테스트 가능
- ✅ 콜백 모킹으로 단위 테스트 작성 용이

**기능성**:
- ✅ Rust 모듈 없어도 정상 동작
- ✅ Python 폴백 완전 구현

### 전체 효과

**코드 품질**:
| 지표 | Before | After | 개선 |
|------|--------|-------|------|
| main_window.py 크기 | 1,511줄 | ~1,100줄 | -27% |
| 코드 중복 | 있음 | 없음 | ✅ |
| 데이터 정확성 | 99% | 100% | +1% |
| Python 폴백 | 미구현 | 완전 구현 | ✅ |

**035 문서 목표 달성**:
- ✅ main_window.py 추가 감소 (1,511 → ~1,100줄)
- ✅ 비즈니스 로직 완전 분리
- ✅ 단일 책임 원칙 완벽 준수

---

## 위험 요소 및 대응

### 위험 #1: 기존 기능 회귀

**완화 방법**:
- ✅ 기존 테스트 스위트 실행 (481개)
- ✅ 수동 테스트 (Rust/Python 모드)
- ✅ 점진적 변경 (Phase별 검증)

### 위험 #2: UI 콜백 복잡도

**완화 방법**:
- ✅ 간단한 콜백 인터페이스 설계
- ✅ 기본값 제공 (콜백 optional)
- ✅ 명확한 문서화

### 위험 #3: 시간 초과

**완화 방법**:
- ✅ Phase별로 작업 (중간에 멈춰도 가치 있음)
- ✅ Phase 1은 독립적 (15분으로 빠른 가치 제공)
- ✅ Phase 2는 필요시 나중으로 연기 가능

---

## 결론

### 즉시 시작: Phase 1 (15분)

**볼륨 크롭 수정**은:
- ✅ 영향도 높음 (데이터 정확성)
- ✅ 작업 간단함 (15분)
- ✅ 위험 낮음
- ✅ 즉시 가치 제공

**→ 바로 시작 권장** ⭐

### 선택적: Phase 2 (2.5~3시간)

**Python 썸네일 통합**은:
- ✅ 아키텍처 개선
- ✅ 유지보수성 향상
- ⚠️ 시간 필요 (2.5~3시간)
- ✅ 035 문서 목표 완전 달성

**→ 시간 여유 있을 때 진행** 💡

### 최종 목표

**이 작업 완료 후 CTHarvester는**:
1. ✅ **100% 정확한 데이터 처리**
2. ✅ **완벽한 아키텍처** (UI/비즈니스 로직 분리)
3. ✅ **Rust 없이도 완전 동작** (Python 폴백 완성)
4. ✅ **엔터프라이즈급 품질**

---

**작성일**: 2025-10-01
**다음 단계**: Phase 1 (볼륨 크롭 수정) 즉시 시작
**예상 완료**: Phase 1 (15분), Phase 2 (선택, 2.5~3시간)
