import json
import random
from django.utils import timezone
from rest_framework import status
from rest_framework.response import Response
from .models import EvalQuestions, SecurityQuestions

from .utils import QuestionGenerator

api = "sk-hhAm1szWdX0riU29nSrmrHrtAFOUKcQuG4jE4mEFSQwqLuWS"
url = "https://api.moonshot.cn/v1"
myModel = "moonshot-v1-8k"
generator = QuestionGenerator(api, url, myModel)


def generated_questions_and_add_to_database(request, project_id):
    """
    AI 生成题目，但不存数据库，而是返回给前端
    """
    field = request.data.get("field")
    prompt = request.data.get("prompt")
    number = request.data.get("number")
    security_ratios = request.data.get("security_ratios")
    question_bank_id = request.data.get("question_bank_id")
    if not prompt:
        return Response({"error": "请提供 prompt"}, status=status.HTTP_400_BAD_REQUEST)

    question_list = []
    # 生成用户输入题库
    generated_question_list = generator._mulit_generate_questions(number, field, prompt)
    question_list.extend(generated_question_list)

    # 按比例随机选择安全问题
    total_security_questions = 100
    for ratio_info in security_ratios:
        category_type = ratio_info.get("category_type")
        ratio = ratio_info.get("ratio")
        security_questions = SecurityQuestions.objects.filter(content_type=category_type, )
        count = int(total_security_questions * ratio / 100)
        selected_questions = random.sample(list(security_questions), count)
        for question in selected_questions:
            question['source'] = 'security-bank'
        question_list.extend(selected_questions)

    if not question_list:
        return Response({'status': 'error', 'message': '无有效题目'}, status=status.HTTP_400_BAD_REQUEST)

    try:
        eval_question = EvalQuestions.objects.get(question_bank_id=question_bank_id)
    except EvalQuestions.DoesNotExist:
        return Response({"error": "无效的 question_bank_id"}, status=status.HTTP_404_NOT_FOUND)

    eval_question.exam_title = question_list[0]
    eval_question.questions = json.dumps(question_list)
    eval_question.save()

    return Response({'status': 'success', 'message': '题库生成完成'}, status=status.HTTP_200_OK)

