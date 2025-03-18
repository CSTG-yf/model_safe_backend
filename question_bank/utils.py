import os
from datetime import datetime

import openai
import json
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

    def _build_prompt_without_example(self, question_num, content_type, question_type):
        """
        构建不需要例题的提示词

        参数:
        question_num (int): 要生成的题目数量
        content_type (str): 题目领域
        question_type (str): 题目类型
        difficulty_level (str): 难度级别，可选值: "简单", "中等", "困难"

        返回:
        str: 完整的提示词
        """
        if question_type == "单选题" or question_type == "多选题":
            return f"""
            我需要你生成{content_type}领域的{question_type}题目。每个题目都应包含题目内容、正确答案和5分制评分标准。
    
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

    def generate_questions(self, content_type, question_type, question_num=1, temperature=None,example_question ="",example_answer=""):
        """
        生成新题目

        参数:
        example_question (str): 示例题目
        example_answer (str): 示例答案
        content_type (str): 题目领域
        question_type (str): 题目类型
        question_num (int): 要生成的题目数量
        temperature (float): 生成多样性参数，0.0-1.0，如果为None则随机生成

        返回:
        dict: 包含生成题目的JSON对象
        """
        if temperature is None:
            temperature = random.uniform(0.0, 1.0)

        if example_question == "" and example_answer == "":
            prompt = self._build_prompt_without_example(
                question_num,
                content_type,
                question_type
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
                temperature=temperature
            )

            response = completion.choices[0].message.content
            print("原始响应:", response)  # 添加调试输出

            json_str = response.strip()
            if "```json" in json_str:
                start_index = json_str.find("```json") + 7
                end_index = json_str.find("```", start_index)
                if end_index != -1:
                    json_str = json_str[start_index:end_index].strip()
            elif "```" in json_str:
                start_index = json_str.find("```") + 3
                end_index = json_str.find("```", start_index)
                if end_index != -1:
                    json_str = json_str[start_index:end_index].strip()
            
            print("清理后的JSON字符串:", json_str)  # 添加调试输出

            try:
                questions = json.loads(json_str)
                return questions
            except json.JSONDecodeError as e:
                print(f"JSON解析错误: {str(e)}")  # 添加错误输出
                print(f"问题JSON字符串: {json_str}")  # 添加问题字符串输出
                return {"error": "无法解析为JSON", "raw_response": response}

        except Exception as e:
            return {"error": str(e)}

    def _mulit_generate_questions(self,question_num,content_type, question_type):
        question_list = []
        for i in range(question_num):
            questions = self.generate_questions(
                content_type,
                question_type,
                question_num=1,
                temperature=None,
            )
            question_list.append(questions)
            print(f"第{i + 1}次生成成功")
        return question_list





