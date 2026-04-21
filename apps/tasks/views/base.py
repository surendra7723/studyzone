from core.views import BaseAPIView


class TasksBaseView(BaseAPIView):
    """Base view for tasks with standard response helpers."""

    def get(self, request, *args, **kwargs):
        return self.success(data={"app": "tasks"})
