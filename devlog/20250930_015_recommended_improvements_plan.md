# 권장 개선사항 계획

날짜: 2025-09-30
작성자: Code Review Analysis

## 개요

치명적 문제와 중요 개선사항 완료 후 착수할 권장(Nice-to-have) 개선사항들에 대한 계획이다. 이 개선사항들은 사용자 경험, 개발자 경험, 프로젝트 성숙도를 향상시킬 것이다.

## 전제 조건

이 계획은 다음 작업이 완료된 후 시작한다:
- ✅ 치명적 문제 4건 모두 수정 완료
- ✅ 중요 개선사항 6건 모두 완료
- ✅ 코드 모듈화 완료
- ✅ 테스트 커버리지 70% 이상 달성

## 개선사항 1: UI/UX 개선

### 현황 분석

**문제점**:
1. 진행률 표시가 복잡 (3단계 샘플링 + 가중치 계산)
2. 3D 렌더링 시 UI 블로킹 (라인 3190-3192)
3. 에러 메시지가 기술적이고 사용자 친화적이지 않음
4. 다국어 지원 (한국어/영어)이 있으나 불완전
5. 단축키 부족
6. 툴팁/도움말 부족

**사용자 피드백 (예상)**:
- "진행률이 갑자기 변하는 것 같아요"
- "3D 뷰 로딩 중 프로그램이 멈춰요"
- "무슨 에러인지 이해하기 어려워요"
- "키보드로 빠르게 작업하고 싶어요"

### 목표

- 직관적이고 예측 가능한 진행률 표시
- 반응성 있는 UI (비블로킹)
- 사용자 친화적인 에러 메시지
- 완전한 다국어 지원
- 키보드 단축키 전체 지원
- 컨텍스트 도움말

### 수정 계획

#### Phase 1.1: 진행률 표시 단순화 (3일)

**문제 분석**:
현재 진행률 계산이 복잡함:
```python
# 현재: 3단계 샘플링 + 레벨별 가중치
Stage 1: 30개 (빠른 추정)
Stage 2: 100개 (중간 추정)
Stage 3: 나머지 (정확한 추정)
+ 레벨별 가중치 (Level 2는 Level 1의 1/4)
```

**개선안**: 선형 진행률 + ETA

**core/progress_tracker.py** (새 파일):

```python
"""
단순화된 진행률 추적
"""
from typing import Optional, Callable
from dataclasses import dataclass
from datetime import datetime, timedelta
import time


@dataclass
class ProgressInfo:
    """진행 상황 정보"""
    current: int
    total: int
    percentage: float
    eta_seconds: Optional[float]
    elapsed_seconds: float
    speed: float  # items per second

    @property
    def eta_formatted(self) -> str:
        """ETA를 사람이 읽기 쉬운 형식으로"""
        if self.eta_seconds is None:
            return "Calculating..."

        if self.eta_seconds < 60:
            return f"{int(self.eta_seconds)}s"
        elif self.eta_seconds < 3600:
            minutes = int(self.eta_seconds / 60)
            seconds = int(self.eta_seconds % 60)
            return f"{minutes}m {seconds}s"
        else:
            hours = int(self.eta_seconds / 3600)
            minutes = int((self.eta_seconds % 3600) / 60)
            return f"{hours}h {minutes}m"

    @property
    def elapsed_formatted(self) -> str:
        """경과 시간을 사람이 읽기 쉬운 형식으로"""
        if self.elapsed_seconds < 60:
            return f"{int(self.elapsed_seconds)}s"
        elif self.elapsed_seconds < 3600:
            minutes = int(self.elapsed_seconds / 60)
            seconds = int(self.elapsed_seconds % 60)
            return f"{minutes}m {seconds}s"
        else:
            hours = int(self.elapsed_seconds / 3600)
            minutes = int((self.elapsed_seconds % 3600) / 60)
            return f"{hours}h {minutes}m"


class SimpleProgressTracker:
    """
    단순하고 예측 가능한 진행률 추적

    특징:
    - 선형 진행률 (0-100%)
    - 이동 평균 기반 ETA
    - 부드러운 업데이트
    """

    def __init__(
        self,
        total_items: int,
        callback: Optional[Callable[[ProgressInfo], None]] = None,
        smoothing_window: int = 10,
        min_samples_for_eta: int = 5
    ):
        """
        Args:
            total_items: 전체 작업 항목 수
            callback: 진행 상황 업데이트 콜백
            smoothing_window: 이동 평균 윈도우 크기
            min_samples_for_eta: ETA 계산을 위한 최소 샘플 수
        """
        self.total_items = total_items
        self.callback = callback
        self.smoothing_window = smoothing_window
        self.min_samples_for_eta = min_samples_for_eta

        self.completed_items = 0
        self.start_time = time.time()
        self.last_update_time = self.start_time

        # 속도 추적 (이동 평균용)
        self.speed_samples = []

    def update(self, increment: int = 1):
        """
        진행 상황 업데이트

        Args:
            increment: 완료된 항목 수
        """
        self.completed_items += increment

        # 현재 시간
        now = time.time()
        elapsed = now - self.start_time

        # 속도 계산 (items/sec)
        if elapsed > 0:
            current_speed = self.completed_items / elapsed

            # 이동 평균에 추가
            self.speed_samples.append(current_speed)
            if len(self.speed_samples) > self.smoothing_window:
                self.speed_samples.pop(0)

            # 평균 속도
            avg_speed = sum(self.speed_samples) / len(self.speed_samples)
        else:
            avg_speed = 0

        # 진행률
        percentage = (self.completed_items / self.total_items) * 100

        # ETA 계산
        remaining_items = self.total_items - self.completed_items
        if avg_speed > 0 and len(self.speed_samples) >= self.min_samples_for_eta:
            eta_seconds = remaining_items / avg_speed
        else:
            eta_seconds = None

        # ProgressInfo 생성
        info = ProgressInfo(
            current=self.completed_items,
            total=self.total_items,
            percentage=percentage,
            eta_seconds=eta_seconds,
            elapsed_seconds=elapsed,
            speed=avg_speed
        )

        # 콜백 호출
        if self.callback:
            self.callback(info)

        self.last_update_time = now

    def reset(self):
        """진행 상황 초기화"""
        self.completed_items = 0
        self.start_time = time.time()
        self.last_update_time = self.start_time
        self.speed_samples = []

    def get_info(self) -> ProgressInfo:
        """현재 진행 상황 정보 반환"""
        elapsed = time.time() - self.start_time
        percentage = (self.completed_items / self.total_items) * 100

        if self.speed_samples:
            avg_speed = sum(self.speed_samples) / len(self.speed_samples)
            remaining_items = self.total_items - self.completed_items
            eta_seconds = remaining_items / avg_speed if avg_speed > 0 else None
        else:
            avg_speed = 0
            eta_seconds = None

        return ProgressInfo(
            current=self.completed_items,
            total=self.total_items,
            percentage=percentage,
            eta_seconds=eta_seconds,
            elapsed_seconds=elapsed,
            speed=avg_speed
        )
```

**ui/progress_dialog.py 개선**:

```python
from PyQt5.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout,
    QProgressBar, QLabel, QPushButton
)
from PyQt5.QtCore import Qt

class ModernProgressDialog(QDialog):
    """
    현대적이고 깔끔한 진행률 다이얼로그

    개선사항:
    - 단일 진행률 바
    - 명확한 ETA 표시
    - 현재/전체 개수 표시
    - 속도 표시
    """

    def __init__(self, parent=None, title="Processing"):
        super().__init__(parent)
        self.setWindowTitle(title)
        self.setModal(True)
        self.setMinimumWidth(500)

        self.is_cancelled = False
        self.init_ui()

    def init_ui(self):
        layout = QVBoxLayout()

        # 제목
        self.title_label = QLabel("Processing thumbnails...")
        self.title_label.setStyleSheet("font-size: 14pt; font-weight: bold;")
        layout.addWidget(self.title_label)

        # 진행률 바
        self.progress_bar = QProgressBar()
        self.progress_bar.setMinimum(0)
        self.progress_bar.setMaximum(100)
        self.progress_bar.setTextVisible(True)
        self.progress_bar.setFormat("%p%")
        self.progress_bar.setStyleSheet("""
            QProgressBar {
                border: 2px solid grey;
                border-radius: 5px;
                text-align: center;
                height: 30px;
            }
            QProgressBar::chunk {
                background-color: #4CAF50;
                border-radius: 3px;
            }
        """)
        layout.addWidget(self.progress_bar)

        # 상세 정보
        info_layout = QHBoxLayout()

        # 현재/전체
        self.count_label = QLabel("0 / 0")
        info_layout.addWidget(self.count_label)

        info_layout.addStretch()

        # 속도
        self.speed_label = QLabel("Speed: -")
        info_layout.addWidget(self.speed_label)

        info_layout.addStretch()

        # 경과 시간
        self.elapsed_label = QLabel("Elapsed: 0s")
        info_layout.addWidget(self.elapsed_label)

        info_layout.addStretch()

        # ETA
        self.eta_label = QLabel("ETA: Calculating...")
        info_layout.addWidget(self.eta_label)

        layout.addLayout(info_layout)

        # 취소 버튼
        button_layout = QHBoxLayout()
        button_layout.addStretch()
        self.cancel_button = QPushButton("Cancel")
        self.cancel_button.clicked.connect(self.cancel)
        button_layout.addWidget(self.cancel_button)
        layout.addLayout(button_layout)

        self.setLayout(layout)

    def update_progress(self, info: ProgressInfo):
        """
        진행 상황 업데이트

        Args:
            info: ProgressInfo 객체
        """
        # 진행률
        self.progress_bar.setValue(int(info.percentage))

        # 개수
        self.count_label.setText(f"{info.current:,} / {info.total:,}")

        # 속도
        if info.speed > 1:
            self.speed_label.setText(f"Speed: {info.speed:.1f} items/s")
        else:
            self.speed_label.setText(f"Speed: {1/info.speed:.1f} s/item")

        # 경과 시간
        self.elapsed_label.setText(f"Elapsed: {info.elapsed_formatted}")

        # ETA
        self.eta_label.setText(f"ETA: {info.eta_formatted}")

    def cancel(self):
        """취소 버튼 클릭"""
        self.is_cancelled = True
        self.cancel_button.setEnabled(False)
        self.cancel_button.setText("Cancelling...")
        self.title_label.setText("Cancelling, please wait...")
```

#### Phase 1.2: 3D 렌더링 비블로킹 처리 (4일)

**문제**: 3D 뷰 업데이트 시 UI 스레드 블로킹

