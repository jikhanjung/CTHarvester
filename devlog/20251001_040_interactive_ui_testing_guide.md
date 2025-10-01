# Interactive UI Testing Guide

**Date**: 2025-10-01
**Project**: CTHarvester
**Topic**: How to Test Interactive UI Components with pytest-qt

---

## Overview

Interactive UI components (forms, progress dialogs, file browsers) require special testing strategies. This guide shows how to test them effectively using pytest-qt.

---

## Core Principles

### 1. **Separation of Concerns**
- Test **logic** separately from **UI rendering**
- Mock external dependencies (file I/O, long operations)
- Focus on user interactions and state changes

### 2. **pytest-qt Tools**
```python
qtbot.mouseClick(widget, Qt.LeftButton)      # Click
qtbot.keyClick(widget, Qt.Key_Enter)         # Keyboard
qtbot.waitSignal(signal, timeout=1000)       # Wait for signals
qtbot.addWidget(widget)                       # Auto-cleanup
```

### 3. **Mocking Strategy**
- Mock file dialogs → Return test paths
- Mock long operations → Instant completion
- Mock external APIs → Controlled responses

---

## Interactive Pattern Examples

### Pattern 1: Form Input Testing

**Component**: SettingsDialog with text fields, checkboxes, comboboxes

```python
def test_form_input_and_save(qtbot, tmp_path):
    """Test filling form and saving settings"""

    # Setup: Create settings manager with temp file
    settings_file = tmp_path / "settings.yaml"
    settings_manager = SettingsManager(settings_file)

    # Create dialog
    dialog = SettingsDialog(settings_manager)
    qtbot.addWidget(dialog)

    # === INTERACT: Change form values ===

    # 1. ComboBox selection
    language_combo = dialog.language_combo
    language_combo.setCurrentIndex(1)  # Select "English"
    assert language_combo.currentText() == "English"

    # 2. Checkbox toggle
    remember_check = dialog.remember_position_check
    qtbot.mouseClick(remember_check, Qt.LeftButton)
    assert remember_check.isChecked() == True

    # 3. SpinBox value
    max_size_spin = dialog.max_thumbnail_size_spin
    max_size_spin.setValue(512)
    assert max_size_spin.value() == 512

    # === SAVE: Click OK button ===
    ok_button = find_button(dialog, "OK")

    with qtbot.waitSignal(dialog.accepted, timeout=1000):
        qtbot.mouseClick(ok_button, Qt.LeftButton)

    # === VERIFY: Settings were saved ===
    settings = settings_manager.load_settings()
    assert settings['language'] == 'en'
    assert settings['remember_window_position'] == True
    assert settings['max_thumbnail_size'] == 512
```

**Key Techniques**:
- Direct property access: `widget.setValue()`
- Signal verification: `waitSignal(dialog.accepted)`
- State persistence check: Read from file after save

---

### Pattern 2: File Dialog Mocking

**Component**: Settings dialog with "Browse" buttons

```python
def test_browse_for_directory(qtbot, monkeypatch, tmp_path):
    """Test file browser interaction"""

    test_dir = tmp_path / "test_data"
    test_dir.mkdir()

    # === MOCK: Replace QFileDialog ===
    def mock_get_directory(*args, **kwargs):
        return str(test_dir)  # Return our test directory

    monkeypatch.setattr(
        QFileDialog,
        'getExistingDirectory',
        mock_get_directory
    )

    dialog = SettingsDialog(settings_manager)
    qtbot.addWidget(dialog)

    # === INTERACT: Click browse button ===
    browse_button = find_button(dialog, "Browse...")
    qtbot.mouseClick(browse_button, Qt.LeftButton)

    # === VERIFY: Path was set ===
    path_field = dialog.default_directory_field
    assert path_field.text() == str(test_dir)
```

**Key Techniques**:
- `monkeypatch.setattr()` to replace dialog functions
- Return controlled test values
- No actual file dialog appears

---

### Pattern 3: Progress Dialog Testing

**Component**: ProgressDialog with live updates

```python
def test_progress_updates_with_eta(qtbot):
    """Test progress updates and ETA calculation"""

    parent = QMainWindow()
    qtbot.addWidget(parent)

    dialog = ProgressDialog(parent)
    qtbot.addWidget(dialog)
    dialog.show()

    # === SETUP: Initialize progress ===
    total_steps = 100
    dialog.setup_unified_progress(total_steps, initial_estimate_seconds=50)

    # Verify initial state
    assert dialog.total_steps == 100
    assert dialog.current_step == 0
    assert dialog.pb_progress.value() == 0

    # === INTERACT: Simulate progress updates ===
    for step in [10, 25, 50, 75, 100]:
        dialog.update_unified_progress(step, detail_text=f"Processing {step}")
        qtbot.wait(10)  # Small delay for UI update

        # Verify progress bar updated
        expected_percentage = int((step / total_steps) * 100)
        assert dialog.pb_progress.value() == expected_percentage

    # === VERIFY: ETA was calculated ===
    eta_text = dialog.lbl_detail.text()
    assert "ETA:" in eta_text or "Complete" in eta_text
```

