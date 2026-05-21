from asgiref.sync import async_to_sync
from channels.generic.websocket import AsyncWebsocketConsumer
import json
import logging

from channels.layers import get_channel_layer


logger = logging.getLogger(__name__)


class EvaluationConsumer(AsyncWebsocketConsumer):
    # 存储所有活跃连接的字典
    active_connections = {}

    async def connect(self):
        self.evaluation_batch = self.scope['url_route']['kwargs'].get('evaluation_batch', 0)
        self.group_name = f"evaluation_{self.evaluation_batch}"

        if self.evaluation_batch in EvaluationConsumer.active_connections:
            logger.info("Evaluation websocket already active evaluation_batch=%s", self.evaluation_batch)
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
    
    async def send_progress(self, event):
        """
        处理并发送进度消息到WebSocket客户端
        
        Args:
            event: 包含消息内容的事件字典
        """
        # 从事件中提取数据
        message = event.get('message', '')
        progress = event.get('progress', 0)
        tag = event.get('tag', '')
        
        # 发送消息到WebSocket
        await self.send(text_data=json.dumps({
            'message': message,
            'progress': progress,
            'tag': tag
        }))

    @classmethod
    def send_message(cls, message, progress, tag, evaluation_batch=0):
        """
        同步方法，用于从其他地方发送消息到WebSocket
        
        Args:
            message: 要发送的消息内容
            progress: 进度值
            tag: 消息标签
            evaluation_batch: 评估批次ID，用于标识发送目标
        """
        channel_layer = get_channel_layer()
        group_name = f'evaluation_{evaluation_batch}'
        
        # 使用async_to_sync将异步调用转换为同步调用
        async_to_sync(channel_layer.group_send)(
            group_name,
            {
                'type': 'send_progress',
                'message': message,
                'progress': progress,
                'tag': tag
            }
        )
        
