# Phase 2 Step 1: Python 썸네일 의존성 분석

**날짜**: 2025-10-01
**단계**: Phase 2 - Step 1 (의존성 분석)
**목적**: create_thumbnail_python()의 UI 의존성 파악 및 분리 전략 수립

---

## 📋 의존성 분석 결과

### 메서드 정보

**위치**: `ui/main_window.py:818-1219`
**크기**: **402줄**
**복잡도**: 높음 (UI, 비즈니스 로직, 진행률 관리 혼재)

### 주요 의존성 목록

| 카테고리 | 의존성 | 사용 빈도 | 분리 방법 |
|---------|--------|----------|----------|
| **설정 데이터** | `self.settings_hash` | 높음 (8회) | 파라미터 전달 |
| **스레드풀** | `self.threadpool` | 중간 (3회) | 파라미터 전달 |
| **디렉토리** | `self.edtDirname.text()` | 낮음 (5회) | 파라미터 전달 |
| **진행률 UI** | `self.progress_dialog` | 높음 (15회+) | 콜백 함수 |
| **썸네일 관리자** | `self.thumbnail_manager` | 높음 (5회) | ThumbnailGenerator 멤버 |
| **볼륨 데이터** | `self.minimum_volume` | 낮음 (2회) | 반환값 |
| **레벨 정보** | `self.level_info` | 중간 (3회) | 반환값 |
| **UI 커서** | `QApplication.setOverrideCursor()` | 낮음 (2회) | MainWindow에 남김 |
| **타이밍** | `self.thumbnail_start_time` | 낮음 (1회) | 로컬 변수 |

---

## 🔍 상세 분석

### 1. 설정 데이터 (settings_hash)

**사용 위치**:
```python
Line 849: size = max(int(self.settings_hash["image_width"]), ...)
Line 850: width = int(self.settings_hash["image_width"])
Line 851: height = int(self.settings_hash["image_height"])
Line 896: seq_begin = self.settings_hash["seq_begin"]
Line 897: seq_end = self.settings_hash["seq_end"]
Line 1007: self.thumbnail_manager = ThumbnailManager(..., self.settings_hash, ...)
```

**분리 전략**: 딕셔너리를 파라미터로 전달

### 2. 스레드풀 (threadpool)

**사용 위치**:
```python
Line 854: logger.info(f"Thread configuration: maxThreadCount={self.threadpool.maxThreadCount()}")
Line 873: logger.info(f"Thread pool: max={self.threadpool.maxThreadCount()}, ...")
Line 1007: self.thumbnail_manager = ThumbnailManager(..., self.threadpool, ...)
```

**분리 전략**: QThreadPool 객체를 파라미터로 전달

### 3. 진행률 다이얼로그 (progress_dialog)

**사용 위치** (15회+):
```python
Line 920: self.progress_dialog = ProgressDialog(self)
Line 921: self.progress_dialog.update_language()
Line 922: self.progress_dialog.setModal(True)
Line 923: self.progress_dialog.show()
Line 925: self.progress_dialog.setup_unified_progress(...)
Line 932: self.progress_dialog.lbl_text.setText(...)
Line 933: self.progress_dialog.lbl_detail.setText(...)
Line 937-939: self.progress_dialog.level_work_distribution = ...
Line 971: if self.progress_dialog.is_cancelled:
Line 1007: ... = ThumbnailManager(self, self.progress_dialog, ...)
Line 1076: if was_cancelled or self.progress_dialog.is_cancelled:
```

**분리 전략**: 콜백 함수로 대체
```python
# 콜백 정의
def progress_callback(current, total, message, detail=None):
    # UI 업데이트
    pass

def cancel_check():
    return self.progress_dialog.is_cancelled
```

### 4. 썸네일 관리자 (thumbnail_manager)

**사용 위치**:
```python
Line 1007: self.thumbnail_manager = ThumbnailManager(...)
Line 1024: level_img_arrays, was_cancelled = self.thumbnail_manager.process_level(...)
Line 1068: global_step_counter = self.thumbnail_manager.global_step_counter
```

