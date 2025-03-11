import os
from celery import Celery

# 设置默认的 Django settings 模块
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'ai_evaluation.settings')

app = Celery('ai_evaluation')

app.config_from_object('ai_evaluation.settings', namespace='CELERY')

app.conf.update(
    broker_url='redis://localhost:6379/0',
    result_backend='redis://localhost:6379/0',
    accept_content=['json'],
    task_serializer='json',
    result_serializer='json',
    timezone='Asia/Shanghai'
)

# 自动发现任务
# app.autodiscover_tasks()

@app.task(bind=True)
def debug_task(self):
    print(f'Request: {self.request!r}')