**해결**: QThread로 3D 데이터 준비 분리

**ui/widgets/mcube_widget.py 개선**:

```python
from PyQt5.QtCore import QThread, pyqtSignal
from PyQt5.QtWidgets import QOpenGLWidget
import numpy as np
import logging

logger = logging.getLogger(__name__)


class MeshGenerationThread(QThread):
    """
    메시 생성 스레드 (비블로킹)
    """
    finished = pyqtSignal(object, object)  # vertices, faces
    error = pyqtSignal(str)
    progress = pyqtSignal(int)

    def __init__(self, volume_data, threshold):
        super().__init__()
        self.volume_data = volume_data
        self.threshold = threshold

    def run(self):
        try:
            import mcubes

            logger.info(f"Generating mesh with threshold={self.threshold}")

            # Marching cubes 실행
            self.progress.emit(30)
            vertices, faces = mcubes.marching_cubes(self.volume_data, self.threshold)

            self.progress.emit(60)

            # 정규화
            vertices = vertices.astype(np.float32)
            faces = faces.astype(np.uint32)

            self.progress.emit(90)

            logger.info(f"Mesh generated: {len(vertices)} vertices, {len(faces)} faces")

            self.finished.emit(vertices, faces)

        except Exception as e:
            logger.error(f"Mesh generation failed: {e}", exc_info=True)
            self.error.emit(str(e))


class MCubeWidget(QOpenGLWidget):
    """
    OpenGL 기반 3D 메시 뷰어 (개선됨)
    """

    def __init__(self, parent=None):
        super().__init__(parent)
        self.volume_data = None
        self.mesh_vertices = None
        self.mesh_faces = None
        self.threshold = 127.5

        self.mesh_generation_thread = None

    def set_volume_data(self, volume_data):
        """볼륨 데이터 설정"""
        self.volume_data = volume_data
        logger.info(f"Volume data set: shape={volume_data.shape}")

    def update_mesh(self, threshold):
        """
        메시 업데이트 (비블로킹)

        Args:
            threshold: 임계값
        """
        if self.volume_data is None:
            logger.warning("No volume data available")
            return

        # 이전 스레드 정리
        if self.mesh_generation_thread and self.mesh_generation_thread.isRunning():
            logger.debug("Previous mesh generation still running, waiting...")
            self.mesh_generation_thread.wait(1000)

        # 진행률 다이얼로그 표시
        from ui.progress_dialog import ModernProgressDialog
        progress_dialog = ModernProgressDialog(self, title="Generating 3D Mesh")
        progress_dialog.show()

        # 새 스레드 시작
        self.mesh_generation_thread = MeshGenerationThread(
            self.volume_data.copy(),
            threshold
        )

        def on_finished(vertices, faces):
            self.mesh_vertices = vertices
            self.mesh_faces = faces
            self.update()  # OpenGL 리렌더링
            progress_dialog.close()
            logger.info("Mesh update complete")

        def on_error(error_msg):
            progress_dialog.close()
            logger.error(f"Mesh generation error: {error_msg}")
            # 에러 다이얼로그 표시
            from PyQt5.QtWidgets import QMessageBox
            QMessageBox.warning(
                self,
                "Mesh Generation Error",
                f"Failed to generate 3D mesh:\n{error_msg}"
            )

        def on_progress(value):
            from core.progress_tracker import ProgressInfo
            info = ProgressInfo(
                current=value,
                total=100,
                percentage=value,
                eta_seconds=None,
                elapsed_seconds=0,
                speed=0
            )
            progress_dialog.update_progress(info)

        self.mesh_generation_thread.finished.connect(on_finished)
        self.mesh_generation_thread.error.connect(on_error)
        self.mesh_generation_thread.progress.connect(on_progress)

        self.mesh_generation_thread.start()

    def paintGL(self):
        """OpenGL 렌더링"""
        if self.mesh_vertices is None or self.mesh_faces is None:
            return

        # 기존 렌더링 코드...
```

#### Phase 1.3: 사용자 친화적 에러 메시지 (3일)

**현재**:
```
Error: Image processing failed: [Errno 2] No such file or directory: '/path/to/file.tif'
```

**개선**:
```
Cannot open image file

The file 'file.tif' could not be found in the selected directory.

Possible solutions:
• Check if the file was moved or deleted
• Verify you have permission to access the directory
• Try reopening the directory

Technical details: [Errno 2] No such file or directory: '/path/to/file.tif'
```

**utils/error_messages.py** (새 파일):

```python
"""
사용자 친화적 에러 메시지 생성
"""
from typing import Dict, List, Optional
from dataclasses import dataclass
import logging

logger = logging.getLogger(__name__)


@dataclass
class UserError:
    """사용자 친화적 에러 정보"""
    title: str
    message: str
    solutions: List[str]
    technical_details: Optional[str] = None


class ErrorMessageBuilder:
    """에러 메시지 빌더"""

    # 에러 타입별 템플릿
    ERROR_TEMPLATES = {
        'file_not_found': UserError(
            title="Cannot find file",
            message="The file '{filename}' could not be found.",
            solutions=[
                "Check if the file was moved or deleted",
                "Verify the file path is correct",
                "Try selecting the file again"
            ]
        ),
        'permission_denied': UserError(
            title="Permission denied",
            message="You don't have permission to access '{filename}'.",
            solutions=[
                "Check file permissions",
                "Try running the application as administrator",
                "Move the file to a different location"
            ]
        ),
        'invalid_image': UserError(
            title="Invalid image file",
            message="The file '{filename}' is not a valid image or is corrupted.",
            solutions=[
                "Check if the file can be opened with other image viewers",
                "Try converting the image to a different format",
                "Re-export the image from the source"
            ]
        ),
        'out_of_memory': UserError(
            title="Out of memory",
            message="Not enough memory to process this image stack.",
            solutions=[
                "Close other applications to free up memory",
                "Try processing a smaller region",
                "Consider upgrading your system memory",
                "Use a lower resolution level"
            ]
        ),
        'disk_space': UserError(
            title="Not enough disk space",
            message="There is not enough disk space to save the output.",
            solutions=[
                "Free up disk space by deleting unnecessary files",
                "Choose a different output location",
                "Reduce the output quality or resolution"
            ]
        ),
        'opengl_error': UserError(
            title="3D rendering error",
            message="Failed to initialize 3D visualization.",
            solutions=[
                "Update your graphics drivers",
                "Check if your system supports OpenGL 3.0+",
                "Try disabling 3D features in preferences"
            ]
        ),
        'rust_module_missing': UserError(
            title="Performance module not available",
            message="The high-performance Rust module could not be loaded.",
            solutions=[
                "Reinstall the application",
                "The program will use slower Python fallback",
                "Check the log file for details"
            ]
        )
    }

    @classmethod
    def build_error(
        cls,
        error_type: str,
        exception: Exception,
        **kwargs
    ) -> UserError:
        """
        사용자 친화적 에러 메시지 생성

        Args:
            error_type: 에러 타입 키
            exception: 원본 예외
            **kwargs: 템플릿 변수 (예: filename)

        Returns:
            UserError 객체
        """
        # 템플릿 가져오기
        template = cls.ERROR_TEMPLATES.get(error_type)

        if template is None:
            # 기본 에러
            return UserError(
                title="An error occurred",
                message=str(exception),
                solutions=["Please check the log file for details"],
                technical_details=f"{type(exception).__name__}: {exception}"
            )

        # 템플릿에 변수 적용
        title = template.title
        message = template.message.format(**kwargs)
        solutions = template.solutions.copy()

        # 기술적 세부사항 추가
        technical_details = f"{type(exception).__name__}: {exception}"

        return UserError(
            title=title,
            message=message,
            solutions=solutions,
            technical_details=technical_details
        )

    @classmethod
    def from_exception(cls, exception: Exception, **kwargs) -> UserError:
        """
        예외로부터 자동으로 에러 타입 감지

        Args:
            exception: 예외 객체
            **kwargs: 추가 컨텍스트

        Returns:
            UserError 객체
        """
        import errno

        # FileNotFoundError
        if isinstance(exception, FileNotFoundError):
            return cls.build_error('file_not_found', exception, **kwargs)

        # PermissionError
        elif isinstance(exception, PermissionError):
            return cls.build_error('permission_denied', exception, **kwargs)

        # MemoryError
        elif isinstance(exception, MemoryError):
            return cls.build_error('out_of_memory', exception, **kwargs)

        # OSError with specific errno
        elif isinstance(exception, OSError):
            if exception.errno == errno.ENOSPC:
                return cls.build_error('disk_space', exception, **kwargs)
            elif exception.errno == errno.EACCES:
                return cls.build_error('permission_denied', exception, **kwargs)

        # PIL/Image errors
        elif 'PIL' in str(type(exception)) or 'Image' in str(type(exception)):
            return cls.build_error('invalid_image', exception, **kwargs)

        # OpenGL errors
        elif 'OpenGL' in str(exception) or 'GL' in str(type(exception).__name__):
            return cls.build_error('opengl_error', exception, **kwargs)

        # ModuleNotFoundError for Rust
        elif isinstance(exception, (ModuleNotFoundError, ImportError)):
            if 'ctharvester_rs' in str(exception):
                return cls.build_error('rust_module_missing', exception, **kwargs)

        # 기본 처리
        return cls.build_error('unknown', exception, **kwargs)


def show_error_dialog(parent, user_error: UserError):
    """
    에러 다이얼로그 표시

    Args:
        parent: 부모 위젯
        user_error: UserError 객체
    """
    from PyQt5.QtWidgets import QMessageBox, QTextEdit

    msg_box = QMessageBox(parent)
    msg_box.setIcon(QMessageBox.Critical)
    msg_box.setWindowTitle(user_error.title)

    # 메시지 구성
    text = user_error.message + "\n\n"
    text += "Possible solutions:\n"
    for i, solution in enumerate(user_error.solutions, 1):
        text += f"{i}. {solution}\n"

    msg_box.setText(text)

    # 기술적 세부사항 (접을 수 있게)
    if user_error.technical_details:
        msg_box.setDetailedText(user_error.technical_details)

    msg_box.exec_()
```

**적용 예시**:

```python
# ui/main_window.py
from utils.error_messages import ErrorMessageBuilder, show_error_dialog

def open_directory(self):
    try:
        # 디렉토리 열기 로직
        ...
    except Exception as e:
        logger.error(f"Failed to open directory: {e}", exc_info=True)

        # 사용자 친화적 에러 표시
        user_error = ErrorMessageBuilder.from_exception(
            e,
            filename=os.path.basename(selected_dir)
        )
        show_error_dialog(self, user_error)
```

