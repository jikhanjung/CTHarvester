# CTHarvester 코드베이스 종합 분석 및 개선 계획

**날짜**: 2025-09-30
**작성자**: Codebase Analysis Report
**목적**: 전체 코드베이스 분석 및 개선 방향 제시

---

## 📋 목차

1. [프로젝트 현황](#프로젝트-현황)
2. [높은 우선순위 개선사항](#높은-우선순위-개선사항)
3. [중간 우선순위 개선사항](#중간-우선순위-개선사항)
4. [낮은 우선순위 개선사항](#낮은-우선순위-개선사항)
5. [예상 개선 효과](#예상-개선-효과)
6. [실행 계획](#실행-계획)

---

## 프로젝트 현황

### 기본 정보

- **총 Python 파일**: 71개
- **테스트 커버리지**: 195개 테스트 (~95% 코어 모듈)
- **프로젝트 상태**: 최근 대규모 리팩토링 완료 (2025-09-30)
- **총 코드 라인**: ~8,000줄

### 디렉토리 구조

```
CTHarvester/
├── CTHarvester.py          151줄 (✅ 최적화 완료)
├── config/                 78줄
├── core/                   1,126줄
├── ui/                     1,743줄 (⚠️ main_window.py 1,952줄)
├── utils/                  440줄
├── security/               220줄 (✅ 보안 모듈)
├── tests/                  2,200줄 (✅ 195개 테스트)
└── [루트 디렉토리]         ✅ 정리 완료 (6개 필수 파일만 유지)
```

### 최근 리팩토링 성과

2025-09-30에 완료된 주요 작업:
- ✅ CTHarvester.py: 4,840줄 → 151줄 (96.6% 감소)
- ✅ 모듈화 완료 (Phase 1-4)
- ✅ 테스트 129개 → 195개 (+51%)
- ✅ 보안 모듈 구축
- ✅ CI/CD 파이프라인 구축

---

## 높은 우선순위 개선사항

### 1. ⭐ main_window.py 파일 과도한 크기

**파일**: `ui/main_window.py`
**현재 크기**: 1,952 라인 (92KB)
**우선순위**: 🔴 높음 (즉시 처리)

#### 문제점

단일 클래스가 너무 많은 책임을 보유하고 있으며, 복잡한 메소드들이 존재:

| 메소드 | 라인 수 | 대략적 위치 | 책임 |
|--------|---------|------------|------|
| `create_thumbnail_python()` | 323 | ~723-1046 | 썸네일 생성 (Python) |
| `open_dir()` | 232 | ~1179-1411 | 디렉토리 열기 및 파일 로딩 |
| `__init__()` | 200 | ~45-245 | UI 초기화 |
| `load_thumbnail_data_from_disk()` | 160 | ~1055-1215 | 썸네일 로딩 |
| `create_thumbnail_rust()` | 149 | ~802-951 | 썸네일 생성 (Rust) |
| `sort_file_list_from_dir()` | 96 | ~1412-1508 | 파일 정렬 |
| `get_cropped_volume()` | 86 | ~1509-1595 | 볼륨 크롭 |

#### 현재 구조

```python
CTHarvesterMainWindow (1,952줄)
├── UI 초기화 (200줄)
├── 썸네일 생성 로직 (472줄)
├── 파일 처리 로직 (328줄)
├── 설정 관리 (100줄)
├── 이벤트 핸들러 (852줄)
```

#### 제안: 모듈 분리

```python
# 분리 후 구조
CTHarvesterMainWindow (UI만, ~500줄)
ThumbnailGenerator (썸네일 로직, ~500줄)
FileHandler (파일 I/O, ~350줄)
VolumeProcessor (볼륨 처리, ~300줄)
UISetup (UI 초기화 헬퍼, ~300줄)
```

#### 코드 예시

**Before - 모든 것이 main_window.py에**:
```python
class CTHarvesterMainWindow:
    def create_thumbnail_python(self, ...):  # 323 lines
        # 복잡한 썸네일 생성 로직...
        for level in range(total_levels):
            # 이미지 처리
            # 다운샘플링
            # 파일 저장

    def open_dir(self):  # 232 lines
        # 파일 처리 로직...
        # 검증
        # 로딩
```

**After - 분리된 구조**:
```python
# thumbnail_generator.py
class ThumbnailGenerator:
    """썸네일 생성 전용 클래스"""

    def generate_python(self, directory, options):
        """Python 기반 썸네일 생성"""
        # 썸네일 생성 로직만 집중
        pass

    def generate_rust(self, directory, options):
        """Rust 모듈을 사용한 고성능 썸네일 생성"""
        pass

    def load_from_disk(self, directory):
        """디스크에서 기존 썸네일 로딩"""
        pass

# file_handler.py
class FileHandler:
    """파일 I/O 전용 클래스"""

    def open_directory(self, path):
        """디렉토리 열기 및 파일 목록 가져오기"""
        pass

    def sort_files(self, files):
        """파일 정렬 (자연 정렬)"""
        pass

    def validate_directory(self, path):
        """디렉토리 검증"""
        pass

# volume_processor.py
class VolumeProcessor:
    """볼륨 처리 전용 클래스"""

    def get_cropped_volume(self, volume, bounds):
        """볼륨 크롭"""
        pass

    def resample_volume(self, volume, scale):
        """볼륨 리샘플링"""
        pass

# main_window.py (간소화)
class CTHarvesterMainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setup_ui()

        # 헬퍼 클래스 초기화
        self.thumbnail_gen = ThumbnailGenerator()
        self.file_handler = FileHandler()
        self.volume_processor = VolumeProcessor()

    def open_dir(self):
        """디렉토리 열기 - 위임 패턴"""
        path = QFileDialog.getExistingDirectory(...)

        # 파일 핸들러에 위임
        files = self.file_handler.open_directory(path)

        # 썸네일 생성기에 위임
        self.thumbnail_gen.generate(files)

        # UI 업데이트만 담당
        self.update_ui(files)
```

#### 예상 효과

- 📉 **main_window.py 크기**: 1,952줄 → ~500줄 (74% 감소)
- ✅ **단일 책임 원칙** 준수
- 🧪 **단위 테스트** 작성 용이
- 🔄 **코드 재사용성** 증가
- 👥 **신규 개발자 이해도** 향상

---

### 2. UI 테스트 거의 없음

**미커버 모듈**: UI 전체 (1,743줄)
**우선순위**: 🔴 높음

#### 문제점

현재 테스트 커버리지가 높지만 (195개, 95%), UI 컴포넌트는 거의 테스트되지 않음:

| 파일 | 크기 | 테스트 상태 |
|------|------|------------|
| `ui/main_window.py` | 1,952줄 | ❌ 테스트 없음 |
| `ui/dialogs/settings_dialog.py` | 442줄 | ❌ 테스트 없음 |
| `ui/widgets/mcube_widget.py` | 727줄 | ❌ 테스트 없음 |
| `ui/widgets/object_viewer_2d.py` | 559줄 | ❌ 테스트 없음 |

#### 제안: pytest-qt 사용한 UI 테스트

```python
# tests/ui/test_main_window.py
import pytest
from pytestqt.qtbot import QtBot
from ui.main_window import CTHarvesterMainWindow

def test_main_window_initialization(qtbot):
    """메인 윈도우가 올바르게 초기화되는지 테스트"""
    window = CTHarvesterMainWindow()
    qtbot.addWidget(window)

    # 기본 속성 검증
    assert window.windowTitle() == "CT Harvester v0.2.3"
    assert window.edtDirname.placeholderText() == "Select directory to load CT data"
    assert window.btnOpenDir.isEnabled()

def test_open_directory_updates_ui(qtbot, tmp_path):
    """디렉토리 열기가 UI를 올바르게 업데이트하는지 테스트"""
    window = CTHarvesterMainWindow()
    qtbot.addWidget(window)

    # 테스트 이미지 디렉토리 생성
    test_dir = tmp_path / "test_images"
    test_dir.mkdir()
    for i in range(10):
        img_path = test_dir / f"test_{i:04d}.tif"
        # 간단한 더미 이미지 생성
        from PIL import Image
        import numpy as np
        img = Image.fromarray(np.zeros((100, 100), dtype=np.uint8))
        img.save(str(img_path))

    # 디렉토리 열기
    window.open_directory_internal(str(test_dir))

    # UI 업데이트 검증
    assert window.edtDirname.text() == str(test_dir)
    assert window.obj_viewer_2d.minimum_volume is not None

def test_thumbnail_generation_progress(qtbot, mocker):
    """썸네일 생성 중 진행률이 올바르게 업데이트되는지 테스트"""
    window = CTHarvesterMainWindow()
    qtbot.addWidget(window)

    # 진행률 시그널 모킹
    progress_values = []
    window.progress_updated.connect(lambda val: progress_values.append(val))

    # 썸네일 생성 시뮬레이션
    window.start_thumbnail_generation(test_params)

    # 진행률이 업데이트될 때까지 대기
    qtbot.waitUntil(lambda: len(progress_values) > 0, timeout=5000)

    # 최종 진행률이 100%인지 확인
    assert progress_values[-1] == 100

def test_settings_dialog_saves_preferences(qtbot):
    """설정 다이얼로그가 설정을 올바르게 저장하는지 테스트"""
    from ui.dialogs import SettingsDialog

    dialog = SettingsDialog()
    qtbot.addWidget(dialog)

    # 설정 변경
    dialog.spinMaxThreads.setValue(4)
    dialog.cbxUseRust.setChecked(True)

    # 저장 버튼 클릭
    qtbot.mouseClick(dialog.btnSave, Qt.LeftButton)

    # 설정이 저장되었는지 확인
    from utils.settings_manager import SettingsManager
    settings = SettingsManager()
    assert settings.get('max_threads') == 4
    assert settings.get('use_rust') is True

def test_mcube_widget_renders_without_crash(qtbot):
    """MCube 위젯이 크래시 없이 렌더링되는지 테스트"""
    from ui.widgets import MCubeWidget
    import numpy as np

    widget = MCubeWidget()
    qtbot.addWidget(widget)

    # 테스트 볼륨 데이터
    volume = np.random.rand(50, 50, 50)

    # 렌더링 시도
    widget.set_volume(volume)
    widget.show()

    # 크래시 없이 렌더링되는지 확인
    qtbot.waitExposed(widget)
    assert widget.isVisible()

@pytest.mark.parametrize("threshold", [0, 64, 128, 192, 255])
def test_threshold_slider_updates_visualization(qtbot, threshold):
    """임계값 슬라이더가 시각화를 업데이트하는지 테스트"""
    window = CTHarvesterMainWindow()
    qtbot.addWidget(window)

    # 슬라이더 값 변경
    window.slider_threshold.setValue(threshold)

    # 시각화가 업데이트되었는지 확인
    assert window.obj_viewer_2d.threshold == threshold
```

#### 엣지 케이스 테스트

```python
# tests/ui/test_edge_cases.py

def test_open_empty_directory(qtbot, tmp_path):
    """빈 디렉토리 열 때 적절한 에러 메시지 표시"""
    window = CTHarvesterMainWindow()
    qtbot.addWidget(window)

    empty_dir = tmp_path / "empty"
    empty_dir.mkdir()

    # 에러 메시지 캡처
    with pytest.warns(UserWarning, match="No supported image files"):
        window.open_directory_internal(str(empty_dir))

def test_open_directory_no_permission(qtbot, tmp_path):
    """권한 없는 디렉토리 접근 시 적절한 처리"""
    window = CTHarvesterMainWindow()
    qtbot.addWidget(window)

    restricted_dir = tmp_path / "restricted"
    restricted_dir.mkdir(mode=0o000)

    try:
        with pytest.raises(PermissionError):
            window.open_directory_internal(str(restricted_dir))
    finally:
        restricted_dir.chmod(0o755)

def test_invalid_file_format_ignored(qtbot, tmp_path):
    """지원하지 않는 파일 형식은 무시"""
    window = CTHarvesterMainWindow()
    qtbot.addWidget(window)

    test_dir = tmp_path / "mixed"
    test_dir.mkdir()

    # 지원 형식
    (test_dir / "valid.tif").write_bytes(b"fake_tif")
    # 미지원 형식
    (test_dir / "invalid.txt").write_text("not an image")
    (test_dir / "invalid.exe").write_bytes(b"executable")

    window.open_directory_internal(str(test_dir))

    # 지원 형식만 로드되었는지 확인
    assert len(window.image_files) == 1
    assert window.image_files[0].endswith("valid.tif")

@pytest.mark.parametrize("seq_begin,seq_end,expected", [
    (0, 10, 11),      # 정상 범위
    (0, 0, 1),        # 단일 이미지
    (100, 200, 101),  # 큰 범위
    (10, 5, None),    # 역순 (에러)
])
def test_sequence_range_validation(seq_begin, seq_end, expected):
    """시퀀스 범위 검증 테스트"""
    window = CTHarvesterMainWindow()

    if expected is None:
        with pytest.raises(ValueError):
            window.validate_sequence_range(seq_begin, seq_end)
    else:
        count = window.validate_sequence_range(seq_begin, seq_end)
        assert count == expected
```

#### 통합 테스트

```python
# tests/integration/test_full_workflow.py

def test_full_thumbnail_generation_workflow(qtbot, tmp_path):
    """전체 썸네일 생성 워크플로우 테스트"""
    # 1. 메인 윈도우 초기화
    window = CTHarvesterMainWindow()
    qtbot.addWidget(window)

    # 2. 테스트 이미지 디렉토리 준비
    test_dir = prepare_test_images(tmp_path, count=50)

    # 3. 디렉토리 열기
    window.open_directory_internal(str(test_dir))
    assert window.edtDirname.text() == str(test_dir)

    # 4. 썸네일 생성 시작
    window.start_thumbnail_generation()

    # 5. 완료될 때까지 대기 (최대 30초)
    qtbot.waitUntil(
        lambda: window.thumbnail_generation_complete,
        timeout=30000
    )

    # 6. 썸네일 파일 생성 확인
    thumbnail_dir = test_dir / ".thumbnail"
    assert thumbnail_dir.exists()
    assert len(list(thumbnail_dir.glob("*.tif"))) > 0

    # 7. UI 상태 확인
    assert window.btnResample.isEnabled()
    assert window.progress_bar.value() == 100
```

#### 예상 효과

- 🧪 **테스트 커버리지**: 40% → 70%+ (전체 프로젝트)
- 🐛 **UI 버그 조기 발견**
- 🔒 **리팩토링 시 안정성 보장**
- ✅ **회귀 테스트 자동화**

---

### 3. 아키텍처: Controller 패턴 도입

**현재 문제**: `CTHarvesterMainWindow`가 너무 많은 책임 보유
**우선순위**: 🔴 높음

#### 현재 의존성

```
CTHarvesterMainWindow
├── UI 렌더링
├── 썸네일 생성
├── 파일 I/O
├── 설정 관리
├── 이벤트 처리
├── 볼륨 처리
└── imports:
    ├── config.constants
    ├── ui.dialogs
    ├── ui.widgets
    ├── core.thumbnail_manager
    ├── core.progress_manager
    ├── security.file_validator
    ├── vertical_stack_slider (루트!) ⚠️
    └── utils.*
```

#### 제안: Controller 패턴

```python
# controllers/thumbnail_controller.py
class ThumbnailController:
    """썸네일 생성 비즈니스 로직 전용 컨트롤러"""

    def __init__(self, view, model):
        self.view = view
        self.model = model
        self.generator = ThumbnailGenerator()
        self.progress_manager = ProgressManager()

    def generate_thumbnails(self, directory, options):
        """썸네일 생성 워크플로우 제어"""
        # 1. 파일 검증
        if not self._validate_directory(directory):
            self.view.show_error("Invalid directory")
            return

        # 2. 진행률 초기화
        self.progress_manager.start()

        # 3. 생성 시작
        self.generator.generate(directory, options)

        # 4. 진행률 업데이트 (시그널 연결)
        self.generator.progress.connect(self._on_progress)
        self.generator.completed.connect(self._on_completed)

    def _on_progress(self, value):
        """진행률 업데이트 핸들러"""
        self.view.update_progress(value)
        eta = self.progress_manager.calculate_eta()
        self.view.update_eta(eta)

    def _on_completed(self):
        """완료 핸들러"""
        self.view.show_message("Thumbnail generation completed")
        self.model.set_thumbnails_ready(True)

# controllers/file_controller.py
class FileController:
    """파일 I/O 비즈니스 로직 전용 컨트롤러"""

    def __init__(self, view, model):
        self.view = view
        self.model = model
        self.file_handler = FileHandler()
        self.validator = SecureFileValidator()

    def open_directory(self, path):
        """디렉토리 열기 워크플로우 제어"""
        try:
            # 1. 보안 검증
            validated_path = self.validator.validate_path(path)

            # 2. 파일 목록 가져오기
            files = self.file_handler.list_images(validated_path)

            if not files:
                self.view.show_warning("No image files found")
                return

            # 3. 모델 업데이트
            self.model.set_directory(validated_path)
            self.model.set_files(files)

            # 4. 뷰 업데이트
            self.view.update_directory_label(validated_path)
            self.view.enable_controls(True)

        except FileSecurityError as e:
            self.view.show_error(f"Security error: {e}")
        except Exception as e:
            self.view.show_error(f"Failed to open directory: {e}")

# controllers/settings_controller.py
class SettingsController:
    """설정 관리 전용 컨트롤러"""

    def __init__(self, view, model):
        self.view = view
        self.model = model
        self.settings_manager = SettingsManager()

    def load_settings(self):
        """설정 로드"""
        settings = self.settings_manager.load()
        self.model.set_settings(settings)
        self.view.apply_settings(settings)

    def save_settings(self, settings):
        """설정 저장"""
        try:
            self.settings_manager.save(settings)
            self.model.set_settings(settings)
            self.view.show_message("Settings saved")
        except Exception as e:
            self.view.show_error(f"Failed to save settings: {e}")

# ui/main_window.py (간소화)
class CTHarvesterMainWindow(QMainWindow):
    """순수 UI 담당 - 비즈니스 로직은 컨트롤러에 위임"""

    def __init__(self):
        super().__init__()
        self.setup_ui()

        # 모델 초기화
        self.model = CTHarvesterModel()

        # 컨트롤러 초기화
        self.thumbnail_ctrl = ThumbnailController(self, self.model)
        self.file_ctrl = FileController(self, self.model)
        self.settings_ctrl = SettingsController(self, self.model)

        # 설정 로드
        self.settings_ctrl.load_settings()

    def on_open_dir_clicked(self):
        """디렉토리 열기 버튼 클릭 - UI 이벤트만 처리"""
        path = QFileDialog.getExistingDirectory(
            self,
            self.tr("Select Directory"),
            self.model.get_last_directory()
        )

        if path:
            # 비즈니스 로직은 컨트롤러에 위임
            self.file_ctrl.open_directory(path)

    def on_generate_thumbnails_clicked(self):
        """썸네일 생성 버튼 클릭"""
        options = self._get_thumbnail_options()

        # 비즈니스 로직은 컨트롤러에 위임
        self.thumbnail_ctrl.generate_thumbnails(
            self.model.get_directory(),
            options
        )

    # View 인터페이스 구현 (컨트롤러가 호출)
    def update_progress(self, value):
        """진행률 업데이트"""
        self.progress_bar.setValue(value)

    def update_eta(self, eta):
        """예상 남은 시간 업데이트"""
        self.label_eta.setText(f"ETA: {eta}")

    def show_error(self, message):
        """에러 메시지 표시"""
        QMessageBox.critical(self, "Error", message)

    def show_message(self, message):
        """정보 메시지 표시"""
        QMessageBox.information(self, "Information", message)

    def enable_controls(self, enabled):
        """컨트롤 활성화/비활성화"""
        self.btnResample.setEnabled(enabled)
        self.btnSaveCropped.setEnabled(enabled)
```

#### 예상 효과

- 📦 **모듈화**: 독립적으로 테스트 가능
- 🔄 **재사용성**: 비즈니스 로직 다른 곳에서도 사용 가능
- 🧪 **테스트 용이**: Mock 객체로 쉽게 테스트
- 🧹 **가독성**: 각 클래스의 책임이 명확
- 🛠️ **유지보수**: 변경 영향 범위 최소화

---

## 중간 우선순위 개선사항

### 4. 루트 디렉토리 정리

**현재 상태**: ✅ **완료됨** (2025-09-30)
**우선순위**: ~~🟡 중간~~ → ✅ 완료

#### 산재된 파일 목록

```bash
# 테스트 파일들 (8개)
PCA_test.py                  # PCA 알고리즘 실험
PCA_test2.py                 # PCA 추가 실험
pymcubes_test.py             # PyMCubes 라이브러리 테스트
vtk_test.py                  # VTK 테스트 1
vtk_test2.py                 # VTK 테스트 2
vtk_test3.py                 # VTK 테스트 3
vtk_test4.py                 # VTK 테스트 4
test_settings_dialog.py      # 설정 다이얼로그 테스트

# 실험/프로토타입 파일들 (6개)
box_counting.py              # 빈 파일 (0 bytes)
mcube_test.py                # Marching Cubes 실험
multithread.py               # 멀티스레딩 실험
mdstatistics.py              # 통계 계산 실험
resample.py                  # 리샘플링 실험
convert_tps.py               # TPS 파일 변환

# 유틸리티 스크립트 (2개)
convert_icon.py              # 아이콘 변환 (유지 필요)
manage_version.py            # 버전 관리 (유지 필요)

# UI 컴포넌트 (잘못된 위치)
vertical_stack_slider.py     # ⚠️ UI 위젯인데 루트에 위치 (381줄)

# 중복 파일
file_security.py             # ⚠️ security/file_validator.py와 중복
```

#### 완료된 작업 (2025-09-30)

```bash
# ✅ 1. 테스트/실험 파일 제거 (14개)
# - PCA_test.py, PCA_test2.py
# - vtk_test.py, vtk_test2.py, vtk_test3.py, vtk_test4.py
# - pymcubes_test.py, mcube_test.py
# - test_settings_dialog.py
# - multithread.py, mdstatistics.py, resample.py
# - box_counting.py (빈 파일)
# - file_security.py (중복 파일)

# ✅ 2. 유틸리티 스크립트 이동
mv convert_icon.py scripts/
mv convert_tps.py scripts/

# ✅ 3. UI 위젯을 올바른 위치로 이동
mv vertical_stack_slider.py ui/widgets/
```

#### Import 경로 업데이트 ✅

```python
# ui/main_window.py 수정 완료

# Before
from vertical_stack_slider import VerticalTimeline

# After
from ui.widgets.vertical_stack_slider import VerticalTimeline
```

#### 정리 후 구조 ✅

```
CTHarvester/
├── CTHarvester.py          # 메인 엔트리
├── CTLogger.py             # 로거
├── version.py              # 버전 정보
├── build.py                # 빌드 스크립트
├── build_cross_platform.py # 크로스 플랫폼 빌드
├── manage_version.py       # 버전 관리
├── requirements.txt
├── ...
├── scripts/                # ✅ 유틸리티 스크립트
│   ├── convert_icon.py     # 이동됨
│   ├── convert_tps.py      # 이동됨
│   └── (기타 테스트 스크립트들)
└── ui/
    └── widgets/
        └── vertical_stack_slider.py  # ✅ 이동됨
```

**최종 결과**: 루트 디렉토리에 6개의 필수 파일만 유지, 14개 불필요한 파일 제거

#### 예상 효과

- 🗂️ **깔끔한 프로젝트 구조**
- 🎯 **핵심 파일 쉽게 파악** (신규 개발자)
- 🧹 **혼란 제거**
- 📁 **명확한 파일 분류**

---

### 5. ~~메모리 사용 최적화~~ (불필요)

**현재 상태**: ✅ **문제 없음** - 재분석 완료
**위치**: `ui/main_window.py:1179-1439`
**우선순위**: ~~🟡 중간~~ → ❌ 불필요

#### 재분석 결과

초기 분석에서는 `minimum_volume`이 원본 데이터 전체를 로드한다고 오해했으나, 실제로는 **가장 작은 LoD 레벨**만 로드합니다:

```python
# minimum_volume은 최소 해상도 썸네일 데이터
# 예: 원본이 2048x2048이어도, minimum_volume은 256x256으로 다운샘플링됨
```

#### 실제 메모리 사용량

| 원본 데이터 | minimum_volume 크기 | 메모리 사용 |
|------------|-------------------|-----------|
| 2000 슬라이스 × 2048 × 2048 | 2000 × 256 × 256 | ~128MB |
| 1000 슬라이스 × 4096 × 4096 | 1000 × 256 × 256 | ~64MB |

**결론**: `minimum_volume`은 이미 메모리 효율적으로 설계되어 있으므로 추가 최적화 불필요

**참고**: 향후 원본 크기 데이터를 직접 로드해야 하는 기능이 추가될 경우, 위의 분석 내용이 다시 유용할 수 있습니다.

---

### 5. 리소스 누수 방지

**문제점**: 일부 파일 핸들링에서 명시적 close 없음
**우선순위**: 🟡 중간

#### 취약한 패턴들

```python
# 패턴 1: open() 후 close() 없음
fh = open(obj_filename, 'w')
for v in vertices:
    fh.write('v {} {} {}\n'.format(v[0], v[1], v[2]))
for f in faces:
    fh.write('f {} {} {}\n'.format(f[0]+1, f[1]+1, f[2]+1))
# close() 호출 없음 ⚠️
# 예외 발생 시 파일 핸들 누수

# 패턴 2: Image.open() 후 close() 없음
img = Image.open(path)
arr = np.array(img)
process(arr)
# img.close() 호출 없음 ⚠️

# 패턴 3: 반복문에서 리소스 누적
for i in range(1000):
    img = Image.open(files[i])
    data = np.array(img)
    # 명시적 close 없이 다음 반복
    # GC가 즉시 실행 안 될 수 있음
```

#### 개선 방안

```python
# 개선 1: Context Manager 사용 (with 문)
# Before
fh = open(obj_filename, 'w')
for v in vertices:
    fh.write('v {} {} {}\n'.format(v[0], v[1], v[2]))
# fh.close() 없음

# After
with open(obj_filename, 'w') as fh:
    for v in vertices:
        fh.write('v {} {} {}\n'.format(v[0], v[1], v[2]))
# 자동으로 close()됨, 예외 발생 시에도 보장 ✅

# 개선 2: PIL Image도 Context Manager
# Before
img = Image.open(path)
arr = np.array(img)
process(arr)

# After
with Image.open(path) as img:
    arr = np.array(img)
process(arr)
# 자동으로 close()됨 ✅

# 개선 3: 명시적 정리 (with 사용 불가능한 경우)
try:
    img = Image.open(path)
    arr = np.array(img)
    process(arr)
finally:
    if img:
        img.close()  # 항상 실행 ✅

# 개선 4: 반복문에서 명시적 해제
for i in range(1000):
    img = None  # 이전 참조 제거
    try:
        img = Image.open(files[i])
        data = np.array(img)
        process(data)
    finally:
        if img:
            img.close()
        # 주기적 GC (선택사항)
        if i % 100 == 0:
            import gc
            gc.collect()
```

#### 코드 스캔 및 수정 대상

```bash
# 파일 핸들 누수 가능성 검색
grep -n "open(" ui/main_window.py | grep -v "with"

# PIL Image 누수 가능성 검색
grep -n "Image.open(" ui/main_window.py | grep -v "with"
```

#### 예상 효과

- 🔒 **파일 핸들 누수** 방지
- 💥 **예외 발생 시에도 리소스 정리** 보장
- 🐧 **리눅스에서 "Too many open files" 에러** 방지
- 🪟 **Windows에서 파일 잠금 문제** 방지

---

### 6. 엣지 케이스 테스트 강화

**현재 상태**: 테스트는 주로 happy path만 커버
**우선순위**: 🟡 중간

#### 미커버 시나리오

```python
# tests/edge_cases/test_directory_operations.py

def test_open_empty_directory(qtbot, tmp_path):
    """빈 디렉토리 열 때 적절한 메시지"""
    window = CTHarvesterMainWindow()
    qtbot.addWidget(window)

    empty_dir = tmp_path / "empty"
    empty_dir.mkdir()

    # 에러 대신 경고 표시
    with pytest.warns(UserWarning, match="No supported image files"):
        window.open_directory_internal(str(empty_dir))

    # UI 상태 확인
    assert not window.btnResample.isEnabled()

def test_open_directory_no_permission(qtbot, tmp_path):
    """권한 없는 디렉토리 접근 시 적절한 처리"""
    window = CTHarvesterMainWindow()
    qtbot.addWidget(window)

    restricted_dir = tmp_path / "restricted"
    restricted_dir.mkdir(mode=0o000)

    try:
        with pytest.raises(PermissionError):
            window.open_directory_internal(str(restricted_dir))

        # 에러 메시지가 사용자 친화적인지 확인
        # (실제로는 QMessageBox를 모킹해서 확인)
    finally:
        restricted_dir.chmod(0o755)

def test_open_directory_with_mixed_files(qtbot, tmp_path):
    """지원/미지원 파일이 섞여 있을 때"""
    window = CTHarvesterMainWindow()
    qtbot.addWidget(window)

    test_dir = tmp_path / "mixed"
    test_dir.mkdir()

    # 지원 형식
    create_test_image(test_dir / "valid1.tif")
    create_test_image(test_dir / "valid2.tif")

    # 미지원 형식
    (test_dir / "invalid.txt").write_text("not an image")
    (test_dir / "README.md").write_text("# README")
    (test_dir / "script.py").write_text("print('hello')")

    window.open_directory_internal(str(test_dir))

    # 지원 형식만 로드되었는지 확인
    assert len(window.image_files) == 2
    assert all(f.endswith('.tif') for f in window.image_files)

def test_open_directory_with_corrupted_images(qtbot, tmp_path):
    """손상된 이미지 파일 처리"""
    window = CTHarvesterMainWindow()
    qtbot.addWidget(window)

    test_dir = tmp_path / "corrupted"
    test_dir.mkdir()

    # 정상 이미지
    create_test_image(test_dir / "good1.tif")

    # 손상된 이미지 (잘못된 데이터)
    (test_dir / "corrupted.tif").write_bytes(b"not a real tif file")

    # 정상 이미지
    create_test_image(test_dir / "good2.tif")

    # 경고와 함께 정상 파일만 로드
    with pytest.warns(UserWarning, match="corrupted"):
        window.open_directory_internal(str(test_dir))

    assert len(window.image_files) == 2

# tests/edge_cases/test_memory_limits.py

def test_thumbnail_generation_large_images(qtbot, tmp_path):
    """매우 큰 이미지 처리 (10000x10000)"""
    window = CTHarvesterMainWindow()
    qtbot.addWidget(window)

    test_dir = tmp_path / "large"
    test_dir.mkdir()

    # 10000x10000 이미지 생성
    large_img = Image.fromarray(
        np.random.randint(0, 255, (10000, 10000), dtype=np.uint8)
    )
    large_img.save(test_dir / "huge.tif")

    window.open_directory_internal(str(test_dir))

    # 메모리 에러 없이 처리되는지 확인
    window.generate_thumbnails()
    qtbot.waitUntil(lambda: window.thumbnail_complete, timeout=60000)

    assert window.thumbnail_complete

@pytest.mark.slow
def test_out_of_memory_handling(qtbot, tmp_path, monkeypatch):
    """메모리 부족 시 graceful degradation"""
    window = CTHarvesterMainWindow()
    qtbot.addWidget(window)

    # numpy.zeros를 모킹하여 MemoryError 시뮬레이션
    def mock_zeros(*args, **kwargs):
        raise MemoryError("Insufficient memory")

    monkeypatch.setattr(np, "zeros", mock_zeros)

    test_dir = create_test_directory(tmp_path, num_images=100)

    # 메모리 부족 시 적절한 에러 메시지
    with pytest.raises(MemoryError):
        window.open_directory_internal(str(test_dir))

    # UI가 여전히 반응하는지 확인
    assert window.isEnabled()

def test_disk_full_during_save(qtbot, tmp_path, monkeypatch):
    """디스크 공간 부족 시 처리"""
    window = CTHarvesterMainWindow()
    qtbot.addWidget(window)

    # Image.save를 모킹하여 OSError 시뮬레이션
    def mock_save(self, path, *args, **kwargs):
        raise OSError("No space left on device")

    monkeypatch.setattr(Image.Image, "save", mock_save)

    # 저장 시도
    with pytest.raises(OSError, match="No space left"):
        window.save_cropped_images(str(tmp_path))

    # 사용자 친화적 에러 메시지가 표시되었는지 확인

# tests/edge_cases/test_sequence_validation.py

@pytest.mark.parametrize("seq_begin,seq_end,expected", [
    (0, 10, 11),      # 정상 범위
    (0, 0, 1),        # 단일 이미지
    (100, 200, 101),  # 큰 범위
    (10, 5, None),    # 역순 (에러 예상)
    (-1, 10, None),   # 음수 (에러 예상)
    (0, 10000, None), # 범위 초과 (에러 예상)
])
def test_sequence_range_validation(seq_begin, seq_end, expected):
    """시퀀스 범위 검증 테스트"""
    window = CTHarvesterMainWindow()

    if expected is None:
        with pytest.raises((ValueError, IndexError)):
            window.validate_sequence_range(seq_begin, seq_end)
    else:
        count = window.validate_sequence_range(seq_begin, seq_end)
        assert count == expected

@pytest.mark.parametrize("threshold", [-1, 0, 128, 255, 256, 1000])
def test_threshold_boundary_values(qtbot, threshold):
    """임계값 경계 테스트"""
    window = CTHarvesterMainWindow()
    qtbot.addWidget(window)

    if 0 <= threshold <= 255:
        # 유효한 범위
        window.set_threshold(threshold)
        assert window.get_threshold() == threshold
    else:
        # 범위 밖
        with pytest.raises(ValueError):
            window.set_threshold(threshold)
```

#### 예상 효과

- 🐛 **프로덕션 버그** 대폭 감소
- 🔒 **견고성** 향상
- 😊 **사용자 경험** 개선 (적절한 에러 메시지)
- 📈 **신뢰성** 증가

---

### 7. Docstring 개선

**문제점**: 복잡한 함수에 docstring 부족
**우선순위**: 🟡 중간

#### 개선 전후 비교

**Before**:
```python
# ui/main_window.py:723
def calculate_total_thumbnail_work(self, seq_begin, seq_end, size, max_size):
    # Simple comment only
    work = 0
    # ... complex logic ...
    return work
```

**After**:
```python
def calculate_total_thumbnail_work(self, seq_begin, seq_end, size, max_size):
    """Calculate total work units for thumbnail generation across all LoD levels.

    This function computes the weighted total work required to generate thumbnails
    at multiple Level of Detail (LoD) levels. Each level is progressively smaller
    and requires less work, but the first level has extra weight due to I/O overhead.

    The calculation follows this algorithm:
    1. Determine number of LoD levels based on size/max_size ratio
    2. Calculate work at each level: num_images × (size at level)
    3. Apply 1.5x weight to first level (I/O overhead)
    4. Sum all work units

    Args:
        seq_begin (int): Starting sequence number (inclusive)
        seq_end (int): Ending sequence number (inclusive)
        size (int): Initial image dimension (width or height, assumed square)
        max_size (int): Maximum thumbnail size threshold for stopping LoD generation

    Returns:
        int: Total weighted work units

    Side Effects:
        Sets the following instance variables:
        - self.level_sizes (list[int]): Size at each LoD level
        - self.level_work_distribution (list[float]): Work ratio per level
        - self.total_levels (int): Number of LoD levels
        - self.weighted_total_work (int): Same as return value

    Raises:
        ValueError: If seq_begin > seq_end or size <= 0

    Example:
        >>> self.calculate_total_thumbnail_work(0, 99, 2048, 256)
        150  # (100 images × 1 level) × 1.5 weight

        >>> self.calculate_total_thumbnail_work(0, 99, 4096, 256)
        300  # Multiple LoD levels

    Note:
        The first level has 1.5x weight because it involves reading from disk,
        while subsequent levels only downsample from memory. This provides more
        accurate progress estimation.

    See Also:
        - create_thumbnail_python(): Uses this calculation
        - create_thumbnail_rust(): Alternative implementation
        - ProgressManager.calculate_eta(): Uses the work units
    """
    # Validation
    if seq_begin > seq_end:
        raise ValueError(f"seq_begin ({seq_begin}) must be <= seq_end ({seq_end})")
    if size <= 0:
        raise ValueError(f"size must be positive, got {size}")

    # ... implementation ...
```

#### 개선 대상 파일

| 파일 | 현재 상태 | 개선 필요 |
|------|----------|----------|
| `ui/main_window.py` | 35개 메소드 중 15개 docstring 부족 | ⚠️ 높음 |
| `vertical_stack_slider.py` | 클래스 및 메소드 문서화 거의 없음 | ⚠️ 높음 |
| `ui/widgets/mcube_widget.py` | OpenGL 관련 설명 부족 | ⚠️ 중간 |
| `ui/widgets/object_viewer_2d.py` | 일부 메소드만 문서화 | ⚠️ 중간 |
| `core/thumbnail_manager.py` | 양호 | ✅ 낮음 |

#### Docstring 템플릿

```python
def function_name(arg1, arg2, kwarg1=None):
    """One-line summary (period at end).

    More detailed description if needed. Can be multiple paragraphs.
    Explain what the function does, not how it does it.

    Args:
        arg1 (type): Description of arg1
        arg2 (type): Description of arg2
        kwarg1 (type, optional): Description. Defaults to None.

    Returns:
        type: Description of return value

    Raises:
        ExceptionType: When this exception is raised

    Example:
        >>> function_name(1, 2)
        3

    Note:
        Additional notes, warnings, or caveats

    See Also:
        - related_function(): Brief description
        - AnotherClass: Brief description
    """
```

#### 예상 효과

- 📚 **코드 이해도** 향상
- 🤖 **Sphinx로 자동 API 문서** 생성 가능
- 🆕 **신규 개발자 온보딩** 시간 50% 단축
- 🔍 **IDE 자동완성** 품질 향상

---

## 낮은 우선순위 개선사항

### 8. vertical_stack_slider.py 위치 이동

**현재 상태**: ✅ **완료됨** (2025-09-30)
**우선순위**: ~~🟢 낮음~~ → ✅ 완료

```bash
# ✅ 파일 이동 완료
mv vertical_stack_slider.py ui/widgets/

# ✅ Import 경로 업데이트 완료 (main_window.py)
from ui.widgets.vertical_stack_slider import VerticalTimeline
```

---

### 9. Import 최적화

**문제**: 일부 함수 내부 import
**위치**: `ui/main_window.py:723, 778, 806, 1123, 1655`
**우선순위**: 🟢 낮음

```python
# Before (함수 내부 import)
def some_function():
    import logging  # 불필요 - 이미 파일 상단에 import됨
    import configparser  # 순환 import 우려가 없다면 상단으로

# After (파일 상단)
import logging
import configparser

def some_function():
    # import 문 없음
```

---

### 10. 불필요한 sleep 제거

**위치**: `core/thumbnail_manager.py:450, 550, 563`
**우선순위**: 🟢 낮음

```python
# Before
QThread.msleep(100)  # 불필요한 대기
QThread.msleep(10)   # 응답성을 위한 대기

# After
# 이벤트 기반 처리로 변경하거나 최소화
```

---

### 11. API 문서 빌드

**현재**: Sphinx 설정 존재하나 빌드 안 됨
**우선순위**: 🟢 낮음

```bash
# Sphinx 문서 빌드
cd docs/
make html

# GitHub Pages 배포
# .github/workflows/docs.yml 추가
```

---

## 예상 개선 효과

### 정량적 지표

| 항목 | Before | After | 개선율 |
|------|--------|-------|--------|
| **main_window.py 크기** | 1,952줄 | ~500줄 | **-74%** ⭐ |
| **테스트 커버리지 (전체)** | ~40% | ~70% | **+75%** ⭐ |
| **UI 테스트** | 0개 | ~30개 | **∞** ⭐ |
| **루트 디렉토리 파일 수** | 70개 | 56개 | **-20%** ✅ |
| **최대 함수 크기** | 323줄 | <100줄 | **-69%** |
| **Docstring 커버리지** | ~60% | ~90% | **+50%** |

### 정성적 효과

#### 개발 생산성
- ✅ **유지보수성** 대폭 향상 (모듈화로 인한)
- ✅ **신규 개발자 온보딩** 시간 50% 단축
- ✅ **버그 발생률** 감소 (테스트 강화)
- ✅ **코드 재사용성** 증가 (Controller 패턴)

#### 사용자 경험
- ✅ **적절한 에러 메시지** (엣지 케이스 처리)
- ✅ **안정성** 향상 (리소스 누수 방지)

#### 코드 품질
- ✅ **단일 책임 원칙** 준수
- ✅ **테스트 가능한 구조**
- ✅ **명확한 문서화**
- ✅ **일관된 프로젝트 구조**

---

## 실행 계획

### Phase 1 (1-2주): 긴급 개선 🔴

**Week 1: main_window.py 분리**
- [ ] Day 1-2: `ThumbnailGenerator` 클래스 추출
  - `create_thumbnail_python()` 메소드 이동
  - `create_thumbnail_rust()` 메소드 이동
  - `load_thumbnail_data_from_disk()` 메소드 이동
  - 테스트 작성

- [ ] Day 3: `FileHandler` 클래스 추출
  - `open_dir()` 로직 일부 이동
  - `sort_file_list_from_dir()` 메소드 이동
  - 파일 검증 로직 통합
  - 테스트 작성

- [ ] Day 4: `VolumeProcessor` 클래스 추출
  - `get_cropped_volume()` 메소드 이동
  - 리샘플링 로직 이동
  - 테스트 작성

- [ ] Day 5: `UISetup` 헬퍼 클래스 추출
  - `__init__()` 의 UI 초기화 로직 분리
  - 위젯 생성 메소드들 그룹화

**Week 2: UI 테스트 & 정리**
- [ ] Day 1-2: 기본 UI 테스트 작성
  - `test_main_window.py` (초기화, 디렉토리 열기)
  - `test_settings_dialog.py` (설정 저장/로드)

- [ ] Day 3-4: 핵심 기능 테스트
  - 썸네일 생성 워크플로우
  - 진행률 업데이트
  - 에러 핸들링

- [ ] Day 5: 루트 디렉토리 정리
  - `experiments/` 디렉토리 생성 및 파일 이동
  - `scripts/` 디렉토리 생성 및 파일 이동
  - `vertical_stack_slider.py` → `ui/widgets/timeline_slider.py`
  - Import 경로 업데이트

**예상 결과**:
- main_window.py: 1,952줄 → ~1,200줄 (38% 감소)
- UI 테스트: 0개 → ~15개
- 프로젝트 구조 정리 완료

---

### Phase 2 (2-3주): 구조 개선 🟡

**Week 3-4: Controller 패턴 도입**
- [ ] Day 1-2: `ThumbnailController` 구현
  - 썸네일 생성 워크플로우 제어
  - 진행률 관리 통합
  - 테스트 작성

- [ ] Day 3-4: `FileController` 구현
  - 파일 열기 워크플로우 제어
  - 보안 검증 통합
  - 테스트 작성

- [ ] Day 5-6: `SettingsController` 구현
  - 설정 로드/저장 워크플로우
  - 검증 로직 추가
  - 테스트 작성

- [ ] Day 7-8: main_window.py 리팩토링
  - 컨트롤러 통합
  - 비즈니스 로직 제거 (위임)
  - UI 이벤트 핸들링만 남김

- [ ] Day 9-10: 통합 테스트
  - 전체 워크플로우 테스트
  - 리그레션 테스트

**Week 5: 엣지 케이스 테스트**
- [ ] Day 1-2: 디렉토리 관련 엣지 케이스
  - 빈 디렉토리
  - 권한 없음
  - 손상된 파일

- [ ] Day 3-4: 메모리/리소스 관련
  - 대용량 이미지
  - 메모리 부족
  - 디스크 가득 참

- [ ] Day 5: 경계값 테스트
  - 시퀀스 범위
  - 임계값
  - Parametrized 테스트

**예상 결과**:
- main_window.py: ~1,200줄 → ~500줄 (58% 추가 감소, 총 74%)
- 컨트롤러: 3개 클래스 (~600줄)
- 테스트: +30개 (총 ~225개)
- 테스트 커버리지: 50% → 70%

---

### Phase 3 (3-4일): 안정성/문서화 🟢

**Week 6: 리소스 관리 & 문서화**
- [ ] Day 1-2: 리소스 관리 개선
  - Context manager 전환 (open, Image.open)
  - 파일 핸들 누수 검사
  - 테스트 작성

- [ ] Day 3-4: Docstring 개선
  - 주요 클래스/메소드 문서화
  - Google/NumPy 스타일 적용
  - Sphinx 문서 빌드

**예상 결과**:
- 리소스 누수: 0건
- Docstring 커버리지: 90%+
- API 문서 배포 완료

---

### Phase 별 우선순위 요약

```
Phase 1 (1-2주) 🔴 긴급
├─ main_window.py 분리         ⭐⭐⭐⭐⭐
├─ 기본 UI 테스트              ⭐⭐⭐⭐⭐
└─ 루트 디렉토리 정리          ✅ 완료

Phase 2 (2-3주) 🟡 중요
├─ Controller 패턴             ⭐⭐⭐⭐
├─ 엣지 케이스 테스트          ⭐⭐⭐⭐
└─ 통합 테스트                 ⭐⭐⭐

Phase 3 (3-4일) 🟢 개선
├─ 리소스 관리                 ⭐⭐⭐
└─ Docstring 개선              ⭐⭐
```

---

## 시작 가능한 첫 단계

가장 임팩트가 큰 개선부터 시작하려면:

### 1️⃣ **ThumbnailGenerator 추출** (2-3시간)

**목표**: main_window.py에서 썸네일 생성 로직 분리

**작업 내용**:
```python
# 1. 새 파일 생성: core/thumbnail_generator.py
# 2. 다음 메소드들을 이동:
#    - create_thumbnail_python()  (323 lines)
#    - create_thumbnail_rust()    (149 lines)
#    - load_thumbnail_data_from_disk() (160 lines)
# 3. main_window.py에서 이 클래스 사용하도록 수정
# 4. 기본 테스트 작성
```

**예상 효과**:
- main_window.py: 1,952줄 → 1,450줄 (26% 감소)
- 썸네일 로직 재사용 가능
- 독립적으로 테스트 가능

---

## 마무리

이 분석은 CTHarvester 프로젝트가 최근 대규모 리팩토링을 성공적으로 완료했음을 보여줍니다. 그러나 여전히 개선의 여지가 있으며, 특히:

### 핵심 개선 사항
1. **main_window.py 추가 분리** (가장 시급)
2. **UI 테스트 추가** (안정성 보장)
3. **Controller 패턴 도입** (아키텍처 개선)

### 기대 효과
- 🏗️ **더 나은 아키텍처**: 유지보수 용이, 확장 가능
- 🧪 **높은 테스트 커버리지**: 버그 감소, 안정성 향상
- 💾 **메모리 최적화**: 저사양 PC 지원, 대용량 데이터 처리
- 📚 **완벽한 문서화**: 신규 개발자 온보딩 쉬움

이 계획을 단계적으로 실행하면 CTHarvester는 **엔터프라이즈급 품질**을 완전히 갖춘 프로젝트가 될 것입니다.

---

**작성일**: 2025-09-30
**다음 단계**: Phase 1 착수 - ThumbnailGenerator 추출부터 시작
**예상 완료**: Phase 1-3 전체 완료 시 약 4-6주