**Key Techniques**:
- Simulate incremental updates
- `qtbot.wait()` for UI processing
- Check both progress value and text display

---

### Pattern 4: Cancellation Testing

**Component**: Long-running operation with cancel button

```python
def test_progress_cancellation(qtbot):
    """Test cancel button stops operation"""

    parent = QMainWindow()
    qtbot.addWidget(parent)

    dialog = ProgressDialog(parent)
    qtbot.addWidget(dialog)
    dialog.show()

    dialog.setup_unified_progress(total_steps=1000)

    # === INTERACT: Start operation, then cancel ===
    dialog.update_unified_progress(10)

    # Simulate user clicking cancel
    cancel_button = dialog.btnCancel
    qtbot.mouseClick(cancel_button, Qt.LeftButton)

    # === VERIFY: Cancellation flags set ===
    assert dialog.is_cancelled == True
    assert dialog.stop_progress == True
```

**Key Techniques**:
- Check cancellation flags
- Test early cancellation (before completion)
- Verify UI state (button disabled, etc.)

---

### Pattern 5: Tab Navigation Testing

**Component**: QTabWidget with multiple tabs

```python
def test_tab_navigation(qtbot):
    """Test switching between settings tabs"""

    dialog = SettingsDialog(settings_manager)
    qtbot.addWidget(dialog)

    # Find tab widget
    tabs = dialog.findChild(QTabWidget)
    assert tabs is not None

    # === VERIFY: All tabs present ===
    tab_names = [tabs.tabText(i) for i in range(tabs.count())]
    assert "General" in tab_names
    assert "Thumbnails" in tab_names
    assert "Processing" in tab_names

    # === INTERACT: Switch tabs ===
    tabs.setCurrentIndex(1)  # Switch to "Thumbnails"
    assert tabs.currentWidget() == tabs.widget(1)

    # === VERIFY: Tab content loaded ===
    current_tab = tabs.currentWidget()
    # Check for widgets specific to this tab
    assert current_tab.findChild(QSpinBox, "max_thumbnail_size_spin") is not None
```

**Key Techniques**:
- `findChild()` to locate nested widgets
- `setCurrentIndex()` to switch tabs
- Verify tab-specific content

---

### Pattern 6: Validation Testing

**Component**: Form with input validation

```python
def test_numeric_input_validation(qtbot):
    """Test that numeric fields enforce valid ranges"""

    dialog = SettingsDialog(settings_manager)
    qtbot.addWidget(dialog)

    # Find numeric input
    thread_count_spin = dialog.thread_count_spin

    # === TEST: Valid range ===
    thread_count_spin.setValue(4)
    assert thread_count_spin.value() == 4

    # === TEST: Below minimum ===
    thread_count_spin.setValue(0)
    # Should clamp to minimum (1)
    assert thread_count_spin.value() >= 1

    # === TEST: Above maximum ===
    thread_count_spin.setValue(999)
    # Should clamp to maximum (e.g., 16)
    assert thread_count_spin.value() <= thread_count_spin.maximum()
```

**Key Techniques**:
- Test boundary conditions
- Verify auto-clamping behavior
- Check error messages (if displayed)

---

### Pattern 7: Enable/Disable Logic Testing

**Component**: Dependent controls that enable/disable based on other inputs

```python
def test_dependent_control_enabling(qtbot):
    """Test that controls enable/disable based on checkbox"""

    dialog = SettingsDialog(settings_manager)
    qtbot.addWidget(dialog)

    # Find checkbox and dependent field
    auto_save_check = dialog.auto_save_check
    save_interval_spin = dialog.save_interval_spin

    # === TEST: Initially disabled ===
    auto_save_check.setChecked(False)
    assert save_interval_spin.isEnabled() == False

    # === INTERACT: Enable auto-save ===
    qtbot.mouseClick(auto_save_check, Qt.LeftButton)
    assert auto_save_check.isChecked() == True

    # === VERIFY: Dependent control enabled ===
    assert save_interval_spin.isEnabled() == True

    # === INTERACT: Disable again ===
    qtbot.mouseClick(auto_save_check, Qt.LeftButton)
    assert save_interval_spin.isEnabled() == False
```

**Key Techniques**:
- Test both enabled and disabled states
- Verify cascading enable/disable logic
- Check that disabled widgets don't respond to input

---

### Pattern 8: Import/Export Testing

**Component**: Import/Export buttons with file dialogs

