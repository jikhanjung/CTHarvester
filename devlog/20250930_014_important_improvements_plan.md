# 중요 개선사항 수정 계획

날짜: 2025-09-30
작성자: Code Review Analysis

## 개요

치명적 문제 수정 완료 후 착수할 중요(Important) 개선사항들에 대한 계획이다. 이 개선사항들은 코드 품질, 유지보수성, 성능, 안정성을 크게 향상시킬 것이다.

## 전제 조건

이 계획은 다음 작업이 완료된 후 시작한다:
- ✅ 치명적 문제 4건 모두 수정 완료
- ✅ 통합 테스트 통과
- ✅ 메모리 및 스레드 안전성 검증 완료

## 개선사항 1: 코드 구조 및 유지보수성

### 현황 분석

**문제점**:
- `CTHarvester.py`: 4,694줄, 211KB - 거대한 모놀리식 구조
- 166개의 클래스/함수가 단일 파일에 집중
- 중복 코드 다수 (썸네일 로직, 이미지 처리)
- 관심사 분리(Separation of Concerns) 부족

**영향**:
- 코드 이해 시간: 신규 개발자 최소 1주 소요
- 버그 추적 난이도: 높음
- 병합 충돌 빈도: 높음 (팀 작업 시)
- 리팩토링 리스크: 매우 높음

### 목표 아키텍처

```
CTHarvester/
├── main.py                          # 진입점 (50줄)
├── core/
│   ├── __init__.py
│   ├── thumbnail_manager.py        # ThumbnailManager (300줄)
│   ├── thumbnail_worker.py         # ThumbnailWorker, WorkerSignals (200줄)
│   ├── image_processor.py          # 이미지 처리 로직 (400줄)
│   ├── volume_manager.py           # 3D 볼륨 처리 (350줄)
│   ├── mesh_generator.py           # Marching Cubes 메시 생성 (250줄)
│   └── progress_manager.py         # ProgressManager (150줄)
├── ui/
│   ├── __init__.py
│   ├── main_window.py              # CTHarvesterMainWindow (800줄)
│   ├── dialogs.py                  # InfoDialog, PreferencesDialog (300줄)
│   ├── progress_dialog.py          # ThumbnailProgressDialog (200줄)
│   ├── widgets/
│   │   ├── __init__.py
│   │   ├── object_viewer_2d.py     # ObjectViewer2D (400줄)
│   │   ├── mcube_widget.py         # MCubeWidget (600줄)
│   │   └── timeline_slider.py      # 타임라인 슬라이더 (200줄)
│   └── styles.py                   # UI 스타일 정의 (100줄)
├── utils/
│   ├── __init__.py
│   ├── file_utils.py               # 파일 작업 (300줄)
│   ├── image_utils.py              # 이미지 유틸리티 (200줄)
│   ├── settings_manager.py         # QSettings 래퍼 (150줄)
│   └── logger_config.py            # 로깅 설정 (100줄)
├── security/
│   ├── __init__.py
│   └── file_validator.py           # SecureFileValidator (200줄)
├── config/
│   ├── __init__.py
│   ├── constants.py                # 상수 정의 (100줄)
│   └── defaults.py                 # 기본 설정값 (50줄)
├── CTLogger.py                      # 유지 (기존)
├── version.py                       # 유지 (기존)
└── vertical_stack_slider.py         # 유지 (외부 라이브러리)
```

### 수정 계획

#### Phase 1.1: 파일 구조 생성 및 모듈 초안 (3일)

**작업 내용**:
1. 디렉토리 구조 생성
2. `__init__.py` 파일 작성
3. 각 모듈의 인터페이스 정의 (함수 시그니처, 클래스 스켈레톤)

**Day 1**: 디렉토리 및 기본 구조

```bash
# 디렉토리 생성
mkdir -p core ui/widgets utils security config tests/{unit,integration}

# __init__.py 생성
touch core/__init__.py ui/__init__.py ui/widgets/__init__.py
touch utils/__init__.py security/__init__.py config/__init__.py
```

**config/constants.py**:

```python
"""
CTHarvester 전역 상수 정의
"""

# 애플리케이션 정보
APP_NAME = "CTHarvester"
APP_ORGANIZATION = "PaleoBytes"

# 파일 관련
SUPPORTED_IMAGE_EXTENSIONS = ('.bmp', '.jpg', '.jpeg', '.png', '.tif', '.tiff')
SUPPORTED_EXPORT_FORMATS = ('.stl', '.ply', '.obj')
THUMBNAIL_DIR_NAME = ".thumbnail"
THUMBNAIL_EXTENSION = ".tif"

# 썸네일 생성 파라미터
DEFAULT_THUMBNAIL_MAX_SIZE = 500
DEFAULT_SAMPLE_SIZE = 20
DEFAULT_MAX_LEVEL = 10

# 스레드 설정
MIN_THREADS = 1
MAX_THREADS = 8
DEFAULT_THREADS = 4

# 메모리 설정
MEMORY_THRESHOLD_MB = 4096
IMAGE_MEMORY_ESTIMATE_MB = 50  # 이미지당 예상 메모리 사용량

# UI 설정
DEFAULT_WINDOW_WIDTH = 1200
DEFAULT_WINDOW_HEIGHT = 800
PROGRESS_UPDATE_INTERVAL_MS = 100

# 3D 렌더링
DEFAULT_THRESHOLD = 128
DEFAULT_ISO_VALUE = 127.5
DEFAULT_BACKGROUND_COLOR = (0.2, 0.2, 0.2)

# 로깅
LOG_DIR_NAME = "CTHarvester_logs"
LOG_MAX_BYTES = 10 * 1024 * 1024  # 10MB
LOG_BACKUP_COUNT = 5

# 버전 정보
from version import __version__, __version_info__
```

**Day 2-3**: 각 모듈의 인터페이스 정의

**core/thumbnail_manager.py** (초안):

```python
"""
썸네일 생성 및 관리 모듈
"""
from typing import Optional, Callable, List
from PyQt5.QtCore import QThreadPool, QMutex
import logging

logger = logging.getLogger(__name__)


class ThumbnailManager:
    """
    썸네일 생성 프로세스 관리

    Responsibilities:
    - 워커 스레드 생성 및 관리
    - 진행 상황 추적
    - 결과 수집 및 저장
    """

    def __init__(
        self,
        input_dir: str,
        output_dir: str,
        file_list: List[str],
        progress_callback: Optional[Callable[[float], None]] = None,
        error_callback: Optional[Callable[[str], None]] = None
    ):
        """
        Args:
            input_dir: 원본 이미지 디렉토리
            output_dir: 썸네일 저장 디렉토리
            file_list: 처리할 파일 목록
            progress_callback: 진행률 콜백 (0-100)
            error_callback: 에러 콜백
        """
        self.input_dir = input_dir
        self.output_dir = output_dir
        self.file_list = file_list
        self.progress_callback = progress_callback
        self.error_callback = error_callback

        self.threadpool = QThreadPool()
        self.lock = QMutex()
        self.results = {}
        self.completed_tasks = 0
        self.failed_tasks = 0

    def start_generation(self, level: int = 1) -> bool:
        """
        썸네일 생성 시작

        Args:
            level: 피라미드 레벨 (1부터 시작)

        Returns:
            시작 성공 여부
        """
        pass

    def cancel(self):
        """생성 작업 취소"""
        pass

    def wait_for_completion(self, timeout_ms: int = 30000) -> bool:
        """
        완료 대기

        Args:
            timeout_ms: 타임아웃 (밀리초)

        Returns:
            정상 완료 여부
        """
        pass

    def get_results(self) -> dict:
        """완료된 작업 결과 반환"""
        return self.results

    def get_statistics(self) -> dict:
        """처리 통계 정보 반환"""
        return {
            'total': len(self.file_list),
            'completed': self.completed_tasks,
            'failed': self.failed_tasks,
            'progress': (self.completed_tasks / len(self.file_list)) * 100
        }
```

