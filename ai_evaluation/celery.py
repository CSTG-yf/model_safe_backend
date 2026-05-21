import os
from celery import Celery

# 设置默认的 Django settings 模块
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'ai_evaluation.settings')

app = Celery('ai_evaluation')

app.config_from_object('ai_evaluation.settings', namespace='CELERY')

app.conf.update(
    broker_url=os.environ.get('CELERY_BROKER_URL', os.environ.get('REDIS_URL', 'redis://127.0.0.1:6379/0')),
    result_backend=os.environ.get('CELERY_RESULT_BACKEND', os.environ.get('REDIS_URL', 'redis://127.0.0.1:6379/0')),
    accept_content=['json'],
    task_serializer='json',
    result_serializer='json',
    timezone=os.environ.get('DJANGO_TIME_ZONE', 'Asia/Shanghai'),
    task_track_started=True,
    task_time_limit=int(os.environ.get('CELERY_TASK_TIME_LIMIT', '3600')),
    task_soft_time_limit=int(os.environ.get('CELERY_TASK_SOFT_TIME_LIMIT', '3300')),
)

# 自动发现任务
app.autodiscover_tasks()

@app.task(bind=True)
def debug_task(self):
    app.log.get_default_logger().info('Request: %r', self.request)
