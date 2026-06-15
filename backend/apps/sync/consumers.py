import json

from channels.generic.websocket import AsyncWebsocketConsumer
from rest_framework_simplejwt.tokens import UntypedToken
from rest_framework_simplejwt.exceptions import InvalidToken, TokenError


class TaskConsumer(AsyncWebsocketConsumer):
    """Diffuse les mutations de tâches aux autres connexions du même utilisateur."""

    async def connect(self):
        token = self._get_token()
        if not token:
            await self.close()
            return
        try:
            UntypedToken(token)
        except (InvalidToken, TokenError):
            await self.close()
            return
        user_id = self._get_user_id(token)
        self.group_name = f"user_{user_id}"
        await self.channel_layer.group_add(self.group_name, self.channel_name)
        await self.accept()

    async def disconnect(self, close_code):
        if hasattr(self, "group_name"):
            await self.channel_layer.group_discard(self.group_name, self.channel_name)

    async def receive(self, text_data):
        data = json.loads(text_data)
        # Le client envoie ses mutations; on les diffuse aux autres connexions.
        await self.channel_layer.group_send(
            self.group_name,
            {"type": "task.mutation", "data": data, "sender": self.channel_name},
        )

    async def task_mutation(self, event):
        # Ne pas renvoyer au sender lui-même
        if event.get("sender") != self.channel_name:
            await self.send(text_data=json.dumps(event["data"]))

    def _get_token(self):
        qs = self.scope.get("query_string", b"").decode()
        for part in qs.split("&"):
            if part.startswith("token="):
                return part[6:]
        headers = dict(self.scope.get("headers", []))
        auth = headers.get(b"authorization", b"").decode()
        if auth.startswith("Bearer "):
            return auth[7:]
        return None

    def _get_user_id(self, token):
        from rest_framework_simplejwt.tokens import AccessToken
        t = AccessToken(token)
        return t["user_id"]