**ui/main_window.py** (초안):

```python
"""
CTHarvester 메인 윈도우
"""
from PyQt5.QtWidgets import QMainWindow, QWidget, QVBoxLayout
from PyQt5.QtCore import Qt
import logging

logger = logging.getLogger(__name__)


class CTHarvesterMainWindow(QMainWindow):
    """
    메인 윈도우 클래스

    Responsibilities:
    - UI 레이아웃 구성
    - 메뉴/툴바 관리
    - 사용자 액션 처리
    - 다른 컴포넌트 조율
    """

    def __init__(self):
        super().__init__()
        self.init_attributes()
        self.init_ui()
        self.load_settings()

    def init_attributes(self):
        """속성 초기화"""
        self.current_dir = None
        self.file_list = []
        self.thumbnail_manager = None
        self.volume_manager = None

    def init_ui(self):
        """UI 초기화"""
        self._setup_window()
        self._create_menu_bar()
        self._create_toolbar()
        self._create_central_widget()
        self._create_status_bar()

    def _setup_window(self):
        """윈도우 기본 설정"""
        pass

    def _create_menu_bar(self):
        """메뉴바 생성"""
        pass

    def _create_toolbar(self):
        """툴바 생성"""
        pass

    def _create_central_widget(self):
        """중앙 위젯 생성"""
        pass

    def _create_status_bar(self):
        """상태바 생성"""
        pass

    # Action handlers
    def on_open_directory(self):
        """디렉토리 열기 액션"""
        pass

    def on_generate_thumbnails(self):
        """썸네일 생성 액션"""
        pass

    def on_crop_images(self):
        """이미지 크롭 액션"""
        pass

    def on_export_mesh(self):
        """3D 메시 내보내기 액션"""
        pass

    # Settings
    def load_settings(self):
        """설정 불러오기"""
        pass

    def save_settings(self):
        """설정 저장"""
        pass
```

#### Phase 1.2: 코드 이전 - Core 모듈 (5일)

**작업 순서** (의존성 낮은 것부터):
1. `utils/` 모듈 (독립적 유틸리티)
2. `core/progress_manager.py`
3. `core/image_processor.py`
4. `core/thumbnail_worker.py`
5. `core/thumbnail_manager.py`

**Day 4-5**: utils 모듈

**utils/image_utils.py**:

```python
"""
이미지 처리 유틸리티 함수
"""
from PIL import Image
import numpy as np
from typing import Tuple, Optional
import logging

logger = logging.getLogger(__name__)


def detect_bit_depth(image_path: str) -> int:
    """
    이미지 비트 깊이 감지

    Args:
        image_path: 이미지 파일 경로

    Returns:
        비트 깊이 (8 또는 16)

    Raises:
        ValueError: 지원하지 않는 이미지 형식
    """
    try:
        with Image.open(image_path) as img:
            if img.mode == 'I;16':
                return 16
            elif img.mode in ('L', 'RGB', 'RGBA'):
                return 8
            else:
                logger.warning(f"Unsupported image mode: {img.mode}, assuming 8-bit")
                return 8
    except Exception as e:
        logger.error(f"Failed to detect bit depth for {image_path}: {e}")
        raise ValueError(f"Cannot detect bit depth: {e}") from e


def load_image_as_array(
    image_path: str,
    target_dtype: Optional[np.dtype] = None
) -> np.ndarray:
    """
    이미지를 numpy 배열로 로드 (메모리 효율적)

    Args:
        image_path: 이미지 파일 경로
        target_dtype: 목표 데이터 타입 (None이면 자동)

    Returns:
        numpy 배열
    """
    try:
        with Image.open(image_path) as img:
            # 자동 dtype 결정
            if target_dtype is None:
                if img.mode == 'I;16':
                    target_dtype = np.uint16
                else:
                    target_dtype = np.uint8

            arr = np.array(img, dtype=target_dtype)
            return arr

    except Exception as e:
        logger.error(f"Failed to load image {image_path}: {e}")
        raise


def downsample_image(
    img_array: np.ndarray,
    factor: int = 2,
    method: str = 'subsample'
) -> np.ndarray:
    """
    이미지 다운샘플링

    Args:
        img_array: 입력 이미지 배열
        factor: 다운샘플링 비율 (기본 2)
        method: 'subsample' (빠름) 또는 'average' (품질 좋음)

    Returns:
        다운샘플링된 배열
    """
    if method == 'subsample':
        # 간단한 서브샘플링 (가장 빠름)
        return img_array[::factor, ::factor]

    elif method == 'average':
        # 블록 평균 (더 나은 품질)
        h, w = img_array.shape[:2]
        new_h, new_w = h // factor, w // factor

        # factor x factor 블록으로 리셰이프
        if len(img_array.shape) == 2:
            # 그레이스케일
            reshaped = img_array[:new_h*factor, :new_w*factor].reshape(
                new_h, factor, new_w, factor
            )
            return reshaped.mean(axis=(1, 3)).astype(img_array.dtype)
        else:
            # 컬러
            reshaped = img_array[:new_h*factor, :new_w*factor].reshape(
                new_h, factor, new_w, factor, -1
            )
            return reshaped.mean(axis=(1, 3)).astype(img_array.dtype)

    else:
        raise ValueError(f"Unknown method: {method}")


def average_images(
    img1: np.ndarray,
    img2: np.ndarray
) -> np.ndarray:
    """
    두 이미지 평균화 (오버플로 방지)

    Args:
        img1: 첫 번째 이미지
        img2: 두 번째 이미지

    Returns:
        평균 이미지
    """
    # 오버플로 방지를 위해 더 큰 dtype 사용
    if img1.dtype == np.uint8:
        temp_dtype = np.uint16
    elif img1.dtype == np.uint16:
        temp_dtype = np.uint32
    else:
        temp_dtype = np.float64

    # 평균 계산
    avg = (img1.astype(temp_dtype) + img2.astype(temp_dtype)) // 2

    return avg.astype(img1.dtype)


def save_image_from_array(
    img_array: np.ndarray,
    output_path: str,
    compress: bool = True
) -> bool:
    """
    numpy 배열을 이미지 파일로 저장

    Args:
        img_array: 저장할 이미지 배열
        output_path: 출력 파일 경로
        compress: 압축 여부 (TIFF)

    Returns:
        저장 성공 여부
    """
    try:
        # dtype에 따라 PIL 모드 결정
        if img_array.dtype == np.uint16:
            mode = 'I;16'
        elif img_array.dtype == np.uint8:
            mode = 'L' if len(img_array.shape) == 2 else 'RGB'
        else:
            logger.warning(f"Converting from {img_array.dtype} to uint8")
            img_array = img_array.astype(np.uint8)
            mode = 'L'

        img = Image.fromarray(img_array, mode=mode)

        # TIFF 압축 설정
        if output_path.lower().endswith('.tif') or output_path.lower().endswith('.tiff'):
            if compress:
                img.save(output_path, compression='tiff_deflate')
            else:
                img.save(output_path)
        else:
            img.save(output_path)

        return True

    except Exception as e:
        logger.error(f"Failed to save image to {output_path}: {e}")
        return False


def get_image_dimensions(image_path: str) -> Tuple[int, int]:
    """
    이미지 크기 조회 (전체 로드 없이)

    Args:
        image_path: 이미지 파일 경로

    Returns:
        (width, height)
    """
    try:
        with Image.open(image_path) as img:
            return img.size
    except Exception as e:
        logger.error(f"Failed to get image dimensions: {e}")
        raise
```

