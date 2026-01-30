# app/matches/consumers.py
import json
from channels.generic.websocket import AsyncWebsocketConsumer


class SignalingConsumer(AsyncWebsocketConsumer):
    async def connect(self):
        user = self.scope.get("user")

        # 인증 필수: Anonymous면 거절
        if not user or user.is_anonymous:
            await self.close(code=4401)  # Unauthorized
            return

        self.user_id = user.id
        self.session_id = self.scope["url_route"]["kwargs"]["session_id"]
        self.room_group_name = f"session_{self.session_id}"

        await self.channel_layer.group_add(self.room_group_name, self.channel_name)
        await self.accept()

        await self.send_json(
            {
                "type": "joined",
                "sessionId": self.session_id,
                "userId": self.user_id,
            }
        )

    async def disconnect(self, close_code):
        await self.channel_layer.group_discard(self.room_group_name, self.channel_name)

        await self.channel_layer.group_send(
            self.room_group_name,
            {
                "type": "peer.left",
                "sessionId": self.session_id,
                "userId": getattr(self, "user_id", None),
            },
        )

    async def receive(self, text_data):
        data = json.loads(text_data)
        msg_type = data.get("type")

        if msg_type in ["offer", "answer", "ice"]:
            await self.channel_layer.group_send(
                self.room_group_name,
                {
                    "type": "signal.message",
                    "payload": data,
                },
            )

    async def signal_message(self, event):
        await self.send(text_data=json.dumps(event["payload"]))

    async def peer_left(self, event):
        await self.send_json(
            {
                "type": "peer-left",
                "sessionId": self.session_id,
                "userId": event.get("userId"),
            }
        )
