from pathlib import Path
import os

# Build paths inside the project like this: BASE_DIR / 'subdir'.
BASE_DIR = Path(__file__).resolve().parent.parent

# Database
# https://docs.djangoproject.com/en/6.0/ref/settings/#databases
DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.postgresql",
        "NAME": os.getenv("DB_NAME", "surendra"),
        "USER": os.getenv("DB_USER", "surendra"),
        "PASSWORD": os.getenv("DB_PASSWORD", "surendra"),
        "HOST": os.getenv("DB_HOST", "localhost"),
        "PORT": os.getenv("DB_PORT", "5432"),
    }
}


# Use custom user model
AUTH_USER_MODEL = "user.User"

# Quick-start development settings - unsuitable for production
# See https://docs.djangoproject.com/en/6.0/howto/deployment/checklist/

# SECURITY WARNING: keep the secret key used in production secret!
SECRET_KEY = os.getenv("SECRET_KEY", "django-insecure-dev-only-key")
# SECURITY WARNING: don't run with debug turned on in production!
DEBUG = True

ALLOWED_HOSTS = []

# Debug toolbar configuration
INTERNAL_IPS = [
    "127.0.0.1",
    "localhost",
]

# Application definition
INSTALLED_APPS = [
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
    "rest_framework",
    "rest_framework_simplejwt",
    "drf_spectacular",
    "django_extensions",
    "core.apps.CoreConfig",
    "apps.user.apps.UserConfig",
    "apps.social.apps.SocialConfig",
    "config.apps.ConfigConfig",
    "apps.tasks.apps.TasksConfig",
    "apps.pomodoro.apps.PomodoroConfig",
    "debug_toolbar",
    'django_celery_beat',
    "dictionary_app",
]

# Make django-extensions use IPython by default in shell_plus.
SHELL_PLUS = "ipython"

MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
    "debug_toolbar.middleware.DebugToolbarMiddleware",
]

ROOT_URLCONF = "config.urls"

TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "DIRS": [],
        "APP_DIRS": True,
        "OPTIONS": {
            "context_processors": [
                "django.template.context_processors.debug",
                "django.template.context_processors.request",
                "django.contrib.auth.context_processors.auth",
                "django.contrib.messages.context_processors.messages",
            ],
        },
    },
]

WSGI_APPLICATION = "config.wsgi.application"
ASGI_APPLICATION = "config.asgi.application"

CHANNEL_LAYERS = {
    "default": {
        "BACKEND": "channels_redis.core.RedisChannelLayer",
        "CONFIG": {
            "hosts": [os.getenv("CHANNEL_REDIS_URL", os.getenv("CELERY_BROKER_URL", "redis://localhost:6379/0"))],
        },
    }
}

# REST Framework Configuration
REST_FRAMEWORK = {
    "DEFAULT_AUTHENTICATION_CLASSES": (
        "rest_framework_simplejwt.authentication.JWTAuthentication",
    ),
    "DEFAULT_PERMISSION_CLASSES": (
        "rest_framework.permissions.IsAuthenticated",
    ),
    "DEFAULT_SCHEMA_CLASS": "drf_spectacular.openapi.AutoSchema",
    "DEFAULT_THROTTLE_CLASSES": (
        "rest_framework.throttling.AnonRateThrottle",
        "rest_framework.throttling.UserRateThrottle",
    ),
    "DEFAULT_THROTTLE_RATES": {
        "anon": os.getenv("DRF_THROTTLE_ANON", "100/hour"),
        "user": os.getenv("DRF_THROTTLE_USER", "1000/hour"),
    },
}

# JWT Configuration
from datetime import timedelta

SIMPLE_JWT = {
    "ACCESS_TOKEN_LIFETIME": timedelta(minutes=60),
    "REFRESH_TOKEN_LIFETIME": timedelta(days=1),
    "ROTATE_REFRESH_TOKENS": True,
    "BLACKLIST_AFTER_ROTATION": False,
    "UPDATE_LAST_LOGIN": True,
}

