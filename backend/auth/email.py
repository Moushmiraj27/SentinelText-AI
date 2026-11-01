"""Password-reset email delivery using environment-configured SMTP."""
import os
import smtplib
from email.message import EmailMessage


def smtp_is_configured() -> bool:
    return all(os.getenv(name) for name in ("SMTP_HOST", "SMTP_FROM"))


def send_reset_email(email: str, token: str) -> None:
    base = os.getenv("FRONTEND_URL", "http://localhost:5173").rstrip("/")
    link = f"{base}/#reset_token={token}"
    message = EmailMessage()
    message["Subject"] = "Reset your SentinelText password"
    message["From"] = os.getenv("SMTP_FROM")
    message["To"] = email
    message.set_content(f"Use this link to reset your SentinelText password. It expires in 30 minutes.\n\n{link}\n\nIf you did not request this, ignore this email.")

    host = os.getenv("SMTP_HOST")
    port = int(os.getenv("SMTP_PORT", "587"))
    username = os.getenv("SMTP_USERNAME")
    password = os.getenv("SMTP_PASSWORD")
    if port == 465:
        with smtplib.SMTP_SSL(host, port, timeout=10) as server:
            if username:
                server.login(username, password or "")
            server.send_message(message)
        return

    with smtplib.SMTP(host, port, timeout=10) as server:
        if os.getenv("SMTP_STARTTLS", "true").lower() == "true":
            server.starttls()
        if username:
            server.login(username, password or "")
        server.send_message(message)
