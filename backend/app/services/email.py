import smtplib
from dataclasses import dataclass, field
from email.message import EmailMessage as MimeEmailMessage
from typing import Protocol

from app.core.config import Settings


@dataclass
class EmailMessage:
    to: str
    subject: str
    text_body: str
    html_body: str


class EmailSender(Protocol):
    def send(self, message: EmailMessage) -> None: ...


class SmtpEmailSender:
    """Sends mail via stdlib smtplib. Points at Mailpit locally (see docker-compose.yml)."""

    def __init__(self, settings: Settings) -> None:
        self._settings = settings

    def send(self, message: EmailMessage) -> None:
        mime_message = MimeEmailMessage()
        mime_message["Subject"] = message.subject
        mime_message["From"] = self._settings.email_from
        mime_message["To"] = message.to
        mime_message.set_content(message.text_body)
        mime_message.add_alternative(message.html_body, subtype="html")

        with smtplib.SMTP(self._settings.smtp_host, self._settings.smtp_port) as smtp:
            if self._settings.smtp_use_tls:
                smtp.starttls()
            if self._settings.smtp_username:
                smtp.login(self._settings.smtp_username, self._settings.smtp_password)
            smtp.send_message(mime_message)


@dataclass
class FakeEmailSender:
    """In-memory test double — the only EmailSender CI ever uses."""

    sent: list[EmailMessage] = field(default_factory=list)

    def send(self, message: EmailMessage) -> None:
        self.sent.append(message)


def render_verification_email(code: str, ttl_minutes: int) -> tuple[str, str, str]:
    """Returns (subject, text_body, html_body) for a verification-code email."""
    subject = "Confirm your LeseBuddy email address"
    text_body = (
        f"Welcome to LeseBuddy!\n\n"
        f"Your verification code is: {code}\n\n"
        f"This code expires in {ttl_minutes} minutes.\n\n"
        f"If you didn't create a LeseBuddy account, you can safely ignore this email."
    )
    html_body = f"""\
<div style="font-family: sans-serif; max-width: 480px; margin: 0 auto;">
  <h1 style="color: #244c3b;">Lese<span style="color: #4f8f69;">Buddy</span></h1>
  <p>Welcome to LeseBuddy! Use the code below to confirm your email address:</p>
  <p style="font-size: 32px; font-weight: 700; letter-spacing: 0.3em; color: #244c3b;
            background: #e5f3e8; padding: 16px 20px; border-radius: 10px; text-align: center;">
    {code}
  </p>
  <p style="color: #777d74; font-size: 13px;">This code expires in {ttl_minutes} minutes.</p>
  <p style="color: #777d74; font-size: 13px;">
    If you didn't create a LeseBuddy account, you can safely ignore this email.
  </p>
</div>
"""
    return subject, text_body, html_body
