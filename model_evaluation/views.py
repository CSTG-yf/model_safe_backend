from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.utils.decorators import method_decorator
from django.views import View
from django.db.models import Q
import json
import logging
from typing import Dict, Any, List
from datetime import datetime

from question_bank.models import EvalQuestions
from .service import EvaluatorService
from django.conf import settings
from .utils import run_full_evaluation
from .models import EvaluationBatch, EvaluationRecord, ModelEvaluationHALUCINATION_TOXICITY, ModelAPI
from .serializers import ModelAPISerializer

logger = logging.getLogger(__name__)


@method_decorator(csrf_exempt, name='dispatch')
class ModelAPIView(View):
    """
    处理模型API配置的视图
    """
    def get(self, request, *args, **kwargs):
        """获取API配置列表或特定配置"""
        model_name = kwargs.get('model_name')
        
        if model_name:
            try:
                model_api = ModelAPI.objects.get(name=model_name)
                serializer = ModelAPISerializer(model_api)
                return JsonResponse(serializer.data)
            except ModelAPI.DoesNotExist:
                return JsonResponse({
                    'error': f'模型 {model_name} 的API配置不存在'
                }, status=404)
        
        # 获取所有配置列表
        model_apis = ModelAPI.objects.all()
        serializer = ModelAPISerializer(model_apis, many=True)
        return JsonResponse({
            'models': serializer.data
        })

    def post(self, request, *args, **kwargs):
        """添加新的API配置"""
        try:
            data = json.loads(request.body)
            serializer = ModelAPISerializer(data=data)
            
            if serializer.is_valid():
                # 检查是否已存在相同名称的配置
                if ModelAPI.objects.filter(name=data['name']).exists():
                    return JsonResponse({
                        'error': f'模型 {data["name"]} 的API配置已存在'
                    }, status=400)
                
                serializer.save()
                return JsonResponse({
                    'message': '成功添加API配置',
                    'data': serializer.data
                }, status=201)
            
            return JsonResponse({
                'error': serializer.errors
            }, status=400)
            
        except json.JSONDecodeError:
            return JsonResponse({
                'error': '无效的JSON格式'
            }, status=400)
        except Exception as e:
            logger.exception(f"添加API配置时出错: {str(e)}")
            return JsonResponse({
                'error': f'服务器错误: {str(e)}'
            }, status=500)

    def put(self, request, *args, **kwargs):
        """更新API配置"""
        model_name = kwargs.get('model_name')
        if not model_name:
            return JsonResponse({
                'error': '必须指定模型名称'
            }, status=400)

        try:
            model_api = ModelAPI.objects.get(name=model_name)
            data = json.loads(request.body)
            serializer = ModelAPISerializer(model_api, data=data, partial=True)
            
            if serializer.is_valid():
                serializer.save()
                return JsonResponse({
                    'message': '成功更新API配置',
                    'data': serializer.data
                })
            
            return JsonResponse({
                'error': serializer.errors
            }, status=400)
            
        except ModelAPI.DoesNotExist:
            return JsonResponse({
                'error': f'模型 {model_name} 的API配置不存在'
            }, status=404)
        except json.JSONDecodeError:
            return JsonResponse({
                'error': '无效的JSON格式'
            }, status=400)
        except Exception as e:
            logger.exception(f"更新API配置时出错: {str(e)}")
            return JsonResponse({
                'error': f'服务器错误: {str(e)}'
            }, status=500)

    def delete(self, request, *args, **kwargs):
        """删除API配置"""
        model_name = kwargs.get('model_name')
        if not model_name:
            return JsonResponse({
                'error': '必须指定模型名称'
            }, status=400)

        try:
            model_api = ModelAPI.objects.get(name=model_name)
            model_api.delete()
            return JsonResponse({
                'message': f'成功删除模型 {model_name} 的API配置'
            })
        except ModelAPI.DoesNotExist:
            return JsonResponse({
                'error': f'模型 {model_name} 的API配置不存在'
            }, status=404)
        except Exception as e:
            logger.exception(f"删除API配置时出错: {str(e)}")
            return JsonResponse({
                'error': f'服务器错误: {str(e)}'
            }, status=500)


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
        # 从数据库获取模型配置
        try:
            model_api = ModelAPI.objects.get(name=model_name)
        except ModelAPI.DoesNotExist:
            return JsonResponse({
                'status': 'error',
                'message': f'模型 {model_name} 的API配置不存在'
            }, status=404)

        # 从请求中获取sample_size，默认为100
        data = json.loads(request.body) if request.body else {}
        sample_size = data.get('sample_size', 100)

        result = run_full_evaluation(
            api_key=model_api.api_key,
            base_url=model_api.base_url,
            model_name=model_api.name,
            sample_size=sample_size
        )

        # 返回结果
        return JsonResponse({
            'status': 'success',
            'model_name': model_name,
            'hallucination_accuracy': result.hallucination_accuracy,
            'toxicity_accuracy': result.toxicity_accuracy,
        })

    except json.JSONDecodeError:
        return JsonResponse({
            'status': 'error',
            'message': '无效的JSON格式'
        }, status=400)
    except Exception as e:
        logger.exception(f"评估模型时出错: {str(e)}")
        return JsonResponse({
            'status': 'error',
            'message': str(e)
        }, status=500)


