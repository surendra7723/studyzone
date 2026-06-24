from django.core.mail.backends.smtp import EmailBackend
from django.conf import settings
from .resolver import get_email_config, get_twilio_config

class DynamicSMTPBackend(EmailBackend):
    """
    An SMTP backend that resolves host/credentials dynamically on each connection.
    Honors EMAIL_CONFIG_SOURCE = "env" | "db" with fallback to env.
    """

    def __init__(self, fail_silently=False, **kwargs):
        # Do NOT pass host/port/etc. to super() here.
        # Instead, we use placeholders; open() will override them.
        super().__init__(fail_silently=fail_silently, **kwargs)
        self._refreshed = False  # to avoid repeated refreshes in same request

    def _refresh_config(self):
        """Pull the latest config and update instance attributes."""
        config = get_email_config()

        self.host = config["host"]
        self.port = config["port"]
        self.username = config["username"]
        self.password = config["password"]
        self.use_tls = config["use_tls"]
        self.use_ssl = config["use_ssl"]
        # Default from email is usually used by the mailer, not the backend itself,
        # but we can store it for later reference if needed.
        self.default_from_email = config.get("default_from_email")

    def open(self):
        """
        Ensure we have fresh credentials before establishing the connection.
        This is called by send_messages() before every sending attempt.
        """
        # Force a refresh every time we open (or cache per request if you prefer)
        self._refresh_config()

        # If the connection is already open but the config changed, we must
        # close it so it reconnects with the new credentials.
        if self.connection is not None:
            # You could check if host/port changed to avoid unnecessary close,
            # but closing is safe and cheap.
            self.close()

        return super().open()

    # Optionally, to be extra safe, also refresh in send_messages:
    def send_messages(self, email_messages):
        self._refresh_config()
        # If we use a persistent connection, ensure it's closed so open() refreshes.
        if self.connection is not None:
            self.close()
        return super().send_messages(email_messages)