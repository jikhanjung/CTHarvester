# main_window.py 분리 가능 루틴 분석

**날짜**: 2025-10-01
**목적**: create_thumbnail_python 외에 분리 가능한 루틴 식별
**현재 파일 크기**: 1,817 줄

---

## 📊 메소드 분류 및 분석

### 전체 메소드 분포 (20줄 이상)

| 카테고리 | 메소드 | 라인 수 | 분리 가능성 |
|---------|--------|---------|-----------|
| **THUMBNAIL** | `create_thumbnail_python` | 402 | ⚠️ 복잡 (보류) |
| **OTHER** | `progress_callback` | 114 | ⭐⭐⭐ 높음 |
| **UI_INIT** | `__init__` | 215 | ⭐⭐⭐⭐⭐ 매우 높음 |
| **LOAD** | `open_dir` | 80 | ⭐⭐ 중간 |
| **EXPORT** | `save_result` | 73 | ⭐⭐⭐⭐ 높음 |
| **SETTINGS** | `read_settings` | 70 | ⭐⭐⭐⭐⭐ 매우 높음 |
| **UI_EVENT** | `comboLevelIndexChanged` | 62 | ⭐ 낮음 |
| **OTHER** | `closeEvent` | 58 | ⭐⭐ 중간 |
| **THUMBNAIL** | `load_thumbnail_data_from_disk` | 51 | ⭐⭐ 중간 |
| **THUMBNAIL** | `_update_3d_view_with_thumbnails` | 49 | ⭐⭐ 중간 |
| **3D_VIEW** | `update_3D_view` | 48 | ⭐ 낮음 |
| **SETTINGS** | `save_settings` | 43 | ⭐⭐⭐⭐⭐ 매우 높음 |
| **THUMBNAIL** | `create_thumbnail_rust` | 41 | ⭐⭐ 중간 |
| **EXPORT** | `export_3d_model` | 41 | ⭐⭐⭐⭐ 높음 |

**총 줄 수**: 1,817줄
**분리 가능 예상**: ~600줄 (33%)

---

## 🎯 우선순위별 분리 권장사항

### 우선순위 1: UI 초기화 분리 (215줄) ⭐⭐⭐⭐⭐

**현재 상황**:
- `__init__` 메소드가 215줄
- 모든 위젯 생성, 레이아웃 구성, 시그널 연결을 한 곳에서 처리
- 가독성 매우 낮음

**제안**: `ui/setup/main_window_setup.py` 생성

