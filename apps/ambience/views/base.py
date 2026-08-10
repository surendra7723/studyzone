from core.views import BaseAPIView


class AmbienceBaseView(BaseAPIView):
    """Base view for ambience with standard response helpers."""

    def get(self, request, *args, **kwargs):
        return self.success(data={"app": "ambience"})
