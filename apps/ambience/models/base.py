from django.db import models
from core.models import TimeStampedModel


class BaseAmbienceModel(TimeStampedModel):
    """Base model for ambience. Inherits timestamps from core."""

    class Meta:
        abstract = True
        app_label = "ambience"
