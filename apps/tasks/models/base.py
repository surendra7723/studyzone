from django.db import models
from core.models import TimeStampedModel


class BaseTasksModel(TimeStampedModel):
    """Base model for tasks. Inherits timestamps from core."""

    class Meta:
        abstract = True
        app_label = "tasks"