**utils/file_utils.py**:

```python
"""
파일 시스템 유틸리티
"""
import os
import re
from typing import List, Optional, Tuple
from pathlib import Path
import logging

from config.constants import SUPPORTED_IMAGE_EXTENSIONS, THUMBNAIL_DIR_NAME
from security.file_validator import SecureFileValidator, FileSecurityError

logger = logging.getLogger(__name__)


def find_image_files(
    directory: str,
    extensions: Optional[tuple] = None,
    recursive: bool = False
) -> List[str]:
    """
    디렉토리에서 이미지 파일 찾기

    Args:
        directory: 검색 디렉토리
        extensions: 허용할 확장자 (None이면 기본값)
        recursive: 하위 디렉토리 포함 여부

    Returns:
        파일명 목록 (정렬됨)
    """
    if extensions is None:
        extensions = SUPPORTED_IMAGE_EXTENSIONS

    try:
        # 보안 검증된 파일 목록
        file_list = SecureFileValidator.secure_listdir(directory)

        # 확장자 필터링
        filtered = [
            f for f in file_list
            if os.path.splitext(f)[1].lower() in extensions
        ]

        return sorted(filtered)

    except FileSecurityError as e:
        logger.error(f"Security error while listing directory: {e}")
        return []
    except Exception as e:
        logger.error(f"Failed to list directory {directory}: {e}")
        return []


def parse_filename(
    filename: str,
    pattern: Optional[str] = None
) -> Optional[Tuple[str, int, str]]:
    """
    파일명 파싱 (prefix, number, extension)

    Args:
        filename: 파일명
        pattern: 정규표현식 패턴 (None이면 기본)

    Returns:
        (prefix, number, extension) 또는 None

    Example:
        "scan_00123.tif" -> ("scan_", 123, "tif")
    """
    if pattern is None:
        # 기본 패턴: prefix + 숫자 + extension
        pattern = r'^(.+?)(\d+)\.([a-zA-Z]+)$'

    match = re.match(pattern, filename)
    if match:
        prefix, number_str, ext = match.groups()
        try:
            number = int(number_str)
            return (prefix, number, ext)
        except ValueError:
            logger.warning(f"Cannot parse number in filename: {filename}")
            return None
    else:
        return None


def create_thumbnail_directory(base_dir: str, level: int = 1) -> str:
    """
    썸네일 디렉토리 생성

    Args:
        base_dir: 기본 디렉토리
        level: 피라미드 레벨

    Returns:
        생성된 디렉토리 경로

    Raises:
        OSError: 디렉토리 생성 실패
    """
    if level == 1:
        thumb_dir = os.path.join(base_dir, THUMBNAIL_DIR_NAME)
    else:
        thumb_dir = os.path.join(base_dir, THUMBNAIL_DIR_NAME, f"level{level}")

    try:
        os.makedirs(thumb_dir, exist_ok=True)
        logger.info(f"Created thumbnail directory: {thumb_dir}")
        return thumb_dir
    except OSError as e:
        logger.error(f"Failed to create thumbnail directory: {e}")
        raise


def get_thumbnail_path(base_dir: str, level: int, index: int) -> str:
    """
    썸네일 파일 경로 생성

    Args:
        base_dir: 기본 디렉토리
        level: 피라미드 레벨
        index: 인덱스

    Returns:
        썸네일 파일 경로
    """
    from config.constants import THUMBNAIL_EXTENSION

    if level == 1:
        thumb_dir = os.path.join(base_dir, THUMBNAIL_DIR_NAME)
    else:
        thumb_dir = os.path.join(base_dir, THUMBNAIL_DIR_NAME, f"level{level}")

    filename = f"{index:06d}{THUMBNAIL_EXTENSION}"
    return os.path.join(thumb_dir, filename)


def clean_old_thumbnails(base_dir: str) -> bool:
    """
    이전 썸네일 디렉토리 삭제

    Args:
        base_dir: 기본 디렉토리

    Returns:
        삭제 성공 여부
    """
    import shutil

    thumb_dir = os.path.join(base_dir, THUMBNAIL_DIR_NAME)

    if os.path.exists(thumb_dir):
        try:
            shutil.rmtree(thumb_dir)
            logger.info(f"Removed old thumbnail directory: {thumb_dir}")
            return True
        except Exception as e:
            logger.error(f"Failed to remove thumbnail directory: {e}")
            return False
    return True


def get_directory_size(directory: str) -> int:
    """
    디렉토리 전체 크기 계산

    Args:
        directory: 디렉토리 경로

    Returns:
        바이트 단위 크기
    """
    total_size = 0
    try:
        for dirpath, dirnames, filenames in os.walk(directory):
            for filename in filenames:
                filepath = os.path.join(dirpath, filename)
                if os.path.exists(filepath):
                    total_size += os.path.getsize(filepath)
    except Exception as e:
        logger.error(f"Failed to calculate directory size: {e}")

    return total_size


def format_file_size(size_bytes: int) -> str:
    """
    파일 크기를 사람이 읽기 쉬운 형식으로 변환

    Args:
        size_bytes: 바이트 단위 크기

    Returns:
        포맷된 문자열 (예: "1.5 GB")
    """
    for unit in ['B', 'KB', 'MB', 'GB', 'TB']:
        if size_bytes < 1024.0:
            return f"{size_bytes:.2f} {unit}"
        size_bytes /= 1024.0
    return f"{size_bytes:.2f} PB"
```

**Day 6-8**: Core 모듈 이전

이 단계에서는 기존 `CTHarvester.py`에서 클래스/함수를 추출하여 새 모듈로 이동한다.

**이전 전략**:
1. 새 모듈에 코드 복사
2. 의존성 import 수정
3. 기존 파일에서 import 추가
4. 테스트 실행
5. 성공 시 기존 코드 제거

**core/thumbnail_worker.py** (완성):

