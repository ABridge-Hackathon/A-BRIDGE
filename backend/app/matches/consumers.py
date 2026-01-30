import json
from channels.generic.websocket import AsyncJsonWebsocketConsumer


class SignalingConsumer(AsyncJsonWebsocketConsumer):
    async def connect(self):
        self.session_id = self.scope["url_route"]["kwargs"]["session_id"]
        self.room_group_name = f"session_{self.session_id}"

        await self.channel_layer.group_add(self.room_group_name, self.channel_name)
        await self.accept()

        await self.send_json(
            {
                "type": "joined",
                "sessionId": self.session_id,
            }
        )

    async def disconnect(self, close_code):
        room = getattr(self, "room_group_name", None)
        if not room:
            return

        # 먼저 나부터 그룹에서 빼고
        await self.channel_layer.group_discard(room, self.channel_name)

        # 남아있는 사람들에게 "나감" 알림
        await self.channel_layer.group_send(
            room,
            {
                "type": "peer.left",
                "sessionId": getattr(self, "session_id", None),
            },
        )

    async def receive(self, text_data=None, bytes_data=None):
        if not text_data:
            return

        data = json.loads(text_data)
        msg_type = data.get("type")

        if msg_type in ("offer", "answer", "ice"):
            await self.channel_layer.group_send(
                self.room_group_name,
                {"type": "signal.message", "payload": data},
            )

    async def signal_message(self, event):
        await self.send_json(event["payload"])

    async def peer_left(self, event):
        await self.send_json(
            {
                "type": "peer-left",
                "sessionId": event.get("sessionId"),
            }
        )
