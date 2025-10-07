# 치명적 문제 수정 계획

날짜: 2025-09-30
작성자: Code Review Analysis

## 개요

코드베이스 전체 분석을 통해 발견된 치명적(Critical) 수준의 문제들에 대한 수정 계획을 수립한다. 이 문제들은 프로그램 안정성, 보안, 성능에 직접적인 영향을 미치므로 최우선으로 수정해야 한다.

## 문제 1: 메모리 관리 및 누수 위험

### 현상
- 대용량 CT 이미지 처리 시 메모리 사용량이 지속적으로 증가
- 4GB 이상 이미지 스택 처리 시 프로그램 충돌 발생
- 16비트 이미지 처리 시 메모리 사용량 급증

### 원인 분석

#### 1.1 PIL Image 객체 메모리 해제 불완전
**위치**: `CTHarvester.py:294-648` (ThumbnailWorker 클래스)

```python
# 문제 코드 (라인 456-500)
img1 = Image.open(file1_path)
arr1 = np.array(img1, dtype=np.uint16 if img1_is_16bit else np.uint8)
# img1이 명시적으로 해제되지 않음
```

**문제점**:
- PIL Image 객체가 스코프를 벗어나도 즉시 메모리 해제되지 않음
- 대량 이미지 처리 시 가비지 컬렉터가 따라잡지 못함
- numpy 배열 변환 시 추가 메모리 복사 발생

#### 1.2 16비트 이미지 처리 시 중복 복사
**위치**: `CTHarvester.py:456-622`

```python
# 현재 흐름
img1 = Image.open(file1_path)           # 메모리 1
arr1 = np.array(img1, ...)              # 메모리 2 (복사)
new_arr = (arr1 + arr2) // 2            # 메모리 3 (새 배열)
new_img = Image.fromarray(new_arr)      # 메모리 4 (PIL 변환)
```

동일 이미지 데이터가 최대 4번 메모리에 존재할 수 있음.

#### 1.3 타입 체크 불충분
**위치**: `CTHarvester.py:3289-3296`

```python
# 문제 코드
if self.minimum_volume and isinstance(self.minimum_volume, list):
    minimum_volume = np.array(self.minimum_volume, dtype=np.uint8)
# list가 아닌 경우 처리 누락
```

### 수정 계획

#### Phase 1.1: Context Manager 패턴 적용 (2일)

**파일**: `CTHarvester.py`

**수정 1**: ThumbnailWorker.run() 메서드 (라인 456-620)

```python
def _load_and_process_image(self, filepath, is_16bit):
    """이미지를 로드하고 numpy 배열로 변환 (메모리 효율적)"""
    try:
        with Image.open(filepath) as img:
            # 즉시 numpy 배열로 변환
            arr = np.array(img, dtype=np.uint16 if is_16bit else np.uint8)
            # with 블록 종료 시 img 자동 해제
            return arr
    except Exception as e:
        logger.error(f"Failed to load image {filepath}: {e}")
        raise

def _process_image_pair(self, file1_path, file2_path, is_16bit):
    """두 이미지를 처리하고 평균화 (메모리 최적화)"""
    try:
        # 순차적 로드 및 처리
        arr1 = self._load_and_process_image(file1_path, is_16bit)

        if file2_path:
            arr2 = self._load_and_process_image(file2_path, is_16bit)
            # in-place 연산으로 메모리 절약
            arr1 = arr1.astype(np.uint32)  # 오버플로 방지
            arr1 += arr2
            arr1 //= 2
            del arr2  # 명시적 해제
            arr1 = arr1.astype(np.uint16 if is_16bit else np.uint8)

        # 리샘플링
        height, width = arr1.shape
        new_height, new_width = height // 2, width // 2

        # PIL 없이 numpy로 직접 다운샘플링 (더 빠르고 메모리 효율적)
        resampled = arr1[::2, ::2]  # 2x2 블록의 첫 픽셀만 선택

        del arr1  # 원본 배열 해제
        return resampled

    except Exception as e:
        logger.error(f"Image processing failed: {e}")
        return None
```

**수정 2**: 명시적 가비지 컬렉션 (라인 620 이후 추가)

