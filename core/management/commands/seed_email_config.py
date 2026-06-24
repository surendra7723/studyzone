# core/management/commands/seed_email_config.py
from django.core.management.base import BaseCommand
from django.conf import settings
from core.models import EmailServer, PhoneServer

class Command(BaseCommand):
    help = "Seed EmailServer and TwilioConfig from environment variables"

    def handle(self, *args, **options):
        EmailServer.objects.update_or_create(
            is_active=True,
            defaults={
                "host": settings.EMAIL_HOST,
                "port": settings.EMAIL_PORT,
                "username": settings.EMAIL_HOST_USER,
                "password": settings.EMAIL_HOST_PASSWORD,
                "use_tls": settings.EMAIL_USE_TLS,
                "use_ssl": settings.EMAIL_USE_SSL,
                "default_from_email": settings.DEFAULT_FROM_EMAIL,
            }
        )
        PhoneServer.objects.update_or_create(
            is_active=True,
            defaults={
                "account_sid": settings.TWILIO_ACCOUNT_SID,
                "auth_token": settings.TWILIO_AUTH_TOKEN,
                "from_number": settings.TWILIO_FROM_NUMBER,
            }
        )
        self.stdout.write(self.style.SUCCESS("Seeded email & Twilio configs from env"))