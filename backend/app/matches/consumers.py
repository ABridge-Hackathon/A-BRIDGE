import json
from urllib.parse import parse_qs

from channels.generic.websocket import AsyncJsonWebsocketConsumer
from channels.db import database_sync_to_async

# peerCount를 "서버 재시작/멀티프로세스"에도 버티게 하려면 Redis가 제일 깔끔함
from app.common.redis_client import get_redis

PEERCOUNT_TTL_SEC = 60 * 30  # 30분 (세션 TTL이랑 맞추면 좋음)


def _peercount_key(session_id: str) -> str:
    return f"ws:peerCount:{session_id}"


class SignalingConsumer(AsyncJsonWebsocketConsumer):
    """
    WS Signaling Protocol (Front spec)
      - URL: ws://<host>/ws/signaling/<sessionId>/?userId=<int>   (JWT 붙이면 token으로 교체)
      - Envelope:
        {
          "type": "...",
          "sessionId": "...",
          "fromUserId": 1,
          "payload": {...}
        }
    """

    async def connect(self):
        self.session_id = self.scope["url_route"]["kwargs"]["session_id"]
        self.room_group_name = f"session_{self.session_id}"

        # 1) 임시 인증: querystring userId 사용 (JWT 붙이면 여기만 바꾸면 됨)
        self.user_id = self._get_user_id_from_query()
        if not self.user_id:
            # 4401 Unauthorized (앱에서 처리하기 쉬움)
            await self.close(code=4401)
            return

        # 2) group join
        await self.channel_layer.group_add(self.room_group_name, self.channel_name)
        await self.accept()

        # 3) peerCount 증가 + joined/peer-joined 이벤트
        peer_count = await self._peercount_incr()

        # 나에게 joined
        await self.send_json(
            {
                "type": "joined",
                "sessionId": self.session_id,
                "fromUserId": self.user_id,
                "payload": {"peerCount": peer_count},
            }
        )

        # 나를 제외한 나머지에게 peer-joined
        await self.channel_layer.group_send(
            self.room_group_name,
            {
                "type": "peer.joined",  # handler: peer_joined
                "sessionId": self.session_id,
                "fromUserId": self.user_id,
                "payload": {"peerCount": peer_count},
            },
        )

    async def disconnect(self, close_code):
        # connect 실패한 케이스 방어
        room = getattr(self, "room_group_name", None)
        session_id = getattr(self, "session_id", None)
        user_id = getattr(self, "user_id", None)
        if not room or not session_id or not user_id:
            return

        # 1) peerCount 감소
        peer_count = await self._peercount_decr()

        # 2) "나 나감"을 먼저 브로드캐스트 (중요!)
        #    ※ group_discard 먼저 해버리면, 레이스 상황에서 이벤트 전달이 꼬일 수 있어서
        await self.channel_layer.group_send(
            room,
            {
                "type": "peer.left",  # handler: peer_left
                "sessionId": session_id,
                "fromUserId": user_id,
                "payload": {"peerCount": peer_count},
            },
        )

        # 3) 그 다음 group에서 제거
        await self.channel_layer.group_discard(room, self.channel_name)

    async def receive(self, text_data=None, bytes_data=None):
        if not text_data:
            return

        try:
            data = json.loads(text_data)
        except Exception:
            return

        msg_type = data.get("type")

        # 스펙: join은 connect에서 이미 처리하니까, 클라가 join 보내도 무시/ack만 주면 됨
        if msg_type == "join":
            await self.send_json(
                {
                    "type": "joined",
                    "sessionId": self.session_id,
                    "fromUserId": self.user_id,
                    "payload": {"peerCount": await self._peercount_get()},
                }
            )
            return

        # 스펙: leave는 "정상 종료" 이벤트로 권장 (Ctrl+C 같은 강제 종료는 100% 보장 어려움)
        if msg_type == "leave":
            # 상대에게 peer-left를 먼저 보낸 후 끊기
            await self.channel_layer.group_send(
                self.room_group_name,
                {
                    "type": "peer.left",
                    "sessionId": self.session_id,
                    "fromUserId": self.user_id,
                    "payload": {"peerCount": max(0, (await self._peercount_get()) - 1)},
                },
            )
            await self.close(code=1000)
            return

        # offer/answer/ice만 중계
        if msg_type in ("offer", "answer", "ice"):
            payload = data.get("payload") or {}

            # 서버가 envelope 강제로 통일해서 전달
            event = {
                "type": "signal.message",  # handler: signal_message
                "envelope": {
                    "type": msg_type,
                    "sessionId": self.session_id,
                    "fromUserId": self.user_id,
                    "payload": payload,
                },
            }
            await self.channel_layer.group_send(self.room_group_name, event)

    # ---- group handlers ----

    async def signal_message(self, event):
        """
        offer/answer/ice 중계.
        내 메시지도 내게 돌아오게 되는데(그룹 브로드캐스트),
        프론트에서 fromUserId로 필터링하면 됨.
        """
        envelope = event.get("envelope") or {}
        await self.send_json(envelope)

    async def peer_joined(self, event):
        # 내가 보낸 peer-joined도 나한테 올 수 있으니 fromUserId로 무시
        if event.get("fromUserId") == self.user_id:
            return
        await self.send_json(
            {
                "type": "peer-joined",
                "sessionId": event.get("sessionId"),
                "fromUserId": event.get("fromUserId"),
                "payload": event.get("payload") or {},
            }
        )

    async def peer_left(self, event):
        # 내가 보낸 peer-left도 나한테 올 수 있으니 fromUserId로 무시
        if event.get("fromUserId") == self.user_id:
            return
        await self.send_json(
            {
                "type": "peer-left",
                "sessionId": event.get("sessionId"),
                "fromUserId": event.get("fromUserId"),
                "payload": event.get("payload") or {},
            }
        )

    # ---- helpers ----

    def _get_user_id_from_query(self):
        """
        ws://.../ws/signaling/<sessionId>/?userId=1
        """
        qs = self.scope.get("query_string", b"").decode("utf-8")
        params = parse_qs(qs)
        user_id = (params.get("userId") or [None])[0]
        try:
            return int(user_id) if user_id is not None else None
        except Exception:
            return None

    async def _peercount_get(self) -> int:
        r = get_redis()
        raw = r.get(_peercount_key(self.session_id))
        try:
            return int(raw) if raw is not None else 0
        except Exception:
            return 0

    async def _peercount_incr(self) -> int:
        r = get_redis()
        key = _peercount_key(self.session_id)
        val = r.incr(key)
        r.expire(key, PEERCOUNT_TTL_SEC)
        return int(val)

    async def _peercount_decr(self) -> int:
        r = get_redis()
        key = _peercount_key(self.session_id)
        val = r.decr(key)
        if val <= 0:
            r.delete(key)
            return 0
        r.expire(key, PEERCOUNT_TTL_SEC)
        return int(val)
