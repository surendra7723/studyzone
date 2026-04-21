
from django.db import models
from django.conf import settings
from core.models.base import TimeStampedModel


class Category(TimeStampedModel):
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='categories')
    name = models.CharField(max_length=100)
    color = models.CharField(max_length=7, default='#3498db')  # Hex color

    class Meta:
        verbose_name_plural = 'Categories'
        unique_together = ('user', 'name')

    def __str__(self):
        return self.name


class Task(TimeStampedModel):
    class Priority(models.IntegerChoices):
        LOW = 1, 'Low'
        MEDIUM = 2, 'Medium'
        HIGH = 3, 'High'

    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='tasks')
    category = models.ForeignKey(Category, on_delete=models.SET_NULL, null=True, blank=True, related_name='tasks')
    title = models.CharField(max_length=255)
    description = models.TextField(blank=True, null=True)
    priority = models.IntegerField(choices=Priority.choices, default=Priority.MEDIUM)
    due_date = models.DateTimeField(null=True, blank=True)
    goal = models.ForeignKey('pomodoro.Goal', on_delete=models.SET_NULL, null=True, blank=True, related_name='tasks')
    estimated_pomodoros = models.PositiveIntegerField(default=1)
    is_completed = models.BooleanField(default=False)
    
    def __str__(self):
        return self.title