```python
import gc

def run(self):
    try:
        # ... 기존 코드 ...

        # 10개 이미지마다 명시적 GC
        if self.idx % 10 == 0:
            gc.collect()

    except Exception as e:
        logger.error(f"Worker {self.idx} failed: {e}")
        self.signals.error.emit(str(e))
    finally:
        self.signals.finished.emit()
```

#### Phase 1.2: 타입 체크 강화 (1일)

**파일**: `CTHarvester.py:3289-3296`

```python
def _validate_minimum_volume(self):
    """minimum_volume 타입 검증 및 변환"""
    if self.minimum_volume is None:
        return None

    if isinstance(self.minimum_volume, list):
        try:
            return np.array(self.minimum_volume, dtype=np.uint8)
        except (ValueError, TypeError) as e:
            logger.error(f"Failed to convert minimum_volume list: {e}")
            return None

    elif isinstance(self.minimum_volume, np.ndarray):
        # 이미 numpy 배열인 경우
        if self.minimum_volume.dtype != np.uint8:
            return self.minimum_volume.astype(np.uint8)
        return self.minimum_volume

    else:
        logger.warning(f"Invalid minimum_volume type: {type(self.minimum_volume)}")
        return None
```

#### Phase 1.3: 메모리 모니터링 추가 (1일)

```python
import psutil
import os

class MemoryMonitor:
    """메모리 사용량 모니터링 클래스"""

    def __init__(self, threshold_mb=4096):
        self.process = psutil.Process(os.getpid())
        self.threshold_bytes = threshold_mb * 1024 * 1024
        self.peak_usage = 0

    def check_memory(self):
        """현재 메모리 사용량 확인"""
        mem_info = self.process.memory_info()
        current_usage = mem_info.rss

        if current_usage > self.peak_usage:
            self.peak_usage = current_usage

        if current_usage > self.threshold_bytes:
            logger.warning(
                f"High memory usage: {current_usage / 1024 / 1024:.2f} MB "
                f"(threshold: {self.threshold_mb} MB)"
            )
            gc.collect()  # 강제 가비지 컬렉션

        return current_usage

    def get_peak_usage_mb(self):
        """최대 메모리 사용량 반환 (MB)"""
        return self.peak_usage / 1024 / 1024
```

**적용 위치**: ThumbnailManager.__init__

```python
def __init__(self, ...):
    # ... 기존 코드 ...
    self.memory_monitor = MemoryMonitor(threshold_mb=4096)

def on_worker_result(self, idx, img_array):
    # ... 기존 코드 ...

    # 메모리 체크
    if idx % 50 == 0:  # 50개마다 체크
        current_mem = self.memory_monitor.check_memory()
        logger.debug(f"Memory usage: {current_mem / 1024 / 1024:.2f} MB")
```

### 검증 방법

1. **메모리 프로파일링**
   ```python
   # test_memory_profiling.py
   import memory_profiler

   @profile
   def test_thumbnail_generation():
       # 3000개 이미지로 테스트
       # 메모리 사용량 추적
   ```

2. **스트레스 테스트**
   - 8GB 이미지 스택으로 테스트
   - 메모리 사용량이 4GB 이하 유지되는지 확인

3. **성능 비교**
   - 수정 전/후 처리 시간 비교
   - 메모리 사용량 피크 비교

---

## 문제 2: 스레드 안전성 문제

### 현상
- 썸네일 생성 중 간헐적 데이터 손실
- 진행률 표시 오류 (음수 또는 100% 초과)
- 멀티코어 CPU에서도 단일 코어만 사용 (성능 8배 손실)

### 원인 분석

#### 2.1 레이스 컨디션
**위치**: `CTHarvester.py:1148-1159`

```python
# 문제 코드
def on_worker_result(self, idx, img_array):
    with QMutexLocker(self.lock):
        # lock 보호 구간
        pass

    # lock 외부에서 self.results 접근 (위험!)
    self.results[idx] = img_array
    self.completed_tasks += 1
```

#### 2.2 강제 단일 스레드
**위치**: `CTHarvester.py:948-952`