```python
# ui/setup/main_window_setup.py
class MainWindowSetup:
    """MainWindow UI 초기화 전담 클래스"""

    def __init__(self, main_window):
        self.window = main_window

    def setup_directory_controls(self):
        """디렉토리 선택 컨트롤 초기화"""
        self.window.dirname_layout = QHBoxLayout()
        self.window.dirname_widget = QWidget()
        self.window.btnOpenDir = QPushButton(self.window.tr("Open Directory"))
        self.window.btnOpenDir.clicked.connect(self.window.open_dir)
        self.window.edtDirname = QLineEdit()
        self.window.cbxUseRust = QCheckBox(self.window.tr("Use Rust"))
        # ... (30줄)

    def setup_image_info_controls(self):
        """이미지 정보 표시 컨트롤 초기화"""
        self.window.image_info_layout = QHBoxLayout()
        self.window.lblLevel = QLabel(self.window.tr("Level"))
        self.window.comboLevel = QComboBox()
        self.window.comboLevel.currentIndexChanged.connect(
            self.window.comboLevelIndexChanged
        )
        # ... (25줄)

    def setup_viewer_controls(self):
        """이미지 뷰어 및 슬라이더 컨트롤 초기화"""
        self.window.image_widget = QWidget()
        self.window.image_label = ObjectViewer2D(self.window.image_widget)
        self.window.threshold_slider = QSlider(Qt.Vertical)
        # ... (40줄)

    def setup_crop_controls(self):
        """크롭 관련 버튼 초기화"""
        self.window.btnSetBottom = QPushButton(self.window.tr("Set Bottom"))
        self.window.btnSetTop = QPushButton(self.window.tr("Set Top"))
        self.window.btnReset = QPushButton(self.window.tr("Reset"))
        # ... (20줄)

    def setup_action_buttons(self):
        """저장/내보내기 버튼 초기화"""
        self.window.btnSave = QPushButton(self.window.tr("Save cropped image stack"))
        self.window.btnExport = QPushButton(self.window.tr("Export 3D Model"))
        self.window.btnPreferences = QPushButton(...)
        # ... (30줄)

    def setup_3d_viewer(self):
        """3D 뷰어 위젯 초기화"""
        self.window.mcube_widget = MCubeWidget(self.window)
        self.window.mcube_widget.setGeometry(self.window.mcube_geometry)
        # ... (20줄)

    def setup_layouts(self):
        """전체 레이아웃 구성"""
        self.window.main_layout = QHBoxLayout()
        self.window.main_layout.addWidget(self.window.image_widget)
        self.window.main_layout.addWidget(self.window.sub_widget)
        # ... (30줄)

    def setup_all(self):
        """전체 UI 초기화 실행"""
        self.setup_directory_controls()
        self.setup_image_info_controls()
        self.setup_viewer_controls()
        self.setup_crop_controls()
        self.setup_action_buttons()
        self.setup_3d_viewer()
        self.setup_layouts()
```

**main_window.py에서 사용**:
```python
class CTHarvesterMainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.m_app = QApplication.instance()

        # 기본 설정
        self.setWindowIcon(QIcon(resource_path("CTHarvester_48_2.png")))
        self.setWindowTitle(f"{self.tr('CT Harvester')} v{PROGRAM_VERSION}")
        self.setGeometry(QRect(100, 100, 600, 550))

        # 데이터 초기화
        self.settings_hash = {}
        self.level_info = []
        self.threadpool = QThreadPool()

        # 헬퍼 초기화
        self.settings_manager = SettingsManager()
        self.file_handler = FileHandler()
        self.thumbnail_generator = ThumbnailGenerator()
        self.volume_processor = VolumeProcessor()

        # 설정 읽기
        self.read_settings()

        # UI 초기화 (위임)
        ui_setup = MainWindowSetup(self)
        ui_setup.setup_all()
```

**예상 효과**:
- **-215줄** (1,817 → 1,602줄, -11.8%)
- 가독성 대폭 향상
- UI 구조 파악 용이
- 테스트 가능

---

### 우선순위 2: 설정 관리 분리 (113줄) ⭐⭐⭐⭐⭐

**현재 상황**:
- `read_settings()`: 70줄
- `save_settings()`: 43줄
- 총 113줄의 설정 관리 코드

**제안**: `ui/handlers/settings_handler.py` 생성

