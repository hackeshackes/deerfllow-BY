"""V03 — Branding XSS rejection tests for ``AdminBrandingConfig``.

Verifies that ``AdminBrandingConfig`` rejects HTML / script-tag payloads
at the model level, regardless of where the value is later rendered.
The pattern ``r"^[^<>]*$"`` should reject any string containing ``<`` or ``>``.
"""

from __future__ import annotations

import pytest
from pydantic import ValidationError

from deerflow.admin.config_store import AdminBrandingConfig


@pytest.mark.parametrize(
    "field, payload",
    [
        ("name", "<script>alert('xss')</script>"),
        ("short_name", "<img src=x onerror=alert(1)>"),
        ("tagline", "Hello <b>world</b>"),
        ("description", "Evil </textarea><script>alert(1)</script>"),
        ("support_email", "ops@example.com<script>"),
        ("login_badge", "<svg/onload=alert(1)>"),
        ("login_title", "登录 {<script>alert(1)</script>}"),
        ("homepage_capabilities_title", "a<b>c"),
    ],
)
def test_branding_rejects_html_in_text_fields(field: str, payload: str) -> None:
    with pytest.raises(ValidationError):
        AdminBrandingConfig(**{field: payload})


def test_branding_rejects_oversize_text() -> None:
    long_value = "a" * 201  # _MAX_LEN is 200
    with pytest.raises(ValidationError):
        AdminBrandingConfig(name=long_value)


def test_branding_accepts_safe_chinese_and_template_braces() -> None:
    """The {name} / {support_email} template placeholders must remain valid."""
    cfg = AdminBrandingConfig(
        name="MicX Agent",
        short_name="MicX",
        tagline="中文优先 · 邀请制团队工作台",
        description="围绕文件、对话与长任务的工作台。",
        support_email="ops@example.com",
        website_path="/",
        docs_path="/zh/docs",
        login_title="登录 {name}",
        homepage_team_description="如需帮助，请联系 {support_email}。",
    )
    assert cfg.name == "MicX Agent"
    assert "{name}" in cfg.login_title
    assert "{support_email}" in cfg.homepage_team_description


def test_branding_rejects_path_traversal_in_paths() -> None:
    """Paths must start with `/` and contain only safe URL characters."""
    for bad in ("../etc/passwd", "/foo;rm -rf /", "/foo bar", "http://evil.com"):
        with pytest.raises(ValidationError):
            AdminBrandingConfig(website_path=bad)


def test_branding_accepts_paths_with_template_braces() -> None:
    """``website_path`` and ``docs_path`` allow ``{}`` for future templating."""
    cfg = AdminBrandingConfig(website_path="/{lang}", docs_path="/{lang}/docs")
    assert cfg.website_path == "/{lang}"
    assert cfg.docs_path == "/{lang}/docs"


def test_branding_pattern_allows_empty_string() -> None:
    """``^[^<>]*$`` permits empty strings; this is intentional because Pydantic
    defaults already populate every field. We assert the policy explicitly so a
    future tightening (e.g. ``+`` quantifier) does not silently regress callers
    that rely on defaults to fill in blank fields.
    """
    cfg = AdminBrandingConfig(name="", short_name="")
    assert cfg.name == ""
    assert cfg.short_name == ""


def test_branding_rejects_path_without_leading_slash() -> None:
    with pytest.raises(ValidationError):
        AdminBrandingConfig(website_path="docs")