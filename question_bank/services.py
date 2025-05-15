import json
import uuid
import random
from rest_framework import status
from rest_framework.response import Response
from .models import EvalQuestions, SecurityQuestions
from django.forms.models import model_to_dict
from .utils import QuestionGenerator
from django.db import transaction
import logging
logger = logging.getLogger(__name__)

api = "sk-hhAm1szWdX0riU29nSrmrHrtAFOUKcQuG4jE4mEFSQwqLuWS"
url = "https://api.moonshot.cn/v1"
myModel = "moonshot-v1-8k"
generator = QuestionGenerator(api, url, myModel)

from .consumers import QuestionBankConsumer

def generated_questions_and_add_to_database(request, project_id):
    """
    AI 生成题目，并将结果存储到数据库
    """
    # 初始化 consumer
    consumer = QuestionBankConsumer()

    # 提取请求参数
    field = request.data.get("field")
    prompt = request.data.get("prompt")
    number = request.data.get("number", 10)  # 默认生成10道题
    security_ratios = request.data.get("security_ratio", [])  # 默认空列表
    question_bank_id = request.data.get("question_bank_id")
    # 参数校验
    if not prompt:
        return Response({"error": "请提供 prompt"}, status=status.HTTP_400_BAD_REQUEST)
    if not question_bank_id:
        return Response({"error": "请提供 question_bank_id"}, status=status.HTTP_400_BAD_REQUEST)
    question_list = []
    # 生成用户输入题库
    try:
        generated_question_list = generator._mulit_generate_questions(number, field, prompt)
        for i, question in enumerate(generated_question_list, start=1):
            question_list.append(question)
            # 发送进度更新(每10%发送一次)
            progress = int((i / number) * 100)
            if(progress % 10 == 0 & progress != 100):
                logger.info(f'题目生成进度: {progress}%')
                consumer.send_message(f'题目生成进度: {progress}%',progress,"generating",project_id)
            elif(progress == 100):
                logger.info(f'题目生成进度: 99%')
                consumer.send_message(f'题目生成进度: 99%',99,"generating",project_id)
    except Exception as e:
        return Response({"error": f"生成题目失败: {str(e)}"}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

    # 按比例随机选择安全问题（默认设置为10题）
    total_security_questions = 10
    if security_ratios:
        try:
            # 计算总需要的安全题目数量
            total_required = sum(
                int(total_security_questions * ratio_info.get("ratio", 0) / 100)
                for ratio_info in security_ratios
                if isinstance(ratio_info.get("ratio", 0), (int, float)) and ratio_info.get("ratio", 0) > 0
            )

            # 初始化已选题目ID集合
            selected_ids = set()
            # 初始化未选中题目ID列表
            remaining_ids = []

            # 第一轮：按比例尽可能选择指定类型的题目
            for ratio_info in security_ratios:
                category_type = ratio_info.get("category_type")
                ratio = ratio_info.get("ratio", 0)

                if not isinstance(ratio, (int, float)) or ratio <= 0:
                    continue

                count = int(total_security_questions * ratio / 100)
                # 查询指定类型的题目ID
                questions = SecurityQuestions.objects.filter(content_type=category_type).values_list('id', flat=True)

                # 过滤掉已选题目
                available_ids = [q_id for q_id in questions if q_id not in selected_ids]
                # 随机选取
                selected_ids.update(random.sample(available_ids, min(count, len(available_ids))))
                # 记录未选中的题目ID供后续使用
                remaining_ids.extend([q_id for q_id in questions if q_id not in selected_ids])

            # 如果已选题目不够总数，从剩余题目中补足
            if len(selected_ids) < total_required:
                needed = total_required - len(selected_ids)
                # 过滤掉已选题目
                available_remain = [q_id for q_id in remaining_ids if q_id not in selected_ids]
                # 随机补足
                selected_ids.update(random.sample(available_remain, min(needed, len(available_remain))))

            # 查询最终选中的题目
            selected_questions = SecurityQuestions.objects.filter(id__in=selected_ids)

            # 标记题目来源并加入列表
            for q in selected_questions:
                q_dict = model_to_dict(q, exclude=["id"])
                q_dict['source'] = 'security-bank'
                question_list.append(q_dict)

        except Exception as e:
            return Response({"error": f"安全题目处理失败: {str(e)}"}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

    # 检查是否有有效题目
    if not question_list:
        return Response({'status': 'error', 'message': '无有效题目'}, status=status.HTTP_400_BAD_REQUEST)
    # 存储题目到数据库
    try:
        with transaction.atomic():
            eval_question, created = EvalQuestions.objects.get_or_create(
                question_bank_id=question_bank_id,
                defaults={"exam_title": f"{field}_题库"}
            )

            # 智能数据清理函数
            def clean_question_data(item, existing_ids=None):
                if existing_ids is None:
                    existing_ids = set()

                # 处理安全题库题目
                if isinstance(item, SecurityQuestions):
                    cleaned = {
                        'source': 'security-bank',
                        'content_type': item.content_type,
                        'question_type': item.question_type,
                        'question': item.question,
                        'options': item.options if isinstance(item.options, (list, dict)) else json.loads(item.options),
                        'answer': item.answer,
                        'scoring_criteria': item.scoring_criteria if isinstance(item.scoring_criteria, dict)
                        else json.loads(item.scoring_criteria)
                    }
                # 处理AI生成题目（可能是字典或字符串）
                else:
                    if isinstance(item, str):
                        try:
                            item = json.loads(item)
                        except json.JSONDecodeError:
                            item = {'question': item}
                    cleaned = {
                        k: (v.strip() if isinstance(v, str) else v)
                        for k, v in item.items()
                        if k not in ['id', 'created_at', 'updated_at']
                    }
                    # 处理嵌套JSON字段
                    for json_field in ['options', 'scoring_criteria']:
                        if json_field in cleaned:
                            if isinstance(cleaned[json_field], str):
                                try:
                                    cleaned[json_field] = json.loads(cleaned[json_field])
                                except:
                                    pass

                # 生成唯一question_id
                if 'question_id' not in cleaned:
                    # 生成UUID作为question_id
                    while True:
                        new_id = str(uuid.uuid4())
                        if new_id not in existing_ids:
                            cleaned['question_id'] = new_id
                            existing_ids.add(new_id)
                            break

                return cleaned, existing_ids

            # 处理所有题目数据
            cleaned_questions = []
            existing_ids = set()

            # 如果是更新已有题库，先收集已有question_id
            if not created and eval_question.questions:
                existing_questions = eval_question.questions
                if isinstance(existing_questions, str):
                    try:
                        existing_questions = json.loads(existing_questions)
                    except json.JSONDecodeError:
                        existing_questions = []

                if isinstance(existing_questions, list):
                    for q in existing_questions:
                        if isinstance(q, dict) and 'question_id' in q:
                            existing_ids.add(q['question_id'])

            # 清理并添加新题目
            for item in question_list:
                try:
                    cleaned, existing_ids = clean_question_data(item, existing_ids)
                    if cleaned:  # 确保数据有效
                        cleaned_questions.append(cleaned)
                except Exception as e:
                    logger.error(f"清理题目数据失败: {str(e)}")

            # 直接赋予Python对象（JSONField会自动处理序列化）
            if created:
                eval_question.questions = cleaned_questions
            else:
                # 安全读取现有数据
                existing = eval_question.questions
                if existing is None:
                    existing = []
                elif isinstance(existing, str):
                    try:
                        existing = json.loads(existing)
                    except json.JSONDecodeError:
                        existing = []
                # 确保类型统一
                if not isinstance(existing, list):
                    existing = [existing]
                if not isinstance(cleaned_questions, list):
                    cleaned_questions = [cleaned_questions]
                eval_question.questions = existing + cleaned_questions
            eval_question.save()
        consumer.send_message(f'题目生成进度: {progress}%',progress,"success",project_id)
        return Response({
            'status': 'success',
            'message': '题库生成完成',
            'question_bank_id': question_bank_id,
        }, status=status.HTTP_200_OK)
    except Exception as e:
        return Response({"error": f"存储失败: {str(e)}"}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)