```python
# 문제 코드
if self.threadpool.maxThreadCount() != 1:
    self.threadpool.setMaxThreadCount(1)
    logger.info(f"Python fallback using single thread for stability")
```

멀티코어 활용 불가로 성능 저하.

### 수정 계획

#### Phase 2.1: Thread-Safe 데이터 구조 (2일)

**파일**: `CTHarvester.py:1106-1314`

```python
from threading import RLock
from collections import OrderedDict

class ThumbnailManager:
    def __init__(self, ...):
        # QMutex 대신 threading.RLock 사용 (재진입 가능)
        self.lock = RLock()
        self.results = OrderedDict()  # 순서 보장
        self.completed_tasks = 0
        self.failed_tasks = 0
        self.in_progress = set()  # 진행 중인 작업 추적

    def on_worker_started(self, idx):
        """워커 시작 시 호출"""
        with self.lock:
            self.in_progress.add(idx)
            logger.debug(f"Worker {idx} started, in_progress: {len(self.in_progress)}")

    def on_worker_result(self, idx, img_array):
        """워커 완료 시 호출 (thread-safe)"""
        with self.lock:
            # 모든 상태 업데이트를 lock 내부에서 수행
            if idx not in self.results:  # 중복 방지
                self.results[idx] = img_array
                self.completed_tasks += 1

                # 진행 중 세트에서 제거
                self.in_progress.discard(idx)

                # 진행률 업데이트
                progress = (self.completed_tasks / self.total_tasks) * 100

                # 안전성 체크
                if not (0 <= progress <= 100):
                    logger.error(
                        f"Invalid progress: {progress:.2f}% "
                        f"(completed={self.completed_tasks}, total={self.total_tasks})"
                    )
                    progress = max(0, min(100, progress))

                logger.debug(
                    f"Task {idx} completed: {self.completed_tasks}/{self.total_tasks} "
                    f"({progress:.1f}%), in_progress: {len(self.in_progress)}"
                )

                # UI 업데이트 (Qt signal은 thread-safe)
                self.progress_callback(progress)
            else:
                logger.warning(f"Duplicate result for task {idx}")

    def on_worker_error(self, idx, error_msg):
        """워커 에러 시 호출"""
        with self.lock:
            self.failed_tasks += 1
            self.in_progress.discard(idx)
            logger.error(f"Task {idx} failed: {error_msg}")

            # 실패한 작업도 completed로 간주 (무한 대기 방지)
            self.completed_tasks += 1

    def is_complete(self):
        """모든 작업 완료 여부 (thread-safe)"""
        with self.lock:
            return (self.completed_tasks + self.failed_tasks >= self.total_tasks and
                    len(self.in_progress) == 0)
```

#### Phase 2.2: 멀티스레딩 복원 (3일)

**파일**: `CTHarvester.py:948-952`

```python
def _determine_optimal_thread_count(self):
    """최적 스레드 수 결정"""
    cpu_count = os.cpu_count() or 1

    # 메모리 기반 제한
    available_memory_gb = psutil.virtual_memory().available / (1024**3)

    # 이미지당 약 50MB 메모리 사용 가정
    memory_based_limit = int(available_memory_gb * 1024 / 50)

    # CPU와 메모리 중 작은 값 선택
    optimal_threads = min(cpu_count, memory_based_limit, 8)  # 최대 8

    logger.info(
        f"Thread count: {optimal_threads} "
        f"(CPU: {cpu_count}, Memory limit: {memory_based_limit})"
    )

    return max(1, optimal_threads)

def __init__(self, ...):
    # ... 기존 코드 ...

    # 최적 스레드 수 설정
    optimal_threads = self._determine_optimal_thread_count()
    self.threadpool.setMaxThreadCount(optimal_threads)
```

#### Phase 2.3: Worker 시그널 강화 (1일)

