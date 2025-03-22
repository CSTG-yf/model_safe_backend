from rest_framework import viewsets
from rest_framework.views import APIView
from rest_framework.response import Response
from .tasks import run_jailbreak_workflow
from .utils import JailbreakService
from .serializers import ScoreRecordSerializer
from rest_framework.decorators import action
from rest_framework import status
from rest_framework import  permissions

class StartWorkflowAPI(APIView):
    permission_classes = [permissions.AllowAny]
    def post(self,request):
        """启动工作流"""
        data = request.data
        project_id = data['project_id']
        model_name = data['model_name']
        ev_time = data['ev_time']

        try:
            run_jailbreak_workflow.delay(model_name, ev_time,project_id)
        except Exception as e:
            return Response({'error': str(e)}, status=500)

        return Response({
            'status': 'started'
        },status=200)


class ScoreHistoryViewSet(viewsets.ModelViewSet):
    """
    包含标准 CRUD 和自定义查询操作
    """
    serializer_class = ScoreRecordSerializer
    @action(detail=False, methods=['get'], url_path='(?P<project_id>[^/.]+)/get-sessions')
    def get_all_score_history(self, request,project_id=None):
        """获取全部记录"""
        try:
            records = JailbreakService.get_all_session_by_project_id(project_id)
            return Response({'results': records}, status=status.HTTP_200_OK)
        except Exception as e:
            return Response({'error': str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

    @action(detail=False, methods=['post'], url_path='(?P<project_id>[^/.]+)/query-by-session-id')
    def query_by_session_id(self, request,project_id=None):
        """自定义参数查询"""
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        
        try:
            records = JailbreakService.get_score_history_by_session_id(
                session_id=serializer.validated_data['session_id'],
                project_id=project_id
            )
            return Response({'result': records}, status=200)
        except Exception as e:
            return Response({'error': str(e)}, status=500)

# class IterationRecordViewSet(viewsets.ModelViewSet):
#     """
#     迭代记录视图集（与 question_bank 保持结构一致）
#     """
#     serializer_class = IterationRecordSerializer
#
#     def get_queryset(self):
#         """支持分页和过滤"""
#         return JailbreakService.get_all_iterations()
#
#     @action(detail=False, methods=['get'], url_path='get-all-iteration-records')
#     def get_all_iteration_records(self, request):
#         """获取全部记录"""
#         try:
#             records = JailbreakService.get_all_iterations().values(
#             'category_index', 'title_index', 'prompt_num', 'cycle_num', 'score_info'
#         )
#             return Response({'results': records}, status=status.HTTP_200_OK)
#         except Exception as e:
#             return Response({'error': str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
#     @action(detail=False, methods=['post'], url_path='filter-records')
#     def filter_records(self, request):
#         """多条件过滤查询（对应原 get_iteration_history 功能）"""
#         serializer = self.get_serializer(data=request.data)
#         serializer.is_valid(raise_exception=True)
#
#         try:
#             records = JailbreakService.get_iteration_history(
#                 category_index=serializer.validated_data['category_index'],
#                 title_index=serializer.validated_data['title_index'],
#                 prompt_num=serializer.validated_data['prompt_num']
#             )
#             return Response({'results': records}, status=status.HTTP_200_OK)
#         except Exception as e:
#             return Response({'error': str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)