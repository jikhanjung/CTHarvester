"""Import and startup smoke tests.

The cheapest check that catches the largest class of user-only crashes: a module
that fails to import, or an app that dies on startup, on a platform or Python
version the developer does not use.

These tests are deliberately dependency-heavy — they exercise the real import
graph (PyQt5, PyOpenGL, Pillow, numpy, scipy, pymcubes) rather than mocking it,
so a broken native extension or a version-only stdlib symbol turns into an
immediate red build.

Run on every OS x Python combination in the CI matrix:
    pytest tests/test_smoke.py -m smoke
"""

import importlib
import os
import pkgutil
import subprocess
import sys
from pathlib import Path

import pytest

PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

# Packages whose every submodule must import cleanly.
PACKAGES = ("config", "core", "security", "ui", "utils")

# Top-level modules that are part of the runtime import graph.
# Build scripts (build.py, build_cross_platform.py) are excluded: they are
# tooling, not shipped code.
TOP_LEVEL_MODULES = ("version", "CTLogger", "CTHarvester")


def _discover_modules():
    """Return every importable module name under PACKAGES, plus TOP_LEVEL_MODULES."""
    names = []
    for pkg_name in PACKAGES:
        pkg = importlib.import_module(pkg_name)
        names.append(pkg_name)
        for info in pkgutil.walk_packages(pkg.__path__, prefix=f"{pkg_name}."):
            names.append(info.name)
    return sorted(set(names)) + list(TOP_LEVEL_MODULES)


@pytest.mark.smoke
def test_python_version_is_supported():
    """The declared minimum in pyproject.toml is 3.12; fail loudly below it.

    Catches version-only stdlib symbols (e.g. ``itertools.batched`` is 3.12+)
    being used on an interpreter that predates them.
    """
    assert sys.version_info >= (3, 12), f"Python 3.12+ required, running {sys.version}"


@pytest.mark.smoke
@pytest.mark.parametrize("module_name", _discover_modules())
def test_module_imports(module_name):
    """Every project module imports without error.

    Catches missing native extensions (PyQt5.sip, PIL._imaging), platform-only
    imports, and import-time side effects that fail on a clean machine.
    """
    importlib.import_module(module_name)


@pytest.mark.smoke
def test_third_party_native_extensions_load():
    """Native extensions actually load, not just resolve as names.

    A wheel can install yet ship a broken/absent binary; importing the pure
    Python shim would still succeed. Touch the compiled submodules directly.
    """
    import numpy  # noqa: F401

    # Pillow's C extension is loaded lazily by PIL.Image.
    import PIL
    import PIL.Image  # noqa: F401
    import PyQt5.sip  # noqa: F401
    from PyQt5.QtWidgets import QApplication  # noqa: F401

    PIL.Image.new("L", (1, 1))


@pytest.mark.smoke
@pytest.mark.ui
def test_main_window_starts_and_closes(qtbot):
    """The real main window constructs, shows, and closes offscreen.

    This is the startup path users hit. It exercises Qt widget construction,
    the OpenGL viewer, icon/resource loading, and settings initialization —
    the "works from source, broken when packaged/on Windows" surface.
    """
    os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

    from ui.main_window import CTHarvesterMainWindow

    window = CTHarvesterMainWindow()
    qtbot.addWidget(window)
    window.show()
    qtbot.waitExposed(window)

    assert window.isVisible()

    window.close()
    assert not window.isVisible()


@pytest.mark.smoke
def test_bundled_resources_exist():
    """Icons and translations referenced at startup are present on disk.

    These are the usual "works from source, missing when frozen" gaps; checking
    them in-tree at least keeps the manifest honest.
    """
    from utils.common import resource_path

    required = [
        "resources/icons/icon.png",
        "resources/translations/CTHarvester_en.qm",
        "resources/translations/CTHarvester_ko.qm",
    ]
    missing = [rel for rel in required if not os.path.exists(resource_path(rel))]
    assert not missing, f"Missing bundled resources: {missing}"


@pytest.mark.smoke
def test_self_test_flag_boots_and_exits_cleanly():
    """`CTHarvester.py --self-test` must start the app and exit 0.

    The packaged-build smoke test in .github/workflows/reusable_build.yml runs
    the frozen executable with this flag on all three platforms and gates the
    release on its exit code. Removing or renaming the flag would turn that gate
    into a permanent failure, so it is pinned here at the source level too.

    Run as a subprocess rather than by calling main(): the flag is parsed from
    sys.argv and the app calls sys.exit(), neither of which survives an in-process
    call.
    """
    env = dict(os.environ, QT_QPA_PLATFORM="offscreen")
    result = subprocess.run(
        [sys.executable, str(PROJECT_ROOT / "CTHarvester.py"), "--self-test"],
        cwd=PROJECT_ROOT,
        env=env,
        capture_output=True,
        text=True,
        timeout=120,
    )

    assert result.returncode == 0, (
        f"--self-test exited {result.returncode}\nstdout:\n{result.stdout}\n"
        f"stderr:\n{result.stderr}"
    )
