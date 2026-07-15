"""Shared upload management logic.

Pure business logic — no FastAPI/HTTP dependencies.
Both Gateway and Client delegate to these functions.
"""

import os
import re
from pathlib import Path
from urllib.parse import quote

from deerflow.config.paths import VIRTUAL_PATH_PREFIX, get_paths


class PathTraversalError(ValueError):
    """Raised when a path escapes its allowed base directory."""


class DangerousFileTypeError(ValueError):
    """Raised when an uploaded file uses a disallowed (executable/script) extension."""


# Extensions that could lead to code execution if served, executed by a misconfigured
# downstream (nginx + PHP-FPM, JSP container, .htaccess handlers), or rendered by
# an agent tool that auto-detects MIME. We reject these regardless of content-type.
_DANGEROUS_EXTENSIONS: frozenset[str] = frozenset({
    # Server-side scripts
    ".php", ".php3", ".php4", ".php5", ".php7", ".phps", ".phtml", ".phar",
    ".jsp", ".jspx", ".asp", ".aspx", ".cer", ".asa",
    # Native executables / shell
    ".exe", ".msi", ".bat", ".cmd", ".com", ".scr", ".cpl",
    ".sh", ".bash", ".zsh", ".ksh", ".csh", ".fish",
    ".ps1", ".ps2", ".psc1", ".psm1", ".vbs", ".vbe", ".jse", ".wsf", ".wsh",
    # Python / Ruby / Perl / Node
    ".py", ".pyc", ".pyo", ".pyz", ".pyw",
    ".rb", ".rbw", ".pl", ".pm", ".cgi",
    ".js", ".mjs", ".cjs",
    # Other dangerous formats
    ".svg",  # served as image/svg+xml can carry <script> when rendered inline
    ".swf",
    ".jar", ".war",
})

# Compound-suffix entries — matched against the tail of the filename so that
# ``payload.user.ini`` is blocked even though ``Path.suffix`` only sees
# ``.ini``. Single-dot entries belong in ``_DANGEROUS_EXTENSIONS`` instead.
_DANGEROUS_SUFFIX_TAILS: frozenset[str] = frozenset({
    ".user.ini",
})

# Filenames that are dangerous regardless of any suffix. These are matched
# case-insensitively against the basename (without parent directories).
# ``Path.suffix`` only returns the final ``.ext``, so compound entries like
# ``.user.ini`` and bare names like ``.htaccess`` would never trigger a
# suffix-based check. Splitting them out avoids that footgun.
_DANGEROUS_FILENAMES: frozenset[str] = frozenset({
    ".htaccess",
    ".htpasswd",
    "web.config",
})


def validate_upload_extension(filename: str) -> None:
    """Reject filenames with extensions known to enable RCE/XSS when served.

    Defense in depth on top of nginx content-type forcing — a misconfigured
    reverse proxy or a downstream tool that re-serves files by extension could
    still trigger code execution. The check is case-insensitive.

    Raises:
        DangerousFileTypeError: If the extension is on the deny list.
    """
    path = Path(filename)
    basename = path.name.lower()

    # 1. Bare-filename entries — config files that have no suffix at all
    #    (``.htaccess``) or that act like config files when named bare
    #    (``web.config``). Match by exact lowercase basename.
    if basename in _DANGEROUS_FILENAMES:
        raise DangerousFileTypeError(
            f"Filename {basename!r} is not allowed for security reasons. "
            "Server-control configuration files are blocked."
        )

    # 2. Compound-suffix entries — match any filename whose tail is on the
    #    deny list, regardless of how many dotted segments precede it. This
    #    covers ``payload.user.ini`` because ``Path.suffix`` would only see
    #    ``.ini``.
    lowered = filename.lower()
    for dangerous in _DANGEROUS_SUFFIX_TAILS:
        if lowered.endswith(dangerous):
            raise DangerousFileTypeError(
                f"File extension {dangerous!r} is not allowed for security reasons. "
                "Server-control configuration files are blocked."
            )

    # 3. Standard suffix check — the canonical case for things like ``.php``,
    #    ``.svg``, ``.exe``. ``Path.suffix`` returns the final dotted segment.
    ext = path.suffix.lower()
    if ext in _DANGEROUS_EXTENSIONS:
        raise DangerousFileTypeError(
            f"File extension {ext!r} is not allowed for security reasons. "
            "Server-side scripts, executables, and active-content formats (HTML, SVG) are blocked."
        )


# thread_id must be alphanumeric, hyphens, underscores, or dots only.
_SAFE_THREAD_ID = re.compile(r"^[a-zA-Z0-9._-]+$")


def validate_thread_id(thread_id: str) -> None:
    """Reject thread IDs containing characters unsafe for filesystem paths.

    Raises:
        ValueError: If thread_id is empty or contains unsafe characters.
    """
    if not thread_id or not _SAFE_THREAD_ID.match(thread_id):
        raise ValueError(f"Invalid thread_id: {thread_id!r}")


def get_uploads_dir(thread_id: str) -> Path:
    """Return the uploads directory path for a thread (no side effects)."""
    validate_thread_id(thread_id)
    return get_paths().sandbox_uploads_dir(thread_id)


