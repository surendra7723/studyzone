from django.urls import path, include
from rest_framework.routers import DefaultRouter

from .views import PomodoroSessionViewSet, GoalViewSet

app_name = "pomodoro"

router = DefaultRouter()
router.register(
    r"sessions", PomodoroSessionViewSet, basename="pomodoro-session"
)
router.register(r"goals", GoalViewSet, basename="goal")

urlpatterns = [
    path("", include(router.urls)),
]