```python
"""
썸네일 생성 워커
"""
from PyQt5.QtCore import QRunnable, QObject, pyqtSignal
import traceback
import logging

from utils.image_utils import (
    load_image_as_array,
    downsample_image,
    average_images,
    save_image_from_array
)
from security.file_validator import SecureFileValidator

logger = logging.getLogger(__name__)


class WorkerSignals(QObject):
    """워커 시그널"""
    started = pyqtSignal(int)                    # idx
    finished = pyqtSignal()
    error = pyqtSignal(int, str)                 # idx, error_msg
    result = pyqtSignal(int, object)             # idx, img_array
    progress = pyqtSignal(int, int, int)         # idx, current, total


class ThumbnailWorker(QRunnable):
    """
    썸네일 생성 워커 (QRunnable)

    두 개의 연속된 이미지를 평균화하고 1/2 크기로 다운샘플링
    """

    def __init__(
        self,
        idx: int,
        file1_path: str,
        file2_path: str = None,
        output_path: str = None,
        is_16bit: bool = False,
        progress_dialog=None
    ):
        """
        Args:
            idx: 워커 인덱스
            file1_path: 첫 번째 이미지 경로
            file2_path: 두 번째 이미지 경로 (None이면 단일 이미지 처리)
            output_path: 출력 파일 경로
            is_16bit: 16비트 이미지 여부
            progress_dialog: 진행 상황 다이얼로그 (취소 체크용)
        """
        super().__init__()
        self.idx = idx
        self.file1_path = file1_path
        self.file2_path = file2_path
        self.output_path = output_path
        self.is_16bit = is_16bit
        self.progress_dialog = progress_dialog

        self.signals = WorkerSignals()

    def run(self):
        """워커 실행 (스레드에서 호출됨)"""
        exception_occurred = False

        try:
            # 시작 시그널
            self.signals.started.emit(self.idx)

            # 취소 체크
            if self.progress_dialog and hasattr(self.progress_dialog, 'is_cancelled'):
                if self.progress_dialog.is_cancelled:
                    logger.debug(f"Worker {self.idx} cancelled before start")
                    return

            # 실제 작업 수행
            result = self._process_images()

            # 결과 확인
            if result is not None:
                # 저장
                if self.output_path:
                    success = save_image_from_array(result, self.output_path)
                    if not success:
                        raise RuntimeError(f"Failed to save to {self.output_path}")

                # 결과 시그널
                self.signals.result.emit(self.idx, result)
            else:
                raise RuntimeError("Processing returned None")

        except KeyboardInterrupt:
            logger.warning(f"Worker {self.idx} interrupted")
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
            # 항상 finished 시그널 발송
            self.signals.finished.emit()

            if exception_occurred:
                logger.debug(f"Worker {self.idx} finished with errors")
            else:
                logger.debug(f"Worker {self.idx} finished successfully")

    def _process_images(self):
        """이미지 처리 (내부 메서드)"""
        try:
            # 첫 번째 이미지 로드
            img1 = load_image_as_array(
                self.file1_path,
                target_dtype=np.uint16 if self.is_16bit else np.uint8
            )

            # 두 번째 이미지 처리
            if self.file2_path:
                img2 = load_image_as_array(
                    self.file2_path,
                    target_dtype=np.uint16 if self.is_16bit else np.uint8
                )

                # 평균화
                img_avg = average_images(img1, img2)
                del img1, img2  # 메모리 해제
            else:
                # 단일 이미지
                img_avg = img1

            # 다운샘플링
            result = downsample_image(img_avg, factor=2, method='subsample')
            del img_avg

            return result

        except Exception as e:
            logger.error(f"Image processing failed in worker {self.idx}: {e}")
            raise
```

#### Phase 1.3: 코드 이전 - UI 모듈 (5일)

**Day 9-13**: UI 컴포넌트 분리

**ui/widgets/object_viewer_2d.py** 생성 및 이전
**ui/widgets/mcube_widget.py** 생성 및 이전
**ui/dialogs.py** 생성 및 이전
**ui/main_window.py** 완성

#### Phase 1.4: 통합 및 테스트 (3일)

**Day 14-16**:
1. `main.py` 작성
2. 모든 import 경로 수정
3. 통합 테스트 실행
4. 버그 수정

**main.py**:

```python
"""
CTHarvester - CT Image Stack Preprocessing Tool
Entry Point
"""
import sys
import os
from PyQt5.QtWidgets import QApplication, QMessageBox
import logging

# 프로젝트 루트를 Python 경로에 추가
project_root = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, project_root)

from CTLogger import setup_logger
from ui.main_window import CTHarvesterMainWindow
from config.constants import APP_NAME, APP_ORGANIZATION
from version import __version__

logger = setup_logger(__name__)


def main():
    """메인 함수"""
    logger.info(f"Starting {APP_NAME} v{__version__}")

    # Qt Application 생성
    app = QApplication(sys.argv)
    app.setApplicationName(APP_NAME)
    app.setOrganizationName(APP_ORGANIZATION)
    app.setApplicationVersion(__version__)

    try:
        # 메인 윈도우 생성
        window = CTHarvesterMainWindow()

        # 초기화 확인
        if not window.check_initialization():
            logger.critical("Application initialization failed")
            QMessageBox.critical(
                None,
                "Initialization Error",
                "CTHarvester failed to initialize.\n"
                "Please check the log file for details."
            )
            return 1

        # 윈도우 표시
        window.show()

        # 이벤트 루프 시작
        return app.exec_()

    except Exception as e:
        logger.critical(f"Fatal error: {e}", exc_info=True)

        QMessageBox.critical(
            None,
            "Fatal Error",
            f"An unexpected error occurred:\n{e}\n\n"
            "Please report this issue to the developers."
        )

        return 1


if __name__ == '__main__':
    exit_code = main()
    logger.info(f"Application exiting with code {exit_code}")
    sys.exit(exit_code)
```

### 검증 방법

1. **정적 분석**
   ```bash
   # import 순환 참조 체크
   find . -name "*.py" -exec python -m py_compile {} \;

   # 코드 복잡도 측정
   radon cc -s -a .
   ```

2. **단위 테스트**
   - 각 모듈별 독립 테스트
   - 커버리지 70% 이상

3. **통합 테스트**
   - 전체 워크플로우 테스트
   - 기존 기능 회귀 테스트

---

## 개선사항 2: 성능 병목 현상

### 현황 분석

**문제점**:
1. 단일 스레드 강제 사용 (라인 948-952)
2. PIL 기반 처리가 느림 (Rust 대비 8-10배)
3. ETA 계산 오버헤드

**성능 지표**:
- 현재: 3000 이미지 처리 시 9-10분 (Python)
- Rust: 2-3분
- 목표: 4-5분 (최적화된 Python 멀티스레드)

### 수정 계획

#### Phase 2.1: 멀티스레딩 복원 및 최적화 (치명적 문제 수정 후)

이 부분은 "치명적 문제 2: 스레드 안전성"에서 이미 다뤘으므로 생략.

#### Phase 2.2: NumPy 최적화 (3일)

**Day 17-19**: 이미지 처리 로직 최적화

**utils/image_utils.py** 추가:

```python
def downsample_image_fast(img_array: np.ndarray) -> np.ndarray:
    """
    고속 다운샘플링 (Numba JIT 컴파일)

    약 30% 성능 향상
    """
    try:
        import numba

        @numba.jit(nopython=True, parallel=True)
        def _downsample_core(arr):
            h, w = arr.shape
            new_h, new_w = h // 2, w // 2
            result = np.empty((new_h, new_w), dtype=arr.dtype)

            for i in numba.prange(new_h):
                for j in range(new_w):
                    # 2x2 블록 평균
                    result[i, j] = (
                        arr[i*2, j*2] + arr[i*2, j*2+1] +
                        arr[i*2+1, j*2] + arr[i*2+1, j*2+1]
                    ) // 4

            return result

        return _downsample_core(img_array)

    except ImportError:
        logger.warning("Numba not available, using standard downsampling")
        return img_array[::2, ::2]
```

