"""
Thin SMTP helper – reads credentials from env vars.

Required env vars
-----------------
SMTP_HOST, SMTP_PORT, SMTP_USER, SMTP_PASS, (optional) EMAIL_FROM
"""

from __future__ import annotations

import os, smtplib, ssl
from email.message import EmailMessage

# ------------------------------------------------------------------ env config
SMTP_HOST: str | None = os.getenv("SMTP_HOST")
SMTP_PORT: int = int(os.getenv("SMTP_PORT", 587))
SMTP_USER: str | None = os.getenv("SMTP_USER")
SMTP_PASS: str | None = os.getenv("SMTP_PASS")
EMAIL_FROM: str | None = os.getenv("EMAIL_FROM", SMTP_USER)


# ------------------------------------------------------------------ core helper


def send_email(to_addr: str, subject: str, body: str) -> None:
    """Send a plain‑text email via the configured SMTP relay.

    Silently no‑ops if credentials are missing (useful in dev).
    """
    if not all([SMTP_HOST, SMTP_USER, SMTP_PASS]):
        print("⚠️  EMAIL: SMTP creds not configured – skipping send")
        return

    msg = EmailMessage()
    msg["From"] = EMAIL_FROM or SMTP_USER or "bot@example.com"
    msg["To"] = to_addr
    msg["Subject"] = subject
    msg.set_content(body)

    ctx = ssl.create_default_context()
    with smtplib.SMTP(SMTP_HOST, SMTP_PORT) as server:
        server.starttls(context=ctx)
        server.login(SMTP_USER, SMTP_PASS)
        server.send_message(msg)
        print(f"✅ Email sent → {to_addr}: {subject}")
