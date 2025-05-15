from asgiref.sync import async_to_sync
from channels.generic.websocket import AsyncWebsocketConsumer
import json

from channels.layers import get_channel_layer


class EvaluationConsumer(AsyncWebsocketConsumer):
    # 存储所有活跃连接的字典
    active_connections = {}

    async def connect(self):
        self.evaluation_batch = self.scope['url_route']['kwargs'].get('evaluation_batch', 0)
        self.group_name = f"evaluation_{self.evaluation_batch}"

        if self.evaluation_batch in EvaluationConsumer.active_connections:
            print("该任务已经有一个活跃连接")
            await self.close()
            return

        # 将当前连接加入到对应的组
        await self.channel_layer.group_add(
            self.group_name,
            self.channel_name
        )

        # 存储连接实例
        EvaluationConsumer.active_connections[self.evaluation_batch] = self

        # 接受WebSocket连接
        await self.accept()

    async def disconnect(self, close_code):
        await self.channel_layer.group_discard(self.group_name, self.channel_name)
        # 移除存储的连接实例
        if self.evaluation_batch in EvaluationConsumer.active_connections:
            del EvaluationConsumer.active_connections[self.evaluation_batch]

    async def send_message(self,evaluation_batch, event):
        channel_layer = get_channel_layer()
        group_name = f'evaluation_{evaluation_batch}'
        async_to_sync(channel_layer.group_send)(
            group_name,
            {
                'type': 'send_progress',
                'message': event['message'],
                'progress': event['progress'],
                'tag': event['tag'],
            }
        )
        