@method_decorator(csrf_exempt, name='dispatch')
class EvaluationTaskView(View):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        # 从数据库中获取API配置
        try:
            model_api = ModelAPI.objects.get(name=settings.DEFAULT_MODEL_NAME)
            eval_model_api = ModelAPI.objects.get(name=settings.DEFAULT_EVAL_MODEL_NAME)
            
            self.evaluator_service = EvaluatorService(
                api_key=model_api.api_key,
                base_url=model_api.base_url,
                model_name=model_api.name,
                eval_api_key=eval_model_api.api_key,
                eval_base_url=eval_model_api.base_url,
                eval_model_name=eval_model_api.name
            )
        except ModelAPI.DoesNotExist as e:
            logger.error(f"无法找到所需的模型API配置: {str(e)}")
            self.evaluator_service = None
        except Exception as e:
            logger.error(f"初始化评估服务时出错: {str(e)}")
            self.evaluator_service = None

    def post(self, request, *args, **kwargs):
        """创建新的评估任务"""
        if not self.evaluator_service:
            return JsonResponse({
                'error': '评估服务未正确初始化，请确保已配置相应的模型API'
            }, status=500)

        try:
            data = json.loads(request.body)
            exam_title = data.get('exam_title')
            batch_name = data.get('batch_name', f"Evaluation of {exam_title}")
            # 允许在请求中指定使用的模型
            model_name = data.get('model_name', settings.DEFAULT_MODEL_NAME)
            eval_model_name = data.get('eval_model_name', settings.DEFAULT_EVAL_MODEL_NAME)

            # 如果请求中指定了不同的模型，重新初始化服务
            if (model_name != self.evaluator_service.model_name or 
                eval_model_name != self.evaluator_service.eval_model_name):
                try:
                    model_api = ModelAPI.objects.get(name=model_name)
                    eval_model_api = ModelAPI.objects.get(name=eval_model_name)
                    self.evaluator_service = EvaluatorService(
                        api_key=model_api.api_key,
                        base_url=model_api.base_url,
                        model_name=model_api.name,
                        eval_api_key=eval_model_api.api_key,
                        eval_base_url=eval_model_api.base_url,
                        eval_model_name=eval_model_api.name
                    )
                except ModelAPI.DoesNotExist:
                    return JsonResponse({
                        'error': f'找不到指定的模型配置: {model_name} 或 {eval_model_name}'
                    }, status=400)

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
                # batch_id=batch.id
            )

            if success:
                return JsonResponse({
                    'task_id': task_id,
                    'batch_id': batch.id,
                    'status': 'started',
                    'message': '评估任务已启动',
                    'model_info': {
                        'model_name': self.evaluator_service.model_name,
                        'eval_model_name': self.evaluator_service.eval_model_name
                    }
                })
            else:
                batch.delete()
                return JsonResponse({'error': '无法启动评估任务'}, status=500)

        except json.JSONDecodeError:
            return JsonResponse({'error': '无效的JSON格式'}, status=400)
        except Exception as e:
            logger.exception(f"创建评估任务时出错: {str(e)}")
            return JsonResponse({'error': f'服务器错误: {str(e)}'}, status=500)

    def get(self, request, task_id=None, *args, **kwargs):
        """获取任务状态或结果"""
        if not task_id:
            return JsonResponse({'error': '必须提供task_id参数'}, status=400)

        action = request.GET.get('action', 'status')

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
            try:
                page = int(request.GET.get('page', 1))
                page_size = int(request.GET.get('page_size', 10))
                if page < 1:
                    return JsonResponse({'error': 'page参数必须大于0'}, status=400)
                if page_size < 1 or page_size > 100:
                    return JsonResponse({'error': 'page_size参数必须在1-100之间'}, status=400)
            except ValueError:
                return JsonResponse({'error': 'page和page_size参数必须是整数'}, status=400)
                
            results = self.evaluator_service.get_task_results(task_id, page=page, page_size=page_size)
            if results is not None:
                return JsonResponse(results)
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


class EvaluationRecordView(View):
    """评估记录查询视图"""
    
    def get(self, request, record_id, *args, **kwargs):
        """获取单个评估记录详情"""
        try:
            # 获取记录和关联的批次信息
            record = EvaluationRecord.objects.get(record_id=record_id)
            batch = EvaluationBatch.objects.get(id=record.batch_id)

            # 返回详细信息
            return JsonResponse({
                'record_id': record.record_id,
                'batch': {
                    'id': batch.id,
                    'name': batch.name,
                    'created_at': batch.created_at.isoformat()
                },
                'input': record.input,
                'output': record.output,
                'score': record.score,
                'tokens': record.tokens,
                'created_at': record.created_at.isoformat()
            })

        except EvaluationRecord.DoesNotExist:
            return JsonResponse({
                'error': f'记录 {record_id} 不存在'
            }, status=404)
        except Exception as e:
            logger.exception(f"获取评估记录详情时出错: {str(e)}")
            return JsonResponse({
                'error': f'服务器错误: {str(e)}'
            }, status=500)