#### Phase 1.4: 다국어 지원 완성 (4일)

**현재 상태**:
- `.ts` 파일 존재 (CTHarvester_en.ts, CTHarvester_ko.ts)
- 일부 문자열만 번역됨
- 동적 문자열 번역 누락

**개선 계획**:

**Day 1-2**: 번역 파일 업데이트

```bash
# 번역 가능한 문자열 추출
pylupdate5 -verbose main.py ui/*.py -ts translations/ctharvester_en.ts translations/ctharvester_ko.ts

# 번역 파일 편집 (Qt Linguist 사용)
linguist translations/ctharvester_ko.ts

# .qm 파일 생성 (실행 시 사용)
lrelease translations/ctharvester_ko.ts -qm translations/ctharvester_ko.qm
```

**config/i18n.py** (새 파일):

```python
"""
국제화(i18n) 지원
"""
from PyQt5.QtCore import QTranslator, QLocale, QCoreApplication
import os
import logging

logger = logging.getLogger(__name__)


class TranslationManager:
    """번역 관리자"""

    SUPPORTED_LANGUAGES = {
        'en': 'English',
        'ko': '한국어',
    }

    def __init__(self, app):
        self.app = app
        self.translator = QTranslator()
        self.current_language = 'en'

    def load_language(self, language_code: str) -> bool:
        """
        언어 로드

        Args:
            language_code: 언어 코드 ('en', 'ko')

        Returns:
            로드 성공 여부
        """
        if language_code not in self.SUPPORTED_LANGUAGES:
            logger.warning(f"Unsupported language: {language_code}")
            return False

        # 번역 파일 경로
        translations_dir = os.path.join(
            os.path.dirname(__file__),
            '..',
            'translations'
        )
        qm_file = os.path.join(
            translations_dir,
            f'ctharvester_{language_code}.qm'
        )

        if not os.path.exists(qm_file):
            logger.error(f"Translation file not found: {qm_file}")
            return False

        # 기존 번역 제거
        self.app.removeTranslator(self.translator)

        # 새 번역 로드
        if self.translator.load(qm_file):
            self.app.installTranslator(self.translator)
            self.current_language = language_code
            logger.info(f"Loaded language: {language_code}")
            return True
        else:
            logger.error(f"Failed to load translation: {qm_file}")
            return False

    def get_system_language(self) -> str:
        """시스템 언어 감지"""
        locale = QLocale.system().name()  # 예: 'ko_KR', 'en_US'
        language_code = locale.split('_')[0]

        if language_code in self.SUPPORTED_LANGUAGES:
            return language_code
        else:
            return 'en'  # 기본값

    @staticmethod
    def tr(text: str, context: str = None) -> str:
        """
        문자열 번역

        Args:
            text: 원본 텍스트
            context: 컨텍스트 (클래스명 등)

        Returns:
            번역된 텍스트
        """
        if context:
            return QCoreApplication.translate(context, text)
        else:
            return QCoreApplication.translate("Global", text)
```

**main.py 수정**:

```python
from config.i18n import TranslationManager

def main():
    app = QApplication(sys.argv)

    # 번역 관리자 초기화
    translation_manager = TranslationManager(app)

    # 시스템 언어 또는 설정된 언어 로드
    settings = QSettings()
    language = settings.value('language', translation_manager.get_system_language())
    translation_manager.load_language(language)

    # 메인 윈도우 생성
    window = CTHarvesterMainWindow()
    window.translation_manager = translation_manager  # 전달
    window.show()

    return app.exec_()
```

**ui/main_window.py에서 사용**:

```python
from config.i18n import TranslationManager

class CTHarvesterMainWindow(QMainWindow):
    def create_menu_bar(self):
        menubar = self.menuBar()

        # 파일 메뉴
        file_menu = menubar.addMenu(TranslationManager.tr("File", "MainWindow"))

        open_action = QAction(TranslationManager.tr("Open Directory", "MainWindow"), self)
        open_action.triggered.connect(self.open_directory)
        file_menu.addAction(open_action)

        # ...

    def change_language(self, language_code: str):
        """언어 변경"""
        if self.translation_manager.load_language(language_code):
            # 설정 저장
            settings = QSettings()
            settings.setValue('language', language_code)

            # UI 업데이트 필요 메시지
            QMessageBox.information(
                self,
                TranslationManager.tr("Language Changed", "MainWindow"),
                TranslationManager.tr(
                    "Please restart the application for the language change to take effect.",
                    "MainWindow"
                )
            )
```

**Day 3-4**: 모든 문자열 번역 적용

```python
# 번역이 필요한 모든 문자열을 self.tr() 또는 TranslationManager.tr()로 감싸기

# 변경 전
button = QPushButton("Open Directory")

# 변경 후
button = QPushButton(self.tr("Open Directory"))
```

#### Phase 1.5: 키보드 단축키 전체 지원 (2일)

**config/shortcuts.py** (새 파일):

```python
"""
키보드 단축키 정의
"""
from PyQt5.QtCore import Qt
from dataclasses import dataclass
from typing import Dict


@dataclass
class Shortcut:
    """단축키 정의"""
    key: str  # Qt key sequence
    description: str
    action: str  # action name


class ShortcutManager:
    """단축키 관리자"""

    SHORTCUTS: Dict[str, Shortcut] = {
        # 파일 작업
        'open_directory': Shortcut(
            key='Ctrl+O',
            description='Open directory',
            action='open_directory'
        ),
        'reload_directory': Shortcut(
            key='F5',
            description='Reload current directory',
            action='reload_directory'
        ),
        'save_cropped': Shortcut(
            key='Ctrl+S',
            description='Save cropped images',
            action='save_cropped'
        ),
        'export_mesh': Shortcut(
            key='Ctrl+E',
            description='Export 3D mesh',
            action='export_mesh'
        ),
        'quit': Shortcut(
            key='Ctrl+Q',
            description='Quit application',
            action='quit'
        ),

        # 썸네일 생성
        'generate_thumbnails': Shortcut(
            key='Ctrl+T',
            description='Generate thumbnails',
            action='generate_thumbnails'
        ),

        # 뷰 조작
        'zoom_in': Shortcut(
            key='Ctrl++',
            description='Zoom in',
            action='zoom_in'
        ),
        'zoom_out': Shortcut(
            key='Ctrl+-',
            description='Zoom out',
            action='zoom_out'
        ),
        'zoom_fit': Shortcut(
            key='Ctrl+0',
            description='Fit to window',
            action='zoom_fit'
        ),
        'toggle_3d_view': Shortcut(
            key='F3',
            description='Toggle 3D view',
            action='toggle_3d_view'
        ),

        # 탐색
        'next_slice': Shortcut(
            key='Right',
            description='Next slice',
            action='next_slice'
        ),
        'prev_slice': Shortcut(
            key='Left',
            description='Previous slice',
            action='prev_slice'
        ),
        'first_slice': Shortcut(
            key='Home',
            description='First slice',
            action='first_slice'
        ),
        'last_slice': Shortcut(
            key='End',
            description='Last slice',
            action='last_slice'
        ),
        'jump_forward_10': Shortcut(
            key='Ctrl+Right',
            description='Jump forward 10 slices',
            action='jump_forward_10'
        ),
        'jump_backward_10': Shortcut(
            key='Ctrl+Left',
            description='Jump backward 10 slices',
            action='jump_backward_10'
        ),

        # 크롭 영역
        'set_bottom': Shortcut(
            key='B',
            description='Set bottom boundary',
            action='set_bottom'
        ),
        'set_top': Shortcut(
            key='T',
            description='Set top boundary',
            action='set_top'
        ),
        'reset_crop': Shortcut(
            key='Ctrl+R',
            description='Reset crop region',
            action='reset_crop'
        ),

        # 임계값 조정
        'increase_threshold': Shortcut(
            key='Up',
            description='Increase threshold',
            action='increase_threshold'
        ),
        'decrease_threshold': Shortcut(
            key='Down',
            description='Decrease threshold',
            action='decrease_threshold'
        ),

        # 도움말
        'show_shortcuts': Shortcut(
            key='F1',
            description='Show keyboard shortcuts',
            action='show_shortcuts'
        ),
        'show_about': Shortcut(
            key='Ctrl+I',
            description='About CTHarvester',
            action='show_about'
        ),
    }

    @classmethod
    def get_shortcut(cls, action: str) -> Shortcut:
        """액션에 해당하는 단축키 반환"""
        return cls.SHORTCUTS.get(action)

    @classmethod
    def get_all_shortcuts(cls) -> Dict[str, Shortcut]:
        """모든 단축키 반환"""
        return cls.SHORTCUTS.copy()
```

**ui/dialogs.py에 단축키 도움말 추가**:

```python
class ShortcutDialog(QDialog):
    """키보드 단축키 도움말 다이얼로그"""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Keyboard Shortcuts")
        self.setMinimumSize(600, 400)
        self.init_ui()

    def init_ui(self):
        layout = QVBoxLayout()

        # 제목
        title = QLabel("Keyboard Shortcuts")
        title.setStyleSheet("font-size: 16pt; font-weight: bold;")
        layout.addWidget(title)

        # 단축키 목록
        from config.shortcuts import ShortcutManager

        shortcuts = ShortcutManager.get_all_shortcuts()

        # 카테고리별로 그룹화
        categories = {
            'File': ['open_directory', 'reload_directory', 'save_cropped', 'export_mesh', 'quit'],
            'Thumbnails': ['generate_thumbnails'],
            'View': ['zoom_in', 'zoom_out', 'zoom_fit', 'toggle_3d_view'],
            'Navigation': ['next_slice', 'prev_slice', 'first_slice', 'last_slice',
                          'jump_forward_10', 'jump_backward_10'],
            'Crop': ['set_bottom', 'set_top', 'reset_crop'],
            'Threshold': ['increase_threshold', 'decrease_threshold'],
            'Help': ['show_shortcuts', 'show_about'],
        }

        for category, actions in categories.items():
            # 카테고리 헤더
            header = QLabel(f"\n{category}")
            header.setStyleSheet("font-weight: bold; font-size: 12pt;")
            layout.addWidget(header)

            # 단축키 목록
            for action in actions:
                if action in shortcuts:
                    shortcut = shortcuts[action]
                    item = QLabel(f"  {shortcut.key:20s}  -  {shortcut.description}")
                    item.setStyleSheet("font-family: monospace;")
                    layout.addWidget(item)

        # 닫기 버튼
        close_button = QPushButton("Close")
        close_button.clicked.connect(self.accept)
        layout.addWidget(close_button)

        self.setLayout(layout)
```

