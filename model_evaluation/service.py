import logging
import uuid
from typing import List, Dict, Any, Optional
from concurrent.futures import ThreadPoolExecutor
import threading

from .utils import Evaluator
from .consumers import ProgressConsumer
from .models import EvaluationBatch, EvaluationRecord

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
        self._task_locks = {}

    def create_evaluator(self, task_id: str) -> Evaluator:
        """创建评估器实例"""
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

    def _run_evaluation_task(self, task_id: str, evaluator: Evaluator, questions_data: List[List], batch_id: int):
        """在后台线程中运行评估任务"""
        try:
            total_questions = len(questions_data)
            current_progress = 0

            # 发送任务开始消息
            ProgressConsumer.send_message({
                "type": "progress",
                "data": {
                    "current": current_progress,
                    "total": total_questions,
                    "percent": 0
                }
            }, task_id)

            # 存储批次信息
            self.active_tasks[task_id] = batch_id

            # 处理每个问题
            for question_data in questions_data:
                if task_id not in self.active_tasks:  # 检查任务是否被取消
                    logger.info(f"Task {task_id} was cancelled")
                    return

                # 评估单个问题
                result = evaluator.evaluate(question_data)
                if result:
                    record_id, prompt, response, score, tokens = result
                    
                    # 更新进度
                    current_progress += 1
                    ProgressConsumer.send_message({
                        "type": "progress",
                        "data": {
                            "current": current_progress,
                            "total": total_questions,
                            "percent": (current_progress / total_questions) * 100
                        }
                    }, task_id)

            # 更新批次状态
            batch = EvaluationBatch.objects.get(id=batch_id)
            records = EvaluationRecord.objects.filter(batch_id=batch_id)
            if records.exists():
                batch.average_score = sum(r.score for r in records) / records.count()
                batch.total_tokens = sum(r.tokens for r in records)
            batch.completed = True
            batch.save()

            # 发送完成消息
            ProgressConsumer.send_message({
                "type": "summary",
                "data": {
                    "total_records": batch.total_records,
                    "average_score": batch.average_score,
                    "total_tokens": batch.total_tokens,
                    "completed": True
                }
            }, task_id)

        except Exception as e:
            logger.exception(f"Task {task_id} failed: {str(e)}")
            ProgressConsumer.send_message({
                "type": "error",
                "data": {
                    "message": str(e)
                }
            }, task_id)
        finally:
            if task_id in self._task_locks:
                del self._task_locks[task_id]

    def start_evaluation_task(self, task_id: str, questions_data: List[List], batch_id: int) -> bool:
        """启动评估任务"""
        try:
            if task_id in self.active_tasks:
                return False

            # 创建任务锁
            self._task_locks[task_id] = threading.Lock()
            
            # 创建评估器
            evaluator = self.create_evaluator(task_id)
            
            # 在线程池中启动任务
            self.executor.submit(
                self._run_evaluation_task,
                task_id,
                evaluator,
                questions_data,
                batch_id
            )
            
            return True

        except Exception as e:
            logger.exception(f"Failed to start task {task_id}: {str(e)}")
            if task_id in self._task_locks:
                del self._task_locks[task_id]
            return False

    def get_task_status(self, task_id: str) -> Dict[str, Any]:
        """获取任务状态"""
        try:
            batch_id = self.active_tasks.get(task_id)
            if batch_id:
                batch = EvaluationBatch.objects.get(id=batch_id)
                records = EvaluationRecord.objects.filter(batch_id=batch_id)
                return {
                    'completed': batch.completed,
                    'total_records': batch.total_records,
                    'completed_records': records.count(),
                    'average_score': batch.average_score,
                    'total_tokens': batch.total_tokens
                }
        except Exception as e:
            logger.exception(f"Error getting task status: {str(e)}")
        return {'error': '无法获取任务状态'}

    def get_task_batch(self, task_id: str) -> Optional[EvaluationBatch]:
        """获取任务对应的批次"""
        try:
            batch_id = self.active_tasks.get(task_id)
            if batch_id:
                return EvaluationBatch.objects.get(id=batch_id)
        except Exception as e:
            logger.exception(f"Error getting task batch: {str(e)}")
        return None

    def get_task_results(self, task_id: str, page: int = 1, page_size: int = 10) -> Optional[Dict[str, Any]]:
        """获取任务结果
        
        Args:
            task_id: 任务ID
            page: 页码，从1开始
            page_size: 每页记录数
            
        Returns:
            包含任务结果、统计信息和分页信息的字典
        """
        try:
            batch_id = self.active_tasks.get(task_id)
            if not batch_id:
                return None
                
            # 获取批次信息
            batch = EvaluationBatch.objects.get(id=batch_id)
            
            # 获取所有记录
            all_records = EvaluationRecord.objects.filter(batch_id=batch_id)
            total_records = all_records.count()
            
            # 计算分页
            start = (page - 1) * page_size
            end = start + page_size
            records = all_records[start:end]
            
            # 计算统计信息
            total_tokens = sum(record.tokens for record in all_records)
            avg_score = sum(record.score for record in all_records) / total_records if total_records > 0 else 0
            
            return {
                'task_id': task_id,
                'batch': {
                    'id': batch.id,
                    'name': batch.name,
                    'created_at': batch.created_at.isoformat(),
                    'completed': batch.completed
                },
                'statistics': {
                    'total_records': total_records,
                    'total_tokens': total_tokens,
                    'average_score': round(avg_score, 4)
                },
                'pagination': {
                    'current_page': page,
                    'page_size': page_size,
                    'total_pages': (total_records + page_size - 1) // page_size
                },
                'records': [{
                    'record_id': record.record_id,
                    'input': record.input,
                    'output': record.output,
                    'score': record.score,
                    'tokens': record.tokens,
                    'created_at': record.created_at.isoformat()
                } for record in records]
            }
            
        except Exception as e:
            logger.exception(f"Error getting task results: {str(e)}")
            return None

    def cancel_task(self, task_id: str) -> bool:
        """取消任务"""
        try:
            if task_id in self.active_tasks:
                del self.active_tasks[task_id]
                ProgressConsumer.send_message({
                    "type": "progress",
                    "data": {
                        "status": "cancelled",
                        "message": "任务已取消"
                    }
                }, task_id)
                return True
        except Exception as e:
            logger.exception(f"Error cancelling task: {str(e)}")
        return False

    def cleanup_task(self, task_id: str) -> bool:
        """清理任务资源"""
        try:
            if task_id in self.active_tasks:
                del self.active_tasks[task_id]
            if task_id in self._task_locks:
                del self._task_locks[task_id]
            return True
        except Exception as e:
            logger.exception(f"Error cleaning up task: {str(e)}")
        return False

    def get_new_task_id(self) -> str:
        """生成新的任务ID"""
        return str(uuid.uuid4())