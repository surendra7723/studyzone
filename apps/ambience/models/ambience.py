from django.db import models

from .base import BaseAmbienceModel


class Category(BaseAmbienceModel):
    name = models.CharField(max_length=100, unique=True)

    class Meta:
        verbose_name_plural = "Categories"
        ordering = ["name"]

    def __str__(self):
        return self.name


class AmbienceTrack(BaseAmbienceModel):
    name = models.CharField(max_length=255)
    category = models.ForeignKey(
        Category, on_delete=models.SET_NULL, null=True, blank=True, related_name="tracks"
    )
    file = models.FileField(upload_to="ambience/")
    duration_seconds = models.PositiveIntegerField()
    is_active = models.BooleanField(default=True, db_index=True)

    class Meta:
        ordering = ["name"]

    def __str__(self):
        return self.name