```python
def test_export_settings(qtbot, monkeypatch, tmp_path):
    """Test exporting settings to file"""

    export_file = tmp_path / "exported_settings.yaml"

    # === MOCK: File save dialog ===
    def mock_get_save_filename(*args, **kwargs):
        return (str(export_file), "YAML files (*.yaml)")

    monkeypatch.setattr(
        QFileDialog,
        'getSaveFileName',
        mock_get_save_filename
    )

    dialog = SettingsDialog(settings_manager)
    qtbot.addWidget(dialog)

    # === INTERACT: Click Export button ===
    export_button = find_button(dialog, "Export Settings...")
    qtbot.mouseClick(export_button, Qt.LeftButton)

    # === VERIFY: File was created ===
    assert export_file.exists()

    # === VERIFY: Content is valid YAML ===
    import yaml
    with open(export_file) as f:
        exported_data = yaml.safe_load(f)
    assert 'language' in exported_data
    assert 'max_thumbnail_size' in exported_data


def test_import_settings(qtbot, monkeypatch, tmp_path):
    """Test importing settings from file"""

    # Create test settings file
    import_file = tmp_path / "import_settings.yaml"
    import_file.write_text("""
language: en
max_thumbnail_size: 256
remember_window_position: true
    """)

    # === MOCK: File open dialog ===
    def mock_get_open_filename(*args, **kwargs):
        return (str(import_file), "YAML files (*.yaml)")

    monkeypatch.setattr(
        QFileDialog,
        'getOpenFileName',
        mock_get_open_filename
    )

    dialog = SettingsDialog(settings_manager)
    qtbot.addWidget(dialog)

    # === INTERACT: Click Import button ===
    import_button = find_button(dialog, "Import Settings...")
    qtbot.mouseClick(import_button, Qt.LeftButton)

    # === VERIFY: UI updated with imported values ===
    assert dialog.language_combo.currentText() == "English"
    assert dialog.max_thumbnail_size_spin.value() == 256
    assert dialog.remember_position_check.isChecked() == True
```

**Key Techniques**:
- Mock both save and open dialogs
- Create/verify actual files
- Test round-trip (export → import)

---

### Pattern 9: Reset to Defaults

**Component**: Reset button that restores default values

```python
def test_reset_to_defaults(qtbot):
    """Test reset button restores default settings"""

    dialog = SettingsDialog(settings_manager)
    qtbot.addWidget(dialog)

    # === SETUP: Change some values ===
    dialog.language_combo.setCurrentIndex(2)  # Korean
    dialog.max_thumbnail_size_spin.setValue(512)
    dialog.remember_position_check.setChecked(True)

    # === INTERACT: Click Reset button ===
    reset_button = find_button(dialog, "Reset to Defaults")

    # May show confirmation dialog - mock it
    def mock_question(*args, **kwargs):
        return QMessageBox.Yes

    monkeypatch.setattr(QMessageBox, 'question', mock_question)

    qtbot.mouseClick(reset_button, Qt.LeftButton)

    # === VERIFY: Values reset to defaults ===
    defaults = settings_manager.get_defaults()
    assert dialog.language_combo.currentIndex() == 0  # Auto
    assert dialog.max_thumbnail_size_spin.value() == defaults['max_thumbnail_size']
    assert dialog.remember_position_check.isChecked() == defaults['remember_window_position']
```

**Key Techniques**:
- Mock confirmation dialogs
- Compare against known default values
- Test all controls were reset

---

### Pattern 10: Apply vs OK Behavior

**Component**: Dialogs with Apply and OK buttons

```python
def test_apply_button_saves_without_closing(qtbot):
    """Apply should save but keep dialog open"""

    dialog = SettingsDialog(settings_manager)
    qtbot.addWidget(dialog)
    dialog.show()

    # Change a value
    dialog.language_combo.setCurrentIndex(1)

    # === INTERACT: Click Apply ===
    apply_button = find_button(dialog, "Apply")
    qtbot.mouseClick(apply_button, Qt.LeftButton)

    # === VERIFY: Settings saved ===
    settings = settings_manager.load_settings()
    assert settings['language'] == 'en'

    # === VERIFY: Dialog still open ===
    assert dialog.isVisible() == True


def test_ok_button_saves_and_closes(qtbot):
    """OK should save and close dialog"""

    dialog = SettingsDialog(settings_manager)
    qtbot.addWidget(dialog)
    dialog.show()

    # Change a value
    dialog.language_combo.setCurrentIndex(1)

    # === INTERACT: Click OK ===
    ok_button = find_button(dialog, "OK")

    with qtbot.waitSignal(dialog.accepted, timeout=1000):
        qtbot.mouseClick(ok_button, Qt.LeftButton)

    # === VERIFY: Settings saved ===
    settings = settings_manager.load_settings()
    assert settings['language'] == 'en'

    # === VERIFY: Dialog closed (or accepted) ===
    assert dialog.result() == QDialog.Accepted


def test_cancel_button_discards_changes(qtbot):
    """Cancel should discard changes and close"""

    # Save initial state
    settings_manager.save_settings({'language': 'en'})
    initial = settings_manager.load_settings()

    dialog = SettingsDialog(settings_manager)
    qtbot.addWidget(dialog)
    dialog.show()

    # Change a value
    dialog.language_combo.setCurrentIndex(2)  # Korean

    # === INTERACT: Click Cancel ===
    cancel_button = find_button(dialog, "Cancel")

    with qtbot.waitSignal(dialog.rejected, timeout=1000):
        qtbot.mouseClick(cancel_button, Qt.LeftButton)

    # === VERIFY: Settings NOT changed ===
    current = settings_manager.load_settings()
    assert current['language'] == initial['language']
```

