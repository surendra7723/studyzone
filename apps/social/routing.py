from django.urls import path

from .consumers import SocialPresenceConsumer

websocket_urlpatterns = [
    path("ws/social/presence/", SocialPresenceConsumer.as_asgi()),
]
