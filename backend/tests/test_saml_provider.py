"""Tests for the SAML 2.0 provider wrapper."""
from __future__ import annotations

import pytest

from app.gateway.identity.auth.saml.idp import SAMLUserInfo
from app.gateway.identity.auth.saml.provider import SAMLConfig, SAMLProvider


def _valid_config(**overrides) -> SAMLConfig:
    base = {
        "idp_entity_id": "https://idp.example.com/idp",
        "idp_sso_url": "https://idp.example.com/sso",
        "idp_x509_cert": "MIIDdummycert",
        "sp_entity_id": "https://app.micx.example.com/saml/metadata",
        "sp_acs_url": "https://app.micx.example.com/saml/acs",
    }
    base.update(overrides)
    return SAMLConfig(**base)


def test_saml_config_rejects_empty_idp_entity_id():
    with pytest.raises(ValueError, match="idp_entity_id"):
        _valid_config(idp_entity_id="")


def test_saml_config_rejects_empty_idp_sso_url():
    with pytest.raises(ValueError, match="idp_sso_url"):
        _valid_config(idp_sso_url="")


def test_saml_config_rejects_empty_idp_x509_cert():
    with pytest.raises(ValueError, match="idp_x509_cert"):
        _valid_config(idp_x509_cert="")


def test_saml_config_rejects_empty_sp_entity_id():
    with pytest.raises(ValueError, match="sp_entity_id"):
        _valid_config(sp_entity_id="")


def test_saml_config_rejects_empty_sp_acs_url():
    with pytest.raises(ValueError, match="sp_acs_url"):
        _valid_config(sp_acs_url="")


def test_saml_provider_constructs():
    p = SAMLProvider(_valid_config())
    assert p.config.idp_entity_id == "https://idp.example.com/idp"


def test_saml_provider_metadata_url_contains_entity_id():
    p = SAMLProvider(_valid_config(sp_entity_id="https://app.micx-tenant.example.com/saml/metadata"))
    md = p.get_sp_metadata()
    assert "EntityDescriptor" in md
    assert "https://app.micx-tenant.example.com/saml/metadata" in md
    assert "AssertionConsumerService" in md


def test_saml_provider_metadata_is_valid_xml():
    import xml.etree.ElementTree as ET

    p = SAMLProvider(_valid_config())
    md = p.get_sp_metadata()
    # Should be parseable as XML
    root = ET.fromstring(md)
    assert root.tag.endswith("EntityDescriptor")


def test_saml_user_info_frozen():
    info = SAMLUserInfo(
        name_id="u-1", email="u@x", name="User", groups=["g1"]
    )
    with pytest.raises(Exception):  # FrozenInstanceError or AttributeError
        info.email = "other@x"  # type: ignore[misc]
