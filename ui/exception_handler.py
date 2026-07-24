"""Global exception hook and Qt slot guards.

A GUI event loop is unforgiving about unhandled exceptions. In PyQt5 >= 5.5 an
exception that escapes a slot causes ``sys.excepthook`` to run and then the
interpreter calls ``abort()`` — the window disappears with no message and no
chance to save state.

Two layers, in order of importance:

1. :func:`guard_slot` — decorate every user-triggered handler that does I/O,
   parsing or numeric work. The exception never escapes the slot, so the event
   loop survives, the wait cursor is restored, and the user gets a dialog with
   actionable suggestions from :mod:`ui.errors`.
2. :func:`install_global_exception_hook` — the backstop. It cannot stop PyQt5
   from aborting after an unguarded slot raises, but it guarantees the failure
   is *logged with a traceback* and, where possible, shown to the user first.
   Without it the crash is silent.

Usage::

    from ui.exception_handler import guard_slot

    class MainWindow(QMainWindow):
        @guard_slot("opening directory")
        def on_open_directory(self):
            ...
"""

import functools
import inspect
import logging
import sys
import traceback
from typing import Callable, Optional

from PyQt5.QtWidgets import QApplication

from ui.errors import ErrorCode, map_exception_to_error_code, show_error

logger = logging.getLogger(__name__)

__all__ = ["guard_slot", "install_global_exception_hook", "restore_all_override_cursors"]


def restore_all_override_cursors() -> None:
    """Pop every pushed override cursor.

    A handler that raises between ``setOverrideCursor`` and
    ``restoreOverrideCursor`` leaves the app stuck showing a busy cursor with no
    busy work. Cursors nest, so unwind the whole stack.
    """
    app = QApplication.instance()
    if app is None:
        return
    # Bounded: a runaway loop here would hang the UI worse than the stuck cursor.
    for _ in range(64):
        if QApplication.overrideCursor() is None:
            return
        QApplication.restoreOverrideCursor()


def guard_slot(
    context: str,
    error_code: Optional[ErrorCode] = None,
    reraise: bool = False,
) -> Callable:
    """Wrap a Qt slot so an exception is reported instead of killing the app.

    Args:
        context: Short description of what the slot was doing, in the gerund
            (e.g. ``"opening directory"``). Used in the log line and to help
            :func:`~ui.errors.map_exception_to_error_code` pick a message.
        error_code: Force a specific :class:`~ui.errors.ErrorCode` instead of
            inferring one from the exception type.
        reraise: Re-raise after reporting. Only for tests, or for slots where a
            caller genuinely needs to see the failure.

    Returns:
        A decorator preserving the wrapped function's name and docstring.

    Notes:
        ``KeyboardInterrupt`` and ``SystemExit`` are deliberately not caught —
        they are shutdown signals, not application errors.

        **Signal arity.** PyQt5 inspects a slot's signature and passes only as
        many signal arguments as the slot declares. A naive ``*args`` wrapper
        defeats that introspection — sip sees a variadic callable and forwards
        *every* signal argument (a ``clicked(bool)``, a ``currentIndexChanged``
        int, two ``rangeChanged`` values), raising ``TypeError`` on a slot that
        declared none. This wrapper therefore trims extra positional arguments
        to what the wrapped function actually accepts, reproducing PyQt's own
        behaviour, so decorating a parameterless slot stays safe.

    Example:
        >>> @guard_slot("exporting mesh", ErrorCode.EXPORT_FAILED)
        ... def on_export(self):
        ...     write_obj(self.mesh, self.path)
    """

    def decorator(func: Callable) -> Callable:
        # Determine how many positional args func accepts, so we can drop the
        # surplus that a Qt signal would otherwise force onto a slot that
        # declared fewer parameters (see "Signal arity" above).
        try:
            params = list(inspect.signature(func).parameters.values())
            accepts_varargs = any(p.kind == p.VAR_POSITIONAL for p in params)
            max_positional = sum(
                1 for p in params if p.kind in (p.POSITIONAL_ONLY, p.POSITIONAL_OR_KEYWORD)
            )
        except (TypeError, ValueError):
            # Builtins / C callables without an introspectable signature.
            accepts_varargs, max_positional = True, None

        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            if not accepts_varargs and max_positional is not None:
                args = args[:max_positional]
            try:
                return func(*args, **kwargs)
            except (KeyboardInterrupt, SystemExit):
                raise
            except Exception as exc:  # noqa: BLE001 - deliberate catch-all boundary
                restore_all_override_cursors()

                logger.error("Unhandled exception while %s", context, exc_info=exc)

                code = error_code or map_exception_to_error_code(exc, context)
                # `self` for a bound slot; used as the dialog parent when it is
                # a widget. Anything else falls back to a parentless dialog.
                parent = args[0] if args else None
                _show_error_safely(parent, code, context, exc)

                if reraise:
                    raise
                return None

        return wrapper

    return decorator


def _show_error_safely(parent, error_code: ErrorCode, context: str, exc: Exception) -> None:
    """Show an error dialog, never raising from the reporting path itself.

    If the UI is already too broken to show a dialog (no QApplication, teardown
    in progress), the log line written by the caller is the record of record.
    """
    try:
        from PyQt5.QtWidgets import QWidget

        if QApplication.instance() is None:
            return
        dialog_parent = parent if isinstance(parent, QWidget) else None
        show_error(dialog_parent, error_code, context, exception=exc, include_traceback=True)
    except Exception:  # noqa: BLE001 - reporting must not raise
        logger.exception("Failed to display error dialog for: %s", context)


def install_global_exception_hook(show_dialog: bool = True) -> Callable:
    """Install ``sys.excepthook`` as a backstop for unguarded code paths.

    Call once, early in :func:`main`, before the event loop starts.

    Args:
        show_dialog: Also attempt a user-visible dialog. Disable for headless
            runs and tests, where logging alone is wanted.

    Returns:
        The previous ``sys.excepthook``, so tests can restore it.

    Notes:
        This does not prevent PyQt5 from aborting the process after an
        exception escapes a slot — only :func:`guard_slot` does that. What it
        guarantees is that the traceback reaches the log instead of vanishing.
    """
    previous_hook = sys.excepthook

    def handle_exception(exc_type, exc_value, exc_traceback):
        if issubclass(exc_type, KeyboardInterrupt):
            previous_hook(exc_type, exc_value, exc_traceback)
            return

        restore_all_override_cursors()

        formatted = "".join(traceback.format_exception(exc_type, exc_value, exc_traceback))
        logger.critical("Unhandled exception reached the top level:\n%s", formatted)

        if show_dialog and isinstance(exc_value, Exception):
            code = map_exception_to_error_code(exc_value)
            _show_error_safely(None, code, "an unexpected operation", exc_value)

    sys.excepthook = handle_exception
    logger.debug("Global exception hook installed")
    return previous_hook
