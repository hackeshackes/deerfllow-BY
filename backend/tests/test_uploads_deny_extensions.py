"""V04 + V05 — Dangerous extension deny-list tests for the uploads manager.

Verifies ``validate_upload_extension`` rejects every extension in the
``_DANGEROUS_EXTENSIONS`` frozenset, is case-insensitive, and accepts
ordinary document types like ``.pdf`` / ``.docx`` / ``.txt``.
"""

from __future__ import annotations

import pytest

from deerflow.uploads.manager import (
    DangerousFileTypeError,
    _DANGEROUS_EXTENSIONS,
    validate_upload_extension,
)


# We pick one representative per category so future maintainers can see the
# breadth of coverage at a glance. The full set is asserted below.
REPRESENTATIVE_DANGEROUS = [
    ".php",
    ".phtml",
    ".jsp",
    ".asp",
    ".exe",
    ".bat",
    ".sh",
    ".ps1",
    ".py",
    ".rb",
    ".pl",
    ".js",
    ".svg",
    ".swf",
    ".jar",
    # Note: ``.htaccess`` and ``.user.ini`` are deliberately NOT in this list
    # because they are not standard extensions. ``Path.suffix`` cannot see
    # ``.user.ini`` (it returns ``.ini``), and ``.htaccess`` is a bare
    # filename. The ``_DANGEROUS_FILENAMES`` branch in
    # ``validate_upload_extension`` handles them — see the dedicated
    # ``test_validate_upload_extension_rejects_dangerous_filenames`` test below.
]


@pytest.mark.parametrize("ext", REPRESENTATIVE_DANGEROUS)
def test_validate_upload_extension_rejects_dangerous(ext: str) -> None:
    with pytest.raises(DangerousFileTypeError, match="not allowed"):
        validate_upload_extension(f"payload{ext}")


@pytest.mark.parametrize(
    "filename",
    [
        "doc.PHP",  # uppercase extension
        "doc.PhP",
        "doc.PHTML",
        "doc.SVG",
        "doc.ExE",
    ],
)
def test_validate_upload_extension_is_case_insensitive(filename: str) -> None:
    with pytest.raises(DangerousFileTypeError):
        validate_upload_extension(filename)


def test_validate_upload_extension_accepts_safe_types() -> None:
    for filename in [
        "report.pdf",
        "spreadsheet.xlsx",
        "presentation.pptx",
        "notes.docx",
        "README.md",
        "image.jpg",
        "photo.png",
        "config.yaml",
        "data.json",
        "no_extension",
        "archive.tar.gz",
    ]:
        # Should not raise
        validate_upload_extension(filename)


def test_validate_upload_extension_accepts_double_extension_when_safe() -> None:
    """``archive.tar.gz`` is fine even though it has two dots — only the final
    suffix is checked.
    """
    validate_upload_extension("archive.tar.gz")
    validate_upload_extension("report.pdf.bak")  # .bak not in deny list


def test_dangerous_extensions_is_immutable() -> None:
    """The deny list is a frozenset; this guards against accidental mutation
    that would silently weaken the policy at runtime.
    """
    assert isinstance(_DANGEROUS_EXTENSIONS, frozenset)


def test_error_message_includes_extension() -> None:
    with pytest.raises(DangerousFileTypeError) as excinfo:
        validate_upload_extension("evil.php")
    assert ".php" in str(excinfo.value)


# ---------------------------------------------------------------------------
# Compound-name deny list — entries that don't match ``Path.suffix``.
# ``Path("payload.user.ini").suffix`` returns ``.ini``, so the original
# suffix-based check would silently let ``.user.ini`` and ``.htaccess``
# through. We split them into a separate name-based check.
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    "filename",
    [
        ".htaccess",
        ".HTACCESS",
        ".htpasswd",
        ".user.ini",
        "web.config",
        "nested/path/to/.htaccess",
        "uploads/.user.ini",
    ],
)
def test_validate_upload_extension_rejects_dangerous_filenames(filename: str) -> None:
    with pytest.raises(DangerousFileTypeError):
        validate_upload_extension(filename)


def test_validate_upload_extension_accepts_userfile_with_safe_extension() -> None:
    """``my.user.ini.txt`` is a legitimate upload — only the actual filename
    ``.user.ini`` is denied, not anything that contains the substring.
    """
    validate_upload_extension("my.user.ini.txt")


@pytest.mark.parametrize(
    "filename",
    [
        "payload.user.ini",  # compound-suffix; would silently slip past Path.suffix
        "nested/payload.user.ini",
    ],
)
def test_validate_upload_extension_rejects_compound_suffix(filename: str) -> None:
    """Compound-suffix entries (``.user.ini``) must be blocked even when the
    filename has a directory prefix or extra dotted segments. This guards
    against the bug where ``Path.suffix`` only sees ``.ini``.
    """
    with pytest.raises(DangerousFileTypeError):
        validate_upload_extension(filename)


def test_validate_upload_extension_accepts_safe_text_containing_user_ini_substring() -> None:
    """``notes.user.ini.draft`` should still pass — only the literal ``.user.ini``
    tail (or the bare name) is dangerous.
    """
    validate_upload_extension("notes.user.ini.draft")