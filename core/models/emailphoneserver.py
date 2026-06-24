from django.db import models
from django.core.cache import cache
from fernet_fields import EncryptedTextField

class EmailServer(models.Model):
    name = models.CharField(max_length=255, default="Default Email Server")
    host = models.CharField(max_length=255)
    port = models.PositiveIntegerField()
    username = models.CharField(max_length=255)
    password = EncryptedTextField()
    use_tls = models.BooleanField(default=False)
    use_ssl = models.BooleanField(default=False)
    default_from_email = models.EmailField()
    is_active = models.BooleanField(default=True)

    class Meta:
        verbose_name = "Email Server"
        verbose_name_plural = "Email Servers"

    def __str__(self):
        return f"{self.name} ({self.host}:{self.port})"
    

class PhoneServer(models.Model):
    name = models.CharField(max_length=255, default="Default Phone Server")
    account_sid = models.CharField(max_length=255)
    auth_token = EncryptedTextField()
    from_number = models.CharField(max_length=20)
    is_active = models.BooleanField(default=True)

    class Meta:
        verbose_name = "Phone Server"
        verbose_name_plural = "Phone Servers"

    def __str__(self):
        return f"{self.name} ({self.from_number})"