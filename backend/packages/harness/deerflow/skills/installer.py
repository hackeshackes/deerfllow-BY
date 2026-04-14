"""Shared skill archive installation logic.

Pure business logic — no FastAPI/HTTP dependencies.
Both Gateway and Client delegate to these functions.
"""

import logging
import posixpath
import re
import shutil
import stat
import tempfile
import zipfile
from pathlib import Path, PurePosixPath, PureWindowsPath

from deerflow.skills.loader import get_skills_root_path
from deerflow.skills.validation import _validate_skill_frontmatter

logger = logging.getLogger(__name__)

_FRONTMATTER_NAME_RE = re.compile(r"(^---\s*\n(?:.*\n)*?name:\s*)([^\n]+)", re.MULTILINE)


def _rewrite_skill_name(skill_file: Path, new_name: str) -> None:
    content = skill_file.read_text(encoding="utf-8")
    updated, count = _FRONTMATTER_NAME_RE.subn(rf"\1{new_name}", content, count=1)
    if count != 1:
        raise ValueError("Failed to rewrite skill name in SKILL.md")
    skill_file.write_text(updated, encoding="utf-8")


def _extract_plain_skill_file(skill_file: Path, dest_root: Path) -> None:
    content = skill_file.read_text(encoding="utf-8")
    temp_skill_dir = dest_root / "plain-skill"
    temp_skill_dir.mkdir(parents=True, exist_ok=True)
    (temp_skill_dir / "SKILL.md").write_text(content, encoding="utf-8")


class SkillAlreadyExistsError(ValueError):
    """Raised when a skill with the same name is already installed."""


def is_unsafe_zip_member(info: zipfile.ZipInfo) -> bool:
    """Return True if the zip member path is absolute or attempts directory traversal."""
    name = info.filename
    if not name:
        return False
    normalized = name.replace("\\", "/")
    if normalized.startswith("/"):
        return True
    path = PurePosixPath(normalized)
    if path.is_absolute():
        return True
    if PureWindowsPath(name).is_absolute():
        return True
    if ".." in path.parts:
        return True
    return False


def is_symlink_member(info: zipfile.ZipInfo) -> bool:
    """Detect symlinks based on the external attributes stored in the ZipInfo."""
    mode = info.external_attr >> 16
    return stat.S_ISLNK(mode)


def should_ignore_archive_entry(path: Path) -> bool:
    """Return True for macOS metadata dirs and dotfiles."""
    return path.name.startswith(".") or path.name == "__MACOSX"


def resolve_skill_dir_from_archive(temp_path: Path) -> Path:
    """Locate the skill root directory from extracted archive contents.

    Filters out macOS metadata (__MACOSX) and dotfiles (.DS_Store).

    Returns:
        Path to the skill directory.

    Raises:
        ValueError: If the archive is empty after filtering.
    """
    items = [p for p in temp_path.iterdir() if not should_ignore_archive_entry(p)]
    if not items:
        raise ValueError("Skill archive is empty")
    if len(items) == 1 and items[0].is_dir():
        return items[0]
    return temp_path


def safe_extract_skill_archive(
    zip_ref: zipfile.ZipFile,
    dest_path: Path,
    max_total_size: int = 512 * 1024 * 1024,
) -> None:
    """Safely extract a skill archive with security protections.

    Protections:
    - Reject absolute paths and directory traversal (..).
    - Skip symlink entries instead of materialising them.
    - Enforce a hard limit on total uncompressed size (zip bomb defence).

    Raises:
        ValueError: If unsafe members or size limit exceeded.
    """
    dest_root = dest_path.resolve()
    total_written = 0

    for info in zip_ref.infolist():
        if is_unsafe_zip_member(info):
            raise ValueError(f"Archive contains unsafe member path: {info.filename!r}")

        if is_symlink_member(info):
            logger.warning("Skipping symlink entry in skill archive: %s", info.filename)
            continue

        normalized_name = posixpath.normpath(info.filename.replace("\\", "/"))
        member_path = dest_root.joinpath(*PurePosixPath(normalized_name).parts)
        if not member_path.resolve().is_relative_to(dest_root):
            raise ValueError(f"Zip entry escapes destination: {info.filename!r}")
        member_path.parent.mkdir(parents=True, exist_ok=True)

        if info.is_dir():
            member_path.mkdir(parents=True, exist_ok=True)
            continue

        with zip_ref.open(info) as src, member_path.open("wb") as dst:
            while chunk := src.read(65536):
                total_written += len(chunk)
                if total_written > max_total_size:
                    raise ValueError("Skill archive is too large or appears highly compressed.")
                dst.write(chunk)


def install_skill_from_archive(
    zip_path: str | Path,
    *,
    skills_root: Path | None = None,
    conflict_strategy: str = "error",
    rename_to: str | None = None,
) -> dict:
    """Install a skill from a .skill archive (ZIP).

    Args:
        zip_path: Path to the .skill file.
        skills_root: Override the skills root directory. If None, uses
            the default from config.

    Returns:
        Dict with success, skill_name, message.

    Raises:
        FileNotFoundError: If the file does not exist.
        ValueError: If the file is invalid (wrong extension, bad ZIP,
            invalid frontmatter, duplicate name).
    """
    logger.info("Installing skill from %s", zip_path)
    path = Path(zip_path)
    if not path.is_file():
        if not path.exists():
            raise FileNotFoundError(f"Skill file not found: {zip_path}")
        raise ValueError(f"Path is not a file: {zip_path}")
    if path.suffix != ".skill":
        raise ValueError("File must have .skill extension")

    if skills_root is None:
        skills_root = get_skills_root_path()
    custom_dir = skills_root / "custom"
    custom_dir.mkdir(parents=True, exist_ok=True)

    with tempfile.TemporaryDirectory() as tmp:
        tmp_path = Path(tmp)

        try:
            zf = zipfile.ZipFile(path, "r")
        except FileNotFoundError:
            raise FileNotFoundError(f"Skill file not found: {zip_path}") from None
        except (zipfile.BadZipFile, IsADirectoryError):
            try:
                _extract_plain_skill_file(path, tmp_path)
            except UnicodeDecodeError:
                raise ValueError("File is not a valid ZIP archive") from None
        else:
            with zf:
                safe_extract_skill_archive(zf, tmp_path)

        skill_dir = resolve_skill_dir_from_archive(tmp_path)

        is_valid, message, skill_name = _validate_skill_frontmatter(skill_dir)
        if not is_valid:
            raise ValueError(f"Invalid skill: {message}")
        if not skill_name or "/" in skill_name or "\\" in skill_name or ".." in skill_name:
            raise ValueError(f"Invalid skill name: {skill_name}")

        final_skill_name = rename_to or skill_name
        if not final_skill_name or "/" in final_skill_name or "\\" in final_skill_name or ".." in final_skill_name:
            raise ValueError(f"Invalid skill name: {final_skill_name}")

        target = custom_dir / final_skill_name
        if target.exists():
            if conflict_strategy == "replace":
                shutil.rmtree(target)
            elif conflict_strategy == "rename" and rename_to:
                pass
            else:
                raise SkillAlreadyExistsError(f"Skill '{final_skill_name}' already exists")

        shutil.copytree(skill_dir, target)
        if rename_to and rename_to != skill_name:
            _rewrite_skill_name(target / "SKILL.md", rename_to)
        logger.info("Skill %r installed to %s", final_skill_name, target)

    return {
        "success": True,
        "skill_name": final_skill_name,
        "message": f"Skill '{final_skill_name}' installed successfully",
    }
