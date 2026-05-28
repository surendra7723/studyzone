from rest_framework import permissions, viewsets

from .models import PomodoroSession
from .serializers import PomodoroSessionSerializer


class PomodoroSessionViewSet(viewsets.ModelViewSet):
    queryset = PomodoroSession.objects.all()
    serializer_class = PomodoroSessionSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        return self.queryset.filter(user=self.request.user)

    def perform_create(self, serializer):
        serializer.save(user=self.request.user)