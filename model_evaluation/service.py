import logging
import uuid
from typing import List, Dict, Any, Optional, Tuple
from concurrent.futures import ThreadPoolExecutor

from .utils import Evaluator

from .consumers import ProgressConsumer

logger = logging.getLogger(__name__)


class EvaluatorService:
    def __init__(self, api_key: str, base_url: str, model_name: str,
                 eval_api_key: str, eval_base_url: str, eval_model_name: str):
        self.api_key = api_key
        self.base_url = base_url
        self.model_name = model_name
        self.eval_api_key = eval_api_key
        self.eval_base_url = eval_base_url
        self.eval_model_name = eval_model_name
        self.active_tasks = {}
        self.executor = ThreadPoolExecutor(max_workers=5)

    def create_evaluator(self, task_id: str) -> Evaluator:
        return Evaluator(
            api_key=self.api_key,
            base_url=self.base_url,
            model_name=self.model_name,
            eval_api_key=self.eval_api_key,
            eval_base_url=self.eval_base_url,
            eval_model_name=self.eval_model_name,
            task_id=task_id,
            logger_name=f"evaluator.task.{task_id}"
        )

    def evaluate_question(self, question_data: List) -> Optional[Tuple]:
        try:
            task_id = f"single_{question_data[0]}"
            evaluator = self.create_evaluator(task_id)
            result = evaluator.evaluate(question_data)
            return result
        except Exception as e:
            logger.exception(f"评估问题 {question_data[0]} 时出错: {str(e)}")
            return None

    def start_evaluation_task(self, task_id: str, questions: List[List]) -> bool:
        if task_id in self.active_tasks:
            logger.warning(f"任务ID {task_id} 已存在")
            return False

        try:
            evaluator = self.create_evaluator(task_id)
            future = self.executor.submit(evaluator.evaluate_multiple, questions)
            self.active_tasks[task_id] = {
                'evaluator': evaluator,
                'future': future,
                'status': 'running'
            }
            return True
        except Exception as e:
            logger.exception(f"启动评估任务 {task_id} 时出错: {str(e)}")

            ProgressConsumer.send_message({
                "type": "error",
                "data": {
                    "record_id": "system",
                    "message": f"启动评估任务失败: {str(e)}"
                }
            }, task_id)

            return False

    def get_task_status(self, task_id: str) -> Dict[str, Any]:
        if task_id not in self.active_tasks:
            return {'status': 'not_found'}

        task = self.active_tasks[task_id]

        if task['future'].done():
            if task['future'].exception():
                return {
                    'status': 'error',
                    'error': str(task['future'].exception())
                }

            if task['status'] == 'running':
                task['status'] = 'completed'

            return {
                'status': task['status'],
                'results': task['evaluator'].get_results()
            }
        else:
            return {'status': 'running'}

    def cancel_task(self, task_id: str) -> bool:
        if task_id not in self.active_tasks:
            return False

        try:
            task = self.active_tasks[task_id]
            cancelled = task['future'].cancel()

            if cancelled:
                task['status'] = 'cancelled'

                ProgressConsumer.send_message({
                    "type": "progress",
                    "data": {
                        "current": 0,
                        "total": 0,
                        "percent": 0,
                        "status": "cancelled"
                    }
                }, task_id)

                return True
            else:
                return False
        except Exception as e:
            logger.exception(f"取消任务 {task_id} 时出错: {str(e)}")
            return False

    def get_task_results(self, task_id: str) -> Optional[List[Dict[str, Any]]]:
        status = self.get_task_status(task_id)

        if status['status'] == 'completed':
            return status['results']

        return None

    def cleanup_task(self, task_id: str) -> bool:
        if task_id in self.active_tasks:
            del self.active_tasks[task_id]
            return True
        return False

    def get_new_task_id(self) -> str:
        return f"task_{uuid.uuid4()}"