```python
class WorkerSignals(QObject):
    finished = pyqtSignal()
    error = pyqtSignal(int, str)  # (idx, error_msg)
    result = pyqtSignal(int, object)  # (idx, img_array)
    started = pyqtSignal(int)  # 추가: 작업 시작 시그널
    progress = pyqtSignal(int, int, int)  # 추가: (idx, current, total)

class ThumbnailWorker(QRunnable):
    def run(self):
        try:
            # 시작 시그널 발송
            self.signals.started.emit(self.idx)

            # ... 기존 처리 로직 ...

            # 결과 시그널 발송
            self.signals.result.emit(self.idx, result)

        except Exception as e:
            logger.error(f"Worker {self.idx} exception: {e}", exc_info=True)
            self.signals.error.emit(self.idx, str(e))
        finally:
            # 항상 finished 시그널 발송
            self.signals.finished.emit()
```

### 검증 방법

1. **동시성 테스트**
   ```python
   # test_thread_safety.py
   def test_concurrent_thumbnail_generation():
       # 100개 워커 동시 실행
       # 결과 개수 확인 (누락/중복 없음)
       # 진행률 범위 확인 (0-100%)
   ```

2. **성능 벤치마크**
   - 단일 스레드 vs 멀티 스레드 처리 시간 비교
   - CPU 사용률 모니터링

3. **스트레스 테스트**
   - 1000개 이미지로 10회 반복 테스트
   - 데이터 손실/중복 없는지 확인

---

## 문제 3: 에러 처리 부재

### 현상
- 예외 발생 시 스택 트레이스 출력 실패
- 워커 스레드가 정상 종료되지 않음 (좀비 프로세스)
- UI 초기화 실패 시 프로그램 완전 종료

### 원인 분석

#### 3.1 traceback 미포트
**위치**: `CTHarvester.py:166-175`

```python
# 문제 코드
def run(self):
    try:
        # ...
    except Exception as e:
        # traceback 모듈이 임포트되지 않음
        error_details = traceback.format_exc()
```

#### 3.2 finished 시그널 미발송
**위치**: `CTHarvester.py:350-355`

```python
# 문제 코드
def run(self):
    if self.progress_dialog.is_cancelled:
        logger.debug(f"Worker cancelled at idx={self.idx}")
        return  # finished 시그널 발송 안 됨!
```

#### 3.3 UI 초기화 예외 처리 부재
**위치**: `CTHarvester.py:3000-3100`

### 수정 계획

#### Phase 3.1: Import 수정 및 에러 핸들러 강화 (1일)

**파일**: `CTHarvester.py` (상단에 추가)

```python
import traceback
import sys
from functools import wraps

def safe_execute(error_return_value=None):
    """예외를 안전하게 처리하는 데코레이터"""
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            try:
                return func(*args, **kwargs)
            except Exception as e:
                logger.error(
                    f"Exception in {func.__name__}: {e}\n"
                    f"{traceback.format_exc()}"
                )
                return error_return_value
        return wrapper
    return decorator
```

**적용 예시**:

```python
@safe_execute(error_return_value=None)
def _load_and_process_image(self, filepath, is_16bit):
    """이미지 로드 (예외 안전)"""
    with Image.open(filepath) as img:
        return np.array(img, dtype=np.uint16 if is_16bit else np.uint8)
```

#### Phase 3.2: Worker 종료 보장 (1일)

**파일**: `CTHarvester.py:350-355`

```python
class ThumbnailWorker(QRunnable):
    def run(self):
        exception_occurred = False
        try:
            # 취소 체크
            if self.progress_dialog and self.progress_dialog.is_cancelled:
                logger.debug(f"Worker {self.idx} cancelled")
                return

            # 실제 작업 수행
            result = self._do_work()

            # 결과 전송
            if result is not None:
                self.signals.result.emit(self.idx, result)
            else:
                self.signals.error.emit(self.idx, "Result is None")
                exception_occurred = True

        except KeyboardInterrupt:
            logger.warning(f"Worker {self.idx} interrupted by user")
            exception_occurred = True
            raise

        except Exception as e:
            logger.error(
                f"Worker {self.idx} failed: {e}\n"
                f"{traceback.format_exc()}"
            )
            self.signals.error.emit(self.idx, str(e))
            exception_occurred = True

        finally:
            # 항상 finished 시그널 발송 (중요!)
            self.signals.finished.emit()

            # 명시적 정리
            if exception_occurred:
                logger.debug(f"Worker {self.idx} finished with errors")
            else:
                logger.debug(f"Worker {self.idx} finished successfully")
```

