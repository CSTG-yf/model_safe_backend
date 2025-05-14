from channels.generic.websocket import AsyncWebsocketConsumer
import json
from asgiref.sync import async_to_sync
from channels.layers import get_channel_layer

class QuestionBankConsumer(AsyncWebsocketConsumer):
    """
    WebSocket消费者，用于向前端实时推送评估进度
    """
    
    # 存储所有活跃连接的字典
    active_connections = {}
    
    async def connect(self):
        """建立WebSocket连接"""
        # 从URL路径中获取评估任务的唯一标识
        self.project_id = self.scope['url_route']['kwargs'].get('project_id', 0)
        print("self.project_id为:", self.project_id)
        self.group_name = f'{self.project_id}'
        
        if self.project_id in ProgressConsumer.active_connections:
            print("该任务已经有一个活跃连接")
            await self.close()
            return


        # 将当前连接加入到对应的组
        await self.channel_layer.group_add(
            self.group_name,
            self.channel_name
        )
        
        # 存储连接实例
        ProgressConsumer.active_connections[self.project_id] = self
        
        # 接受WebSocket连接
        await self.accept()
    
    async def disconnect(self, close_code):
        """断开WebSocket连接"""
        # 从组中移除连接
        await self.channel_layer.group_discard(
            self.group_name,
            self.channel_name
        )
        
        # 移除存储的连接实例
        if self.project_id in ProgressConsumer.active_connections:
            del ProgressConsumer.active_connections[self.project_id]
    
    async def receive(self, text_data):
        """接收前端发送的消息"""
        # 解析接收到的JSON数据
        data = json.loads(text_data)
        
    @classmethod
    def send_message(cls, message, progress, tag, project_id=0):
        """
        同步方法，用于从其他地方发送消息到WebSocket
        
        Args:
            message: 要发送的消息内容
            project_id: 任务ID，用于标识发送目标
        """
        channel_layer = get_channel_layer()
        group_name = f'{project_id}'
        
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