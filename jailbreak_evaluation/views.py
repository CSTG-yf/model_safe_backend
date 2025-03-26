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
        mode = data['mode']

        try:
            run_jailbreak_workflow.delay(model_name, ev_time,project_id,mode)
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
    @action(detail=False, methods=['get'], url_path='(?P<project_id>[^/.]+)/get-taskids')
    def get_all_score_history(self, request,project_id=None):
        """获取全部记录"""
        try:
            records = JailbreakService.get_all_session_by_project_id(project_id)
            return Response({'results': records}, status=status.HTTP_200_OK)
        except Exception as e:
            return Response({'error': str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

    @action(detail=False, methods=['post'], url_path='(?P<project_id>[^/.]+)/query-by-task-id')
    def query_by_session_id(self, request,project_id=None):
        """自定义参数查询"""
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        
        try:
            records = JailbreakService.get_score_history_by_session_name(
                session_name=serializer.validated_data['task_id'],
                project_id=project_id
            )
            return Response({'result': records}, status=200)
        except Exception as e:
            return Response({'error': str(e)}, status=500)

    @action(detail=False, methods=['post'], url_path='(?P<project_id>[^/.]+)/get-score-in-category')
    def get_score_in_category(self, request,project_id=None):
        """自定义参数查询"""
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        
        try:
            records = JailbreakService.get_score_in_category(
                session_name=serializer.validated_data['task_id'],
                project_id=project_id
            )
            return Response({'result': records}, status=200)
        except Exception as e:
            return Response({'error': str(e)}, status=500)