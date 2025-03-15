import json
import random
from django.utils import timezone
from rest_framework import status
from rest_framework.response import Response
from .models import EvalQuestions, SecurityQuestions

from core.one_api_client import call_one_api  # AI 生成逻辑
from .serializers import SecurityQuestionsSerializer


def generated_questions_and_add_to_database(request):
    """
    AI 生成题目，但不存数据库，而是返回给前端
    """
    system_prompt = "你是一名ai助手"
    prompt = request.data.get("prompt")
    number = request.data.get("number")
    if not prompt:
        return Response({"error": "请提供 prompt"}, status=status.HTTP_400_BAD_REQUEST)

    question_list = []
    for i in range(int(number)):
        # 调用 AI
        ai_response = call_one_api(system_prompt,prompt)
        questions_data = ai_response.get("questions", [])
        question_list.append(i for i in questions_data)

    if not question_list:
        return Response({'status': 'error','message':'无有效题目'}, status=status.HTTP_400_BAD_REQUEST)

    eval_question = EvalQuestions.objects.create(
        exam_title=question_list[0],
        project_id=request.data.get("project_id"),
        created_at=timezone.now(),
        questions=json.dumps(question_list),
    )

    return Response({'status':'success','question_bank_id':eval_question.question_bank_id},status=status.HTTP_200_OK)

def get_question_detail(question_bank_id):
    try:
        eval_question = EvalQuestions.objects.get(question_bank_id=question_bank_id)
        # 反序列化 JSON 字段
        questions = json.loads(eval_question.questions)
        return Response({'status': 'success', 'questions': questions}, status=status.HTTP_200_OK)
    except EvalQuestions.DoesNotExist:
        return Response({'status': 'error', 'message': '题库不存在'}, status=status.HTTP_404_NOT_FOUND)
    except json.JSONDecodeError:
        return Response({'status': 'error', 'message': '题目数据格式错误'}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

def get_security_question_detail():
    # 获取所有安全题库
    try:
        security_questions = SecurityQuestions.objects.all()
        serializer = SecurityQuestionsSerializer(security_questions, many=True)
        return Response({'status': 'success', 'questions':serializer.data}, status=status.HTTP_200_OK)
    except SecurityQuestions.DoesNotExist:
        return Response({'status': 'error', 'message': '题库不存在'}, status=status.HTTP_404_NOT_FOUND)