POMODORO_SESSION_ORPHAN_TTL_HOURS = int(
    os.getenv("POMODORO_SESSION_ORPHAN_TTL_HOURS", "24")
)

SPECTACULAR_SETTINGS = {
    "TITLE": "Studyzone API",
    "DESCRIPTION": "API documentation for the Studyzone backend.",
    "VERSION": "1.0.0",
}

# Email verification settings
EMAIL_VERIFICATION_URL_BASE = os.getenv(
    "EMAIL_VERIFICATION_URL_BASE", "http://localhost:8000"
)
EMAIL_VERIFICATION_TOKEN_TTL_MINUTES = int(
    os.getenv("EMAIL_VERIFICATION_TOKEN_TTL_MINUTES", "30")
)
EMAIL_VERIFICATION_RESEND_COOLDOWN_SECONDS = int(
    os.getenv("EMAIL_VERIFICATION_RESEND_COOLDOWN_SECONDS", "60")
)

# Social auth settings
SOCIAL_AUTH_ENABLED = os.getenv("SOCIAL_AUTH_ENABLED", "true").lower() == "true"
GOOGLE_CLIENT_ID = os.getenv("GOOGLE_CLIENT_ID", "")
FACEBOOK_APP_ID = os.getenv("FACEBOOK_APP_ID", "")
FACEBOOK_APP_SECRET = os.getenv("FACEBOOK_APP_SECRET", "")
SOCIAL_LINK_CONFIRM_URL_BASE = os.getenv(
    "SOCIAL_LINK_CONFIRM_URL_BASE", EMAIL_VERIFICATION_URL_BASE
)
SOCIAL_LINK_TOKEN_TTL_MINUTES = int(os.getenv("SOCIAL_LINK_TOKEN_TTL_MINUTES", "30"))
SOCIAL_LINK_RESEND_COOLDOWN_SECONDS = int(
    os.getenv("SOCIAL_LINK_RESEND_COOLDOWN_SECONDS", "60")
)

SOCIAL_PRESENCE_REDIS_URL = os.getenv(
    "SOCIAL_PRESENCE_REDIS_URL",
    os.getenv("CELERY_BROKER_URL", "redis://localhost:6379/0"),
)
SOCIAL_PRESENCE_TTL_SECONDS = int(os.getenv("SOCIAL_PRESENCE_TTL_SECONDS", "90"))
#Toggle (env) or "db" for emailbackend and phonebackend

EMAIL_CONFIG_SOURCE = os.getenv("EMAIL_CONFIG_SOURCE", "env")
TWILIO_CONFIG_SOURCE = os.getenv("TWILIO_CONFIG_SOURCE", "env")

# Email configuration for local Mailpit verification.
EMAIL_BACKEND = "core.emailbackend.DynamicSMTPBackend"


EMAIL_HOST = os.getenv("EMAIL_HOST", "localhost")
EMAIL_PORT = int(os.getenv("EMAIL_PORT", "1025"))
EMAIL_HOST_USER = os.getenv("EMAIL_HOST_USER", "")
EMAIL_HOST_PASSWORD = os.getenv("EMAIL_HOST_PASSWORD", "")
EMAIL_USE_TLS = os.getenv("EMAIL_USE_TLS", "false").lower() == "true"
EMAIL_USE_SSL = os.getenv("EMAIL_USE_SSL", "false").lower() == "true"
EMAIL_TIMEOUT = int(os.getenv("EMAIL_TIMEOUT", "10"))
DEFAULT_FROM_EMAIL = os.getenv(
    "DEFAULT_FROM_EMAIL", "Studyzone <no-reply@studyzone.local>"
)
SERVER_EMAIL = os.getenv("SERVER_EMAIL", DEFAULT_FROM_EMAIL)
MOCK_TWILIO = True

# Static files (CSS, JavaScript, Images)
STATIC_URL = "static/"