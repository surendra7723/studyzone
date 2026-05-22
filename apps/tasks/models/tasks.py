from django.conf import settings
from django.core.exceptions import ValidationError
from django.core.validators import MinValueValidator, RegexValidator
from django.db import models

from .base import BaseTasksModel


class Category(BaseTasksModel):
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="categories"
    )
    name = models.CharField(max_length=100)
    color = models.CharField(
        max_length=7,
        default="#3498db",
        validators=[
            RegexValidator(
                r"^#[0-9A-Fa-f]{6}$",
                message="Use a valid hex color in the form #RRGGBB.",
            )
        ],
    )

    class Meta:
        verbose_name_plural = "Categories"
        ordering = ["name"]
        constraints = [
            models.UniqueConstraint(
                fields=["user", "name"], name="unique_category_name_per_user"
            ),
        ]

    def clean(self):
        super().clean()
        if self.name:
            self.name = self.name.strip()

    def __str__(self):
        return self.name


class Task(BaseTasksModel):
    class Priority(models.IntegerChoices):
        LOW = 1, "Low"
        MEDIUM = 2, "Medium"
        HIGH = 3, "High"

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="tasks"
    )
    category = models.ForeignKey(
        Category, on_delete=models.SET_NULL, null=True, blank=True, related_name="tasks"
    )
    title = models.CharField(max_length=255)
    description = models.TextField(blank=True, null=True)
    priority = models.IntegerField(
        choices=Priority.choices, default=Priority.MEDIUM, db_index=True
    )
    due_date = models.DateTimeField(null=True, blank=True)
    estimated_pomodoros = models.PositiveIntegerField(
        default=1, validators=[MinValueValidator(1)]
    )
    is_completed = models.BooleanField(default=False, db_index=True)

    class Meta:
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["user", "is_completed"]),
            models.Index(fields=["user", "due_date"]),
        ]

    def clean(self):
        super().clean()
        if self.category and self.user_id and self.category.user_id != self.user_id:
            raise ValidationError(
                {"category": "Category must belong to the same user as the task."}
            )

    def __str__(self):
        return self.title
