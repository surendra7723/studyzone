from django.db import models
from core.models import TimeStampedModel


class BaseServerModel(TimeStampedModel):
    """Base model for server. Inherits timestamps from core."""

    class Meta:
        abstract = True
        app_label = "server"