#### Phase 3.3: UI 초기화 안전성 강화 (2일)

**파일**: `CTHarvester.py:3000-3100`

```python
class CTHarvesterMainWindow(QMainWindow):
    def __init__(self):
        super().__init__()

        # 초기화 상태 추적
        self.initialization_failed = False
        self.failed_components = []

        try:
            self._initialize_ui()
        except Exception as e:
            logger.critical(f"UI initialization failed: {e}\n{traceback.format_exc()}")
            self._show_initialization_error(e)
            self.initialization_failed = True

    def _initialize_ui(self):
        """UI 컴포넌트 초기화 (예외 전파)"""
        try:
            self._init_basic_window()
        except Exception as e:
            self.failed_components.append("basic_window")
            raise RuntimeError(f"Failed to initialize basic window: {e}") from e

        try:
            self._init_opengl_widgets()
        except Exception as e:
            self.failed_components.append("opengl_widgets")
            logger.error(f"OpenGL initialization failed: {e}")
            # OpenGL은 선택적 기능이므로 계속 진행
            self.opengl_available = False

        try:
            self._init_menu_and_toolbar()
        except Exception as e:
            self.failed_components.append("menu_toolbar")
            raise RuntimeError(f"Failed to initialize menu/toolbar: {e}") from e

        try:
            self._init_sliders_and_controls()
        except Exception as e:
            self.failed_components.append("controls")
            raise RuntimeError(f"Failed to initialize controls: {e}") from e

    def _show_initialization_error(self, error):
        """초기화 실패 시 사용자에게 알림"""
        msg = QMessageBox()
        msg.setIcon(QMessageBox.Critical)
        msg.setWindowTitle("Initialization Error")
        msg.setText(
            "CTHarvester failed to initialize properly.\n\n"
            f"Error: {error}\n\n"
            f"Failed components: {', '.join(self.failed_components)}\n\n"
            "Please check the log file for details."
        )
        msg.setStandardButtons(QMessageBox.Ok)
        msg.exec_()

    def check_initialization(self):
        """초기화 성공 여부 확인"""
        if self.initialization_failed:
            logger.error("Application running with failed initialization")
            return False
        return True
```

**main 함수 수정**:

```python
def main():
    app = QApplication(sys.argv)

    try:
        window = CTHarvesterMainWindow()

        # 초기화 확인
        if not window.check_initialization():
            logger.critical("Cannot start application due to initialization failure")
            return 1

        window.show()
        return app.exec_()

    except Exception as e:
        logger.critical(f"Fatal error: {e}\n{traceback.format_exc()}")

        # 최소한의 에러 다이얼로그
        error_dialog = QMessageBox()
        error_dialog.setIcon(QMessageBox.Critical)
        error_dialog.setText(f"Fatal error: {e}")
        error_dialog.exec_()

        return 1

if __name__ == '__main__':
    sys.exit(main())
```

### 검증 방법

1. **예외 처리 테스트**
   ```python
   # test_error_handling.py
   def test_worker_exception():
       # 의도적으로 예외 발생시키기
       # finished 시그널 발송 확인
       # 스택 트레이스 로그 확인
   ```

2. **초기화 실패 시나리오**
   - OpenGL 미지원 환경에서 테스트
   - 권한 없는 디렉토리 접근 테스트

3. **로그 검증**
   - 모든 예외가 로그에 기록되는지 확인
   - 스택 트레이스가 완전한지 확인

---

## 문제 4: 파일 경로 보안 취약점

### 현상
- 악의적 파일명으로 상위 디렉토리 접근 가능
- 디렉토리 순회(Directory Traversal) 공격 위험
- 시스템 파일 읽기/쓰기 가능성

### 원인 분석

#### 4.1 파일명 검증 부재
**위치**: `CTHarvester.py:4281-4350`

```python
# 문제 코드
def get_files_from_directory(self, dir_path):
    files = []
    for filename in os.listdir(dir_path):
        # filename에 '../' 포함 가능
        full_path = os.path.join(dir_path, filename)
        files.append(full_path)
```