**ui/main_window.py에 단축키 적용**:

```python
from config.shortcuts import ShortcutManager

class CTHarvesterMainWindow(QMainWindow):
    def setup_shortcuts(self):
        """키보드 단축키 설정"""
        shortcuts = ShortcutManager.get_all_shortcuts()

        for action_name, shortcut in shortcuts.items():
            # QShortcut 생성
            qs = QShortcut(QKeySequence(shortcut.key), self)

            # 액션 메서드 연결
            method = getattr(self, action_name, None)
            if method:
                qs.activated.connect(method)
            else:
                logger.warning(f"Action method not found: {action_name}")
```

#### Phase 1.6: 툴팁 및 컨텍스트 도움말 (2일)

```python
# ui/main_window.py
class CTHarvesterMainWindow(QMainWindow):
    def create_toolbar(self):
        toolbar = self.addToolBar("Main Toolbar")

        # Open directory
        open_action = QAction(QIcon("icons/folder.png"), "Open Directory", self)
        open_action.setShortcut("Ctrl+O")
        open_action.setStatusTip("Open a directory containing CT images")
        open_action.setToolTip(
            "<b>Open Directory</b><br>"
            "Select a directory containing CT image files.<br>"
            "Supported formats: BMP, JPG, PNG, TIF<br>"
            "<i>Shortcut: Ctrl+O</i>"
        )
        open_action.triggered.connect(self.open_directory)
        toolbar.addAction(open_action)

        # Generate thumbnails
        thumb_action = QAction(QIcon("icons/thumbnail.png"), "Generate Thumbnails", self)
        thumb_action.setShortcut("Ctrl+T")
        thumb_action.setStatusTip("Generate multi-level thumbnails for fast preview")
        thumb_action.setToolTip(
            "<b>Generate Thumbnails</b><br>"
            "Create pyramid thumbnails for efficient navigation.<br>"
            "This may take several minutes depending on image count.<br>"
            "<i>Shortcut: Ctrl+T</i>"
        )
        thumb_action.triggered.connect(self.generate_thumbnails)
        toolbar.addAction(thumb_action)

        # ... 기타 액션들
```

### 검증 방법

1. **사용자 테스트**
   - 5명의 테스터에게 사용 요청
   - 피드백 수집

2. **UI 반응성 테스트**
   - 3D 렌더링 중 UI 조작 가능 여부
   - 진행률 표시 부드러움

3. **접근성 테스트**
   - 모든 기능이 키보드로 접근 가능한지
   - 고대비 모드 지원

---

## 개선사항 2: 설정 파일 관리

### 현황 분석

**문제점**:
1. `QSettings`를 사용하나 설정 항목이 제한적
2. 썸네일 생성 파라미터가 하드코딩됨
3. 사용자 정의 설정 UI 없음
4. 설정 가져오기/내보내기 기능 없음

### 목표

- YAML 기반 설정 파일
- GUI 설정 편집기
- 설정 가져오기/내보내기
- 기본값 복원

### 수정 계획

#### Phase 2.1: YAML 설정 시스템 (3일)

**config/settings.yaml** (기본 설정):

```yaml
# CTHarvester Configuration File

application:
  language: auto  # auto, en, ko
  theme: light    # light, dark
  auto_save_settings: true

window:
  width: 1200
  height: 800
  remember_position: true
  remember_size: true

thumbnails:
  max_size: 500
  sample_size: 20
  max_level: 10
  compression: true
  format: tif  # tif, png

processing:
  threads: auto  # auto, or specific number (1-16)
  memory_limit_gb: 4
  use_rust_module: true  # false to force Python fallback

rendering:
  background_color: [0.2, 0.2, 0.2]
  default_threshold: 128
  anti_aliasing: true
  show_fps: false

export:
  mesh_format: stl  # stl, ply, obj
  image_format: tif  # tif, png, jpg
  compression_level: 6  # 0-9

logging:
  level: INFO  # DEBUG, INFO, WARNING, ERROR
  max_file_size_mb: 10
  backup_count: 5
  console_output: true

paths:
  last_directory: ""
  export_directory: ""
```

**utils/settings_manager.py**:

```python
"""
설정 관리자 (YAML 기반)
"""
import yaml
import os
from pathlib import Path
from typing import Any, Dict
import logging
from copy import deepcopy

logger = logging.getLogger(__name__)


class SettingsManager:
    """
    YAML 기반 설정 관리자

    특징:
    - 기본값 지원
    - 설정 검증
    - 자동 저장
    - 가져오기/내보내기
    """

    DEFAULT_CONFIG_FILE = "settings.yaml"

    def __init__(self, config_dir: str = None):
        """
        Args:
            config_dir: 설정 파일 디렉토리 (None이면 기본 위치)
        """
        if config_dir is None:
            # 기본 위치: ~/.config/CTHarvester (Linux/Mac) 또는 %APPDATA%/CTHarvester (Windows)
            if os.name == 'nt':
                config_dir = os.path.join(os.environ['APPDATA'], 'CTHarvester')
            else:
                config_dir = os.path.join(os.path.expanduser('~'), '.config', 'CTHarvester')

        self.config_dir = Path(config_dir)
        self.config_file = self.config_dir / self.DEFAULT_CONFIG_FILE

        # 디렉토리 생성
        self.config_dir.mkdir(parents=True, exist_ok=True)

        # 설정 로드
        self.settings = {}
        self.default_settings = self._load_default_settings()
        self.load()

    def _load_default_settings(self) -> Dict:
        """기본 설정 로드"""
        default_file = Path(__file__).parent / "settings.yaml"

        if default_file.exists():
            with open(default_file, 'r', encoding='utf-8') as f:
                return yaml.safe_load(f)
        else:
            logger.warning("Default settings file not found")
            return {}

    def load(self):
        """설정 파일 로드"""
        if self.config_file.exists():
            try:
                with open(self.config_file, 'r', encoding='utf-8') as f:
                    self.settings = yaml.safe_load(f) or {}
                logger.info(f"Settings loaded from {self.config_file}")
            except Exception as e:
                logger.error(f"Failed to load settings: {e}")
                self.settings = deepcopy(self.default_settings)
        else:
            # 기본 설정 사용
            self.settings = deepcopy(self.default_settings)
            self.save()

    def save(self):
        """설정 파일 저장"""
        try:
            with open(self.config_file, 'w', encoding='utf-8') as f:
                yaml.dump(self.settings, f, default_flow_style=False, allow_unicode=True)
            logger.info(f"Settings saved to {self.config_file}")
        except Exception as e:
            logger.error(f"Failed to save settings: {e}")

    def get(self, key: str, default: Any = None) -> Any:
        """
        설정값 가져오기 (점 표기법 지원)

        Args:
            key: 설정 키 (예: 'thumbnails.max_size')
            default: 기본값

        Returns:
            설정값
        """
        keys = key.split('.')
        value = self.settings

        for k in keys:
            if isinstance(value, dict) and k in value:
                value = value[k]
            else:
                return default

        return value

    def set(self, key: str, value: Any):
        """
        설정값 설정 (점 표기법 지원)

        Args:
            key: 설정 키 (예: 'thumbnails.max_size')
            value: 설정값
        """
        keys = key.split('.')
        settings = self.settings

        # 중첩 딕셔너리 생성
        for k in keys[:-1]:
            if k not in settings:
                settings[k] = {}
            settings = settings[k]

        # 값 설정
        settings[keys[-1]] = value

    def reset(self):
        """기본 설정으로 초기화"""
        self.settings = deepcopy(self.default_settings)
        self.save()
        logger.info("Settings reset to defaults")

    def export(self, file_path: str):
        """설정 내보내기"""
        try:
            with open(file_path, 'w', encoding='utf-8') as f:
                yaml.dump(self.settings, f, default_flow_style=False, allow_unicode=True)
            logger.info(f"Settings exported to {file_path}")
        except Exception as e:
            logger.error(f"Failed to export settings: {e}")
            raise

    def import_settings(self, file_path: str):
        """설정 가져오기"""
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                imported = yaml.safe_load(f)

            # 검증 후 적용
            if self._validate_settings(imported):
                self.settings = imported
                self.save()
                logger.info(f"Settings imported from {file_path}")
            else:
                raise ValueError("Invalid settings file")

        except Exception as e:
            logger.error(f"Failed to import settings: {e}")
            raise

    def _validate_settings(self, settings: Dict) -> bool:
        """설정 검증"""
        # 기본적인 구조 검증
        required_keys = ['application', 'thumbnails', 'processing']

        for key in required_keys:
            if key not in settings:
                logger.error(f"Missing required key: {key}")
                return False

        return True

    def get_all(self) -> Dict:
        """모든 설정 반환"""
        return deepcopy(self.settings)
```

#### Phase 2.2: 설정 GUI 편집기 (4일)

**ui/settings_dialog.py** (새 파일):

