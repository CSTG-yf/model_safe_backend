import json
import uuid
from rest_framework import status
from rest_framework.response import Response
from .models import EvalQuestions, SecurityQuestions
from django.forms.models import model_to_dict
from django.db import transaction
import logging
from django.core.cache import cache
import openai
import json5
import demjson3
import random


class QuestionGenerator:
    def __init__(self, api_key, base_url, model):
        """
        初始化题目生成器

        参数:
        api_key (str): API密钥
        base_url (str): API基础URL
        model (str): 使用的AI模型名称
        """
        self.api_key = api_key
        self.base_url = base_url
        self.model = model
        self.client = openai.OpenAI(
            api_key=self.api_key,
            base_url=self.base_url
        )

    def _build_prompt(self, example_question, example_answer, question_num, content_type, question_type):
        """
        构建提示词

        参数:
        example_question (str): 示例题目
        example_answer (str): 示例答案
        question_num (int): 要生成的题目数量
        content_type (str): 题目领域
        question_type (str): 题目类型

        返回:
        str: 完整的提示词
        """

        if question_type == "单选题" or question_type == "多选题":
            return f"""
            我需要你根据我提供的例题，生成新的题目。新题目应在保持相似难度的同时，展现不同的知识点和解题思路。每个新题目都应包含题目内容、正确答案和5分制评分标准。

            ## 例题参考
            例题：{example_question}
            答案：{example_answer}

            ## 生成要求
            - 生成 {question_num} 道新题目
            - 题目难度应与例题相似，但内容和解题方法应有变化
            - 题目领域：{content_type}
            - 题目类型：{question_type}
            - 覆盖该领域的不同知识点和应用场景

            ## 每道题目必须包含
            - 清晰且完整的题目描述
            - 详细的解题步骤和正确答案
            - 全面的5分制评分标准

            ## 输出格式 (JSON)
            请按照以下JSON格式输出每道题目，不要出现中文引号：

              {{
                "source": llm,
                "content_type": "{content_type}",
                "question_type": "{question_type}",
                "question": "完整的题目内容",
                "options": [
                  "选项1",
                  "选项2",
                  "选项3",
                  "选项4"
                ],
                "answer": "详细的解题过程和正确答案",
                "scoring_criteria": {{
                  "5分": "完美回答的详细标准",
                  "4分": "良好回答的详细标准",
                  "3分": "及格回答的详细标准",
                  "2分": "不及格但有部分正确的详细标准",
                  "1分": "几乎完全错误的详细标准",
                  "0分": "未回答或完全离题的标准"
                }}
              }}
            """
        else:
            return f"""
            我需要你根据我提供的例题，生成新的题目。新题目应在保持相似难度的同时，展现不同的知识点和解题思路。每个新题目都应包含题目内容、正确答案和5分制评分标准。

            ## 例题参考
            例题：{example_question}
            答案：{example_answer}

            ## 生成要求
            - 生成 {question_num} 道新题目
            - 题目难度应与例题相似，但内容和解题方法应有变化
            - 题目领域：{content_type}
            - 题目类型：{question_type}
            - 覆盖该领域的不同知识点和应用场景

            ## 每道题目必须包含
            - 清晰且完整的题目描述
            - 详细的解题步骤和正确答案
            - 全面的5分制评分标准

            ## 输出格式 (JSON)
            请按照以下JSON格式输出每道题目，不要出现中文引号：

              {{
                "source": llm,
                "content_type": "{content_type}",
                "question_type": "{question_type}",
                "question": "完整的题目内容",
                "answer": "详细的解题过程和正确答案",
                "scoring_criteria": {{
                  "5分": "完美回答的详细标准",
                  "4分": "良好回答的详细标准",
                  "3分": "及格回答的详细标准",
                  "2分": "不及格但有部分正确的详细标准",
                  "1分": "几乎完全错误的详细标准",
                  "0分": "未回答或完全离题的标准"
                }}
              }}
            """

    def _build_prompt_without_example(self, question_num, content_type, question_type, subfield):
        """
        构建不需要例题的提示词

        参数:
        question_num (int): 要生成的题目数量
        content_type (str): 题目领域
        question_type (str): 题目类型
        subfield (str): 子领域
        返回:
        str: 完整的提示词
        """
        if question_type == "单选题" or question_type == "多选题":
            return f"""
            我需要你生成{content_type}领域中的和{subfield}相关的{question_type}题目。每个题目都应包含题目内容、正确答案和5分制评分标准。

            ## 生成要求
            - 生成 {question_num} 道新题目
            - 题目领域：{content_type}
            - 题目类型：{question_type}
            - 尽量覆盖该领域的主要知识点和典型应用场景

            ## 题目要求
            - 若题目类中未要求具体的题目类型，比如“微积分”，则需要随机生成选择题或者计算题或者简答题或者案例分析题确保多样性，若明确提出具体的题目类型，比如“关于微积分的选择题”，则按要求生成选择题
            - 对于选择题：提供明确的选项和正确答案，以及每个选项的分析
            - 对于计算题：提供详细的计算步骤和公式应用过程
            - 对于简答题：提供完整的标准答案和关键点分析
            - 对于案例分析题：提供完整的分析思路和解决方案

            ## 每道题目必须包含
            - 清晰且完整的题目描述
            - 详细的解题步骤和正确答案
            - 全面的5分制评分标准

            ## 输出格式 (JSON)
            请按照以下JSON格式输出每道题目，不要出现中文引号：

              {{
                "source": llm,
                "content_type": "{content_type}",
                "question_type": "{question_type}",
                "question": "完整的题目内容（如果是选择题加入选项）",
                "options": [
                  "选项1",
                  "选项2",
                  "选项3",
                  "选项4"
                ],
                "answer": "详细的解题过程和正确答案",
                "scoring_criteria": {{
                  "5分": "完美回答的详细标准，包括必须涵盖的关键点和解题方法",
                  "4分": "良好回答的详细标准，指出与满分的差距",
                  "3分": "及格回答的详细标准，指出最低通过要求",
                  "2分": "不及格但有部分正确的详细标准，说明主要缺失",
                  "1分": "几乎完全错误的详细标准，说明基本错误",
                  "0分": "未回答或完全离题的标准"
                }}
              }}
            """
        else:
            return f"""
            我需要你生成{content_type}领域的{question_type}题目。每个题目都应包含题目内容、正确答案和5分制评分标准。

            ## 生成要求
            - 生成 {question_num} 道新题目
            - 题目领域：{content_type}
            - 题目类型：{question_type}
            - 尽量覆盖该领域的主要知识点和典型应用场景

            ## 题目要求
            - 对于选择题：提供明确的选项和正确答案，以及每个选项的分析
            - 对于计算题：提供详细的计算步骤和公式应用过程
            - 对于简答题：提供完整的标准答案和关键点分析
            - 对于案例分析题：提供完整的分析思路和解决方案

            ## 每道题目必须包含
            - 清晰且完整的题目描述
            - 详细的解题步骤和正确答案
            - 全面的5分制评分标准

            ## 输出格式 (JSON)
            请按照以下JSON格式输出每道题目，不要出现中文引号：

              {{
                "source": llm,
                "content_type": "{content_type}",
                "question_type": "{question_type}",
                "question": "完整的题目内容（如果是选择题加入选项）",
                "answer": "详细的解题过程和正确答案",
                "scoring_criteria": {{
                  "5分": "完美回答的详细标准，包括必须涵盖的关键点和解题方法",
                  "4分": "良好回答的详细标准，指出与满分的差距",
                  "3分": "及格回答的详细标准，指出最低通过要求",
                  "2分": "不及格但有部分正确的详细标准，说明主要缺失",
                  "1分": "几乎完全错误的详细标准，说明基本错误",
                  "0分": "未回答或完全离题的标准"
                }}
              }}
            """

    def _build_system_prompt(self):
        """
        构建系统提示词

        返回:
        str: 系统提示词
        """
        return """
        你是一个专业的ai评估题目设计专家，精通各个学科和题型的题目创作。
        请为指定领域设计高质量题目，确保题目难度困难，知识点覆盖全面，答案和评分标准清晰。
        """

    def generate_questions(self, content_type, question_type, question_num=1, temperature=None, example_question="",
                           example_answer="", subfield=""):
        """
        生成新题目

        参数:
        example_question (str): 示例题目
        example_answer (str): 示例答案
        content_type (str): 题目领域
        question_type (str): 题目类型
        question_num (int): 要生成的题目数量
        temperature (float): 生成多样性参数，0.0-1.0，如果为None则随机生成
        subfield (str): 子领域

        返回:
        dict: 包含生成题目的JSON对象
        """
        if temperature is None:
            temperature = random.uniform(0.0, 1.0)

        if example_question == "" and example_answer == "":
            prompt = self._build_prompt_without_example(
                question_num,
                content_type,
                question_type,
                subfield
            )
        else:
            prompt = self._build_prompt(
                example_question,
                example_answer,
                question_num,
                content_type,
                question_type
            )

        system_prompt = self._build_system_prompt()

        try:
            completion = self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": prompt}
                ],
                temperature=temperature,
                response_format={"type": "json_object"}
            )

            response = completion.choices[0].message.content

            # 新版清洗逻辑（仅处理Markdown代码块）
            json_str = response.strip()
            json_str = json_str.replace("```json", "").replace("```", "").strip()

            # 处理所有正斜杠转义（兼容Python低版本）
            json_str = json_str.replace(r'\/', '/')

            try:
                # 优先使用json5解析（支持非标准JSON）
                print(json5.loads(json_str))
                return json5.loads(json_str)
            except Exception as e:
                print(f"JSON5解析失败，尝试demjson3: {str(e)}")
                try:
                    # 使用demjson3处理更复杂的格式
                    return demjson3.decode(json_str)
                except demjson3.JSONDecodeError as e2:
                    print(f"最终JSON解析失败: {str(e2)}")
                    return {
                        "error": "Invalid JSON",
                        "detail": str(e2),
                        "raw_response": response
                    }

        except Exception as e:
            return {"error": str(e)}

    def _mulit_generate_questions(self, question_num, content_type, subfield, project_id, question_bank_id):
        """
        批量生成题目
        """
        question_list = []
        error_count = 0
        max_retries = 3

        question_types = ["单选题", "多选题", "简答题", "案例分析题"]

        for i in range(question_num):
            retry = 0
            question_type = random.choice(question_types)
            while retry < max_retries:
                result = self.generate_questions(
                    content_type,
                    question_type,
                    question_num=1,
                    temperature=None,
                    subfield=subfield
                )

                if isinstance(result, dict) and "error" not in result:
                    # 处理可能返回的单个题目对象
                    if isinstance(result, list):
                        question_list.extend(result)
                    else:
                        question_list.append(result)
                        # 调用进度回调函数

                    # 更新进度并检查是否取消
                    progress = int(((i + 1) / question_num) * 100)
                    print(f"生成第{i+1}个问题，进度为{progress}%")
                    if progress < 100:  # 保留最后的100%给整体完成时
                        update_generation_progress(project_id, question_bank_id, progress, f"题目生成进度: {progress}%",
                                                   "generating")

                        # 检查用户是否取消了操作
                        cancelled, save_questions, bank_name = check_user_cancelled(project_id, question_bank_id)
                        if cancelled and not save_questions:
                            # 抛出异常来中断生成过程
                            raise Exception("用户取消生成题库")
                    break
                else:
                    retry += 1
                    print(f"第 {i + 1} 题生成失败，重试 {retry}/{max_retries}")
                    if retry == max_retries:
                        error_count += 1
                        print(f"第 {i + 1} 题生成最终失败: {result.get('error', '未知错误')}")

        print(f"批量生成完成，成功 {question_num - error_count} 题，失败 {error_count} 题")
        return question_list


