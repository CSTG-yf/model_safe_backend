from channels.generic.websocket import AsyncWebsocketConsumer
import json

class EvaluationConsumer(AsyncWebsocketConsumer):
    async def connect(self):
        self.group_name = f"evaluation_{self.scope['url_route']['kwargs']['evaluation_batch']}"
        await self.channel_layer.group_add(self.group_name, self.channel_name)
        await self.accept()

    async def disconnect(self, close_code):
        await self.channel_layer.group_discard(self.group_name, self.channel_name)

    async def send_message(self,evaluation_batch, event):
        async_to_sync(channel_layer.group_send)(
            evaluation_batch,
            {
                'type': 'send_progress',
                'message': event['message'],
                'progress': event['progress'],
                'tag': event['tag'],
            }
        )
        