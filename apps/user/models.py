from django.db import models
from django.contrib.auth.models import AbstractUser

# Create your models here.
class User(AbstractUser):
    is_deleted = models.BooleanField(default=False)
    manager = models.Manager()
    def __str__(self):
        return self.username


class UserProfile(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE,related_name='profile')
    bio = models.TextField(blank=True, null=True)
    profile_picture = models.ImageField(upload_to='profile_pics/', blank=True, null=True)
    location = models.CharField(max_length=100, blank=True, null=True)
    birth_date = models.DateField(blank=True, null=True)
    
    # Study Settings
    preferred_focus_time = models.PositiveIntegerField(default=25, help_text="Default focus duration in minutes")
    preferred_short_break = models.PositiveIntegerField(default=5, help_text="Default short break duration in minutes")
    preferred_long_break = models.PositiveIntegerField(default=15, help_text="Default long break duration in minutes")
    pomodoros_until_long_break = models.PositiveIntegerField(default=4)
    
    def __str__(self):
        return f"{self.user.username}'s profile"
    
