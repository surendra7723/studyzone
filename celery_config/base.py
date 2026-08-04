import os
from celery import Celery

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'myproject.settings')

app = Celery('myproject')

# Load production settings using a dedicated string path
app.config_from_object('myproject.celery.config', namespace='CELERY')

# Automatically discover tasks split across multiple files in apps/
app.autodiscover_tasks()
