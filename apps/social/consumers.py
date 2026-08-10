from channels.db import database_sync_to_async
from channels.generic.websocket import AsyncJsonWebsocketConsumer

from .services import (
    broadcast_presence_change,
    mark_user_offline,
    mark_user_online,
    presence_group_name,
    refresh_user_presence,
)


class SocialPresenceConsumer(AsyncJsonWebsocketConsumer):
    async def connect(self):
        user = self.scope.get("user")
        if not user or not user.is_authenticated:
            await self.close(code=4401)
            return

        self.user = user
        self.group_name = presence_group_name(user.id)
        await self.channel_layer.group_add(self.group_name, self.channel_name)
        became_online = await database_sync_to_async(mark_user_online)(user)
        await self.accept()
        await self.send_json(
            {
                "event": "presence.connected",
                "user_id": user.id,
                "is_online": True,
            }
        )
        if became_online:
            await database_sync_to_async(broadcast_presence_change)(user, True)

    async def disconnect(self, code):
        user = getattr(self, "user", None)
        if user and user.is_authenticated:
            was_online = await database_sync_to_async(mark_user_offline)(user)
            await self.channel_layer.group_discard(self.group_name, self.channel_name)
            if was_online:
                await database_sync_to_async(broadcast_presence_change)(user, False)

    async def receive_json(self, content, **kwargs):
        action = content.get("action")
        if action == "heartbeat":
            await database_sync_to_async(refresh_user_presence)(self.user)
            await self.send_json({"event": "presence.heartbeat", "user_id": self.user.id})
        else:
            await self.send_json({"event": "error", "detail": "Unsupported action."})

    async def social_event(self, event):
        await self.send_json(event["payload"])
