from rest_framework import status
from rest_framework.response import Response
from django.core.cache import cache
from .models import EvaluationBatch

def update_evaluation_progress(project_id,evaluation_id, progress, message="正在生成题库", state="generating"):
    """
    更新题库生成进度并存入缓存
    """
    cache_key = f"evaluation_progress_{project_id}_{evaluation_id}"
    progress_data = {
        'progress': progress,
        'message': message,
        'state': state
    }
    # 设置缓存，过期时间为1小时
    cache.set(cache_key, progress_data, timeout=3600)
    return progress_data

def get_evaluation_progress(request,project_id):
    """
    获取评估进度
    """
    # 获取请求参数
    evaluation_id = request.query_params.get('evaluation_id')
    
    # 参数校验
    if not evaluation_id:
        return Response({"error": "请提供 evaluation_id"}, status=status.HTTP_400_BAD_REQUEST)
    
    try:
        # 构建缓存键
        cache_key = f"evaluation_progress_{project_id}_{evaluation_id}"
        
        # 获取进度信息
        progress_data = cache.get(cache_key)
        
        if progress_data is None:
            # 如果没有找到进度信息，可能是已经完成或尚未开始
            # 检查评估是否存在
            try:
                evaluation = EvaluationBatch.objects.get(id=evaluation_id)
                # 如果评估存在且有结果，则认为已完成
                if evaluation.total_samples > 0:
                    return Response({
                        'status': 'success',
                        'progress': 100,
                        'message': '评估已完成',
                        'state': 'completed',
                    }, status=status.HTTP_200_OK)
                else:
                    return Response({
                        'status': 'info',
                        'progress': 0,
                        'message': '评估尚未开始或进度信息不可用',
                        'state': 'not_started'
                    }, status=status.HTTP_200_OK)
            except EvaluationBatch.DoesNotExist:
                return Response({
                    'status': 'error',
                    'message': '评估不存在',
                }, status=status.HTTP_404_NOT_FOUND)
        
        # 返回进度信息
        return Response({
            'status': 'success',
            'progress': progress_data.get('progress', 0),
            'message': progress_data.get('message', '正在评估'),
            'state': progress_data.get('state', 'evaluating')
        }, status=status.HTTP_200_OK)
        
    except Exception as e:
        import logging
        logger = logging.getLogger(__name__)
        logger.error(f"获取评估进度失败: {str(e)}")
        return Response({
            'status': 'error',
            'message': f'获取进度信息失败: {str(e)}',
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

#用户中途退出模型评估
def cancel_model_evaluation(request, project_id):
    """
    取消模型性能评估生成过程
    """
    evaluation_id = request.data.get("evaluation_id")
    save_evaluation = request.data.get("save_evaluation", False)
    evaluation_name = request.data.get("evaluation_name", "Noname")
    
    if not evaluation_id:
        return Response({"error": "请提供 evaluation_id"}, status=status.HTTP_400_BAD_REQUEST)
    
    # 设置取消标记
    cache_key = f"model_evaluation_cancel_{project_id}_{evaluation_id}"
    cache.set(cache_key, {"save_evaluation": save_evaluation,"evaluation_name":evaluation_name}, timeout=3600)
    
    # 更新进度状态
    if save_evaluation:
        update_evaluation_progress(project_id, evaluation_id, 99, "用户请求保存当前模型测试", "saving")
    else:
        update_evaluation_progress(project_id, evaluation_id, 0, "用户取消模型测试", "cancelled")
    
    return Response({
        "status": "success",
        "message": "已发送取消请求",
        "save_evaluation": save_evaluation
    }, status=status.HTTP_200_OK)

#检查用户是否退出且保存
def check_user_cancelled(project_id,evaluation_id):
    cache_key = f"model_evaluation_cancel_{project_id}_{evaluation_id}"
    cancelled = cache.get(cache_key)
    if cancelled:
        is_save = cancelled.get("save_evaluation", False)
        evaluation_name = cancelled.get("evaluation_name", False)
        return True, is_save,evaluation_name
    return False, None