**Key Techniques**:
- Test Apply doesn't close dialog
- Test OK saves and closes
- Test Cancel discards changes

---

## Common Challenges & Solutions

### Challenge 1: QFileDialog Doesn't Open in Tests

**Problem**: File dialogs hang or don't appear

**Solution**: Always mock them
```python
monkeypatch.setattr(QFileDialog, 'getOpenFileName',
                    lambda *args: (test_path, ""))
```

---

### Challenge 2: Progress Updates Too Fast

**Problem**: Progress completes before tests can check intermediate states

**Solution**: Add small waits
```python
for step in range(0, 100, 10):
    dialog.update_progress(step)
    qtbot.wait(10)  # 10ms pause
    assert dialog.progress_bar.value() == step
```

---

### Challenge 3: Signal Not Emitted

**Problem**: `waitSignal()` times out

**Solution**: Check signal is connected and action actually triggers it
```python
# Debug: Check if signal exists
assert hasattr(dialog, 'accepted')

# Use try/except for optional signals
try:
    with qtbot.waitSignal(dialog.valueChanged, timeout=100):
        dialog.setValue(50)
except:
    # Signal might not emit if value unchanged
    pass
```

---

### Challenge 4: Modal Dialog Blocks Tests

**Problem**: Modal dialog prevents test from continuing

**Solution**: Don't use `exec_()`, use `show()` or `open()`
```python
# BAD (blocks)
dialog.exec_()

# GOOD (non-blocking)
dialog.show()
qtbot.waitExposed(dialog)
```

---

### Challenge 5: Settings Not Persisting

**Problem**: Settings saved in test don't persist

**Solution**: Use `tmp_path` fixture for isolated test environment
```python
def test_settings(tmp_path):
    settings_file = tmp_path / "settings.yaml"
    settings_manager = SettingsManager(settings_file)
    # Now changes are isolated to this test
```

---

## Helper Utilities

### Find Buttons by Text
```python
def find_button(parent, text):
    """Find QPushButton by text"""
    buttons = parent.findChildren(QPushButton)
    for btn in buttons:
        if btn.text() == text:
            return btn
    return None
```

### Find Widgets by Object Name
```python
def find_widget_by_name(parent, widget_class, name):
    """Find widget by objectName"""
    return parent.findChild(widget_class, name)
```

### Wait for Condition
```python
def wait_for_condition(qtbot, condition, timeout=1000):
    """Wait until condition is True"""
    import time
    start = time.time()
    while not condition():
        qtbot.wait(10)
        if (time.time() - start) * 1000 > timeout:
            return False
    return True
```

---

## Summary

### Interactive Testing Checklist

- [ ] **Mock file dialogs** (getOpenFileName, getSaveFileName)
- [ ] **Mock message boxes** (question, information, warning)
- [ ] **Mock long operations** (use instant completion)
- [ ] **Test form input** (text, numbers, checkboxes, combos)
- [ ] **Test validation** (min/max, required fields)
- [ ] **Test save/load** (Apply, OK, Cancel buttons)
- [ ] **Test enable/disable** logic (dependent controls)
- [ ] **Test progress updates** (incremental, ETA, cancellation)
- [ ] **Test tab navigation** (if using QTabWidget)
- [ ] **Test import/export** (round-trip data integrity)

### Key pytest-qt Features

| Feature | Purpose |
|---------|---------|
| `qtbot.mouseClick()` | Simulate mouse clicks |
| `qtbot.keyClick()` | Simulate keyboard input |
| `qtbot.waitSignal()` | Wait for Qt signals |
| `qtbot.wait()` | Pause for UI processing |
| `qtbot.addWidget()` | Auto-cleanup widgets |
| `qtbot.waitExposed()` | Wait for widget to be visible |
| `monkeypatch.setattr()` | Mock dialogs and functions |

---

**Next Steps**: Apply these patterns to test SettingsDialog and ProgressDialog in Phase 3.

---

**Document Version**: 1.0
**Author**: Claude (AI Assistant)
**Date**: 2025-10-01