**requirements.txt에 추가**:
```
numba>=0.58.0
```

#### Phase 2.3: Rust 모듈 개선 (5일)

**Day 20-24**: Rust 코드 리팩토링

**src/lib.rs**:

```rust
use pyo3::prelude::*;
use pyo3::exceptions::PyRuntimeError;
use rayon::prelude::*;
use image::{DynamicImage, GenericImageView, ImageBuffer, Luma};
use std::path::{Path, PathBuf};
use std::sync::{Arc, Mutex};

/// 썸네일 생성 진행 상황
#[pyclass]
struct ThumbnailProgress {
    #[pyo3(get)]
    completed: usize,
    #[pyo3(get)]
    total: usize,
    #[pyo3(get)]
    failed: usize,
}

/// 썸네일 생성 에러
#[derive(Debug)]
enum ThumbError {
    Io(std::io::Error),
    Image(image::ImageError),
    InvalidInput(String),
}

impl std::fmt::Display for ThumbError {
    fn fmt(&self, f: &mut std::fmt::Formatter) -> std::fmt::Result {
        match self {
            ThumbError::Io(e) => write!(f, "IO error: {}", e),
            ThumbError::Image(e) => write!(f, "Image error: {}", e),
            ThumbError::InvalidInput(s) => write!(f, "Invalid input: {}", s),
        }
    }
}

impl From<ThumbError> for PyErr {
    fn from(err: ThumbError) -> PyErr {
        PyRuntimeError::new_err(err.to_string())
    }
}

/// 이미지 쌍 처리
fn process_image_pair(
    file1: &Path,
    file2: Option<&Path>,
    output: &Path,
    is_16bit: bool,
) -> Result<(), ThumbError> {
    // 첫 번째 이미지 로드
    let img1 = image::open(file1)
        .map_err(ThumbError::Image)?;

    let (width, height) = img1.dimensions();

    // 두 번째 이미지 처리
    let averaged = if let Some(file2_path) = file2 {
        let img2 = image::open(file2_path)
            .map_err(ThumbError::Image)?;

        // 평균화 (16비트 지원)
        average_images(&img1, &img2, is_16bit)?
    } else {
        img1
    };

    // 다운샘플링
    let downsampled = averaged.resize(
        width / 2,
        height / 2,
        image::imageops::FilterType::Nearest
    );

    // 저장
    downsampled.save(output)
        .map_err(ThumbError::Image)?;

    Ok(())
}

/// 두 이미지 평균화
fn average_images(
    img1: &DynamicImage,
    img2: &DynamicImage,
    is_16bit: bool,
) -> Result<DynamicImage, ThumbError> {
    let (width, height) = img1.dimensions();

    if img2.dimensions() != (width, height) {
        return Err(ThumbError::InvalidInput(
            "Image dimensions don't match".to_string()
        ));
    }

    if is_16bit {
        // 16비트 처리
        let gray1 = img1.to_luma16();
        let gray2 = img2.to_luma16();

        let result: ImageBuffer<Luma<u16>, Vec<u16>> =
            ImageBuffer::from_fn(width, height, |x, y| {
                let p1 = gray1.get_pixel(x, y)[0] as u32;
                let p2 = gray2.get_pixel(x, y)[0] as u32;
                Luma([(p1 + p2) / 2] as u16])
            });

        Ok(DynamicImage::ImageLuma16(result))
    } else {
        // 8비트 처리
        let gray1 = img1.to_luma8();
        let gray2 = img2.to_luma8();

        let result: ImageBuffer<Luma<u8>, Vec<u8>> =
            ImageBuffer::from_fn(width, height, |x, y| {
                let p1 = gray1.get_pixel(x, y)[0] as u16;
                let p2 = gray2.get_pixel(x, y)[0] as u16;
                Luma([((p1 + p2) / 2) as u8])
            });

        Ok(DynamicImage::ImageLuma8(result))
    }
}

/// 썸네일 생성 (병렬 처리)
#[pyfunction]
fn generate_thumbnails(
    input_files: Vec<(String, Option<String>)>,  // (file1, file2?)
    output_files: Vec<String>,
    is_16bit: bool,
    num_threads: Option<usize>,
) -> PyResult<ThumbnailProgress> {
    // 스레드 풀 설정
    if let Some(threads) = num_threads {
        rayon::ThreadPoolBuilder::new()
            .num_threads(threads)
            .build_global()
            .map_err(|e| PyRuntimeError::new_err(e.to_string()))?;
    }

    let total = input_files.len();
    let completed = Arc::new(Mutex::new(0usize));
    let failed = Arc::new(Mutex::new(0usize));

    // 병렬 처리
    input_files.par_iter()
        .zip(output_files.par_iter())
        .for_each(|((file1, file2_opt), output)| {
            let file2 = file2_opt.as_ref().map(|s| Path::new(s));

            let result = process_image_pair(
                Path::new(file1),
                file2,
                Path::new(output),
                is_16bit,
            );

            match result {
                Ok(_) => {
                    let mut c = completed.lock().unwrap();
                    *c += 1;
                },
                Err(e) => {
                    eprintln!("Failed to process {}: {}", file1, e);
                    let mut f = failed.lock().unwrap();
                    *f += 1;
                }
            }
        });

    let completed_count = *completed.lock().unwrap();
    let failed_count = *failed.lock().unwrap();

    Ok(ThumbnailProgress {
        completed: completed_count,
        total,
        failed: failed_count,
    })
}

/// Python 모듈
#[pymodule]
fn ctharvester_rs(_py: Python, m: &PyModule) -> PyResult<()> {
    m.add_function(wrap_pyfunction!(generate_thumbnails, m)?)?;
    m.add_class::<ThumbnailProgress>()?;
    Ok(())
}
```

**Cargo.toml 업데이트**:

```toml
[dependencies]
pyo3 = { version = "0.22", features = ["extension-module"] }
image = "0.25"
rayon = "1.10"

[profile.release]
lto = true
codegen-units = 1
opt-level = 3
```

### 검증 방법

1. **벤치마크**
   ```python
   # benchmark_thumbnail.py
   import time

   # Python 싱글 스레드
   # Python 멀티 스레드
   # Rust 모듈

   # 각 3회 반복 평균
   ```

2. **프로파일링**
   ```bash
   python -m cProfile -o profile.stats main.py
   python -m pstats profile.stats
   ```

---

## 개선사항 3: Rust 통합 문제

### 현황 분석

**문제점**:
1. `unwrap()` 남용 → 패닉 가능성
2. 에러 전파 불완전
3. 백업 파일이 Git에 포함됨

### 수정 계획

#### Phase 3.1: Rust 에러 처리 개선 (2일)

위 Phase 2.3에서 이미 개선됨 (`Result` 타입 사용).

#### Phase 3.2: Git 정리 (1일)

```bash
# 백업 파일 제거
git rm src/lib_final_backup_*.rs

# .gitignore 업데이트
echo "*.backup.rs" >> .gitignore
echo "**/*_backup_*.rs" >> .gitignore
```

---

## 개선사항 4: 로깅 및 디버깅

### 수정 계획