```python
# ui/handlers/settings_handler.py
class WindowSettingsHandler:
    """MainWindow 전용 설정 핸들러"""

    def __init__(self, main_window, settings_manager):
        self.window = main_window
        self.settings = settings_manager
        self.app = QApplication.instance()

    def read_all_settings(self):
        """모든 설정 읽기"""
        try:
            self._read_directory_settings()
            self._read_geometry_settings()
            self._read_language_settings()
            self._read_processing_settings()
        except Exception as e:
            logger.error(f"Error reading settings: {e}")
            self._apply_defaults()

    def _read_directory_settings(self):
        """디렉토리 관련 설정"""
        self.app.remember_directory = self.settings.get(
            "window.remember_position", True
        )
        if self.app.remember_directory:
            self.app.default_directory = self.settings.get(
                "application.default_directory", "."
            )
        else:
            self.app.default_directory = "."

    def _read_geometry_settings(self):
        """창 크기/위치 설정"""
        self.app.remember_geometry = self.settings.get("window.remember_size", True)
        if self.app.remember_geometry:
            saved_geom = self.settings.get("window.main_geometry", None)
            if saved_geom and isinstance(saved_geom, dict):
                self.window.setGeometry(QRect(
                    saved_geom.get("x", 100),
                    saved_geom.get("y", 100),
                    saved_geom.get("width", 600),
                    saved_geom.get("height", 550),
                ))
            # mcube 설정도 처리...
        else:
            self.window.setGeometry(QRect(100, 100, 600, 550))

    def _read_language_settings(self):
        """언어 설정"""
        lang_code = self.settings.get("application.language", "auto")
        lang_map = {"auto": "en", "en": "en", "ko": "ko"}
        self.app.language = lang_map.get(lang_code, "en")

    def _read_processing_settings(self):
        """처리 관련 설정 (Rust 모듈 등)"""
        use_rust = self.settings.get("processing.use_rust_module", True)
        self.app.use_rust_thumbnail = use_rust
        if hasattr(self.window, "cbxUseRust"):
            self.window.cbxUseRust.setChecked(use_rust)

    def save_all_settings(self):
        """모든 설정 저장"""
        try:
            if self.app.remember_directory:
                self._save_directory_settings()
            if self.app.remember_geometry:
                self._save_geometry_settings()
            self._save_processing_settings()
            self.settings.save()
        except Exception as e:
            logger.error(f"Error saving settings: {e}")

    def _save_directory_settings(self):
        """디렉토리 설정 저장"""
        self.settings.set(
            "application.default_directory",
            self.app.default_directory
        )

    def _save_geometry_settings(self):
        """창 크기/위치 저장"""
        geom = self.window.geometry()
        self.settings.set("window.main_geometry", {
            "x": geom.x(), "y": geom.y(),
            "width": geom.width(), "height": geom.height()
        })
        # mcube 설정도 저장...

    def _save_processing_settings(self):
        """처리 설정 저장"""
        if hasattr(self.window, "cbxUseRust"):
            self.app.use_rust_thumbnail = self.window.cbxUseRust.isChecked()
            self.settings.set(
                "processing.use_rust_module",
                self.app.use_rust_thumbnail
            )

    def _apply_defaults(self):
        """기본값 적용 (오류 시)"""
        self.app.remember_directory = True
        self.app.default_directory = "."
        self.app.remember_geometry = True
        self.window.setGeometry(QRect(100, 100, 600, 550))
        self.app.language = "en"
        self.app.use_rust_thumbnail = True
```

**main_window.py에서 사용**:
```python
class CTHarvesterMainWindow(QMainWindow):
    def __init__(self):
        # ... 초기화 ...

        # 설정 핸들러 초기화
        self.settings_handler = WindowSettingsHandler(self, self.settings_manager)

        # 설정 읽기 (간소화)
        self.settings_handler.read_all_settings()

    def read_settings(self):
        """설정 읽기 - 핸들러에 위임"""
        self.settings_handler.read_all_settings()

    def save_settings(self):
        """설정 저장 - 핸들러에 위임"""
        self.settings_handler.save_all_settings()
```

**예상 효과**:
- **-113줄** (1,602 → 1,489줄, -7.0%)
- 설정 관리 로직 중앙화
- 테스트 용이
- 재사용 가능

---

### 우선순위 3: Export/Save 작업 분리 (114줄) ⭐⭐⭐⭐

**현재 상황**:
- `export_3d_model()`: 41줄
- `save_result()`: 73줄
- 총 114줄의 내보내기/저장 로직

**제안**: `ui/handlers/export_handler.py` 생성

