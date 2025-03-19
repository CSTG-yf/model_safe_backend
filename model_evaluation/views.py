from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.utils.decorators import method_decorator
from django.views import View
import json
import logging
from typing import Dict, Any, List

from question_bank.models import EvalQuestions
from .service import EvaluatorService
from django.conf import settings
from .utils import run_full_evaluation
from .models import EvaluationBatch, EvaluationRecord, ModelEvaluationHALUCINATION_TOXICITY

logger = logging.getLogger(__name__)

def get_evaluation_halucination_toxicity(request, model_name):
    """
        获取特定模型的评估结果
        """
    try:
        result = ModelEvaluationHALUCINATION_TOXICITY.objects.get(model_name=model_name)
        data = {
            'status': 'success',
            'model_name': model_name,
            'hallucination_accuracy': result.hallucination_accuracy,
            'toxicity_accuracy': result.toxicity_accuracy,
            'has_result': True
        }

    except ModelEvaluationHALUCINATION_TOXICITY.DoesNotExist:
        data = {
            'status': 'success',
            'model_name': model_name,
            'has_result': False,
            'message': '模型评估结果不存在'
        }

    return JsonResponse(data)


@csrf_exempt
def trigger_evaluation_halucination_toxicity(request, model_name):
    """
    触发指定模型的评估
    """
    if request.method != 'POST':
        return JsonResponse({
            'status': 'error',
            'message': '只接受POST请求'
        }, status=405)

    try:

        api_key = settings.MODEL_API_KEY,
        base_url = settings.MODEL_BASE_URL,
        model_name = settings.MODEL_NAME,
        sample_size = 100


        result = run_full_evaluation(api_key, base_url, model_name, sample_size)

        # 返回结果
        return JsonResponse({
            'status': 'success',
            'model_name': model_name,
            'hallucination_accuracy': result.hallucination_accuracy,
            'toxicity_accuracy': result.toxicity_accuracy,
            'average_accuracy': (result.hallucination_accuracy + result.toxicity_accuracy) / 2
            if result.hallucination_accuracy is not None and result.toxicity_accuracy is not None
            else None
        })

    except Exception as e:
        return JsonResponse({
            'status': 'error',
            'message': str(e)
        }, status=500)