#### Phase 4.1: 로그 레벨 동적 조정 (2일)

**CTLogger.py 개선**:

```python
def setup_logger(
    name,
    log_dir=None,
    level=logging.INFO,
    console_level=None,
    format_string=None
):
    """
    개선된 로거 설정

    환경변수 지원:
    - CTHARVESTER_LOG_LEVEL: 파일 로그 레벨
    - CTHARVESTER_CONSOLE_LEVEL: 콘솔 로그 레벨
    """
    # 환경변수에서 레벨 읽기
    env_level = os.getenv('CTHARVESTER_LOG_LEVEL')
    if env_level:
        level = getattr(logging, env_level.upper(), logging.INFO)

    env_console_level = os.getenv('CTHARVESTER_CONSOLE_LEVEL')
    if env_console_level:
        console_level = getattr(logging, env_console_level.upper(), level)
    elif console_level is None:
        console_level = level

    # 나머지 기존 코드...
```

#### Phase 4.2: 구조화된 로깅 (3일)

```python
# utils/logger_config.py
import logging
import json
from datetime import datetime

class StructuredLogger:
    """구조화된 로깅 (JSON)"""

    def __init__(self, logger):
        self.logger = logger

    def log_event(self, event_type, **kwargs):
        """이벤트 로깅"""
        event = {
            'timestamp': datetime.now().isoformat(),
            'event_type': event_type,
            **kwargs
        }
        self.logger.info(json.dumps(event))

    def log_performance(self, operation, duration, **kwargs):
        """성능 로깅"""
        self.log_event(
            'performance',
            operation=operation,
            duration_ms=duration * 1000,
            **kwargs
        )

    def log_error(self, error_type, message, **kwargs):
        """에러 로깅"""
        self.log_event(
            'error',
            error_type=error_type,
            message=message,
            **kwargs
        )
```

---

## 개선사항 5: 테스트 커버리지

### 목표

- 단위 테스트 커버리지: 70% 이상
- 통합 테스트: 주요 워크플로우 100%
- 성능 테스트: 회귀 방지

### 수정 계획

#### Phase 5.1: 테스트 인프라 구축 (2일)

**pytest 설정**:

```ini
# pytest.ini
[pytest]
testpaths = tests
python_files = test_*.py
python_classes = Test*
python_functions = test_*

addopts =
    --verbose
    --cov=.
    --cov-report=html
    --cov-report=term-missing
    --cov-fail-under=70

markers =
    unit: Unit tests
    integration: Integration tests
    slow: Slow tests
    performance: Performance tests
```

**conftest.py**:

```python
# tests/conftest.py
import pytest
import tempfile
import shutil
from pathlib import Path
import numpy as np
from PIL import Image

@pytest.fixture
def temp_dir():
    """임시 디렉토리 생성"""
    tmp = tempfile.mkdtemp()
    yield tmp
    shutil.rmtree(tmp)

@pytest.fixture
def sample_images_8bit(temp_dir):
    """8비트 테스트 이미지 생성"""
    images = []
    for i in range(10):
        img = np.random.randint(0, 256, (512, 512), dtype=np.uint8)
        path = Path(temp_dir) / f"test_{i:04d}.png"
        Image.fromarray(img).save(path)
        images.append(str(path))
    return images

@pytest.fixture
def sample_images_16bit(temp_dir):
    """16비트 테스트 이미지 생성"""
    images = []
    for i in range(10):
        img = np.random.randint(0, 65536, (512, 512), dtype=np.uint16)
        path = Path(temp_dir) / f"test_{i:04d}.tif"
        Image.fromarray(img, mode='I;16').save(path)
        images.append(str(path))
    return images
```

#### Phase 5.2: 단위 테스트 작성 (7일)

**tests/unit/test_image_utils.py**:

```python
import pytest
import numpy as np
from utils.image_utils import (
    detect_bit_depth,
    load_image_as_array,
    downsample_image,
    average_images,
    save_image_from_array
)

class TestImageUtils:

    def test_detect_bit_depth_8bit(self, sample_images_8bit):
        assert detect_bit_depth(sample_images_8bit[0]) == 8

    def test_detect_bit_depth_16bit(self, sample_images_16bit):
        assert detect_bit_depth(sample_images_16bit[0]) == 16

    def test_load_image_as_array(self, sample_images_8bit):
        arr = load_image_as_array(sample_images_8bit[0])
        assert isinstance(arr, np.ndarray)
        assert arr.dtype == np.uint8
        assert arr.shape == (512, 512)

    def test_downsample_image_subsample(self):
        img = np.random.randint(0, 256, (512, 512), dtype=np.uint8)
        result = downsample_image(img, factor=2, method='subsample')
        assert result.shape == (256, 256)

    def test_downsample_image_average(self):
        img = np.random.randint(0, 256, (512, 512), dtype=np.uint8)
        result = downsample_image(img, factor=2, method='average')
        assert result.shape == (256, 256)

    def test_average_images_8bit(self):
        img1 = np.full((100, 100), 100, dtype=np.uint8)
        img2 = np.full((100, 100), 200, dtype=np.uint8)
        result = average_images(img1, img2)
        assert result.dtype == np.uint8
        assert np.all(result == 150)

    def test_average_images_16bit(self):
        img1 = np.full((100, 100), 10000, dtype=np.uint16)
        img2 = np.full((100, 100), 20000, dtype=np.uint16)
        result = average_images(img1, img2)
        assert result.dtype == np.uint16
        assert np.all(result == 15000)

    def test_save_and_load_roundtrip(self, temp_dir):
        original = np.random.randint(0, 256, (256, 256), dtype=np.uint8)
        path = f"{temp_dir}/test.tif"

        # 저장
        assert save_image_from_array(original, path)

        # 로드
        loaded = load_image_as_array(path)

        # 비교
        np.testing.assert_array_equal(original, loaded)
```

**tests/unit/test_file_utils.py**:

```python
import pytest
from utils.file_utils import (
    find_image_files,
    parse_filename,
    create_thumbnail_directory,
    get_thumbnail_path
)

class TestFileUtils:

    def test_find_image_files(self, sample_images_8bit):
        import os
        directory = os.path.dirname(sample_images_8bit[0])
        files = find_image_files(directory)
        assert len(files) == 10
        assert all(f.endswith('.png') for f in files)

    def test_parse_filename(self):
        result = parse_filename("scan_00123.tif")
        assert result == ("scan_", 123, "tif")

        result = parse_filename("image0042.png")
        assert result == ("image", 42, "png")

    def test_create_thumbnail_directory(self, temp_dir):
        thumb_dir = create_thumbnail_directory(temp_dir, level=1)
        assert os.path.exists(thumb_dir)
        assert thumb_dir.endswith(".thumbnail")

    def test_get_thumbnail_path(self, temp_dir):
        path = get_thumbnail_path(temp_dir, level=1, index=42)
        assert "000042.tif" in path
```

**tests/unit/test_thumbnail_worker.py**:

