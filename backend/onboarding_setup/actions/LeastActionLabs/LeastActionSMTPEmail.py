# Copyright (c) 2026 LeastAction Labs, Inc.
# This file is part of LeastAction and is licensed under the
# LeastAction Sustainable Use License (see LICENSE.md) or, for files
# marked EE, the LeastAction Enterprise Edition License (see LICENSE_EE.md).
# Use of this file outside those terms is not permitted.
codeblock = {
    "main.py":'''import smtplib
import ssl
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email.utils import formataddr
from src.common.logger.logger import log_info, log_error


def _as_list(value):
    """Normalize a recipient field into a clean list of addresses."""
    if not value:
        return []
    if isinstance(value, str):
        return [addr.strip() for addr in value.replace(";", ",").split(",") if addr.strip()]
    if isinstance(value, (list, tuple)):
        return [str(addr).strip() for addr in value if str(addr).strip()]
    return [str(value).strip()]


def run(least_action_action_object, smtp_host, smtp_port, smtp_user, smtp_password,
        from_addr, to, subject, body, from_name=None, cc=None, bcc=None,
        reply_to=None, use_tls=True, use_ssl=False, is_html=False, **kwargs):
    """
    Send an email over SMTP.

    Parameters:
        least_action_action_object (dict): Action object containing metadata (laui, session_id)
        smtp_host (str): SMTP server hostname (e.g. smtp.gmail.com)
        smtp_port (int): SMTP server port (587 for STARTTLS, 465 for SSL, 25 plain)
        smtp_user (str): SMTP username / login
        smtp_password (str): SMTP password or app password
        from_addr (str): Envelope/from email address
        to (str|list): Recipient(s) — comma-separated string or list
        subject (str): Email subject line
        body (str): Email body (plain text, or HTML when is_html=True)
        from_name (str): Optional display name for the From header
        cc (str|list): Optional CC recipient(s)
        bcc (str|list): Optional BCC recipient(s)
        reply_to (str): Optional Reply-To address
        use_tls (bool): Use STARTTLS (port 587). Default True
        use_ssl (bool): Use implicit SSL (port 465). Overrides use_tls when True
        is_html (bool): Treat body as HTML. Default False (plain text)

    Returns:
        bool: True if the email was accepted by the SMTP server, False otherwise
    """
    server = None
    try:
        log_info("action", "run", "start", "Starting SMTP email send")

        action_id = least_action_action_object.get("laui")
        session_id = least_action_action_object.get("session_id")
        log_info("action", "run", "initialize", "Action initialized")

        to_list = _as_list(to)
        cc_list = _as_list(cc)
        bcc_list = _as_list(bcc)

        if not to_list and not cc_list and not bcc_list:
            log_error("action", "run", "no_recipients", "No recipients provided (to/cc/bcc all empty)")
            return False
        if not smtp_host or not from_addr:
            log_error("action", "run", "missing_config", "smtp_host and from_addr are required")
            return False

        msg = MIMEMultipart("alternative")
        msg["Subject"] = subject or ""
        msg["From"] = formataddr((from_name, from_addr)) if from_name else from_addr
        msg["To"] = ", ".join(to_list)
        if cc_list:
            msg["Cc"] = ", ".join(cc_list)
        if reply_to:
            msg["Reply-To"] = reply_to

        subtype = "html" if is_html else "plain"
        msg.attach(MIMEText(body or "", subtype, "utf-8"))
        log_info("action", "run", "build_message",
                 f"Message built: subtype={subtype}, to={len(to_list)}, cc={len(cc_list)}, bcc={len(bcc_list)}")

        all_recipients = to_list + cc_list + bcc_list
        port = int(smtp_port) if smtp_port else (465 if use_ssl else 587)

        log_info("action", "run", "connect", f"Connecting to SMTP {smtp_host}:{port} (ssl={use_ssl}, tls={use_tls})")
        if use_ssl:
            context = ssl.create_default_context()
            server = smtplib.SMTP_SSL(smtp_host, port, timeout=30, context=context)
        else:
            server = smtplib.SMTP(smtp_host, port, timeout=30)
            if use_tls:
                server.starttls(context=ssl.create_default_context())
                log_info("action", "run", "starttls", "STARTTLS negotiated")

        if smtp_user:
            server.login(smtp_user, smtp_password)
            log_info("action", "run", "auth", "SMTP authentication successful")

        refused = server.sendmail(from_addr, all_recipients, msg.as_string())
        if refused:
            log_error("action", "run", "partial_failure", f"Some recipients refused: {refused}")
            return False

        log_info("action", "run", "success", f"Email sent successfully to {len(all_recipients)} recipient(s)")
        return True

    except smtplib.SMTPAuthenticationError as e:
        log_error("action", "run", "auth_error", f"SMTP authentication failed: {str(e)}")
        return False
    except smtplib.SMTPConnectError as e:
        log_error("action", "run", "connect_error", f"Could not connect to SMTP server: {str(e)}")
        return False
    except smtplib.SMTPException as e:
        log_error("action", "run", "smtp_error", f"SMTP error: {str(e)}")
        return False
    except (TimeoutError, OSError) as e:
        log_error("action", "run", "network_error", f"Network error reaching SMTP server: {str(e)}")
        return False
    except Exception as e:
        log_error("action", "run", "unexpected_error", f"Unexpected error: {str(e)}")
        return False
    finally:
        if server is not None:
            try:
                server.quit()
            except Exception:
                pass
    '''
}

