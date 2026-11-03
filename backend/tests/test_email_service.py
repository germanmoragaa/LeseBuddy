from unittest.mock import ANY, MagicMock, call, patch

from app.core.config import Settings
from app.services.email import EmailMessage, SmtpEmailSender


def _settings(**overrides: object) -> Settings:
    defaults: dict[str, object] = {
        "smtp_host": "smtp.gmail.com",
        "smtp_port": 587,
        "smtp_username": "sender@example.com",
        "smtp_password": "app-password",
        "smtp_use_tls": True,
        "email_from": "LeseBuddy <sender@example.com>",
    }
    defaults.update(overrides)
    return Settings(**defaults)


def _message() -> EmailMessage:
    return EmailMessage(
        to="recipient@example.com",
        subject="Subject",
        text_body="text body",
        html_body="<p>html body</p>",
    )


class TestSmtpEmailSender:
    def test_starttls_then_login_then_send_in_order(self) -> None:
        """Gmail (and any STARTTLS-on-587 provider) requires EHLO, STARTTLS, EHLO again,
        then AUTH, before a message is accepted. smtplib's starttls()/login() each trigger
        their own EHLO internally (login() re-EHLOs because STARTTLS resets connection
        state) — that part is smtplib's responsibility. What our code must get right is
        calling starttls() before login() before send_message(), only when configured to."""
        settings = _settings()
        smtp_instance = MagicMock()
        with patch("app.services.email.smtplib.SMTP") as smtp_class:
            smtp_class.return_value.__enter__.return_value = smtp_instance
            SmtpEmailSender(settings).send(_message())

        smtp_class.assert_called_once_with(settings.smtp_host, settings.smtp_port)
        assert smtp_instance.method_calls == [
            call.starttls(),
            call.login(settings.smtp_username, settings.smtp_password),
            call.send_message(ANY),
        ]

    def test_skips_starttls_and_login_when_disabled(self) -> None:
        """The Mailpit-style local setup (no TLS, no auth) must keep working unchanged."""
        settings = _settings(smtp_use_tls=False, smtp_username="")
        smtp_instance = MagicMock()
        with patch("app.services.email.smtplib.SMTP") as smtp_class:
            smtp_class.return_value.__enter__.return_value = smtp_instance
            SmtpEmailSender(settings).send(_message())

        smtp_instance.starttls.assert_not_called()
        smtp_instance.login.assert_not_called()
        smtp_instance.send_message.assert_called_once()
