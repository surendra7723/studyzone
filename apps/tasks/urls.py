from django.urls import path

from .views import TasksBaseView

app_name = "tasks"

urlpatterns = [
    path("", TasksBaseView.as_view(), name="base"),
]