공격 시나리오:
```python
# 악의적 파일명
filename = "../../../etc/passwd"
full_path = os.path.join("/safe/dir", filename)
# 결과: "/safe/dir/../../../etc/passwd" = "/etc/passwd"
```

### 수정 계획

#### Phase 4.1: 파일명 검증 유틸리티 (1일)

**새 파일**: `file_security.py`

```python
"""
파일 시스템 보안 유틸리티
"""
import os
import re
from pathlib import Path
from typing import Optional
import logging

logger = logging.getLogger(__name__)

class FileSecurityError(Exception):
    """파일 보안 관련 예외"""
    pass

class SecureFileValidator:
    """파일 경로 검증 클래스"""

    # 허용된 파일 확장자
    ALLOWED_EXTENSIONS = {'.bmp', '.jpg', '.jpeg', '.png', '.tif', '.tiff'}

    # 금지된 문자/패턴
    FORBIDDEN_PATTERNS = [
        r'\.\.',        # 상위 디렉토리 참조
        r'^/',          # 절대 경로
        r'^\\',         # Windows 절대 경로
        r'[<>:"|?*]',   # Windows 금지 문자
        r'\x00',        # Null 바이트
    ]

    @staticmethod
    def validate_filename(filename: str) -> str:
        """
        파일명 검증 (디렉토리 순회 방지)

        Args:
            filename: 검증할 파일명

        Returns:
            검증된 파일명 (basename만)

        Raises:
            FileSecurityError: 검증 실패 시
        """
        if not filename:
            raise FileSecurityError("Filename is empty")

        # 금지된 패턴 체크
        for pattern in SecureFileValidator.FORBIDDEN_PATTERNS:
            if re.search(pattern, filename):
                raise FileSecurityError(
                    f"Filename contains forbidden pattern: {filename}"
                )

        # basename만 추출 (디렉토리 부분 제거)
        safe_name = os.path.basename(filename)

        if safe_name != filename:
            logger.warning(
                f"Filename contained directory path: {filename} -> {safe_name}"
            )

        return safe_name

    @staticmethod
    def validate_extension(filename: str) -> bool:
        """파일 확장자 검증"""
        ext = os.path.splitext(filename)[1].lower()
        return ext in SecureFileValidator.ALLOWED_EXTENSIONS

    @staticmethod
    def validate_path(file_path: str, base_dir: str) -> str:
        """
        파일 경로 검증 (base_dir 내부인지 확인)

        Args:
            file_path: 검증할 파일 경로
            base_dir: 허용된 기본 디렉토리

        Returns:
            정규화된 절대 경로

        Raises:
            FileSecurityError: base_dir 외부 경로일 경우
        """
        # 절대 경로로 변환 및 정규화
        abs_base = os.path.abspath(base_dir)
        abs_file = os.path.abspath(file_path)

        # 공통 경로 확인
        common_path = os.path.commonpath([abs_base, abs_file])

        if common_path != abs_base:
            raise FileSecurityError(
                f"Path is outside base directory: {file_path} "
                f"(base: {base_dir})"
            )

        return abs_file

    @staticmethod
    def safe_join(base_dir: str, *paths: str) -> str:
        """
        안전한 경로 결합 (os.path.join의 안전한 버전)

        Args:
            base_dir: 기본 디렉토리
            *paths: 결합할 경로 구성요소들

        Returns:
            안전하게 결합된 경로

        Raises:
            FileSecurityError: 검증 실패 시
        """
        # 각 구성요소 검증
        validated_parts = []
        for part in paths:
            validated_parts.append(
                SecureFileValidator.validate_filename(part)
            )

        # 경로 결합
        joined = os.path.join(base_dir, *validated_parts)

        # 최종 검증
        return SecureFileValidator.validate_path(joined, base_dir)

    @staticmethod
    def secure_listdir(directory: str) -> list:
        """
        안전한 디렉토리 목록 조회

        Args:
            directory: 조회할 디렉토리

        Returns:
            검증된 파일 목록 (basename만)
        """
        if not os.path.isdir(directory):
            raise FileSecurityError(f"Not a directory: {directory}")

        safe_files = []
        try:
            for item in os.listdir(directory):
                try:
                    # 파일명 검증
                    safe_name = SecureFileValidator.validate_filename(item)

                    # 전체 경로 검증
                    full_path = SecureFileValidator.safe_join(directory, safe_name)

                    # 확장자 검증 (이미지 파일만)
                    if os.path.isfile(full_path):
                        if SecureFileValidator.validate_extension(safe_name):
                            safe_files.append(safe_name)
                        else:
                            logger.debug(f"Skipping non-image file: {safe_name}")

                except FileSecurityError as e:
                    logger.warning(f"Skipping invalid file: {item} ({e})")
                    continue

        except OSError as e:
            logger.error(f"Failed to list directory {directory}: {e}")
            raise FileSecurityError(f"Directory access failed: {e}") from e

        return sorted(safe_files)
```