```python
"""
설정 편집 다이얼로그
"""
from PyQt5.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QTabWidget,
    QLabel, QSpinBox, QComboBox, QCheckBox, QPushButton,
    QGroupBox, QFormLayout, QFileDialog, QMessageBox
)
from PyQt5.QtCore import Qt
import logging

from utils.settings_manager import SettingsManager

logger = logging.getLogger(__name__)


class SettingsDialog(QDialog):
    """설정 편집 다이얼로그"""

    def __init__(self, settings_manager: SettingsManager, parent=None):
        super().__init__(parent)
        self.settings_manager = settings_manager
        self.setWindowTitle("Preferences")
        self.setMinimumSize(700, 500)
        self.init_ui()
        self.load_settings()

    def init_ui(self):
        layout = QVBoxLayout()

        # 탭 위젯
        tabs = QTabWidget()

        # 각 탭 생성
        tabs.addTab(self.create_general_tab(), "General")
        tabs.addTab(self.create_thumbnails_tab(), "Thumbnails")
        tabs.addTab(self.create_processing_tab(), "Processing")
        tabs.addTab(self.create_rendering_tab(), "Rendering")
        tabs.addTab(self.create_advanced_tab(), "Advanced")

        layout.addWidget(tabs)

        # 버튼
        button_layout = QHBoxLayout()

        # 가져오기/내보내기
        import_button = QPushButton("Import Settings...")
        import_button.clicked.connect(self.import_settings)
        button_layout.addWidget(import_button)

        export_button = QPushButton("Export Settings...")
        export_button.clicked.connect(self.export_settings)
        button_layout.addWidget(export_button)

        button_layout.addStretch()

        # 기본값 복원
        reset_button = QPushButton("Reset to Defaults")
        reset_button.clicked.connect(self.reset_to_defaults)
        button_layout.addWidget(reset_button)

        # 적용/취소
        cancel_button = QPushButton("Cancel")
        cancel_button.clicked.connect(self.reject)
        button_layout.addWidget(cancel_button)

        apply_button = QPushButton("Apply")
        apply_button.clicked.connect(self.apply_settings)
        button_layout.addWidget(apply_button)

        ok_button = QPushButton("OK")
        ok_button.clicked.connect(self.accept_settings)
        button_layout.addWidget(ok_button)

        layout.addLayout(button_layout)

        self.setLayout(layout)

    def create_general_tab(self):
        """일반 설정 탭"""
        widget = QWidget()
        layout = QVBoxLayout()

        # 언어
        lang_group = QGroupBox("Language")
        lang_layout = QFormLayout()

        self.language_combo = QComboBox()
        self.language_combo.addItems(["Auto (System)", "English", "한국어"])
        lang_layout.addRow("Interface Language:", self.language_combo)

        lang_group.setLayout(lang_layout)
        layout.addWidget(lang_group)

        # 테마
        theme_group = QGroupBox("Appearance")
        theme_layout = QFormLayout()

        self.theme_combo = QComboBox()
        self.theme_combo.addItems(["Light", "Dark"])
        theme_layout.addRow("Theme:", self.theme_combo)

        theme_group.setLayout(theme_layout)
        layout.addWidget(theme_group)

        # 윈도우
        window_group = QGroupBox("Window")
        window_layout = QVBoxLayout()

        self.remember_position_check = QCheckBox("Remember window position")
        window_layout.addWidget(self.remember_position_check)

        self.remember_size_check = QCheckBox("Remember window size")
        window_layout.addWidget(self.remember_size_check)

        window_group.setLayout(window_layout)
        layout.addWidget(window_group)

        layout.addStretch()
        widget.setLayout(layout)
        return widget

    def create_thumbnails_tab(self):
        """썸네일 설정 탭"""
        widget = QWidget()
        layout = QVBoxLayout()

        group = QGroupBox("Thumbnail Generation")
        form_layout = QFormLayout()

        # 최대 크기
        self.thumb_max_size_spin = QSpinBox()
        self.thumb_max_size_spin.setRange(100, 2000)
        self.thumb_max_size_spin.setSuffix(" px")
        form_layout.addRow("Max thumbnail size:", self.thumb_max_size_spin)

        # 샘플 크기
        self.thumb_sample_size_spin = QSpinBox()
        self.thumb_sample_size_spin.setRange(10, 100)
        form_layout.addRow("Sample size:", self.thumb_sample_size_spin)

        # 최대 레벨
        self.thumb_max_level_spin = QSpinBox()
        self.thumb_max_level_spin.setRange(1, 20)
        form_layout.addRow("Max pyramid level:", self.thumb_max_level_spin)

        # 압축
        self.thumb_compression_check = QCheckBox("Enable compression")
        form_layout.addRow("", self.thumb_compression_check)

        # 형식
        self.thumb_format_combo = QComboBox()
        self.thumb_format_combo.addItems(["TIF", "PNG"])
        form_layout.addRow("Format:", self.thumb_format_combo)

        group.setLayout(form_layout)
        layout.addWidget(group)

        layout.addStretch()
        widget.setLayout(layout)
        return widget

    def create_processing_tab(self):
        """처리 설정 탭"""
        widget = QWidget()
        layout = QVBoxLayout()

        group = QGroupBox("Processing Options")
        form_layout = QFormLayout()

        # 스레드 수
        self.threads_spin = QSpinBox()
        self.threads_spin.setRange(1, 16)
        self.threads_spin.setSpecialValueText("Auto")
        form_layout.addRow("Worker threads:", self.threads_spin)

        # 메모리 제한
        self.memory_limit_spin = QSpinBox()
        self.memory_limit_spin.setRange(1, 64)
        self.memory_limit_spin.setSuffix(" GB")
        form_layout.addRow("Memory limit:", self.memory_limit_spin)

        # Rust 모듈
        self.use_rust_check = QCheckBox("Use high-performance Rust module")
        form_layout.addRow("", self.use_rust_check)

        group.setLayout(form_layout)
        layout.addWidget(group)

        layout.addStretch()
        widget.setLayout(layout)
        return widget

    def create_rendering_tab(self):
        """렌더링 설정 탭"""
        widget = QWidget()
        layout = QVBoxLayout()

        group = QGroupBox("3D Rendering")
        form_layout = QFormLayout()

        # 기본 임계값
        self.threshold_spin = QSpinBox()
        self.threshold_spin.setRange(0, 255)
        form_layout.addRow("Default threshold:", self.threshold_spin)

        # 안티앨리어싱
        self.antialiasing_check = QCheckBox("Enable anti-aliasing")
        form_layout.addRow("", self.antialiasing_check)

        # FPS 표시
        self.show_fps_check = QCheckBox("Show FPS counter")
        form_layout.addRow("", self.show_fps_check)

        group.setLayout(form_layout)
        layout.addWidget(group)

        layout.addStretch()
        widget.setLayout(layout)
        return widget

    def create_advanced_tab(self):
        """고급 설정 탭"""
        widget = QWidget()
        layout = QVBoxLayout()

        # 로깅
        log_group = QGroupBox("Logging")
        log_layout = QFormLayout()

        self.log_level_combo = QComboBox()
        self.log_level_combo.addItems(["DEBUG", "INFO", "WARNING", "ERROR"])
        log_layout.addRow("Log level:", self.log_level_combo)

        self.console_output_check = QCheckBox("Enable console output")
        log_layout.addRow("", self.console_output_check)

        log_group.setLayout(log_layout)
        layout.addWidget(log_group)

        layout.addStretch()
        widget.setLayout(layout)
        return widget

    def load_settings(self):
        """설정값을 UI에 로드"""
        s = self.settings_manager

        # 일반
        lang = s.get('application.language', 'auto')
        lang_map = {'auto': 0, 'en': 1, 'ko': 2}
        self.language_combo.setCurrentIndex(lang_map.get(lang, 0))

        theme = s.get('application.theme', 'light')
        self.theme_combo.setCurrentIndex(0 if theme == 'light' else 1)

        self.remember_position_check.setChecked(s.get('window.remember_position', True))
        self.remember_size_check.setChecked(s.get('window.remember_size', True))

        # 썸네일
        self.thumb_max_size_spin.setValue(s.get('thumbnails.max_size', 500))
        self.thumb_sample_size_spin.setValue(s.get('thumbnails.sample_size', 20))
        self.thumb_max_level_spin.setValue(s.get('thumbnails.max_level', 10))
        self.thumb_compression_check.setChecked(s.get('thumbnails.compression', True))

        fmt = s.get('thumbnails.format', 'tif')
        self.thumb_format_combo.setCurrentIndex(0 if fmt == 'tif' else 1)

        # 처리
        threads = s.get('processing.threads', 'auto')
        if threads == 'auto':
            self.threads_spin.setValue(0)
        else:
            self.threads_spin.setValue(int(threads))

        self.memory_limit_spin.setValue(s.get('processing.memory_limit_gb', 4))
        self.use_rust_check.setChecked(s.get('processing.use_rust_module', True))

        # 렌더링
        self.threshold_spin.setValue(s.get('rendering.default_threshold', 128))
        self.antialiasing_check.setChecked(s.get('rendering.anti_aliasing', True))
        self.show_fps_check.setChecked(s.get('rendering.show_fps', False))

        # 고급
        log_level = s.get('logging.level', 'INFO')
        levels = ["DEBUG", "INFO", "WARNING", "ERROR"]
        self.log_level_combo.setCurrentIndex(levels.index(log_level))

        self.console_output_check.setChecked(s.get('logging.console_output', True))

    def save_settings(self):
        """UI에서 설정값 저장"""
        s = self.settings_manager

        # 일반
        lang_map = {0: 'auto', 1: 'en', 2: 'ko'}
        s.set('application.language', lang_map[self.language_combo.currentIndex()])
        s.set('application.theme', 'light' if self.theme_combo.currentIndex() == 0 else 'dark')
        s.set('window.remember_position', self.remember_position_check.isChecked())
        s.set('window.remember_size', self.remember_size_check.isChecked())

        # 썸네일
        s.set('thumbnails.max_size', self.thumb_max_size_spin.value())
        s.set('thumbnails.sample_size', self.thumb_sample_size_spin.value())
        s.set('thumbnails.max_level', self.thumb_max_level_spin.value())
        s.set('thumbnails.compression', self.thumb_compression_check.isChecked())
        s.set('thumbnails.format', 'tif' if self.thumb_format_combo.currentIndex() == 0 else 'png')

        # 처리
        threads = self.threads_spin.value()
        s.set('processing.threads', 'auto' if threads == 0 else threads)
        s.set('processing.memory_limit_gb', self.memory_limit_spin.value())
        s.set('processing.use_rust_module', self.use_rust_check.isChecked())

        # 렌더링
        s.set('rendering.default_threshold', self.threshold_spin.value())
        s.set('rendering.anti_aliasing', self.antialiasing_check.isChecked())
        s.set('rendering.show_fps', self.show_fps_check.isChecked())

        # 고급
        levels = ["DEBUG", "INFO", "WARNING", "ERROR"]
        s.set('logging.level', levels[self.log_level_combo.currentIndex()])
        s.set('logging.console_output', self.console_output_check.isChecked())

        s.save()

    def apply_settings(self):
        """설정 적용"""
        self.save_settings()
        QMessageBox.information(
            self,
            "Settings Applied",
            "Settings have been applied successfully."
        )

    def accept_settings(self):
        """OK 버튼"""
        self.save_settings()
        self.accept()

    def reset_to_defaults(self):
        """기본값 복원"""
        reply = QMessageBox.question(
            self,
            "Reset Settings",
            "Are you sure you want to reset all settings to defaults?",
            QMessageBox.Yes | QMessageBox.No
        )

        if reply == QMessageBox.Yes:
            self.settings_manager.reset()
            self.load_settings()
            QMessageBox.information(self, "Reset Complete", "Settings reset to defaults.")

    def import_settings(self):
        """설정 가져오기"""
        file_path, _ = QFileDialog.getOpenFileName(
            self,
            "Import Settings",
            "",
            "YAML Files (*.yaml *.yml);;All Files (*)"
        )

        if file_path:
            try:
                self.settings_manager.import_settings(file_path)
                self.load_settings()
                QMessageBox.information(self, "Import Complete", "Settings imported successfully.")
            except Exception as e:
                QMessageBox.critical(self, "Import Failed", f"Failed to import settings:\n{e}")

    def export_settings(self):
        """설정 내보내기"""
        file_path, _ = QFileDialog.getSaveFileName(
            self,
            "Export Settings",
            "ctharvester_settings.yaml",
            "YAML Files (*.yaml *.yml);;All Files (*)"
        )

        if file_path:
            try:
                self.settings_manager.export(file_path)
                QMessageBox.information(self, "Export Complete", "Settings exported successfully.")
            except Exception as e:
                QMessageBox.critical(self, "Export Failed", f"Failed to export settings:\n{e}")
```