bashblock = {
    "main.sh":'''# Uses only the Python standard library (smtplib, email, ssl) — no install needed.
echo "LeastActionSMTPEmail: no external dependencies required"'''
}

action_variables = {
    "smtp_host": "smtp.example.com",
    "smtp_port": 587,
    "smtp_user": "reports@example.com",
    "smtp_password": "<app-password>",
    "from_addr": "reports@example.com",
    "from_name": "LeastAction Reports",
    "to": "recipient@example.com",
    "cc": None,
    "bcc": None,
    "reply_to": None,
    "subject": "Report notification",
    "body": "This is an automated message from LeastAction Report Explorer.",
    "use_tls": True,
    "use_ssl": False,
    "is_html": False
}
connection = {}

prompt = (
    "Send an email over SMTP with a custom subject and body when a report event occurs "
    "(e.g. a user flags a report as wrong, or a scheduled report is ready). "
    "Action variables: smtp_host, smtp_port, smtp_user, smtp_password, from_addr (required); "
    "to, subject, body (required); from_name, cc, bcc, reply_to, use_tls, use_ssl, is_html (optional). "
    "Recipients accept a comma-separated string or a list. Set is_html=true to send an HTML report body. "
    "Returns True when the SMTP server accepts the message. "
    "Use as a notification step after task completion, failure, or to escalate a report issue to a team."
)

install_docs = """# LeastActionSMTPEmail — Install Guide

## Dependencies

None — uses the Python standard library (smtplib, email, ssl).

## SMTP Setup

1. Choose an SMTP provider (Gmail, Office 365, SES SMTP, Mailgun, etc.).
2. For Gmail/Office365, create an **app password** — normal account passwords are rejected.
3. Fill the action variables:
   - smtp_host / smtp_port (587 = STARTTLS, 465 = implicit SSL, 25 = plain)
   - smtp_user / smtp_password
   - from_addr (and optional from_name)
4. Leave use_tls=true for port 587, or set use_ssl=true for port 465.
"""

guide_docs = """# LeastActionSMTPEmail — Action Guide

## What it does

Sends an email through any SMTP server. Supports STARTTLS (587), implicit SSL (465),
authenticated or anonymous relay, multiple to/cc/bcc recipients, a Reply-To header,
and plain-text or HTML bodies.

---

## Action Variables

    {
      "smtp_host": "smtp.gmail.com",
      "smtp_port": 587,
      "smtp_user": "reports@example.com",
      "smtp_password": "<app-password>",
      "from_addr": "reports@example.com",
      "from_name": "LeastAction Reports",
      "to": "finance-team@example.com, lead@example.com",
      "cc": null,
      "bcc": null,
      "reply_to": null,
      "subject": "Report issue: Finance Gross-to-Net Summary",
      "body": "The MTD net revenue looks wrong — see <link>.",
      "use_tls": true,
      "use_ssl": false,
      "is_html": false
    }

Recipients (to / cc / bcc) accept a comma-separated string or a list of addresses.
Set is_html=true to send an HTML body (e.g. an inline report).

---

## Ports

| Port | Setting |
|---|---|
| 587 | use_tls=true (STARTTLS) — most common |
| 465 | use_ssl=true (implicit SSL) |
| 25  | use_tls=false, use_ssl=false (plain, unauthenticated relay) |

---

## Returns

True when the SMTP server accepts the message for all recipients. False on auth failure,
connection error, refused recipients, or any exception (full reason is logged).
"""

description = """
Sends an email over SMTP with a custom subject and body. Supports STARTTLS/SSL, auth,
multiple to/cc/bcc recipients, Reply-To, and plain-text or HTML bodies. Returns True when
the message is accepted by the SMTP server.
"""

publisher = "LeastAction"

metadata = {
    "service": "SMTP, Email",
    "category": "Notification",
    "tags": ["email", "smtp", "notify", "alert", "report", "escalation"],
    "airflow_equivalent": "EmailOperator"
}

version_details = {
    "version": "0.0.0",
    "core": ["0.*"]
}