```python
import pytest
from PyQt5.QtCore import QThreadPool
from core.thumbnail_worker import ThumbnailWorker, WorkerSignals

class TestThumbnailWorker:

    def test_worker_signals(self):
        signals = WorkerSignals()
        assert hasattr(signals, 'started')
        assert hasattr(signals, 'finished')
        assert hasattr(signals, 'error')
        assert hasattr(signals, 'result')

    def test_worker_creation(self, sample_images_8bit, temp_dir):
        worker = ThumbnailWorker(
            idx=0,
            file1_path=sample_images_8bit[0],
            file2_path=sample_images_8bit[1],
            output_path=f"{temp_dir}/output.tif",
            is_16bit=False
        )
        assert worker.idx == 0
        assert worker.file1_path == sample_images_8bit[0]

    @pytest.mark.slow
    def test_worker_execution(self, sample_images_8bit, temp_dir):
        import time

        results = []
        errors = []
        finished = []

        def on_result(idx, img):
            results.append((idx, img))

        def on_error(idx, msg):
            errors.append((idx, msg))

        def on_finished():
            finished.append(True)

        worker = ThumbnailWorker(
            idx=0,
            file1_path=sample_images_8bit[0],
            file2_path=sample_images_8bit[1],
            output_path=f"{temp_dir}/output.tif",
            is_16bit=False
        )

        worker.signals.result.connect(on_result)
        worker.signals.error.connect(on_error)
        worker.signals.finished.connect(on_finished)

        # 실행
        pool = QThreadPool()
        pool.start(worker)
        pool.waitForDone(5000)

        # 검증
        assert len(finished) == 1
        assert len(errors) == 0
        assert len(results) == 1
        assert os.path.exists(f"{temp_dir}/output.tif")
```

#### Phase 5.3: 통합 테스트 작성 (5일)

**tests/integration/test_thumbnail_generation.py**:

```python
import pytest
from PyQt5.QtWidgets import QApplication
from core.thumbnail_manager import ThumbnailManager
from utils.file_utils import find_image_files

@pytest.fixture(scope="module")
def qapp():
    """Qt Application"""
    app = QApplication.instance()
    if app is None:
        app = QApplication([])
    yield app

class TestThumbnailGeneration:

    @pytest.mark.integration
    def test_full_thumbnail_generation(self, qapp, sample_images_8bit, temp_dir):
        """전체 썸네일 생성 프로세스 테스트"""
        import os

        input_dir = os.path.dirname(sample_images_8bit[0])
        output_dir = os.path.join(temp_dir, "thumbnails")
        os.makedirs(output_dir, exist_ok=True)

        file_list = find_image_files(input_dir)

        progress_values = []
        def on_progress(value):
            progress_values.append(value)

        manager = ThumbnailManager(
            input_dir=input_dir,
            output_dir=output_dir,
            file_list=file_list,
            progress_callback=on_progress
        )

        # 생성 시작
        success = manager.start_generation(level=1)
        assert success

        # 완료 대기
        completed = manager.wait_for_completion(timeout_ms=10000)
        assert completed

        # 결과 확인
        stats = manager.get_statistics()
        assert stats['completed'] == len(file_list) // 2
        assert stats['failed'] == 0

        # 진행률 확인
        assert len(progress_values) > 0
        assert progress_values[-1] == 100.0

        # 파일 확인
        output_files = os.listdir(output_dir)
        assert len(output_files) == len(file_list) // 2
```

#### Phase 5.4: 성능 테스트 (3일)

**tests/performance/test_benchmark.py**:

```python
import pytest
import time
from utils.image_utils import downsample_image
import numpy as np

class TestPerformance:

    @pytest.mark.performance
    def test_downsample_performance(self):
        """다운샘플링 성능 테스트"""
        img = np.random.randint(0, 256, (4096, 4096), dtype=np.uint8)

        iterations = 100
        start = time.time()

        for _ in range(iterations):
            result = downsample_image(img, factor=2, method='subsample')

        duration = time.time() - start
        avg_time = duration / iterations

        print(f"\nAverage downsample time: {avg_time*1000:.2f} ms")

        # 성능 기준: 100ms 이하
        assert avg_time < 0.1

    @pytest.mark.performance
    def test_thumbnail_generation_speed(self, sample_images_8bit):
        """썸네일 생성 속도 테스트"""
        from core.thumbnail_manager import ThumbnailManager
        import os

        input_dir = os.path.dirname(sample_images_8bit[0])
        file_list = sample_images_8bit

        start = time.time()

        manager = ThumbnailManager(
            input_dir=input_dir,
            output_dir="/tmp/thumb_perf",
            file_list=file_list
        )

        manager.start_generation(level=1)
        manager.wait_for_completion()

        duration = time.time() - start

        images_per_sec = len(file_list) / duration
        print(f"\nThumbnail generation: {images_per_sec:.1f} images/sec")

        # 성능 기준: 최소 10 images/sec
        assert images_per_sec > 10
```

---

## 개선사항 6: 의존성 관리

### 수정 계획

#### Phase 6.1: requirements.txt 버전 고정 (1일)

```txt
# requirements.txt
# Core dependencies
pyqt5>=5.15.0,<6.0.0
pyopengl>=3.1.5,<4.0.0
pyopengl-accelerate>=3.1.5,<4.0.0

# Image processing
pillow>=10.0.0,<11.0.0
numpy>=1.24.0,<2.0.0

# Scientific computing
scipy>=1.10.0,<2.0.0
pymcubes>=0.1.4,<1.0.0

# Performance (optional)
numba>=0.58.0,<1.0.0; platform_machine != "aarch64"

# Utilities
superqt>=0.6.0,<1.0.0
semver>=3.0.0,<4.0.0
psutil>=5.9.0,<6.0.0

# Build
maturin>=1.4.0,<2.0.0

# Development dependencies (install with: pip install -r requirements-dev.txt)
```

```txt
# requirements-dev.txt
-r requirements.txt

# Testing
pytest>=7.4.0,<8.0.0
pytest-cov>=4.1.0,<5.0.0
pytest-qt>=4.2.0,<5.0.0
pytest-benchmark>=4.0.0,<5.0.0

# Code quality
black>=23.12.0,<24.0.0
flake8>=6.1.0,<7.0.0
mypy>=1.7.0,<2.0.0
pylint>=3.0.0,<4.0.0

# Profiling
memory-profiler>=0.61.0,<1.0.0
py-spy>=0.3.14,<1.0.0

# Documentation
sphinx>=7.2.0,<8.0.0
sphinx-rtd-theme>=2.0.0,<3.0.0
```

#### Phase 6.2: Cargo.toml 정리 (1일)

```toml
[package]
name = "ctharvester_rs"
version = "0.2.3"
edition = "2021"
rust-version = "1.75"
authors = ["Jikhan Jung <your@email.com>"]
description = "High-performance thumbnail generation for CTHarvester"
license = "MIT"

[lib]
name = "ctharvester_rs"
crate-type = ["cdylib"]

[dependencies]
pyo3 = { version = "0.22", features = ["extension-module"] }
numpy = "0.22"
image = "0.25"
rayon = "1.10"

[profile.release]
opt-level = 3
lto = true
codegen-units = 1
strip = true

[profile.dev]
opt-level = 0
```

---

## 전체 일정

### 개선사항별 소요 기간

