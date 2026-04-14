from __future__ import annotations

import zipfile
from pathlib import Path

from deerflow.admin import skill_metadata as skill_metadata_module
from deerflow.config.paths import Paths
from deerflow.skills.installer import install_skill_from_archive
from deerflow.skills.loader import load_skills


def _write_skill_archive(path: Path, *, name: str = "demo-skill") -> None:
    content = f"""---
name: {name}
description: Demo skill
author: tester
version: 1.0.0
compatibility: micx-vnext
---

# Demo
"""
    with zipfile.ZipFile(path, "w") as archive:
        archive.writestr(f"{name}/SKILL.md", content)


def test_install_skill_from_archive_supports_rename(tmp_path):
    archive_path = tmp_path / "demo.skill"
    skills_root = tmp_path / "skills"
    _write_skill_archive(archive_path)

    result = install_skill_from_archive(archive_path, skills_root=skills_root, conflict_strategy="rename", rename_to="demo-skill-cn")

    assert result["skill_name"] == "demo-skill-cn"
    skill_file = skills_root / "custom" / "demo-skill-cn" / "SKILL.md"
    assert skill_file.exists()
    assert "name: demo-skill-cn" in skill_file.read_text(encoding="utf-8")


def test_load_skills_merges_admin_metadata(monkeypatch, tmp_path):
    skills_root = tmp_path / "skills"
    custom_skill_dir = skills_root / "custom" / "demo-skill"
    custom_skill_dir.mkdir(parents=True, exist_ok=True)
    (custom_skill_dir / "SKILL.md").write_text(
        """---
name: demo-skill
description: Demo skill
author: tester
version: 1.0.0
---

# Demo
""",
        encoding="utf-8",
    )
    paths = Paths(base_dir=tmp_path)
    monkeypatch.setattr(skill_metadata_module, "get_paths", lambda: paths)
    skill_metadata_module.upsert_skill_metadata(
        "demo-skill",
        source="https://example.com/demo.skill",
        installed_at="2026-04-13T00:00:00+00:00",
        display_name_zh="演示技能",
        description_zh="演示技能说明",
    )

    skills = load_skills(skills_path=skills_root, use_config=False, enabled_only=False)
    skill = next(item for item in skills if item.name == "demo-skill")

    assert skill.source == "https://example.com/demo.skill"
    assert skill.display_name_zh == "演示技能"
    assert skill.description_zh == "演示技能说明"