```python
# ui/handlers/export_handler.py
class ExportHandler:
    """파일 내보내기/저장 전담 클래스"""

    def __init__(self, main_window):
        self.window = main_window

    def export_3d_model_to_obj(self):
        """3D 모델을 OBJ 형식으로 내보내기"""
        # 파일 선택 다이얼로그
        obj_filename = self._get_export_filename()
        if not obj_filename:
            return

        # 볼륨 데이터 획득 및 메시 생성
        try:
            vertices, triangles = self._generate_mesh()
        except Exception as e:
            self._show_error(f"Failed to generate 3D mesh: {e}")
            return

        # OBJ 파일 저장
        self._save_obj_file(obj_filename, vertices, triangles)

    def _get_export_filename(self):
        """파일 저장 경로 선택"""
        filename, _ = QFileDialog.getSaveFileName(
            self.window,
            "Save File As",
            self.window.edtDirname.text(),
            "OBJ format (*.obj)"
        )
        if filename:
            logger.info(f"Exporting 3D model to: {filename}")
        return filename

    def _generate_mesh(self):
        """Marching Cubes로 메시 생성"""
        import mcubes

        threed_volume, _ = self.window.get_cropped_volume()
        isovalue = self.window.image_label.isovalue
        vertices, triangles = mcubes.marching_cubes(threed_volume, isovalue)

        # 좌표 변환
        for i in range(len(vertices)):
            vertices[i] = np.array([
                vertices[i][2],
                vertices[i][0],
                vertices[i][1]
            ])

        return vertices, triangles

    def _save_obj_file(self, filename, vertices, triangles):
        """OBJ 파일 쓰기"""
        try:
            with open(filename, "w") as fh:
                for v in vertices:
                    fh.write(f"v {v[0]} {v[1]} {v[2]}\n")
                for f in triangles:
                    fh.write(f"f {f[0]+1} {f[1]+1} {f[2]+1}\n")
            logger.info(f"Successfully saved OBJ file: {filename}")
        except Exception as e:
            self._show_error(f"Failed to save OBJ file: {e}")

    def save_cropped_image_stack(self):
        """크롭된 이미지 스택 저장"""
        # 디렉토리 선택
        target_dir = self._get_save_directory()
        if not target_dir:
            return

        # 크롭 정보 수집
        crop_info = self._get_crop_info()

        # 진행률 다이얼로그 표시
        progress_dialog = self._create_progress_dialog()

        # 이미지 저장
        self._save_images_with_progress(target_dir, crop_info, progress_dialog)

        # 정리
        self._cleanup_after_save(progress_dialog, target_dir)

    def _get_save_directory(self):
        """저장 디렉토리 선택"""
        target_dirname = QFileDialog.getExistingDirectory(
            self.window,
            self.window.tr("Select directory to save"),
            self.window.edtDirname.text()
        )
        return target_dirname if target_dirname else None

    def _get_crop_info(self):
        """크롭 정보 수집"""
        return {
            "from_x": self.window.image_label.crop_from_x,
            "from_y": self.window.image_label.crop_from_y,
            "to_x": self.window.image_label.crop_to_x,
            "to_y": self.window.image_label.crop_to_y,
            "size_idx": self.window.comboLevel.currentIndex(),
            "top_idx": self.window.image_label.top_idx,
            "bottom_idx": self.window.image_label.bottom_idx,
        }

    def _create_progress_dialog(self):
        """진행률 다이얼로그 생성"""
        from ui.dialogs import ProgressDialog

        dialog = ProgressDialog(self.window)
        dialog.update_language()
        dialog.setModal(True)
        dialog.show()
        return dialog

    def _save_images_with_progress(self, target_dir, crop_info, progress_dialog):
        """진행률 표시하며 이미지 저장"""
        QApplication.setOverrideCursor(Qt.WaitCursor)

        total_count = crop_info["top_idx"] - crop_info["bottom_idx"] + 1

        for i, idx in enumerate(range(crop_info["bottom_idx"], crop_info["top_idx"] + 1)):
            # 파일 경로 생성
            filename = self._build_filename(idx, crop_info["size_idx"])
            source_path = self._get_source_path(filename, crop_info["size_idx"])

            # 이미지 열기, 크롭, 저장
            try:
                self._process_single_image(
                    source_path,
                    target_dir,
                    filename,
                    crop_info
                )
            except Exception as e:
                logger.error(f"Error processing {source_path}: {e}")
                continue

            # 진행률 업데이트
            self._update_progress(progress_dialog, i + 1, total_count)

        QApplication.restoreOverrideCursor()

    def _process_single_image(self, source_path, target_dir, filename, crop_info):
        """단일 이미지 처리 (열기, 크롭, 저장)"""
        with Image.open(source_path) as img:
            if crop_info["from_x"] > -1:
                img = img.crop((
                    crop_info["from_x"],
                    crop_info["from_y"],
                    crop_info["to_x"],
                    crop_info["to_y"]
                ))
            img.save(os.path.join(target_dir, filename))

    def _cleanup_after_save(self, progress_dialog, target_dir):
        """저장 완료 후 정리"""
        progress_dialog.close()

        # 디렉토리 열기 옵션
        if self.window.cbxOpenDirAfter.isChecked():
            os.startfile(target_dir)

    def _show_error(self, message):
        """에러 메시지 표시"""
        QMessageBox.critical(
            self.window,
            self.window.tr("Error"),
            self.window.tr(message)
        )
```