### 검증 방법

1. **설정 지속성 테스트**
   - 설정 변경 후 프로그램 재시작
   - 설정이 유지되는지 확인

2. **가져오기/내보내기 테스트**
   - 설정 내보내기
   - 다른 머신에서 가져오기
   - 설정이 정확히 복원되는지 확인

---

## 개선사항 3: 문서화

### 현황 분석

**현재 상태**:
- README.md, README.ko.md 존재 (기본적인 소개)
- devlog/ 디렉토리 (개발 로그)
- 함수/클래스 docstring 일부만 존재
- API 문서 없음
- 사용자 가이드 없음

### 목표

- 완전한 API 문서 (Sphinx)
- 사용자 가이드
- 개발자 가이드
- 모든 public API에 docstring

### 수정 계획

#### Phase 3.1: Docstring 작성 (5일)

**Google Style Docstring 사용**:

```python
def process_image_pair(
    file1_path: str,
    file2_path: Optional[str],
    output_path: str,
    is_16bit: bool = False
) -> bool:
    """
    두 이미지를 평균화하고 다운샘플링합니다.

    이 함수는 두 개의 연속된 CT 이미지를 로드하여 픽셀 단위로 평균을 계산한 후,
    결과를 1/2 크기로 다운샘플링합니다. 16비트 이미지의 경우 오버플로를 방지하기 위해
    내부적으로 32비트 연산을 사용합니다.

    Args:
        file1_path: 첫 번째 이미지 파일 경로 (필수)
        file2_path: 두 번째 이미지 파일 경로 (None이면 단일 이미지만 처리)
        output_path: 출력 파일 경로
        is_16bit: 16비트 이미지 여부 (기본값: False)

    Returns:
        처리 성공 여부 (True/False)

    Raises:
        FileNotFoundError: 입력 파일을 찾을 수 없는 경우
        ValueError: 이미지 크기가 일치하지 않는 경우
        IOError: 파일 읽기/쓰기 실패

    Example:
        >>> process_image_pair(
        ...     'image001.tif',
        ...     'image002.tif',
        ...     'output.tif',
        ...     is_16bit=True
        ... )
        True

    Note:
        - 두 이미지의 크기(width, height)가 동일해야 합니다.
        - 16비트 이미지는 PIL의 'I;16' 모드로 처리됩니다.
        - 메모리 사용량은 대략 (width * height * 4) bytes입니다.

    See Also:
        - :func:`downsample_image`: 단일 이미지 다운샘플링
        - :func:`average_images`: 이미지 평균화만 수행
    """
    # 구현...
```

**작업 계획**:
- Day 1-2: core/ 모듈
- Day 3: ui/ 모듈
- Day 4: utils/ 모듈
- Day 5: 검토 및 수정

#### Phase 3.2: Sphinx 문서 설정 (3일)

```bash
# Sphinx 설치
pip install sphinx sphinx-rtd-theme sphinx-autodoc-typehints

# 문서 디렉토리 생성
mkdir docs
cd docs
sphinx-quickstart
```

**docs/conf.py**:

```python
import os
import sys
sys.path.insert(0, os.path.abspath('..'))

project = 'CTHarvester'
copyright = '2025, Jikhan Jung'
author = 'Jikhan Jung'

extensions = [
    'sphinx.ext.autodoc',
    'sphinx.ext.napoleon',  # Google/NumPy style docstrings
    'sphinx.ext.viewcode',
    'sphinx.ext.intersphinx',
    'sphinx_autodoc_typehints',
]

templates_path = ['_templates']
exclude_patterns = ['_build', 'Thumbs.db', '.DS_Store']

html_theme = 'sphinx_rtd_theme'
html_static_path = ['_static']

# Napoleon settings
napoleon_google_docstring = True
napoleon_numpy_docstring = False
napoleon_include_init_with_doc = True

# Intersphinx
intersphinx_mapping = {
    'python': ('https://docs.python.org/3', None),
    'numpy': ('https://numpy.org/doc/stable/', None),
}
```

**docs/index.rst**:

```rst
CTHarvester Documentation
=========================

Welcome to CTHarvester's documentation!

CTHarvester is a preprocessing tool for CT (Computed Tomography) image stacks designed for users with limited memory resources.

.. toctree::
   :maxdepth: 2
   :caption: Contents:

   installation
   quickstart
   user_guide
   api_reference
   developer_guide
   changelog

Indices and tables
==================

* :ref:`genindex`
* :ref:`modindex`
* :ref:`search`
```

**docs/api_reference.rst**:

```rst
API Reference
=============

Core Modules
------------

.. automodule:: core.thumbnail_manager
   :members:
   :undoc-members:
   :show-inheritance:

.. automodule:: core.thumbnail_worker
   :members:
   :undoc-members:
   :show-inheritance:

.. automodule:: core.image_processor
   :members:
   :undoc-members:
   :show-inheritance:

UI Modules
----------

.. automodule:: ui.main_window
   :members:
   :undoc-members:
   :show-inheritance:

Utilities
---------

.. automodule:: utils.image_utils
   :members:
   :undoc-members:
   :show-inheritance:

.. automodule:: utils.file_utils
   :members:
   :undoc-members:
   :show-inheritance:
```

```bash
# 문서 빌드
cd docs
make html

# GitHub Pages에 배포
make github
```

#### Phase 3.3: 사용자 가이드 작성 (4일)

**docs/user_guide.rst**:

```rst
User Guide
==========

Installation
------------

Windows
~~~~~~~

1. Download the installer from `GitHub Releases <https://github.com/jikhanjung/CTHarvester/releases>`_
2. Run the installer and follow the instructions
3. Launch CTHarvester from the Start menu

From Source
~~~~~~~~~~~

.. code-block:: bash

   git clone https://github.com/jikhanjung/CTHarvester.git
   cd CTHarvester
   pip install -r requirements.txt
   python main.py

Basic Workflow
--------------

1. Opening a Directory
~~~~~~~~~~~~~~~~~~~~~~

To open a directory containing CT images:

1. Click **File → Open Directory** or press :kbd:`Ctrl+O`
2. Select a directory containing image files (BMP, JPG, PNG, TIF)
3. Wait for thumbnail generation to complete

.. image:: _static/screenshots/open_directory.png
   :alt: Open Directory Dialog

2. Generating Thumbnails
~~~~~~~~~~~~~~~~~~~~~~~~~

CTHarvester automatically generates multi-level thumbnails for fast navigation:

* **Level 1**: Half resolution of original
* **Level 2**: Quarter resolution
* **Level 3**: Eighth resolution
* ...and so on

The thumbnail generation process may take several minutes depending on the number of images.

.. tip::
   You can cancel thumbnail generation at any time by clicking the Cancel button.

3. Navigating Images
~~~~~~~~~~~~~~~~~~~~

Use the following methods to navigate through your image stack:

* **Timeline Slider**: Drag the slider to jump to any position
* **Arrow Keys**: :kbd:`←` previous, :kbd:`→` next
* **Mouse Wheel**: Scroll to navigate
* **Keyboard Shortcuts**:

  * :kbd:`Home`: First slice
  * :kbd:`End`: Last slice
  * :kbd:`Ctrl+→`: Jump forward 10 slices
  * :kbd:`Ctrl+←`: Jump backward 10 slices

4. Setting Crop Region
~~~~~~~~~~~~~~~~~~~~~~

To crop a specific region of interest:

1. Navigate to the bottom boundary of your region
2. Click **Set Bottom** or press :kbd:`B`
3. Navigate to the top boundary
4. Click **Set Top** or press :kbd:`T`

The selected region will be highlighted in green.

.. image:: _static/screenshots/crop_region.png
   :alt: Crop Region Selection

5. Adjusting Threshold
~~~~~~~~~~~~~~~~~~~~~~

For 3D visualization:

1. Use the vertical slider on the right to adjust the threshold
2. Or use keyboard: :kbd:`↑` increase, :kbd:`↓` decrease
3. The 3D view updates in real-time

6. Exporting Results
~~~~~~~~~~~~~~~~~~~~

Cropped Images
^^^^^^^^^^^^^^

To export the cropped image stack:

1. Click **File → Save Cropped Images** or press :kbd:`Ctrl+S`
2. Choose output format (TIF, PNG, JPG)
3. Select output directory
4. Click Save

3D Mesh
^^^^^^^

To export the 3D mesh:

1. Click **File → Export 3D Model** or press :kbd:`Ctrl+E`
2. Choose format (STL, PLY, OBJ)
3. Enter filename
4. Click Save

Troubleshooting
---------------

Thumbnail Generation is Slow
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

* **Solution 1**: Check if the Rust module is installed
* **Solution 2**: Reduce the number of worker threads in Preferences
* **Solution 3**: Close other applications to free up CPU

Out of Memory Error
~~~~~~~~~~~~~~~~~~~

* **Solution 1**: Reduce the crop region size
* **Solution 2**: Use a lower thumbnail level
* **Solution 3**: Increase system memory or use a different computer

3D View Not Working
~~~~~~~~~~~~~~~~~~~

* **Solution 1**: Update graphics drivers
* **Solution 2**: Check if your system supports OpenGL 3.0+
* **Solution 3**: Disable 3D features in Preferences

Keyboard Shortcuts Reference
-----------------------------

.. list-table::
   :header-rows: 1
   :widths: 30 70

   * - Shortcut
     - Action
   * - :kbd:`Ctrl+O`
     - Open directory
   * - :kbd:`Ctrl+S`
     - Save cropped images
   * - :kbd:`Ctrl+E`
     - Export 3D mesh
   * - :kbd:`Ctrl+T`
     - Generate thumbnails
   * - :kbd:`F1`
     - Show keyboard shortcuts
   * - :kbd:`F3`
     - Toggle 3D view
   * - :kbd:`F5`
     - Reload directory
   * - :kbd:`←` :kbd:`→`
     - Navigate slices
   * - :kbd:`↑` :kbd:`↓`
     - Adjust threshold
   * - :kbd:`B`
     - Set bottom boundary
   * - :kbd:`T`
     - Set top boundary