| 개선사항 | Phase | 소요 기간 | 시작 조건 |
|---------|-------|---------|----------|
| 1. 코드 구조 | 1.1 구조 생성 | 3일 | 치명적 문제 완료 |
|  | 1.2 Core 이전 | 5일 | Phase 1.1 완료 |
|  | 1.3 UI 이전 | 5일 | Phase 1.2 완료 |
|  | 1.4 통합 테스트 | 3일 | Phase 1.3 완료 |
| 2. 성능 최적화 | 2.1 멀티스레딩 | 0일 | 치명적 문제에 포함 |
|  | 2.2 NumPy 최적화 | 3일 | Phase 1 완료 |
|  | 2.3 Rust 개선 | 5일 | Phase 2.2 완료 |
| 3. Rust 통합 | 3.1 에러 처리 | 0일 | Phase 2.3에 포함 |
|  | 3.2 Git 정리 | 1일 | 언제든지 |
| 4. 로깅 | 4.1 동적 조정 | 2일 | Phase 1 완료 |
|  | 4.2 구조화 로깅 | 3일 | Phase 4.1 완료 |
| 5. 테스트 | 5.1 인프라 | 2일 | Phase 1 완료 |
|  | 5.2 단위 테스트 | 7일 | Phase 5.1 완료 |
|  | 5.3 통합 테스트 | 5일 | Phase 5.2 완료 |
|  | 5.4 성능 테스트 | 3일 | Phase 5.3 완료 |
| 6. 의존성 | 6.1 requirements | 1일 | 언제든지 |
|  | 6.2 Cargo | 1일 | 언제든지 |

**총 소요 기간**: 약 49일 (약 10주)

### 단계별 일정

#### Stage 1: 기반 구축 (Week 1-4, 16일)
- Week 1 (Day 1-3): 코드 구조 생성, utils 모듈
- Week 2 (Day 4-8): Core 모듈 이전
- Week 3 (Day 9-13): UI 모듈 이전
- Week 4 (Day 14-16): 통합 및 검증

#### Stage 2: 성능 최적화 (Week 5-6, 8일)
- Week 5 (Day 17-19): NumPy 최적화
- Week 5-6 (Day 20-24): Rust 모듈 개선

#### Stage 3: 품질 향상 (Week 7-8, 10일)
- Week 7 (Day 25-26): Git 정리, requirements 고정
- Week 7 (Day 27-28): 로깅 동적 조정
- Week 8 (Day 29-31): 구조화 로깅, Cargo 정리
- Week 8 (Day 32-33): 테스트 인프라
- Week 8 (Day 34): 버퍼

#### Stage 4: 테스트 작성 (Week 9-10, 15일)
- Week 9 (Day 35-41): 단위 테스트
- Week 10 (Day 42-46): 통합 테스트
- Week 10 (Day 47-49): 성능 테스트

### 병렬 작업 가능

다음 작업들은 병렬로 진행 가능:
- 개선사항 3.2 (Git 정리) - 언제든지
- 개선사항 6 (의존성 관리) - 언제든지
- 개선사항 4 (로깅) - 코드 이전 중에도 가능

## 성공 기준

### 정량적 지표

| 항목 | 현재 | 목표 | 측정 방법 |
|------|------|------|----------|
| 최대 파일 크기 | 4,694줄 | <500줄 | `wc -l` |
| 파일당 평균 줄 수 | 4,694줄 | <300줄 | `radon raw` |
| 순환 복잡도 | 높음 | <10 (평균) | `radon cc` |
| 코드 중복률 | 높음 | <5% | `pylint --enable=duplicate-code` |
| 테스트 커버리지 | <10% | >70% | `pytest --cov` |
| 처리 속도 (3000 이미지) | 9-10분 | 4-5분 | 벤치마크 |
| 메모리 사용량 | 불안정 | <4GB | `memory_profiler` |

### 정성적 지표

1. **코드 가독성**: 신규 개발자가 3일 내 코드 이해 가능
2. **유지보수성**: 기능 추가 시 수정 파일 수 <5개
3. **버그 추적**: 에러 발생 시 로그만으로 원인 파악 가능
4. **문서화**: 모든 public API에 docstring 존재

## 위험 요소 및 대응

### 위험 1: 코드 이전 중 기능 회귀
- **확률**: 높음
- **영향**: 심각
- **대응**:
  - 이전 전 전체 테스트 스위트 작성
  - 단계별 검증
  - Git branch 전략 (feature → develop → main)
  - 각 Phase마다 전체 테스트 실행

### 위험 2: 일정 지연
- **확률**: 중간
- **영향**: 중간
- **대응**:
  - 2주마다 검토 미팅
  - 우선순위에 따라 조정
  - 병렬 작업 최대화

### 위험 3: 성능 저하
- **확률**: 낮음
- **영향**: 높음
- **대응**:
  - 각 Phase 후 벤치마크
  - 성능 저하 시 즉시 롤백
  - 프로파일링으로 병목 구간 식별

### 위험 4: 의존성 충돌
- **확률**: 낮음
- **영향**: 중간
- **대응**:
  - 가상 환경 사용
  - CI/CD에서 clean install 테스트
  - 버전 범위 신중히 설정

## 다음 단계

이 계획 완료 후:

1. **권장 개선사항** (Nice-to-have) 착수
   - UI/UX 개선
   - 크로스 플랫폼 빌드
   - 문서화

2. **지속적 개선**
   - 코드 리뷰 프로세스 확립
   - CI/CD 파이프라인 강화
   - 모니터링 시스템 구축

3. **커뮤니티**
   - 오픈소스 기여 가이드 작성
   - Issue 템플릿 생성
   - 개발 로드맵 공개

## 참고 자료

### 코드 품질
- [Clean Code in Python](https://realpython.com/python-clean-code/)
- [The Zen of Python (PEP 20)](https://www.python.org/dev/peps/pep-0020/)
- [Google Python Style Guide](https://google.github.io/styleguide/pyguide.html)

### 테스팅
- [pytest Documentation](https://docs.pytest.org/)
- [Testing Qt Applications](https://doc.qt.io/qt-5/qtest-overview.html)
- [Python Testing Best Practices](https://realpython.com/python-testing/)

### 성능 최적화
- [NumPy Performance Tips](https://numpy.org/doc/stable/user/performance.html)
- [Numba Documentation](https://numba.pydata.org/)
- [Rust Performance Book](https://nnethercote.github.io/perf-book/)

### 소프트웨어 설계
- [SOLID Principles](https://en.wikipedia.org/wiki/SOLID)
- [Design Patterns in Python](https://refactoring.guru/design-patterns/python)
- [Architectural Patterns](https://www.oreilly.com/library/view/software-architecture-patterns/9781491971437/)

## 결론

이 계획은 CTHarvester의 코드 품질을 크게 향상시킬 것이다:

**주요 개선점**:
1. 모놀리식 구조 → 모듈화된 구조 (유지보수성 10배 향상)
2. 단일 스레드 → 멀티 스레드 (성능 4-8배 향상)
3. 테스트 <10% → >70% (안정성 대폭 향상)
4. 불완전한 에러 처리 → 포괄적 에러 처리
5. 하드코딩된 설정 → 동적 설정

**예상 효과**:
- 신규 개발자 온보딩 시간: 1주 → 3일
- 버그 수정 시간: 평균 4시간 → 1시간
- 기능 추가 시간: 평균 2일 → 4시간
- 회귀 버그 감소: 70% 이상

치명적 문제 수정 후 이 계획을 단계적으로 실행하면 CTHarvester는 견고하고 확장 가능한 프로젝트로 발전할 것이다.