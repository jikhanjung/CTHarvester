"""Tests for the global exception hook and Qt slot guards.

These pin the contract that matters: a raising slot must not propagate, the
wait cursor must not be left stuck, and the failure must be logged.
"""

import logging
import sys

import pytest
from PyQt5.QtCore import Qt
from PyQt5.QtGui import QCursor
from PyQt5.QtWidgets import QApplication, QWidget

from ui.errors import ErrorCode
from ui.exception_handler import (
    guard_slot,
    install_global_exception_hook,
    restore_all_override_cursors,
)


@pytest.fixture(autouse=True)
def _silence_dialogs(monkeypatch):
    """Never pop a real modal dialog during tests."""
    monkeypatch.setattr("ui.exception_handler._show_error_safely", lambda *a, **k: None)


class TestGuardSlot:
    def test_return_value_passes_through_when_no_error(self):
        @guard_slot("doing nothing")
        def slot(value):
            return value * 2

        assert slot(21) == 42

    def test_exception_is_swallowed_and_returns_none(self):
        @guard_slot("failing")
        def slot():
            raise ValueError("boom")

        assert slot() is None

    def test_exception_is_logged_with_traceback(self, caplog):
        @guard_slot("failing")
        def slot():
            raise ValueError("boom")

        with caplog.at_level(logging.ERROR, logger="ui.exception_handler"):
            slot()

        assert "Unhandled exception while failing" in caplog.text
        assert "ValueError" in caplog.text
        assert "boom" in caplog.text

    def test_metadata_is_preserved(self):
        @guard_slot("x")
        def slot():
            """Original docstring."""

        assert slot.__name__ == "slot"
        assert slot.__doc__ == "Original docstring."

    def test_reraise_propagates(self):
        @guard_slot("failing", reraise=True)
        def slot():
            raise ValueError("boom")

        with pytest.raises(ValueError, match="boom"):
            slot()

    @pytest.mark.parametrize("exc_type", [KeyboardInterrupt, SystemExit])
    def test_shutdown_signals_are_not_caught(self, exc_type):
        """These mean "stop the program", not "an operation failed"."""

        @guard_slot("failing")
        def slot():
            raise exc_type()

        with pytest.raises(exc_type):
            slot()

    def test_override_cursor_is_restored(self, qapp):
        @guard_slot("failing under a wait cursor")
        def slot():
            QApplication.setOverrideCursor(QCursor(Qt.WaitCursor))
            raise ValueError("boom")

        try:
            slot()
            assert QApplication.overrideCursor() is None
        finally:
            restore_all_override_cursors()

    def test_nested_override_cursors_are_fully_unwound(self, qapp):
        @guard_slot("failing under nested cursors")
        def slot():
            QApplication.setOverrideCursor(QCursor(Qt.WaitCursor))
            QApplication.setOverrideCursor(QCursor(Qt.BusyCursor))
            raise ValueError("boom")

        try:
            slot()
            assert QApplication.overrideCursor() is None
        finally:
            restore_all_override_cursors()

    def test_explicit_error_code_is_used(self, monkeypatch):
        seen = {}

        def capture(parent, error_code, context, exc):
            seen["code"] = error_code

        monkeypatch.setattr("ui.exception_handler._show_error_safely", capture)

        @guard_slot("exporting", ErrorCode.EXPORT_FAILED)
        def slot():
            raise ValueError("boom")

        slot()
        assert seen["code"] is ErrorCode.EXPORT_FAILED

    def test_error_code_is_inferred_when_not_given(self, monkeypatch):
        seen = {}

        def capture(parent, error_code, context, exc):
            seen["code"] = error_code

        monkeypatch.setattr("ui.exception_handler._show_error_safely", capture)

        @guard_slot("reading a file")
        def slot():
            raise PermissionError("nope")

        slot()
        assert seen["code"] is ErrorCode.PERMISSION_DENIED

    def test_works_as_a_method_on_a_widget(self, qtbot):
        class Window(QWidget):
            @guard_slot("failing in a widget slot")
            def on_click(self):
                raise RuntimeError("boom")

        window = Window()
        qtbot.addWidget(window)
        assert window.on_click() is None


class TestSignalArity:
    """A guarded parameterless slot must survive being handed surplus signal args.

    Regression: the original ``*args`` wrapper defeated PyQt5's slot-argument
    introspection, so sip forwarded every signal argument
    (``clicked(bool)``, ``currentIndexChanged(int)``, two ``rangeChanged``
    values) to a slot that declared none, raising TypeError at call time — i.e.
    every guarded button/signal handler broke on interaction.
    """

    def test_extra_positional_args_are_dropped(self):
        received = {}

        @guard_slot("handling a click")
        def slot(self):  # noqa: ARG001 - mimics a parameterless Qt slot
            received["called"] = True
            return "ok"

        # Qt would call this as slot(self, checked=False); the bool is surplus.
        assert slot(object(), False) == "ok"
        assert received["called"] is True

    def test_multiple_extra_args_are_dropped(self):
        @guard_slot("handling a range change")
        def slot(self):  # noqa: ARG001
            return "ok"

        # rangeChanged emits two values on top of self.
        assert slot(object(), 3, 7) == "ok"

    def test_declared_args_are_still_passed(self):
        seen = {}

        @guard_slot("handling a value")
        def slot(self, value):  # noqa: ARG001
            seen["value"] = value

        slot(object(), 42)
        assert seen["value"] == 42

    def test_varargs_slot_receives_everything(self):
        seen = {}

        @guard_slot("handling anything")
        def slot(self, *args):  # noqa: ARG001
            seen["args"] = args

        slot(object(), 1, 2, 3)
        assert seen["args"] == (1, 2, 3)

    def test_guarded_button_slot_on_real_widget(self, qtbot):
        """A guarded slot connected to clicked(bool) must not raise on click."""
        from PyQt5.QtWidgets import QPushButton, QWidget

        class Window(QWidget):
            def __init__(self):
                super().__init__()
                self.calls = 0
                self.button = QPushButton("go", self)
                self.button.clicked.connect(self.on_click)

            @guard_slot("clicking")
            def on_click(self):
                self.calls += 1

        window = Window()
        qtbot.addWidget(window)
        window.button.click()  # emits clicked(False)
        assert window.calls == 1


class TestGlobalExceptionHook:
    def test_installs_and_returns_previous_hook(self):
        original = sys.excepthook
        try:
            previous = install_global_exception_hook(show_dialog=False)
            assert previous is original
            assert sys.excepthook is not original
        finally:
            sys.excepthook = original

    def test_logs_unhandled_exception(self, caplog):
        original = sys.excepthook
        try:
            install_global_exception_hook(show_dialog=False)
            exc = ValueError("unhandled boom")
            with caplog.at_level(logging.CRITICAL, logger="ui.exception_handler"):
                sys.excepthook(type(exc), exc, exc.__traceback__)

            assert "Unhandled exception reached the top level" in caplog.text
            assert "unhandled boom" in caplog.text
        finally:
            sys.excepthook = original

    def test_keyboard_interrupt_delegates_to_previous_hook(self):
        original = sys.excepthook
        calls = []
        try:
            sys.excepthook = lambda *args: calls.append(args)
            install_global_exception_hook(show_dialog=False)

            exc = KeyboardInterrupt()
            sys.excepthook(KeyboardInterrupt, exc, None)

            assert len(calls) == 1, "KeyboardInterrupt must reach the previous hook"
        finally:
            sys.excepthook = original
