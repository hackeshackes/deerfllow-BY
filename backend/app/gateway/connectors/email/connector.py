"""Email connector (SMTP send + IMAP-ready).

Outbound: SMTP send via `aiosmtplib`. The connector is configured with both
SMTP and IMAP credentials; this lets a future poller worker share credentials
with the sender without re-reading the YAML.

Inbound: Email doesn't use webhooks in the traditional sense. Inbound mail
is delivered via IMAP IDLE (push) or polled by a separate worker. That worker
will live next to the runtime and feed messages into the inbound pipeline.
For now `receive_webhook` is a stub that always returns `[]`.
"""
from __future__ import annotations

from email.message import EmailMessage

import aiosmtplib

from ..base import BaseConnector, ConnectorMessage, ConnectorResponse


class EmailConnector(BaseConnector):
    name = "email"
    display_name = "Email (SMTP/IMAP)"

    def __init__(
        self,
        smtp_host: str,
        smtp_port: int,
        smtp_user: str,
        smtp_password: str,
        imap_host: str,
        imap_port: int,
        from_address: str,
        use_tls: bool = True,
        timeout: float = 15.0,
    ) -> None:
        if not from_address:
            raise ValueError("from_address is required")
        self._smtp_host = smtp_host
        self._smtp_port = smtp_port
        self._smtp_user = smtp_user
        self._smtp_password = smtp_password
        self._imap_host = imap_host
        self._imap_port = imap_port
        self._from = from_address
        self._use_tls = use_tls
        self._timeout = timeout

    async def send(self, message: ConnectorMessage) -> ConnectorResponse:
        try:
            to = message.target.get("to", "")
            if not to:
                return ConnectorResponse(
                    success=False, error="email send requires target.to"
                )
            subject = message.target.get("subject") or "(no subject)"

            email = EmailMessage()
            email["From"] = self._from
            email["To"] = to
            email["Subject"] = subject
            email.set_content(message.text)

            await aiosmtplib.send(
                email,
                hostname=self._smtp_host,
                port=self._smtp_port,
                username=self._smtp_user,
                password=self._smtp_password,
                use_tls=self._use_tls,
                timeout=self._timeout,
            )
            return ConnectorResponse(
                success=True,
                external_id=email.get("Message-ID") or "sent",
            )
        except Exception as e:  # noqa: BLE001 — connector boundary
            return ConnectorResponse(success=False, error=str(e))

    async def receive_webhook(self, payload: dict) -> list[ConnectorMessage]:
        """Email has no webhook. Inbound is delivered by an IMAP poller."""
        return []
