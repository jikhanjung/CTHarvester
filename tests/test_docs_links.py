"""Relative links inside docs/ must point at files that exist.

The Sphinx build validates the manual: a broken toctree entry or cross-reference
fails `make docs`, which gates CI. Nothing validates the Markdown notes at the
docs/ root, and that shows -- when this test was written, 11 of the 15 relative
links in those notes were broken, several pointing at ``docs/user_guide/``, a
directory that has never existed in this repository.

Scope is deliberately narrow: relative links in Markdown under docs/. External
URLs are not fetched (a test suite that fails when a website is down is a test
suite people learn to ignore), and the manual's own .rst cross-references are
already the Sphinx build's job.
"""

import re
from pathlib import Path

import pytest

PROJECT_ROOT = Path(__file__).resolve().parent.parent
DOCS = PROJECT_ROOT / "docs"

# [text](target) -- the target may carry a #fragment, which is stripped before
# the file is looked up. Fragments are not verified.
MARKDOWN_LINK = re.compile(r"\[[^\]]*\]\(([^)]+)\)")

EXTERNAL_PREFIXES = ("http://", "https://", "mailto:", "#")


def _relative_links() -> list[tuple[Path, int, str]]:
    """Every relative Markdown link under docs/, as (file, line number, target)."""
    found = []
    for path in sorted(DOCS.rglob("*.md")):
        for lineno, line in enumerate(path.read_text(encoding="utf-8").splitlines(), 1):
            for target in MARKDOWN_LINK.findall(line):
                if not target.startswith(EXTERNAL_PREFIXES):
                    found.append((path, lineno, target))
    return found


@pytest.mark.parametrize(
    ("path", "lineno", "target"),
    _relative_links(),
    ids=lambda value: value.name if isinstance(value, Path) else str(value),
)
def test_relative_link_resolves(path: Path, lineno: int, target: str):
    resolved = (path.parent / target.split("#")[0]).resolve()
    assert resolved.exists(), (
        f"{path.relative_to(PROJECT_ROOT)}:{lineno} links to {target!r}, "
        f"which resolves to {resolved} and does not exist"
    )


def test_there_are_links_to_check():
    """Guard against the regex silently matching nothing after a refactor."""
    assert len(_relative_links()) >= 10
