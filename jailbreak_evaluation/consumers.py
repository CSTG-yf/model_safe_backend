from channels.generic.websocket import AsyncWebsocketConsumer
import json
from asgiref.sync import async_to_sync
from channels.layers import get_channel_layer
from threading import Lock
import logging
logger = logging.getLogger(__name__)

class ProgressConsumer(AsyncWebsocketConsumer):
    """
    WebSocket消费者，用于向前端实时推送评估进度
    """
    
    # 存储所有活跃连接的字典
    active_connections = {}
    
    async def connect(self):
        """建立WebSocket连接"""
        # 从URL路径中获取评估任务的唯一标识,task_id由project_id,model_name和ev_time共同决定
        self.task_id = self.scope['url_route']['kwargs'].get('task_id', 'default')
        logger.info("Jailbreak websocket connecting task_id=%s", self.task_id)
        self.group_name = f'jailbreak_evaluation_{self.task_id}'
        
        if self.task_id in ProgressConsumer.active_connections:
            logger.info("Jailbreak websocket already active task_id=%s", self.task_id)
            await self.close()
            return


        # 将当前连接加入到对应的组
        await self.channel_layer.group_add(
            self.group_name,
            self.channel_name
        )
        
        # 存储连接实例
        ProgressConsumer.active_connections[self.task_id] = self
        
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
        if self.task_id in ProgressConsumer.active_connections:
            del ProgressConsumer.active_connections[self.task_id]
    
    async def receive(self, text_data):
        """接收前端发送的消息"""
        # 解析接收到的JSON数据
        data = json.loads(text_data)
        
        # 处理接收到的消息（如果需要）

    
    async def send_progress(self, event):
        """发送进度消息到前端"""
        # 直接将消息发送到WebSocket
        await self.send(text_data=json.dumps(event['message']))
    

    _lock = Lock()  # 类级别的锁
    @classmethod
    def send_message(cls, message, task_id):
        with cls._lock:  # 确保同一时间只有一个线程发送消息
            try:
                """
                同步方法，用于从其他地方发送消息到WebSocket
                
                Args:
                    message: 要发送的消息内容
                    task_id: 任务ID，用于标识发送目标
                """
                channel_layer = get_channel_layer()
                group_name = f'jailbreak_evaluation_{task_id}'
                
                # 使用async_to_sync将异步调用转换为同步调用
                async_to_sync(channel_layer.group_send)(
                    group_name,
                    {
                        'type': 'send_progress',
                        'message': message
                    }
                )
                # logger.info(f"消息已提交到channel layer\n{message}")
            except Exception as e:
                # logger.error(f"发送消息到channel layer失败: {str(e)}", exc_info=True)
                logger.exception("Failed to send jailbreak websocket message: %s", e)
