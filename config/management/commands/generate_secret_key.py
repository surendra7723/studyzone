import secrets
import string
from django.core.management.base import BaseCommand

class Command(BaseCommand):
    help = "Generates a cryptographically secure secret key for settings.py or .env files."

    def handle(self, *args, **options):
        # Define characters mirroring Django's core generation pattern
        chars = string.ascii_letters + string.digits + "!@#$%^&*(-_=+)"
        
        # Securely pick 50 characters
        secret_key = "".join(secrets.choice(chars) for _ in range(50))
        
        self.stdout.write(self.style.MESSAGES["INFO"]("Generated Secure Secret Key:\n"))
        self.stdout.write(self.style.SUCCESS(secret_key))
        self.stdout.write("\n" + self.style.WARNING("Copy this value into your production configuration or .env file."))
