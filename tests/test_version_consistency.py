"""Version single-source-of-truth tests.

``version.py`` is the only place a version number is written by hand. Every
other file must derive from it. These tests fail the build when a release bump
touches one file and forgets another — the failure mode that previously left
pyproject.toml at 0.2.3-beta.1 while version.py said 0.2.3-beta.2.
"""

import re
import sys
import tomllib
from pathlib import Path

import pytest

PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from version import __version__, __version_info__  # noqa: E402


def _load_toml(name):
    with open(PROJECT_ROOT / name, "rb") as fh:
        return tomllib.load(fh)


def test_version_is_valid_semver():
    """version.py must parse as semver; the build and Cargo both assume it."""
    semver = pytest.importorskip("semver")
    parsed = semver.VersionInfo.parse(__version__)
    assert (parsed.major, parsed.minor, parsed.patch) == __version_info__


def test_pyproject_derives_version_dynamically():
    """pyproject.toml must not hardcode a version that can drift from version.py."""
    data = _load_toml("pyproject.toml")
    project = data["project"]

    assert "version" not in project, (
        "pyproject.toml [project] hardcodes a version. Use "
        'dynamic = ["version"] + [tool.setuptools.dynamic] instead.'
    )
    assert "version" in project.get("dynamic", []), "pyproject.toml must declare version as dynamic"

    attr = data["tool"]["setuptools"]["dynamic"]["version"]["attr"]
    assert attr == "version.__version__", f"Unexpected dynamic version source: {attr}"


def test_cargo_version_matches():
    """The Rust accelerator ships inside the app; keep its version in lockstep."""
    cargo_version = _load_toml("Cargo.toml")["package"]["version"]
    assert cargo_version == __version__, (
        f"Cargo.toml version {cargo_version!r} != version.py {__version__!r}. "
        "Update Cargo.toml when bumping version.py."
    )


def test_constants_reexports_the_real_version():
    """config.constants must expose version.py's value, never its fallback."""
    from config import constants

    assert constants.__version__ == __version__
    assert __version__ == constants.PROGRAM_VERSION
    assert "unknown" not in constants.__version__


def test_docs_conf_does_not_hardcode_version():
    """Sphinx `release` must be imported from version.py, not typed in."""
    source = (PROJECT_ROOT / "docs" / "manual" / "conf.py").read_text(encoding="utf-8")
    hardcoded = re.search(r"^\s*release\s*=\s*['\"]", source, re.MULTILINE)
    assert not hardcoded, "docs/manual/conf.py hardcodes `release`; import it from version.py"
    assert "from version import" in source
