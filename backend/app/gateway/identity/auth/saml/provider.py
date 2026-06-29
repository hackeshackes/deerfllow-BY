"""SAML provider wrapper around `python3-saml`.

We don't reach for the full `OneLogin_Saml2_Auth` for every operation —
metadata generation only needs the settings, and process_response needs
a request-data dict shaped the way python3-saml expects. Both helpers
isolate the `python3-saml` surface so the rest of the codebase can stay
agnostic to its API.
"""
from __future__ import annotations

from dataclasses import dataclass

from onelogin.saml2.settings import OneLogin_Saml2_Settings

from .idp import SAMLUserInfo


@dataclass(frozen=True)
class SAMLConfig:
    """Minimal SAML 2.0 wiring for a single IdP ↔ SP pair."""

    idp_entity_id: str
    idp_sso_url: str
    idp_x509_cert: str
    sp_entity_id: str
    sp_acs_url: str

    def __post_init__(self) -> None:
        for field in (
            "idp_entity_id",
            "idp_sso_url",
            "idp_x509_cert",
            "sp_entity_id",
            "sp_acs_url",
        ):
            if not getattr(self, field):
                raise ValueError(f"{field} is required")


class SAMLProvider:
    def __init__(self, config: SAMLConfig) -> None:
        self.config = config

    # ----------------------------------------------------------------- metadata
    def get_sp_metadata(self) -> str:
        """Generate the SP metadata XML document.

        Validates the generated metadata before returning; an invalid document
        is a programming error (the config is well-formed) and surfaces as
        `RuntimeError`.
        """
        settings = OneLogin_Saml2_Settings(self._build_settings_dict(), sp_validation_only=True)
        metadata = settings.get_sp_metadata()
        errors = settings.validate_metadata(metadata)
        if errors:
            raise RuntimeError(f"SP metadata invalid: {errors}")
        return metadata

    # ------------------------------------------------------------------ helpers
    def _build_settings_dict(self) -> dict:
        return {
            "strict": False,
            "debug": False,
            "sp": {
                "entityId": self.config.sp_entity_id,
                "assertionConsumerService": {
                    "url": self.config.sp_acs_url,
                    "binding": "urn:oasis:names:tc:SAML:2.0:bindings:HTTP-POST",
                },
            },
            "idp": {
                "entityId": self.config.idp_entity_id,
                "singleSignOnService": {
                    "url": self.config.idp_sso_url,
                    "binding": "urn:oasis:names:tc:SAML:2.0:bindings:HTTP-Redirect",
                },
                "x509cert": self.config.idp_x509_cert,
            },
        }