@method_decorator(csrf_exempt, name='dispatch')
class EvaluationTaskView(View):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        # 从设置中获取API配置
        self.evaluator_service = EvaluatorService(
            api_key=settings.MODEL_API_KEY,
            base_url=settings.MODEL_BASE_URL,
            model_name=settings.MODEL_NAME,
            eval_api_key=settings.EVAL_MODEL_API_KEY,
            eval_base_url=settings.EVAL_MODEL_BASE_URL,
            eval_model_name=settings.EVAL_MODEL_NAME
        )

    def post(self, request, *args, **kwargs):
        """创建新的评估任务"""
        try:
            data = json.loads(request.body)
            exam_title = data.get('exam_title')
            batch_name = data.get('batch_name', f"Evaluation of {exam_title}")  # 获取批次名称

            if not exam_title:
                return JsonResponse({'error': '必须提供exam_title'}, status=400)

            try:
                question_bank = EvalQuestions.objects.get(exam_title=exam_title)
            except EvalQuestions.DoesNotExist:
                return JsonResponse({'error': f'题库 {exam_title} 不存在'}, status=404)

            questions_data = self._prepare_questions_data(question_bank.questions)

            task_id = self.evaluator_service.get_new_task_id()
            # 创建评估批次并传递给服务
            batch = EvaluationBatch.objects.create(
                name=batch_name,
                total_records=len(questions_data)
            )

            success = self.evaluator_service.start_evaluation_task(
                task_id,
                questions_data,
                batch_id=batch.id  # 传递批次ID
            )

            if success:
                return JsonResponse({
                    'task_id': task_id,
                    'batch_id': batch.id,
                    'status': 'started',
                    'message': '评估任务已启动'
                })
            else:
                # 如果启动失败，删除刚创建的批次
                batch.delete()
                return JsonResponse({'error': '无法启动评估任务'}, status=500)

        except json.JSONDecodeError:
            return JsonResponse({'error': '无效的JSON格式'}, status=400)
        except Exception as e:
            logger.exception(f"创建评估任务时出错: {str(e)}")
            return JsonResponse({'error': f'服务器错误: {str(e)}'}, status=500)

    def get(self, request, *args, **kwargs):
        task_id = request.GET.get('task_id')
        batch_id = request.GET.get('batch_id')  # 添加批次ID参数

        if not task_id and not batch_id:
            return JsonResponse({'error': '必须提供task_id或batch_id参数'}, status=400)

        action = request.GET.get('action', 'status')

        # 通过批次ID查询
        if batch_id and not task_id:
            try:
                batch_id = int(batch_id)
                batch = EvaluationBatch.objects.get(id=batch_id)

                if action == 'status':
                    records = EvaluationRecord.objects.filter(batch_id=batch_id)
                    return JsonResponse({
                        'batch_id': batch.id,
                        'name': batch.name,
                        'total_records': batch.total_records,
                        'completed_records': records.count(),
                        'average_score': batch.average_score,
                        'total_tokens': batch.total_tokens,
                        'completed': batch.completed,
                        'created_at': batch.created_at.isoformat()
                    })

                elif action == 'results':
                    records = EvaluationRecord.objects.filter(batch_id=batch_id)
                    results = [{
                        'record_id': record.record_id,
                        'input': record.input,
                        'output': record.output,
                        'score': record.score,
                        'tokens': record.tokens,
                        'created_at': record.created_at.isoformat()
                    } for record in records]

                    return JsonResponse({
                        'batch': {
                            'id': batch.id,
                            'name': batch.name,
                            'average_score': batch.average_score,
                            'total_tokens': batch.total_tokens,
                            'completed': batch.completed
                        },
                        'results': results
                    })

                else:
                    return JsonResponse({'error': f'不支持对批次执行的操作: {action}'}, status=400)

            except EvaluationBatch.DoesNotExist:
                return JsonResponse({'error': f'批次 {batch_id} 不存在'}, status=404)
            except ValueError:
                return JsonResponse({'error': 'batch_id必须是整数'}, status=400)
            except Exception as e:
                logger.exception(f"查询批次时出错: {str(e)}")
                return JsonResponse({'error': f'服务器错误: {str(e)}'}, status=500)

        # 原有的task_id查询逻辑
        if action == 'status':
            status = self.evaluator_service.get_task_status(task_id)
            # 尝试添加批次信息
            try:
                batch = self.evaluator_service.get_task_batch(task_id)
                if batch:
                    status['batch'] = {
                        'id': batch.id,
                        'name': batch.name,
                        'completed': batch.completed
                    }
            except Exception:
                pass
            return JsonResponse(status)

        elif action == 'results':
            results = self.evaluator_service.get_task_results(task_id)
            if results is not None:
                return JsonResponse({'results': results})
            else:
                return JsonResponse({'error': '任务结果不可用'}, status=404)

        elif action == 'cancel':
            success = self.evaluator_service.cancel_task(task_id)
            if success:
                return JsonResponse({'status': 'cancelled'})
            else:
                return JsonResponse({'error': '无法取消任务'}, status=400)

        elif action == 'cleanup':
            success = self.evaluator_service.cleanup_task(task_id)
            return JsonResponse({'success': success})

        else:
            return JsonResponse({'error': f'不支持的操作: {action}'}, status=400)

    def _prepare_questions_data(self, questions: List[Dict[str, Any]]) -> List[List]:
        prepared_data = []

        for q in questions:
            question_entry = [
                q.get("question_id"),
                q.get("source", ""),
                q.get("content_type", ""),
                q.get("question_type", ""),
                q.get("question"),
                q.get("options", []),
                q.get("answer", ""),
                q.get("scoring_criteria", "")
            ]
            prepared_data.append(question_entry)

        return prepared_data