def ensure_uploads_dir(thread_id: str) -> Path:
    """Return the uploads directory for a thread, creating it if needed."""
    base = get_uploads_dir(thread_id)
    base.mkdir(parents=True, exist_ok=True)
    return base


def normalize_filename(filename: str) -> str:
    """Sanitize a filename by extracting its basename.

    Strips any directory components and rejects traversal patterns.

    Args:
        filename: Raw filename from user input (may contain path components).

    Returns:
        Safe filename (basename only).

    Raises:
        ValueError: If filename is empty or resolves to a traversal pattern.
    """
    if not filename:
        raise ValueError("Filename is empty")
    safe = Path(filename).name
    if not safe or safe in {".", ".."}:
        raise ValueError(f"Filename is unsafe: {filename!r}")
    # Reject backslashes — on Linux Path.name keeps them as literal chars,
    # but they indicate a Windows-style path that should be stripped or rejected.
    if "\\" in safe:
        raise ValueError(f"Filename contains backslash: {filename!r}")
    if len(safe.encode("utf-8")) > 255:
        raise ValueError(f"Filename too long: {len(safe)} chars")
    return safe


def claim_unique_filename(name: str, seen: set[str]) -> str:
    """Generate a unique filename by appending ``_N`` suffix on collision.

    Automatically adds the returned name to *seen* so callers don't need to.

    Args:
        name: Candidate filename.
        seen: Set of filenames already claimed (mutated in place).

    Returns:
        A filename not present in *seen* (already added to *seen*).
    """
    if name not in seen:
        seen.add(name)
        return name
    stem, suffix = Path(name).stem, Path(name).suffix
    counter = 1
    candidate = f"{stem}_{counter}{suffix}"
    while candidate in seen:
        counter += 1
        candidate = f"{stem}_{counter}{suffix}"
    seen.add(candidate)
    return candidate


def validate_path_traversal(path: Path, base: Path) -> None:
    """Verify that *path* is inside *base*.

    Raises:
        PathTraversalError: If a path traversal is detected.
    """
    try:
        path.resolve().relative_to(base.resolve())
    except ValueError:
        raise PathTraversalError("Path traversal detected") from None


def list_files_in_dir(directory: Path) -> dict:
    """List files (not directories) in *directory*.

    Args:
        directory: Directory to scan.

    Returns:
        Dict with "files" list (sorted by name) and "count".
        Each file entry has ``size`` as *int* (bytes).  Call
        :func:`enrich_file_listing` to stringify sizes and add
        virtual / artifact URLs.
    """
    if not directory.is_dir():
        return {"files": [], "count": 0}

    files = []
    with os.scandir(directory) as entries:
        for entry in sorted(entries, key=lambda e: e.name):
            if not entry.is_file(follow_symlinks=False):
                continue
            st = entry.stat(follow_symlinks=False)
            files.append(
                {
                    "filename": entry.name,
                    "size": st.st_size,
                    "path": entry.path,
                    "extension": Path(entry.name).suffix,
                    "modified": st.st_mtime,
                }
            )
    return {"files": files, "count": len(files)}


def delete_file_safe(base_dir: Path, filename: str, *, convertible_extensions: set[str] | None = None) -> dict:
    """Delete a file inside *base_dir* after path-traversal validation.

    If *convertible_extensions* is provided and the file's extension matches,
    the companion ``.md`` file is also removed (if it exists).

    Args:
        base_dir: Directory containing the file.
        filename: Name of file to delete.
        convertible_extensions: Lowercase extensions (e.g. ``{".pdf", ".docx"}``)
            whose companion markdown should be cleaned up.

    Returns:
        Dict with success and message.

    Raises:
        FileNotFoundError: If the file does not exist.
        PathTraversalError: If path traversal is detected.
    """
    file_path = (base_dir / filename).resolve()
    validate_path_traversal(file_path, base_dir)

    if not file_path.is_file():
        raise FileNotFoundError(f"File not found: {filename}")

    file_path.unlink()

    # Clean up companion markdown generated during upload conversion.
    if convertible_extensions and file_path.suffix.lower() in convertible_extensions:
        file_path.with_suffix(".md").unlink(missing_ok=True)

    return {"success": True, "message": f"Deleted {filename}"}


def upload_artifact_url(thread_id: str, filename: str) -> str:
    """Build the artifact URL for a file in a thread's uploads directory.

    *filename* is percent-encoded so that spaces, ``#``, ``?`` etc. are safe.
    """
    return f"/api/threads/{thread_id}/artifacts{VIRTUAL_PATH_PREFIX}/uploads/{quote(filename, safe='')}"


def upload_virtual_path(filename: str) -> str:
    """Build the virtual path for a file in the uploads directory."""
    return f"{VIRTUAL_PATH_PREFIX}/uploads/{filename}"


def enrich_file_listing(result: dict, thread_id: str) -> dict:
    """Add virtual paths, artifact URLs, and stringify sizes on a listing result.

    Mutates *result* in place and returns it for convenience.
    """
    for f in result["files"]:
        filename = f["filename"]
        f["size"] = str(f["size"])
        f["virtual_path"] = upload_virtual_path(filename)
        f["artifact_url"] = upload_artifact_url(thread_id, filename)
    return result