logger = logging.getLogger(__name__)

api = "sk-hhAm1szWdX0riU29nSrmrHrtAFOUKcQuG4jE4mEFSQwqLuWS"
url = "https://api.moonshot.cn/v1"
myModel = "moonshot-v1-8k"
generator = QuestionGenerator(api, url, myModel)

def check_user_cancelled(project_id,question_bank_id):
    cache_key = f"question_bank_cancel_{project_id}_{question_bank_id}"
    cancelled = cache.get(cache_key)
    if cancelled:
        is_save = cancelled.get("save_questions", False)
        bank_name = cancelled.get("bank_name", False)
        return True, is_save, bank_name
    return False, None, None

def update_generation_progress(project_id,question_bank_id, progress, message="正在生成题库", state="generating"):
    """
    更新题库生成进度并存入缓存
    """
    cache_key = f"question_bank_progress_{project_id}_{question_bank_id}"
    progress_data = {
        'progress': progress,
        'message': message,
        'state': state
    }
    # 设置缓存，过期时间为1小时
    cache.set(cache_key, progress_data, timeout=3600)
    return progress_data

def generated_questions_and_add_to_database(request, project_id):
    """
    AI 生成题目，并将结果存储到数据库
    """

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
    
    # 初始化进度为0%
    update_generation_progress(project_id, question_bank_id, 0, "开始生成题库", "generating")
    
    question_list = []
    # 生成用户输入题库
    try:
        # 传入回调函数，在生成每个问题后更新进度
        generated_question_list = generator._mulit_generate_questions(number, field, prompt,project_id, question_bank_id)
        
        # 检查用户是否在生成题目后取消了操作
        cancelled, save_questions,bank_name = check_user_cancelled(project_id,question_bank_id)
        if cancelled:
            if not save_questions:
                # 用户取消且不保存
                update_generation_progress(project_id, question_bank_id, 0, "用户取消生成题库", "cancelled")
                return Response({
                    "status": "success",
                    "message": "用户取消保存题库",
                }, status=status.HTTP_200_OK)
            # 如果用户选择保存，则继续处理已生成的题目
        
        # 将生成的题目添加到列表中
        question_list.extend(generated_question_list)
        
        # 设置进度为99%，表示题目生成完成，但整个过程还未完成
        logger.info('题目生成进度: 99%')
        update_generation_progress(project_id, question_bank_id, 99, "题目生成进度: 99%", "generating")
    except Exception as e:
        if str(e) == "用户取消生成题库":
            # 用户取消生成
            update_generation_progress(project_id, question_bank_id, 0, "用户取消生成题库", "cancelled")
            return Response({
                "status": "success",
                "message": "用户取消保存题库",
            }, status=status.HTTP_200_OK)
        else:
            # 其他错误
            update_generation_progress(project_id, question_bank_id, 0, f"生成题目失败: {str(e)}", "failed")
            return Response({"error": f"生成题目失败: {str(e)}"}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

    # 按比例随机选择安全问题（默认设置为10题）
    total_security_questions = 10
    
    # 再次检查用户是否取消了操作
    cancelled, save_questions, bank_name = check_user_cancelled(project_id,question_bank_id)
    if cancelled and not save_questions:
        update_generation_progress(project_id, question_bank_id, 0, "用户取消生成题库", "cancelled")
        return Response({
            "status": "success",
            "message": "用户取消保存题库",
        }, status=status.HTTP_200_OK)
    
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
        # 更新缓存中的进度为失败状态
        update_generation_progress(project_id,question_bank_id, 0, "无有效题目", "failed")
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
                eval_question.exam_title = bank_name
            eval_question.save()
        update_generation_progress(project_id,question_bank_id, 100, "题库生成完成", "completed")
        return Response({
            'status': 'success',
            'message': '题库生成完成',
            'question_bank_id': question_bank_id,
        }, status=status.HTTP_200_OK)
    except Exception as e:
        # 更新缓存中的进度为失败状态
        update_generation_progress(question_bank_id, 0, f"存储失败: {str(e)}", "failed")
        return Response({"error": f"存储失败: {str(e)}"}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

def get_question_generation_progress(request,project_id):
    """
    获取题库生成进度
    """
    # 获取请求参数
    question_bank_id = request.data.get('question_bank_id')
    
    # 参数校验
    if not question_bank_id:
        return Response({"error": "请提供 question_bank_id"}, status=status.HTTP_400_BAD_REQUEST)
    
    try:
        # 构建缓存键
        cache_key = f"question_bank_progress_{project_id}_{question_bank_id}"
        
        # 获取进度信息
        progress_data = cache.get(cache_key)
        
        if progress_data is None:
            # 如果没有找到进度信息，可能是已经完成或尚未开始
            # 检查题库是否存在
            try:
                eval_question = EvalQuestions.objects.get(question_bank_id=question_bank_id)
                # 如果题库存在且有题目，则认为已完成
                if eval_question.questions and len(eval_question.questions) > 0:
                    return Response({
                        'status': 'success',
                        'progress': 100,
                        'message': '题库生成已完成',
                        'state': 'completed'
                    }, status=status.HTTP_200_OK)
                else:
                    return Response({
                        'status': 'info',
                        'progress': 0,
                        'message': '题库生成尚未开始或进度信息不可用',
                        'state': 'not_started'
                    }, status=status.HTTP_200_OK)
            except EvalQuestions.DoesNotExist:
                return Response({
                    'status': 'error',
                    'message': '题库不存在',
                }, status=status.HTTP_404_NOT_FOUND)
        
        # 返回进度信息
        return Response({
            'status': 'success',
            'progress': progress_data.get('progress', 0),
            'message': progress_data.get('message', '正在生成题库'),
            'state': progress_data.get('state', 'generating')
        }, status=status.HTTP_200_OK)
        
    except Exception as e:
        logger.error(f"获取题库生成进度失败: {str(e)}")
        return Response({
            'status': 'error',
            'message': f'获取进度信息失败: {str(e)}',
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


def cancel_question_generation(request, project_id):
    """
    取消题库生成过程
    """
    question_bank_id = request.data.get("question_bank_id")
    save_questions = request.data.get("save_questions", False)
    bank_name = request.data.get("bank_name", "Noname")
    
    if not question_bank_id:
        return Response({"error": "请提供 question_bank_id"}, status=status.HTTP_400_BAD_REQUEST)
    
    # 设置取消标记
    cache_key = f"question_bank_cancel_{project_id}_{question_bank_id}"
    cache.set(cache_key, {"save_questions": save_questions,"bank_name":bank_name}, timeout=3600)
    
    # 更新进度状态
    if save_questions:
        update_generation_progress(project_id, question_bank_id, 99, "用户请求保存当前题库", "saving")
    else:
        update_generation_progress(project_id, question_bank_id, 0, "用户取消生成题库", "cancelled")
    
    return Response({
        "status": "success",
        "message": "已发送取消请求",
        "save_questions": save_questions
    }, status=status.HTTP_200_OK)