**분리 전략**: `ThumbnailGenerator`가 `ThumbnailManager` 인스턴스를 멤버로 소유

### 5. 볼륨 데이터 (minimum_volume, level_info)

**사용 위치**:
```python
Line 895: self.minimum_volume = []
Line 1169-1172: self.minimum_volume 업데이트
Line 1090-1101: self.level_info.append(...)
```

**분리 전략**: 반환 딕셔너리에 포함
```python
return {
    'minimum_volume': minimum_volume,
    'level_info': level_info,
    'success': True,
    'cancelled': False
}
```

### 6. UI 커서 (QApplication)

**사용 위치**:
```python
Line 942: QApplication.setOverrideCursor(Qt.WaitCursor)
Line 1112: QApplication.restoreOverrideCursor()
```

**분리 전략**: MainWindow에 남김 (UI 담당)

---

## 🎯 분리 전략

### 옵션 A: 최소 변경 (추천하지 않음)

단순히 코드를 복사하고 `self.xxx`를 파라미터로 변경.

**문제점**:
- UI 의존성 여전히 존재
- 테스트 불가능
- 콜백 없이 진행률 업데이트 불가

### 옵션 B: 콜백 패턴 (추천) ⭐

UI 상호작용을 콜백으로 분리.

**장점**:
- UI와 비즈니스 로직 완전 분리
- 독립적으로 테스트 가능
- 재사용성 높음

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
        cancel_check=None,
        detail_callback=None
    ):
        # 비즈니스 로직
        # 진행률 업데이트: progress_callback(current, total, msg)
        # 취소 확인: if cancel_check(): return
        # 상세 정보: detail_callback(detail_msg)
```

```python
# ui/main_window.py
class CTHarvesterMainWindow:
    def create_thumbnail_python(self):
        # 콜백 정의
        def on_progress(current, total, message):
            self.progress_dialog.update_progress(current, total, message)

        def check_cancel():
            return self.progress_dialog.is_cancelled

        def on_detail(detail_msg):
            self.progress_dialog.lbl_detail.setText(detail_msg)

        # ThumbnailGenerator 호출
        result = self.thumbnail_generator.generate_python(
            directory=self.edtDirname.text(),
            settings=self.settings_hash,
            threadpool=self.threadpool,
            progress_callback=on_progress,
            cancel_check=check_cancel,
            detail_callback=on_detail
        )
```

---

## 📊 콜백 인터페이스 설계

### 콜백 1: 진행률 업데이트

```python
def progress_callback(current: int, total: int, message: str) -> None:
    """
    Args:
        current: 현재 진행 단계
        total: 전체 단계 수
        message: 진행 상태 메시지
    """
    pass
```

**호출 위치**:
- 레벨 시작 시
- 각 이미지 처리 후
- 레벨 완료 시

### 콜백 2: 취소 확인

```python
def cancel_check() -> bool:
    """
    Returns:
        bool: True면 작업 취소, False면 계속 진행
    """
    return False  # 기본값: 취소하지 않음
```

**호출 위치**:
- 각 레벨 시작 전
- 각 이미지 처리 전 (선택적)

### 콜백 3: 상세 정보 업데이트

```python
def detail_callback(detail: str) -> None:
    """
    Args:
        detail: 상세 정보 메시지 (ETA, 속도 등)
    """
    pass
```

**호출 위치**:
- ETA 계산 후
- 속도 측정 후
- 경고 메시지

---

## 🔄 데이터 흐름

### Before (현재)

```
MainWindow.create_thumbnail_python()
├── UI: ProgressDialog 생성 및 직접 제어
├── 데이터: settings_hash, threadpool 직접 접근
├── 로직: ThumbnailManager 생성 및 호출
├── 결과: self.minimum_volume, self.level_info 직접 업데이트
└── UI: QApplication.restoreOverrideCursor()
```

### After (분리 후)

```
MainWindow.create_thumbnail_python()
├── UI 준비: ProgressDialog 생성, 커서 설정
├── 콜백 정의: on_progress, check_cancel, on_detail
├── 호출: ThumbnailGenerator.generate_python(...)
├── 결과 처리: result에서 minimum_volume, level_info 추출
└── UI 정리: 커서 복원, 다이얼로그 닫기