**main_window.py에서 사용**:
```python
class CTHarvesterMainWindow(QMainWindow):
    def __init__(self):
        # ... 초기화 ...
        self.export_handler = ExportHandler(self)

    def export_3d_model(self):
        """3D 모델 내보내기 - 핸들러에 위임"""
        self.export_handler.export_3d_model_to_obj()

    def save_result(self):
        """이미지 저장 - 핸들러에 위임"""
        self.export_handler.save_cropped_image_stack()
```

**예상 효과**:
- **-114줄** (1,489 → 1,375줄, -7.7%)
- Export 로직 재사용 가능
- 진행률 관리 개선 가능
- 테스트 용이

---

### 우선순위 4: Progress Callback 분리 (114줄) ⭐⭐⭐

**현재 상황**:
- `create_thumbnail_rust()` 내부의 `progress_callback` 함수가 114줄
- 중첩 함수로 작성되어 있음

**제안**: `ui/handlers/progress_callback_handler.py` 생성

```python
# ui/handlers/progress_callback_handler.py
class ThumbnailProgressHandler:
    """썸네일 생성 진행률 처리 전담 클래스"""

    def __init__(self, main_window, thumbnail_manager, progress_manager):
        self.window = main_window
        self.thumbnail_mgr = thumbnail_manager
        self.progress_mgr = progress_manager
        self.last_update_time = 0
        self.update_interval = 0.1  # 100ms

    def create_callback(self):
        """진행률 콜백 함수 생성"""
        def progress_callback(percentage):
            import time

            current_time = time.time()
            if current_time - self.last_update_time < self.update_interval:
                return  # 너무 잦은 업데이트 방지

            self.last_update_time = current_time

            # 진행률 업데이트
            self._update_progress_display(percentage)

            # ETA 계산 및 표시
            self._update_eta_display()

            # UI 이벤트 처리
            QApplication.processEvents()

        return progress_callback

    def _update_progress_display(self, percentage):
        """진행률 표시 업데이트"""
        if hasattr(self.window, "progress_dialog") and self.window.progress_dialog:
            self.window.progress_dialog.pb_progress.setValue(int(percentage))

    def _update_eta_display(self):
        """예상 남은 시간 표시"""
        eta = self.progress_mgr.calculate_eta()
        if eta and hasattr(self.window, "progress_dialog") and self.window.progress_dialog:
            self.window.progress_dialog.lbl_detail.setText(f"ETA: {eta}")
```

**예상 효과**:
- **-114줄** (간접적, create_thumbnail_rust 간소화)
- 진행률 관리 로직 재사용 가능
- 테스트 가능

---

## 📈 예상 누적 효과