#### Phase 4.2: CTHarvester.py 적용 (2일)

**파일**: `CTHarvester.py`

```python
from file_security import SecureFileValidator, FileSecurityError

class CTHarvesterMainWindow(QMainWindow):
    def open_dir(self):
        """디렉토리 열기 (보안 강화)"""
        try:
            dir_path = QFileDialog.getExistingDirectory(
                self, "Select Directory", self.last_dir
            )

            if not dir_path:
                return

            # 디렉토리 경로 검증
            dir_path = os.path.abspath(dir_path)

            if not os.path.isdir(dir_path):
                QMessageBox.warning(self, "Error", "Invalid directory")
                return

            # 안전한 파일 목록 조회
            try:
                file_list = SecureFileValidator.secure_listdir(dir_path)
            except FileSecurityError as e:
                logger.error(f"Directory access failed: {e}")
                QMessageBox.critical(
                    self, "Security Error",
                    f"Cannot access directory safely:\n{e}"
                )
                return

            if not file_list:
                QMessageBox.information(
                    self, "No Files",
                    "No valid image files found in directory"
                )
                return

            # 기존 로직 계속...
            self.current_dir = dir_path
            self.file_list = file_list

        except Exception as e:
            logger.error(f"Failed to open directory: {e}\n{traceback.format_exc()}")
            QMessageBox.critical(self, "Error", f"Failed to open directory:\n{e}")

    def load_image(self, filename):
        """이미지 로드 (보안 강화)"""
        try:
            # 파일명 검증
            safe_filename = SecureFileValidator.validate_filename(filename)

            # 안전한 경로 결합
            file_path = SecureFileValidator.safe_join(
                self.current_dir, safe_filename
            )

            # 이미지 로드
            with Image.open(file_path) as img:
                return np.array(img)

        except FileSecurityError as e:
            logger.error(f"File security error: {e}")
            raise
        except Exception as e:
            logger.error(f"Failed to load image {filename}: {e}")
            raise
```

#### Phase 4.3: 추가 보안 강화 (1일)

**파일 크기 제한**:

```python
class SecureFileValidator:
    # 최대 파일 크기 (1GB)
    MAX_FILE_SIZE = 1024 * 1024 * 1024

    @staticmethod
    def validate_file_size(file_path: str) -> bool:
        """파일 크기 검증 (DoS 방지)"""
        try:
            size = os.path.getsize(file_path)
            if size > SecureFileValidator.MAX_FILE_SIZE:
                raise FileSecurityError(
                    f"File too large: {size / (1024**3):.2f} GB "
                    f"(max: {SecureFileValidator.MAX_FILE_SIZE / (1024**3):.2f} GB)"
                )
            return True
        except OSError as e:
            raise FileSecurityError(f"Cannot get file size: {e}") from e
```

**심볼릭 링크 검증**:

```python
@staticmethod
def validate_no_symlink(file_path: str) -> str:
    """심볼릭 링크가 아닌지 확인"""
    if os.path.islink(file_path):
        raise FileSecurityError(f"Symbolic links not allowed: {file_path}")
    return file_path
```

### 검증 방법

