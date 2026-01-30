# app/matches/consumers.py
import json
import hashlib
from urllib.parse import parse_qs

from channels.generic.websocket import AsyncJsonWebsocketConsumer
from django.contrib.auth import get_user_model
from rest_framework_simplejwt.tokens import UntypedToken
from rest_framework_simplejwt.exceptions import InvalidToken, TokenError

from app.common.redis_client import get_redis
from asgiref.sync import sync_to_async

PEERCOUNT_TTL_SEC = 60 * 30  # 30분


def _peercount_key(session_id: str) -> str:
    return f"ws:peerCount:{session_id}"


def _make_ephemeral_user_id(channel_name: str) -> int:
    h = hashlib.sha256(channel_name.encode("utf-8")).hexdigest()
    return int(h[:8], 16)  # 32bit 정수


def _extract_token_from_scope(scope) -> str:
    """
    ws://<host>/ws/signaling/<sessionId>/?token=<ACCESS_TOKEN>
    """
    raw_qs = scope.get("query_string", b"")
    try:
        qs = raw_qs.decode("utf-8")
    except Exception:
        qs = ""
    params = parse_qs(qs)
    token_list = params.get("token") or []
    return token_list[0] if token_list else ""


@sync_to_async
def _get_user_by_id(user_id: int):
    User = get_user_model()
    return User.objects.filter(id=user_id, is_active=True).first()


async def _get_user_from_jwt_async(token: str):
    if not token:
        return None

    try:
        UntypedToken(token)
        payload = UntypedToken(token).payload
        user_id = payload.get("user_id")
        if not user_id:
            return None
    except Exception:
        return None

    return await _get_user_by_id(user_id)


class SignalingConsumer(AsyncJsonWebsocketConsumer):
    """
    WS Signaling Protocol (Front spec)
      - URL: ws://<host>/ws/signaling/<sessionId>/?token=<ACCESS_TOKEN>
      - Envelope:
        {
          "type": "...",
          "sessionId": "...",
          "fromUserId": 123,
          "payload": {...}
        }
    """

    async def connect(self):
        self.session_id = self.scope["url_route"]["kwargs"]["session_id"]
        self.room_group_name = f"session_{self.session_id}"

        #  0) 쿼리스트링 token 인증 (accept 전에!)
        token = _extract_token_from_scope(self.scope)
        user = await _get_user_from_jwt_async(token)

        if not user:
            # 4401/4403 같은 커스텀 close code 사용 가능
            await self.close(code=4401)
            return

        self.user = user
        self.user_id = user.id  # ✅ fromUserId = 실제 userId

        await self.channel_layer.group_add(self.room_group_name, self.channel_name)
        await self.accept()

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
                "type": "peer.joined",
                "sessionId": self.session_id,
                "fromUserId": self.user_id,
                "payload": {"peerCount": peer_count},
            },
        )

    async def disconnect(self, close_code):
        room = getattr(self, "room_group_name", None)
        session_id = getattr(self, "session_id", None)
        user_id = getattr(self, "user_id", None)
        if not room or not session_id or not user_id:
            return

        peer_count = await self._peercount_decr()

        await self.channel_layer.group_send(
            room,
            {
                "type": "peer.left",
                "sessionId": session_id,
                "fromUserId": user_id,
                "payload": {"peerCount": peer_count},
            },
        )

        await self.channel_layer.group_discard(room, self.channel_name)

    async def receive(self, text_data=None, bytes_data=None):
        if not text_data:
            return

        try:
            data = json.loads(text_data)
        except Exception:
            return

        msg_type = data.get("type")

        # join: connect에서 이미 처리했으니 ack만
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

        # leave: 정상 종료 이벤트
        if msg_type == "leave":
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

        # offer/answer/ice만 중계 (Envelope 강제 통일)
        if msg_type in ("offer", "answer", "ice"):
            payload = data.get("payload") or {}

            await self.channel_layer.group_send(
                self.room_group_name,
                {
                    "type": "signal.message",
                    "envelope": {
                        "type": msg_type,
                        "sessionId": self.session_id,
                        "fromUserId": self.user_id,
                        "payload": payload,
                    },
                },
            )

    async def signal_message(self, event):
        await self.send_json(event.get("envelope") or {})

    async def peer_joined(self, event):
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