| 단계 | 분리 항목 | 줄 수 | 누적 감소 | 남은 줄 수 | 감소율 |
|------|----------|-------|----------|-----------|--------|
| **시작** | - | - | - | 1,817 | - |
| 1 | UI 초기화 | -215 | -215 | 1,602 | 11.8% |
| 2 | 설정 관리 | -113 | -328 | 1,489 | 18.0% |
| 3 | Export/Save | -114 | -442 | 1,375 | 24.3% |
| 4 | Progress Callback | -114 | -556 | 1,261 | 30.6% |

**최종 예상 크기**: **1,261줄** (현재 1,817줄 대비 **30.6% 감소**)

---

## 🎯 실행 계획

### Phase A: UI 초기화 분리 (1-2일)

**작업**:
1. `ui/setup/` 디렉토리 생성
2. `MainWindowSetup` 클래스 구현
3. `__init__` 메소드 리팩토링
4. 테스트 작성

**예상 시간**: 1-2일
**위험도**: 낮음 (단순 이동)

---

### Phase B: 설정 관리 분리 (0.5-1일)

**작업**:
1. `ui/handlers/` 디렉토리 생성
2. `WindowSettingsHandler` 클래스 구현
3. `read_settings()`, `save_settings()` 리팩토링
4. 테스트 작성

**예상 시간**: 0.5-1일
**위험도**: 낮음 (로직 변경 없음)

---

### Phase C: Export 작업 분리 (1일)

**작업**:
1. `ExportHandler` 클래스 구현
2. `export_3d_model()`, `save_result()` 리팩토링
3. 진행률 표시 로직 개선
4. 테스트 작성

**예상 시간**: 1일
**위험도**: 중간 (파일 I/O 관련)

---

### Phase D: Progress Callback 분리 (0.5일, 선택)

**작업**:
1. `ThumbnailProgressHandler` 구현
2. `create_thumbnail_rust()` 간소화
3. 테스트 작성

**예상 시간**: 0.5일
**위험도**: 낮음

---

## 💡 권장 사항

### 즉시 시작 가능한 작업

1. **UI 초기화 분리** (Phase A)
   - 가장 임팩트 큼 (-215줄)
   - 위험도 낮음
   - 복잡도 낮음
   - 2일 이내 완료 가능

2. **설정 관리 분리** (Phase B)
   - 두 번째로 임팩트 큼 (-113줄)
   - 매우 간단함
   - 1일 이내 완료 가능

### 추가 고려 사항

**분리하지 않는 것이 좋은 메소드**:
- `update_3D_view()`, `update_curr_slice()` - UI 업데이트 로직, MainWindow와 강하게 결합
- `comboLevelIndexChanged()`, `sliderValueChanged()` - 이벤트 핸들러, 분리 시 오히려 복잡해짐
- `open_dir()` - 여러 컴포넌트 조율, MainWindow에 남겨두는 것이 적절

**create_thumbnail_python 관련**:
- 402줄로 가장 크지만 복잡도가 높아 보류 권장
- 대신 위의 4개 항목 분리로 **556줄 감소** 가능
- 이는 create_thumbnail_python(402줄)보다 **38% 더 많은** 감소

---

## 🏁 결론

**즉시 실행 가능한 개선**:
1. UI 초기화 분리 (215줄) - **최우선 권장**
2. 설정 관리 분리 (113줄) - **두 번째 권장**
3. Export 작업 분리 (114줄) - **세 번째 권장**

**예상 총 효과**:
- **-442줄** (24.3% 감소)
- **3-4일** 작업
- **위험도 낮음**

**create_thumbnail_python 대비 장점**:
- 더 많은 줄 수 감소 (442줄 vs 402줄)
- 위험도 훨씬 낮음
- 작업 시간 짧음
- 즉시 시작 가능

---

**작성일**: 2025-10-01
**다음 단계**: Phase A (UI 초기화 분리) 착수 권장
**예상 완료**: Phase A-C 전체 완료 시 3-4일