1. **보안 테스트**
   ```python
   # test_security.py
   def test_directory_traversal():
       # 악의적 파일명 테스트
       malicious_names = [
           "../../../etc/passwd",
           "..\\..\\..\\windows\\system32",
           "test\x00.txt",
           "/etc/shadow"
       ]
       for name in malicious_names:
           with pytest.raises(FileSecurityError):
               SecureFileValidator.validate_filename(name)
   ```

2. **침투 테스트**
   - 실제 악의적 파일명으로 디렉토리 생성
   - 프로그램이 거부하는지 확인

3. **화이트박스 테스트**
   - 모든 파일 접근 코드 리뷰
   - SecureFileValidator 사용 여부 확인

---

## 전체 수정 일정

### Week 1 (1-5일차)
- **Day 1-2**: 문제 1 (메모리) Phase 1.1 - Context Manager 적용
- **Day 3**: 문제 1 Phase 1.2 - 타입 체크 강화
- **Day 4**: 문제 1 Phase 1.3 - 메모리 모니터링
- **Day 5**: 문제 1 검증 및 테스트

### Week 2 (6-10일차)
- **Day 6-7**: 문제 2 (스레드) Phase 2.1 - Thread-Safe 구조
- **Day 8-9**: 문제 2 Phase 2.2 - 멀티스레딩 복원
- **Day 10**: 문제 2 Phase 2.3 - Worker 시그널 강화

### Week 3 (11-15일차)
- **Day 11**: 문제 2 검증 및 성능 테스트
- **Day 12**: 문제 3 (에러) Phase 3.1 - Import 및 에러 핸들러
- **Day 13**: 문제 3 Phase 3.2 - Worker 종료 보장
- **Day 14-15**: 문제 3 Phase 3.3 - UI 초기화 안전성

### Week 4 (16-20일차)
- **Day 16**: 문제 3 검증 및 테스트
- **Day 17**: 문제 4 (보안) Phase 4.1 - 파일명 검증 유틸리티
- **Day 18-19**: 문제 4 Phase 4.2 - CTHarvester 적용
- **Day 20**: 문제 4 Phase 4.3 - 추가 보안 강화 및 검증

### Week 5 (21-25일차)
- **Day 21-22**: 전체 통합 테스트
- **Day 23**: 성능 벤치마크 (수정 전/후 비교)
- **Day 24**: 문서화 업데이트
- **Day 25**: 코드 리뷰 및 최종 검증

## 성공 기준

### 정량적 지표
1. **메모리 사용량**: 8GB 이미지 스택에서 4GB 이하 유지
2. **처리 속도**: 멀티스레딩으로 4배 이상 향상 (4코어 기준)
3. **안정성**: 1000회 반복 테스트에서 0건의 크래시
4. **에러 복구**: 모든 예외에서 graceful shutdown
5. **보안**: 모든 침투 테스트 통과

### 정성적 지표
1. 코드 가독성 향상
2. 유지보수 용이성 증가
3. 로그 품질 개선
4. 사용자 경험 향상 (진행률 정확도, 에러 메시지 명확성)

## 위험 요소 및 대응

### 위험 1: 성능 저하
- **발생 가능성**: 중
- **영향도**: 높음
- **대응**: 각 Phase마다 벤치마크 수행, 성능 저하 시 롤백

### 위험 2: 기존 기능 회귀
- **발생 가능성**: 중
- **영향도**: 높음
- **대응**: 수정 전 모든 기능 테스트 작성, CI/CD에 통합

### 위험 3: 예상치 못한 버그
- **발생 가능성**: 높음
- **영향도**: 중
- **대응**: Git branch 전략 (feature branch → develop → main)

## 다음 단계

이 계획 완료 후:
1. **중요 개선사항** (Important Issues) 착수
2. 코드 리팩토링 (모놀리식 구조 분할)
3. 테스트 커버리지 70% 이상 달성
4. 문서화 완성

## 참고 자료

- [OWASP Path Traversal](https://owasp.org/www-community/attacks/Path_Traversal)
- [Python Threading Best Practices](https://docs.python.org/3/library/threading.html)
- [Memory Profiling in Python](https://pypi.org/project/memory-profiler/)
- [PyQt Thread Safety](https://doc.qt.io/qt-5/threads-qobject.html)
