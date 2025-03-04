import random
from collections import defaultdict
from rest_framework import status
from rest_framework.response import Response
from .models import MasterQuestion, EvaluationQuestionBank, EvaluationQuestion
from .serializers import (
    MasterQuestionSerializer,
    EvaluationQuestionBankSerializer,
    EvaluationQuestionSerializer
)
from core.one_api_client import call_one_api  # AI 生成逻辑

def preview_generated_questions(request, bank):
    """
    AI 生成题目，但不存数据库，而是返回给前端
    """
    prompt = request.data.get("prompt")
    if not prompt:
        return Response({"error": "请提供 prompt"}, status=status.HTTP_400_BAD_REQUEST)

    # 调用 AI
    ai_response = call_one_api(prompt)
    questions_data = ai_response.get("questions", [])

    return Response({"generated_questions": questions_data})


def add_generated_questions(request, bank):
    """
    用户选择 AI 生成的题目，并存入评测题库
    """
    questions_data = request.data.get("questions", [])

    if not questions_data:
        return Response({"error": "请提供至少一个题目"}, status=status.HTTP_400_BAD_REQUEST)

    for q in questions_data:
        EvaluationQuestion.objects.create(
            evaluation_bank=bank,
            content=q["content"],
            answer=q.get("answer", "")
        )

    return Response({"msg": "题目已成功添加到评测题库"})


def add_master_questions(request, bank):
    """
    从总题库选取题目加入评测题库
    """
    question_ids = request.data.get("question_ids", [])
    master_questions = MasterQuestion.objects.filter(id__in=question_ids)

    for mq in master_questions:
        EvaluationQuestion.objects.create(
            evaluation_bank=bank,
            content=mq.content,
            answer=mq.answer,
            master_question=mq
        )

    return Response({"msg": "从题库添加成功"})


def generate_from_master(request, bank):
    """
    按照用户设定的标签比例，从总题库随机抽取题目，组成评测题库
    """
    total_questions = request.data.get("total_questions")
    tag_distribution = request.data.get("tag_distribution")  # { "1": 40, "2": 30, "3": 20, "4": 5, "5": 5 }

    if not total_questions or not tag_distribution:
        return Response({"error": "请提供 total_questions 和 tag_distribution"}, status=status.HTTP_400_BAD_REQUEST)

    # 计算每个标签需要的题目数量
    tag_counts = {tag: round(total_questions * (percent / 100)) for tag, percent in tag_distribution.items()}

    selected_questions = []
    for tag, count in tag_counts.items():
        questions = list(MasterQuestion.objects.filter(tags__icontains=tag))  # tags 可能是 "1,2,3"
        if len(questions) > count:
            selected_questions.extend(random.sample(questions, count))
        else:
            selected_questions.extend(questions)

    # 将选中的题存入 `EvaluationQuestion`
    for q in selected_questions:
        EvaluationQuestion.objects.create(
            evaluation_bank=bank,
            content=q.content,
            answer=q.answer
        )

    return Response({"msg": "已成功生成评测题库"})
