import os

from celery import Celery

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings")

app = Celery("studyzone")
app.config_from_object("django.conf:settings", namespace="CELERY")
app.autodiscover_tasks()

# Load beat schedule from celery_config module
from celery_config.schedules import CELERY_BEAT_SCHEDULE
app.conf.beat_schedule = CELERY_BEAT_SCHEDULE
