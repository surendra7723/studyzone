import os
from django.conf import settings
from django.core.cache import cache
from core.models.emailphoneserver import EmailServer, PhoneServer

CACHE_TTL = 300  # 5 minutes – adjust as needed

def get_email_config():
    """Returns a dict with SMTP credentials."""
    
    if settings.EMAIL_CONFIG_SOURCE == "db":
        cache_key = "active_email_server"
        server = cache.get(cache_key)
        
        if server is None:
            server = EmailServer.objects.filter(is_active=True).first()
            cache.set(cache_key, server, CACHE_TTL)
        
        if server:
            # Return DB config (as a dict or object)
            return {
                "host": server.host,
                "port": server.port,
                "username": server.username,
                "password": server.password,
                "use_tls": server.use_tls,
                "use_ssl": server.use_ssl,
                "default_from_email": server.default_from_email,
            }
    
    # FALLBACK: Always return environment config if DB is disabled or no record found
    return {
        "host": settings.EMAIL_HOST,
        "port": settings.EMAIL_PORT,
        "username": settings.EMAIL_HOST_USER,
        "password": settings.EMAIL_HOST_PASSWORD,
        "use_tls": settings.EMAIL_USE_TLS,
        "use_ssl": settings.EMAIL_USE_SSL,
        "default_from_email": settings.DEFAULT_FROM_EMAIL,
    }


def get_twilio_config():
    """Returns a dict with Twilio credentials."""
    
    if settings.TWILIO_CONFIG_SOURCE == "db":
        cache_key = "active_twilio_config"
        config = cache.get(cache_key)
        
        if config is None:
            config = PhoneServer.objects.filter(is_active=True).first()
            cache.set(cache_key, config, CACHE_TTL)
        
        if config:
            return {
                "account_sid": config.account_sid,
                "auth_token": config.auth_token,
                "from_number": config.from_number,
            }
    
    # FALLBACK to environment
    return {
        "account_sid": settings.TWILIO_ACCOUNT_SID,
        "auth_token": settings.TWILIO_AUTH_TOKEN,
        "from_number": settings.TWILIO_FROM_NUMBER,
    }