```

#### Phase 3.4: 개발자 가이드 작성 (3일)

**docs/developer_guide.rst**:

```rst
Developer Guide
===============

Setting Up Development Environment
-----------------------------------

Prerequisites
~~~~~~~~~~~~~

* Python 3.11+
* Rust 1.75+ (for Rust module)
* Git

Installation
~~~~~~~~~~~~

.. code-block:: bash

   # Clone repository
   git clone https://github.com/jikhanjung/CTHarvester.git
   cd CTHarvester

   # Create virtual environment
   python -m venv venv
   source venv/bin/activate  # Linux/Mac
   # or
   venv\Scripts\activate  # Windows

   # Install dependencies
   pip install -r requirements-dev.txt

   # Compile Rust module
   maturin develop

Running Tests
~~~~~~~~~~~~~

.. code-block:: bash

   # Run all tests
   pytest

   # Run with coverage
   pytest --cov

   # Run specific test file
   pytest tests/unit/test_image_utils.py

   # Run performance tests
   pytest -m performance

Project Structure
-----------------

::

   CTHarvester/
   ├── main.py                    # Entry point
   ├── core/                      # Core business logic
   │   ├── thumbnail_manager.py
   │   ├── thumbnail_worker.py
   │   └── image_processor.py
   ├── ui/                        # User interface
   │   ├── main_window.py
   │   └── widgets/
   ├── utils/                     # Utility functions
   │   ├── image_utils.py
   │   └── file_utils.py
   ├── security/                  # Security validators
   │   └── file_validator.py
   ├── config/                    # Configuration
   │   ├── constants.py
   │   └── settings.yaml
   ├── src/                       # Rust source code
   │   └── lib.rs
   └── tests/                     # Test suite
       ├── unit/
       ├── integration/
       └── performance/

Architecture
------------

CTHarvester follows a modular architecture with clear separation of concerns:

* **Core**: Business logic, independent of UI
* **UI**: PyQt5-based user interface
* **Utils**: Reusable utility functions
* **Security**: Input validation and security checks

.. image:: _static/architecture_diagram.png
   :alt: Architecture Diagram

Adding New Features
-------------------

1. Create a Feature Branch
~~~~~~~~~~~~~~~~~~~~~~~~~~

.. code-block:: bash

   git checkout -b feature/my-new-feature

2. Write Tests First (TDD)
~~~~~~~~~~~~~~~~~~~~~~~~~~~

.. code-block:: python

   # tests/unit/test_my_feature.py
   import pytest
   from core.my_feature import MyFeatureClass

   class TestMyFeature:
       def test_basic_functionality(self):
           feature = MyFeatureClass()
           result = feature.do_something()
           assert result == expected_value

3. Implement the Feature
~~~~~~~~~~~~~~~~~~~~~~~~~

Follow these guidelines:

* Write clear, descriptive docstrings
* Follow PEP 8 style guide
* Keep functions small and focused
* Use type hints

4. Run Tests
~~~~~~~~~~~~

.. code-block:: bash

   pytest tests/unit/test_my_feature.py

5. Submit Pull Request
~~~~~~~~~~~~~~~~~~~~~~

* Ensure all tests pass
* Update documentation
* Write clear commit messages

Coding Standards
----------------

Style Guide
~~~~~~~~~~~

We follow PEP 8 with these exceptions:

* Maximum line length: 100 characters
* Use double quotes for strings

Type Hints
~~~~~~~~~~

Always use type hints for function signatures:

.. code-block:: python

   def process_image(
       image_path: str,
       threshold: int = 128
   ) -> np.ndarray:
       """Process image with threshold."""
       pass

Docstrings
~~~~~~~~~~

Use Google-style docstrings:

.. code-block:: python

   def function_name(param1: str, param2: int) -> bool:
       """
       Short description.

       Longer description if needed.

       Args:
           param1: Description of param1
           param2: Description of param2

       Returns:
           Description of return value

       Raises:
           ValueError: When something is wrong
       """
       pass

Error Handling
~~~~~~~~~~~~~~

* Use specific exception types
* Always log errors
* Provide user-friendly error messages

.. code-block:: python

   try:
       result = risky_operation()
   except FileNotFoundError as e:
       logger.error(f"File not found: {e}")
       user_error = ErrorMessageBuilder.from_exception(e)
       show_error_dialog(parent, user_error)

Contributing
------------

We welcome contributions! Please:

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Write tests
5. Submit a pull request

See `CONTRIBUTING.md` for detailed guidelines.
```

### 검증 방법

1. **문서 빌드 테스트**
   ```bash
   cd docs
   make html
   # 에러 없이 빌드되는지 확인
   ```

2. **문서 검토**
   - 모든 링크가 작동하는지
   - 코드 예제가 정확한지
   - 스크린샷이 최신인지

3. **사용자 테스트**
   - 비개발자가 문서만 보고 사용 가능한지

---

## 개선사항 4: 빌드 및 배포

### 목표

- 크로스 플랫폼 빌드 (Windows, macOS, Linux)
- GitHub Actions CI/CD 개선
- 자동 릴리스 노트 생성

### 수정 계획

#### Phase 4.1: PyInstaller 크로스 플랫폼 빌드 (4일)

**build_cross_platform.py** (새 파일):

```python
"""
크로스 플랫폼 빌드 스크립트
"""
import os
import sys
import platform
import subprocess
import shutil
from pathlib import Path

def detect_platform():
    """플랫폼 감지"""
    system = platform.system().lower()
    if system == 'darwin':
        return 'macos'
    elif system == 'windows':
        return 'windows'
    elif system == 'linux':
        return 'linux'
    else:
        raise RuntimeError(f"Unsupported platform: {system}")

def build_executable(platform_name):
    """실행 파일 빌드"""
    print(f"Building for {platform_name}...")

    # PyInstaller 명령
    cmd = [
        'pyinstaller',
        '--name=CTHarvester',
        '--windowed',  # GUI 앱
        '--onefile',   # 단일 파일
        f'--icon=icons/icon_{platform_name}.{"icns" if platform_name == "macos" else "ico"}',
        '--add-data=translations:translations',
        '--add-data=config:config',
        '--hidden-import=numpy',
        '--hidden-import=PIL',
        '--hidden-import=PyQt5',
        'main.py'
    ]

    # Rust 모듈 포함 (있는 경우)
    rust_module = f'ctharvester_rs.{"so" if platform_name != "windows" else "pyd"}'
    if os.path.exists(rust_module):
        cmd.append(f'--add-binary={rust_module}:.')

    # 실행
    result = subprocess.run(cmd)

    if result.returncode != 0:
        print("Build failed!")
        sys.exit(1)

    print(f"Build complete for {platform_name}")

def create_installer(platform_name):
    """설치 패키지 생성"""
    if platform_name == 'windows':
        # Inno Setup
        print("Creating Windows installer...")
        subprocess.run([
            'iscc',
            'InnoSetup/setup.iss'
        ])

    elif platform_name == 'macos':
        # DMG
        print("Creating macOS DMG...")
        subprocess.run([
            'hdiutil',
            'create',
            '-volname', 'CTHarvester',
            '-srcfolder', 'dist/CTHarvester.app',
            '-ov',
            'dist/CTHarvester.dmg'
        ])

    elif platform_name == 'linux':
        # AppImage 또는 .deb
        print("Creating Linux package...")
        # AppImage 생성 로직

def main():
    platform_name = detect_platform()
    print(f"Detected platform: {platform_name}")

    # 빌드
    build_executable(platform_name)

    # 설치 패키지
    create_installer(platform_name)

    print("All done!")

if __name__ == '__main__':
    main()
```

#### Phase 4.2: GitHub Actions 개선 (3일)

**.github/workflows/build-all-platforms.yml**:

```yaml
name: Build All Platforms

on:
  push:
    tags:
      - 'v*'
  workflow_dispatch:

