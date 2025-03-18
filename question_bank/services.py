import json
import random
from django.utils import timezone
from rest_framework import status
from rest_framework.response import Response
from .models import EvalQuestions, SecurityQuestions

from core.one_api_client import call_one_api  # AI 生成逻辑
from .serializers import SecurityQuestionsSerializer
from utils import QuestionGenerator

api = "sk-hhAm1szWdX0riU29nSrmrHrtAFOUKcQuG4jE4mEFSQwqLuWS"
url = "https://api.moonshot.cn/v1"
myModel = "moonshot-v1-8k"
generator = QuestionGenerator(api, url, myModel)


def generated_questions_and_add_to_database(request):
    """
    AI 生成题目，但不存数据库，而是返回给前端
    """
    field = request.data.get("field")
    prompt = request.data.get("prompt")
    number = request.data.get("number")
    security_ratios = request.data.get("security_ratios")
    if not prompt:
        return Response({"error": "请提供 prompt"}, status=status.HTTP_400_BAD_REQUEST)

    question_list = []
    # 生成用户输入题库
    generated_question_list = generator._mulit_generate_questions(number,field,prompt)
    question_list.extend(generated_question_list)

    # 按比例随机选择安全问题
    total_security_questions = 100
    for ratio_info in security_ratios:
        category_type = ratio_info.get("category_type")
        ratio = ratio_info.get("ratio")
        security_questions = SecurityQuestions.objects.filter(content_type==category_type)
        count = int(total_security_questions * ratio / 100)
        selected_questions = random.sample(list(security_questions), count)
        for question in selected_questions:
            question['source'] = 'security-bank'
        question_list.extend(selected_questions)

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