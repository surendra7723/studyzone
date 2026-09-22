from pathlib import Path
import os
import dj_database_url

# Build paths inside the project like this: BASE_DIR / 'subdir'.
BASE_DIR = Path(__file__).resolve().parent.parent

# Database
# Use Render's DATABASE_URL in production and the existing DB_* variables locally.
database_url = os.getenv("DATABASE_URL")
if database_url:
    DATABASES = {
        "default": dj_database_url.parse(
            database_url,
            conn_max_age=600,
            ssl_require=os.getenv("DATABASE_SSL_REQUIRE", "true").lower() == "true",
        )
    }
else:
    DATABASES = {
        "default": {
            "ENGINE": "django.db.backends.postgresql",
            "NAME": os.getenv("DB_NAME", "surendra"),
            "USER": os.getenv("DB_USER", "surendra"),
            "PASSWORD": os.getenv("DB_PASSWORD", "surendra"),
            "HOST": os.getenv("DB_HOST", "localhost"),
            "PORT": os.getenv("DB_PORT", "5432"),
            "CONN_MAX_AGE": 600,
        }
    }


# Use custom user model
AUTH_USER_MODEL = "user.User"

# Quick-start development settings - unsuitable for production
# See https://docs.djangoproject.com/en/6.0/howto/deployment/checklist/

# SECURITY WARNING: keep the secret key used in production secret!
SECRET_KEY = os.getenv("SECRET_KEY", "django-insecure-dev-only-key")
# SECURITY WARNING: don't run with debug turned on in production!
DEBUG = os.getenv("DEBUG", "False").lower() == "true"


ALLOWED_HOSTS = [
    host.strip()
    for host in os.getenv("ALLOWED_HOSTS", "").split(",")
    if host.strip()
]

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
    "corsheaders",
    "rest_framework",
    "rest_framework_simplejwt",
    "drf_spectacular",
    "django_filters",
    "core.apps.CoreConfig",
    "apps.user.apps.UserConfig",
    "apps.social.apps.SocialConfig",
    "config.apps.ConfigConfig",
    "apps.tasks.apps.TasksConfig",
    "apps.pomodoro.apps.PomodoroConfig",
    "apps.ambience.apps.AmbienceConfig",
    "apps.notifications.apps.NotificationsConfig",
    'django_celery_beat',
    "dictionary_app",
    "apps.leaderboard",
]

if DEBUG:
    INSTALLED_APPS += [
        "django_extensions",
        "debug_toolbar",
    ]

# Make django-extensions use IPython by default in shell_plus.
SHELL_PLUS = "ipython"

MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
    "whitenoise.middleware.WhiteNoiseMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "corsheaders.middleware.CorsMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
]

if DEBUG:
    MIDDLEWARE += ["debug_toolbar.middleware.DebugToolbarMiddleware"]

ROOT_URLCONF = "config.urls"

CORS_ALLOW_ALL_ORIGINS = True

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
        "rest_framework.authentication.SessionAuthentication",
    ),
    "DEFAULT_PERMISSION_CLASSES": (
        "core.permissions.IsAuthenticatedAndActive",
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

VAPID_PRIVATE_KEY = os.getenv("VAPID_PRIVATE_KEY", "")
VAPID_SUBJECT = os.getenv("VAPID_SUBJECT", "mailto:admin@example.com")
VAPID_AUDIENCE = os.getenv("VAPID_AUDIENCE", "")
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
STORAGES = {
    "default": {
        "BACKEND": "django.core.files.storage.FileSystemStorage",
    },
    "staticfiles": {
        "BACKEND": "whitenoise.storage.CompressedManifestStaticFilesStorage",
    },
}

# Media files
MEDIA_URL = "media/"
MEDIA_ROOT = BASE_DIR / "media"
STATIC_ROOT = BASE_DIR / "staticfiles"

LOGGING = {
    "version": 1,
    "disable_existing_loggers": False,
    "formatters": {
        "verbose": {
            "format": "{levelname} {asctime} {module} {thread:d}{message}",
            "style": "{",
        },
        "simple": {
            "format": "{levelname} {asctime} [{module}] {message}",
            "style": "{",
        },
    },
    "handlers": {
        "console": {
            "level": "INFO",
            "class": "logging.StreamHandler",
            "formatter": "simple",
        },
        "file": {
            "level": "INFO",
            "class": "logging.FileHandler",
            "filename": os.path.join(BASE_DIR, "studyzone.log"),
            "formatter": "verbose",
        },
    },
    "loggers": {
        "django": {
            "handlers": ["console", "file"],
            "level": "INFO",
            "propagate": True,
        },
    },
}