ThumbnailGenerator.generate_python()
├── 입력: directory, settings, threadpool, 콜백들
├── 로직: ThumbnailManager로 썸네일 생성
├── 진행률: progress_callback(current, total, msg) 호출
├── 취소: cancel_check() 확인
└── 출력: dict{minimum_volume, level_info, success, cancelled}
```

---

## 📝 파라미터 매핑

| MainWindow 상태 | 파라미터 이름 | 타입 | 기본값 |
|-----------------|--------------|------|--------|
| `self.edtDirname.text()` | `directory` | str | (필수) |
| `self.settings_hash` | `settings` | dict | (필수) |
| `self.threadpool` | `threadpool` | QThreadPool | (필수) |
| `self.progress_dialog` | `progress_callback` | Callable | None |
| `self.progress_dialog.is_cancelled` | `cancel_check` | Callable | None |
| `self.progress_dialog.lbl_detail` | `detail_callback` | Callable | None |

---

## ✅ 의존성 분리 체크리스트

### 제거 가능 (파라미터화)
- [x] `settings_hash` → `settings` 파라미터
- [x] `threadpool` → `threadpool` 파라미터
- [x] `edtDirname.text()` → `directory` 파라미터

### 제거 가능 (콜백)
- [x] `progress_dialog.update_progress()` → `progress_callback()`
- [x] `progress_dialog.is_cancelled` → `cancel_check()`
- [x] `progress_dialog.lbl_detail.setText()` → `detail_callback()`
- [x] `progress_dialog.setup_unified_progress()` → 초기 호출로 대체

### 제거 가능 (반환값)
- [x] `self.minimum_volume` → `return['minimum_volume']`
- [x] `self.level_info` → `return['level_info']`

### 제거 가능 (로컬 변수화)
- [x] `self.thumbnail_start_time` → 로컬 변수

### MainWindow에 남김 (UI 전용)
- [x] `QApplication.setOverrideCursor()` → MainWindow
- [x] `QApplication.restoreOverrideCursor()` → MainWindow
- [x] `ProgressDialog()` 생성 → MainWindow

### ThumbnailGenerator 멤버로 이동
- [x] `ThumbnailManager` 인스턴스 → `self.thumbnail_manager`

---

## 🎯 다음 단계

### Step 2: 코어 로직 이동 (1시간)

1. `core/thumbnail_generator.py`의 `generate_python()` 구현
2. `ui/main_window.py`의 400줄 로직 복사
3. UI 의존성 제거
4. 콜백 호출 추가
5. 파라미터 처리
6. 반환값 구조화

### Step 3: MainWindow 리팩토링 (30분)

1. `create_thumbnail_python()` 간소화
2. 콜백 함수 정의
3. `ThumbnailGenerator.generate_python()` 호출
4. 반환값으로 UI 업데이트

### Step 4: 테스트 (30분)

1. 단위 테스트
2. 통합 테스트
3. Rust 없는 환경 테스트

---

## 📊 예상 효과

### 코드 크기

| 파일 | Before | After | 변화 |
|------|--------|-------|------|
| `ui/main_window.py` | 1,511줄 | ~1,100줄 | -411줄 (-27%) |
| `core/thumbnail_generator.py` | 플레이스홀더 | ~450줄 | +450줄 |

### 코드 품질

- ✅ 단일 책임 원칙 준수
- ✅ UI와 비즈니스 로직 완전 분리
- ✅ 독립적으로 테스트 가능
- ✅ Python 폴백 완전 구현

---

**작성일**: 2025-10-01
**소요 시간**: 30분
**다음 단계**: Step 2 (코어 로직 이동) 시작
