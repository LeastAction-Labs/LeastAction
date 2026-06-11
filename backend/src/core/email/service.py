# Copyright (c) 2026 LeastAction Labs, Inc.
# This file is part of LeastAction and is licensed under the
# LeastAction Sustainable Use License (see LICENSE.md) or, for files
# marked EE, the LeastAction Enterprise Edition License (see LICENSE_EE.md).
# Use of this file outside those terms is not permitted.
import smtplib
from email.message import EmailMessage

from fastapi import Request

from src.common.secrets import get_secret
from src.common.utils import load_system_config

from .schema import Email


class EmailService:
    def __init__(self):
        smtp_cfg = load_system_config().get("smtp", {})
        self._host = smtp_cfg["host"]
        self._port = int(smtp_cfg["port"])
        self._secure = smtp_cfg.get("secure", False)
        self._user = get_secret("SMTP_USER")
        self._password = get_secret("SMTP_PASS")

    def send_email(self, email: Email):
        msg = EmailMessage()
        msg.set_content(email.message)
        msg["Subject"] = email.subject
        msg["From"] = self._user
        msg["To"] = email.to
        if self._secure:
            client = smtplib.SMTP_SSL(self._host, self._port)
        else:
            client = smtplib.SMTP(self._host, self._port)
            client.starttls()
        client.login(self._user, self._password)
        client.send_message(msg)


def get_email_service(request: Request):
    return request.app.state.email_service
