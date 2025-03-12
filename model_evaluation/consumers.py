import logging
from channels.generic.websocket import AsyncWebsocketConsumer
from asgiref.sync import async_to_sync
from channels.layers import get_channel_layer

logger = logging.getLogger(__name__)


class ProgressConsumer(AsyncWebsocketConsumer):
    """
    消费者类，用于处理进度消息的发送。
    支持多种消息类型，通过字典映射实现可扩展的消息处理逻辑。
    """

    #用于日志输出
    HANDLERS = {
        "progress": lambda data, task_id:
        logger.info(f"[Task {task_id}] Progress: {data['current']}/{data['total']} ({data['percent']}%)"),

        "record_result": lambda data, task_id:
        logger.info(f"[Task {task_id}] Record Result - "
                    f"ID: {data['record_id']}, "
                    f"Input: {data['input']}, "
                    f"Output: {data['output']}, "
                    f"Score: {data['score']}, "
                    f"Tokens: {data['tokens']}"),

        "error": lambda data, task_id:
        logger.error(f"[Task {task_id}] Error - "
                     f"Record ID: {data['record_id']}, "
                     f"Message: {data['message']}"),

        "summary": lambda data, task_id:
        logger.info(f"[Task {task_id}] Summary - "
                    f"Total Records: {data['total_records']}, "
                    f"Average Score: {data['average_score']}, "
                    f"Total Tokens: {data['total_tokens']}"),
    }

    #保存已存在的ws链接
    active_connections = {}

    #链接操作，
    async def connect(self):
        """建立WebSocket连接"""
        # 从URL路径中获取评估任务的唯一标识
        self.task_id = self.scope['url_route']['kwargs'].get('task_id', 'default')
        print("self.task_id为:", self.task_id)
        self.group_name = f'model_evaluation_{self.task_id}'

        if self.task_id in ProgressConsumer.active_connections:
            print("该任务已经有一个活跃连接")
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

    @staticmethod
    def send_message(message, task_id='default'):
        """
        发送进度消息（优化后版本）

        参数:
            message (dict): 包含 type 和 data 字段的消息对象
                - type (str): 消息类型（progress/record_result/error/summary）
                - data (dict): 具体消息内容
            task_id (str): 任务 ID
        """
        message_type = message.get("type")
        data = message.get("data", {})

        #日志输出
        handler = ProgressConsumer.HANDLERS.get(message_type)
        if handler:
            handler(data, task_id)
        else:
            logger.warning(f"[Task {task_id}] Unknown message type: {message_type}")

        #ws发送
        channel_layer = get_channel_layer()
        group_name = f'model_evaluation_{task_id}'

        # 使用async_to_sync将异步调用转换为同步调用
        async_to_sync(channel_layer.group_send)(
            group_name,
            {
                'type': message_type,
                'message': data
            }
        )

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