jobs:
  build-windows:
    runs-on: windows-latest
    steps:
      - uses: actions/checkout@v3

      - name: Set up Python
        uses: actions/setup-python@v4
        with:
          python-version: '3.11'

      - name: Set up Rust
        uses: actions-rs/toolchain@v1
        with:
          toolchain: stable

      - name: Install dependencies
        run: |
          pip install -r requirements.txt
          pip install pyinstaller

      - name: Build Rust module
        run: maturin build --release

      - name: Build executable
        run: python build_cross_platform.py

      - name: Upload artifact
        uses: actions/upload-artifact@v3
        with:
          name: CTHarvester-Windows
          path: dist/CTHarvesterSetup.exe

  build-macos:
    runs-on: macos-latest
    steps:
      - uses: actions/checkout@v3

      - name: Set up Python
        uses: actions/setup-python@v4
        with:
          python-version: '3.11'

      - name: Set up Rust
        uses: actions-rs/toolchain@v1
        with:
          toolchain: stable

      - name: Install dependencies
        run: |
          pip install -r requirements.txt
          pip install pyinstaller

      - name: Build Rust module
        run: maturin build --release

      - name: Build executable
        run: python build_cross_platform.py

      - name: Upload artifact
        uses: actions/upload-artifact@v3
        with:
          name: CTHarvester-macOS
          path: dist/CTHarvester.dmg

  build-linux:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3

      - name: Set up Python
        uses: actions/setup-python@v4
        with:
          python-version: '3.11'

      - name: Set up Rust
        uses: actions-rs/toolchain@v1
        with:
          toolchain: stable

      - name: Install dependencies
        run: |
          pip install -r requirements.txt
          pip install pyinstaller

      - name: Build Rust module
        run: maturin build --release

      - name: Build executable
        run: python build_cross_platform.py

      - name: Upload artifact
        uses: actions/upload-artifact@v3
        with:
          name: CTHarvester-Linux
          path: dist/CTHarvester.AppImage

  create-release:
    needs: [build-windows, build-macos, build-linux]
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3

      - name: Download all artifacts
        uses: actions/download-artifact@v3

      - name: Generate release notes
        id: release_notes
        run: |
          python scripts/generate_release_notes.py > RELEASE_NOTES.md

      - name: Create Release
        uses: softprops/action-gh-release@v1
        with:
          files: |
            CTHarvester-Windows/*
            CTHarvester-macOS/*
            CTHarvester-Linux/*
          body_path: RELEASE_NOTES.md
        env:
          GITHUB_TOKEN: ${{ secrets.GITHUB_TOKEN }}
```

#### Phase 4.3: 자동 릴리스 노트 생성 (2일)

**scripts/generate_release_notes.py**:

```python
"""
자동 릴리스 노트 생성
"""
import subprocess
import re
from datetime import datetime

def get_commits_since_last_tag():
    """마지막 태그 이후 커밋 가져오기"""
    try:
        # 마지막 태그
        last_tag = subprocess.check_output(
            ['git', 'describe', '--tags', '--abbrev=0'],
            text=True
        ).strip()

        # 커밋 로그
        log = subprocess.check_output(
            ['git', 'log', f'{last_tag}..HEAD', '--pretty=format:%s'],
            text=True
        ).strip()

        return log.split('\n')
    except:
        return []

def categorize_commits(commits):
    """커밋을 카테고리별로 분류"""
    categories = {
        'Features': [],
        'Bug Fixes': [],
        'Performance': [],
        'Documentation': [],
        'Other': []
    }

    for commit in commits:
        if commit.startswith('feat:') or commit.startswith('feature:'):
            categories['Features'].append(commit)
        elif commit.startswith('fix:'):
            categories['Bug Fixes'].append(commit)
        elif commit.startswith('perf:'):
            categories['Performance'].append(commit)
        elif commit.startswith('docs:'):
            categories['Documentation'].append(commit)
        else:
            categories['Other'].append(commit)

    return categories

def generate_release_notes():
    """릴리스 노트 생성"""
    commits = get_commits_since_last_tag()
    categories = categorize_commits(commits)

    # 현재 버전
    with open('version.py', 'r') as f:
        content = f.read()
        version_match = re.search(r'__version__\s*=\s*["\']([^"\']+)["\']', content)
        version = version_match.group(1) if version_match else 'Unknown'

    # 릴리스 노트 작성
    notes = f"# CTHarvester v{version}\n\n"
    notes += f"Release Date: {datetime.now().strftime('%Y-%m-%d')}\n\n"

    for category, commits in categories.items():
        if commits:
            notes += f"## {category}\n\n"
            for commit in commits:
                # 'feat:' 등의 prefix 제거
                clean_commit = re.sub(r'^(feat|fix|perf|docs):\s*', '', commit)
                notes += f"- {clean_commit}\n"
            notes += "\n"

    # 설치 방법
    notes += "## Installation\n\n"
    notes += "Download the appropriate installer for your platform:\n\n"
    notes += "- **Windows**: `CTHarvesterSetup.exe`\n"
    notes += "- **macOS**: `CTHarvester.dmg`\n"
    notes += "- **Linux**: `CTHarvester.AppImage`\n\n"

    # 풀 체인지로그 링크
    notes += "## Full Changelog\n\n"
    notes += f"See [CHANGELOG.md](CHANGELOG.md) for complete details.\n"

    print(notes)

if __name__ == '__main__':
    generate_release_notes()
```

### 검증 방법

1. **로컬 빌드 테스트**
   - 각 플랫폼에서 빌드 스크립트 실행
   - 생성된 실행 파일 테스트

2. **CI/CD 테스트**
   - 테스트 태그 푸시
   - 모든 플랫폼 빌드 성공 확인

---

## 개선사항 5: 코드 품질 도구

### 목표

- Pre-commit hooks 설정
- Linter 통합 (black, flake8, mypy)
- 자동 코드 포맷팅

### 수정 계획

#### Phase 5.1: Pre-commit 설정 (2일)

**.pre-commit-config.yaml**:

```yaml
repos:
  # Black (code formatter)
  - repo: https://github.com/psf/black
    rev: 23.12.1
    hooks:
      - id: black
        language_version: python3.11

  # Flake8 (linter)
  - repo: https://github.com/PyCQA/flake8
    rev: 7.0.0
    hooks:
      - id: flake8
        args: ['--max-line-length=100', '--extend-ignore=E203,W503']

  # isort (import sorting)
  - repo: https://github.com/PyCQA/isort
    rev: 5.13.2
    hooks:
      - id: isort
        args: ['--profile', 'black']

  # mypy (type checking)
  - repo: https://github.com/pre-commit/mirrors-mypy
    rev: v1.8.0
    hooks:
      - id: mypy
        additional_dependencies: [types-PyYAML]
        args: ['--ignore-missing-imports']

  # pytest (run tests)
  - repo: local
    hooks:
      - id: pytest
        name: pytest
        entry: pytest
        language: system
        pass_filenames: false
        always_run: true
        args: ['-v']

  # Trailing whitespace
  - repo: https://github.com/pre-commit/pre-commit-hooks
    rev: v4.5.0
    hooks:
      - id: trailing-whitespace
      - id: end-of-file-fixer
      - id: check-yaml
      - id: check-added-large-files
        args: ['--maxkb=1000']
```

**설치 및 설정**:

```bash
# pre-commit 설치
pip install pre-commit

# Git hooks 설치
pre-commit install

# 수동 실행
pre-commit run --all-files
```

#### Phase 5.2: Linter 설정 파일 (1일)

**.flake8**:

```ini
[flake8]
max-line-length = 100
extend-ignore = E203, W503, E501
exclude =
    .git,
    __pycache__,
    build,
    dist,
    .venv,
    venv,
    *.egg-info
```

**pyproject.toml**:

```toml
[tool.black]
line-length = 100
target-version = ['py311']
include = '\.pyi?$'
exclude = '''
/(
    \.git
  | \.venv
  | build
  | dist
)/
'''

[tool.isort]
profile = "black"
line_length = 100
multi_line_output = 3

[tool.mypy]
python_version = "3.11"
warn_return_any = true
warn_unused_configs = true
disallow_untyped_defs = false
ignore_missing_imports = true

[tool.pytest.ini_options]
testpaths = ["tests"]
python_files = ["test_*.py"]
python_classes = ["Test*"]
python_functions = ["test_*"]
addopts = "-v --cov --cov-report=html"
```

#### Phase 5.3: CI에 코드 품질 체크 통합 (1일)

**.github/workflows/code-quality.yml**:

```yaml
name: Code Quality

on:
  push:
    branches: [main, develop]
  pull_request:
    branches: [main, develop]

jobs:
  lint:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3

      - name: Set up Python
        uses: actions/setup-python@v4
        with:
          python-version: '3.11'

      - name: Install dependencies
        run: |
          pip install black flake8 isort mypy pytest

      - name: Run Black
        run: black --check .

      - name: Run Flake8
        run: flake8 .

      - name: Run isort
        run: isort --check-only .

      - name: Run mypy
        run: mypy . --ignore-missing-imports

      - name: Run tests
        run: pytest
```

### 검증 방법

1. **로컬 테스트**
   ```bash
   pre-commit run --all-files
   ```

2. **커밋 테스트**
   - 의도적으로 포맷 위반 코드 작성
   - 커밋 시도 시 자동 수정/거부되는지 확인

---

## 전체 일정

| 개선사항 | Phase | 소요 기간 | 누적 |
|---------|-------|---------|------|
| 1. UI/UX | 1.1 진행률 단순화 | 3일 | 3일 |
|  | 1.2 3D 비블로킹 | 4일 | 7일 |
|  | 1.3 에러 메시지 | 3일 | 10일 |
|  | 1.4 다국어 완성 | 4일 | 14일 |
|  | 1.5 키보드 단축키 | 2일 | 16일 |
|  | 1.6 툴팁 도움말 | 2일 | 18일 |
| 2. 설정 관리 | 2.1 YAML 시스템 | 3일 | 21일 |
|  | 2.2 설정 GUI | 4일 | 25일 |
| 3. 문서화 | 3.1 Docstring | 5일 | 30일 |
|  | 3.2 Sphinx 설정 | 3일 | 33일 |
|  | 3.3 사용자 가이드 | 4일 | 37일 |
|  | 3.4 개발자 가이드 | 3일 | 40일 |
| 4. 빌드/배포 | 4.1 크로스 플랫폼 | 4일 | 44일 |
|  | 4.2 CI/CD 개선 | 3일 | 47일 |
|  | 4.3 릴리스 노트 | 2일 | 49일 |
| 5. 코드 품질 | 5.1 Pre-commit | 2일 | 51일 |
|  | 5.2 Linter 설정 | 1일 | 52일 |
|  | 5.3 CI 통합 | 1일 | 53일 |

**총 소요 기간**: 약 53일 (약 11주)

## 성공 기준

### 정량적 지표

| 항목 | 현재 | 목표 |
|------|------|------|
| UI 반응성 | 3D 렌더링 시 블로킹 | 항상 반응함 |
| 에러 메시지 이해도 | 30% | 90% |
| 문서 커버리지 | 20% | 95% |
| 다국어 완성도 | 50% | 100% |
| 빌드 플랫폼 | Windows만 | Windows + macOS + Linux |
| 코드 스타일 일관성 | 낮음 | 100% (자동 강제) |

### 정성적 지표

1. **사용자 만족도**: 신규 사용자가 10분 내 기본 기능 사용 가능
2. **개발자 경험**: 기여자가 문서만 보고 개발 환경 구축 가능
3. **프로젝트 성숙도**: 오픈소스 베스트 프랙티스 준수

## 위험 요소 및 대응

### 위험 1: 번역 품질
- **확률**: 중간
- **영향**: 중간
- **대응**: 네이티브 스피커 검토 요청

### 위험 2: 문서 유지보수 부담
- **확률**: 높음
- **영향**: 낮음
- **대응**: Sphinx autodoc으로 자동화

### 위험 3: CI/CD 복잡도 증가
- **확률**: 중간
- **영향**: 낮음
- **대응**: 단계적 도입, 모니터링

## 다음 단계

이 계획 완료 후:

1. **커뮤니티 빌딩**
   - Discord/Slack 채널
   - 월간 뉴스레터
   - 사용자 쇼케이스

2. **플러그인 시스템**
   - 타사 확장 기능 지원
   - 플러그인 마켓플레이스

3. **클라우드 통합**
   - 원격 처리 지원
   - 클라우드 스토리지 연동

## 결론

권장 개선사항 완료 시 CTHarvester는:

**사용자 측면**:
- 직관적이고 반응성 있는 UI
- 명확한 에러 메시지
- 완전한 다국어 지원
- 포괄적인 사용자 가이드

**개발자 측면**:
- 완전한 API 문서
- 일관된 코드 스타일
- 자동화된 품질 검사
- 명확한 기여 가이드라인

**프로젝트 측면**:
- 크로스 플랫폼 지원
- 프로페셔널한 릴리스 프로세스
- 높은 코드 품질
- 활발한 커뮤니티

이로써 CTHarvester는 개인 프로젝트에서 성숙한 오픈소스 프로젝트로 발전할 것이다.
