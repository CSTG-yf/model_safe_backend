import os
from datetime import datetime

import openai
import json

api = "sk-hhAm1szWdX0riU29nSrmrHrtAFOUKcQuG4jE4mEFSQwqLuWS"
url = "https://api.moonshot.cn/v1"
myModel = "moonshot-v1-8k"

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

    def _build_prompt(self, example_question, example_answer, question_num, question_field, question_type):
        """
        构建提示词

        参数:
        example_question (str): 示例题目
        example_answer (str): 示例答案
        question_num (int): 要生成的题目数量
        question_field (str): 题目领域
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
            - 题目领域：{question_field}
            - 题目类型：{question_type}
            - 覆盖该领域的不同知识点和应用场景
    
            ## 每道题目必须包含
            - 清晰且完整的题目描述
            - 详细的解题步骤和正确答案
            - 全面的5分制评分标准
    
            ## 输出格式 (JSON)
            请按照以下JSON格式输出每道题目：
                
              {{
                "question": "完整的题目内容",
                “options": [
                  "选项1",
                  "选项2",
                  "选项3",
                  "选项4"
                ],
                "answer": "详细的解题过程和正确答案",
                "question_field": "{question_field}",
                "question_type": "{question_type}",
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
            - 题目领域：{question_field}
            - 题目类型：{question_type}
            - 覆盖该领域的不同知识点和应用场景
    
            ## 每道题目必须包含
            - 清晰且完整的题目描述
            - 详细的解题步骤和正确答案
            - 全面的5分制评分标准
    
            ## 输出格式 (JSON)
            请按照以下JSON格式输出每道题目：
                
              {{
                "question": "完整的题目内容",
                "answer": "详细的解题过程和正确答案",
                "question_field": "{question_field}",
                "question_type": "{question_type}",
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

    def _build_prompt_without_example(self, question_num, question_field, question_type):
        """
        构建不需要例题的提示词

        参数:
        question_num (int): 要生成的题目数量
        question_field (str): 题目领域
        question_type (str): 题目类型
        difficulty_level (str): 难度级别，可选值: "简单", "中等", "困难"

        返回:
        str: 完整的提示词
        """
        if question_type == "单选题" or question_type == "多选题":
            return f"""
            我需要你生成{question_field}领域的{question_type}题目。每个题目都应包含题目内容、正确答案和5分制评分标准。
    
            ## 生成要求
            - 生成 {question_num} 道新题目
            - 题目领域：{question_field}
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
            请按照以下JSON格式输出每道题目：
    
              {{
                "question": "完整的题目内容（如果是选择题加入选项）",
                “options": [
                  "选项1",
                  "选项2",
                  "选项3",
                  "选项4"
                ],
                "answer": "详细的解题过程和正确答案",
                "question_field": "{question_field}",
                "question_type": "{question_type}",
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
            我需要你生成{question_field}领域的{question_type}题目。每个题目都应包含题目内容、正确答案和5分制评分标准。

            ## 生成要求
            - 生成 {question_num} 道新题目
            - 题目领域：{question_field}
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
            请按照以下JSON格式输出每道题目：

              {{
                "question": "完整的题目内容（如果是选择题加入选项）",
                "answer": "详细的解题过程和正确答案",
                "question_field": "{question_field}",
                "question_type": "{question_type}",
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
        请为指定领域设计高质量题目，确保题目难度适中，知识点覆盖全面，答案和评分标准清晰。
        """

    def generate_questions(self, example_question, example_answer, question_field, question_type, question_num=1, temperature=0.8):
        """
        生成新题目

        参数:
        example_question (str): 示例题目
        example_answer (str): 示例答案
        question_field (str): 题目领域
        question_type (str): 题目类型
        question_num (int): 要生成的题目数量
        temperature (float): 生成多样性参数，0.0-1.0

        返回:
        dict: 包含生成题目的JSON对象
        """
        if(example_question == "" and example_answer == ""):
            prompt = self._build_prompt_without_example(
                question_num,
                question_field,
                question_type
            )
        else:
            prompt = self._build_prompt(
                example_question,
                example_answer,
                question_num,
                question_field,
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

            print(json_str)

            try:
                questions = json.loads(json_str)
                return questions
            except json.JSONDecodeError:
                return {"error": "无法解析为JSON", "raw_response": response}

        except Exception as e:
            return {"error": str(e)}

    def save_questions_to_json(self, questions, filename="generated_questions.json"):
        """
        将生成的题目保存到JSON文件，以追加方式添加内容

        参数:
        questions (list/dict): 生成的题目，可以是列表或单个题目的字典
        filename (str): 输出JSON文件名

        返回:
        bool: 保存是否成功
        """
        try:
            if isinstance(questions, dict):
                if "error" in questions:
                    print(f"错误: {questions['error']}")
                    return False
                data_to_save = questions
            else:
                if len(questions) == 1:
                    data_to_save = questions[0]
                else:
                    data_to_save = questions

            try:
                file_exists = os.path.isfile(filename) and os.path.getsize(filename) > 0
            except:
                file_exists = False

            if not file_exists:
                with open(filename, 'w', encoding='utf-8') as f:
                    json.dump(data_to_save, f, ensure_ascii=False, indent=2)
            else:
                try:
                    with open(filename, 'r', encoding='utf-8') as f:
                        existing_data = json.load(f)

                    if isinstance(existing_data, list):
                        if isinstance(data_to_save, list):
                            combined_data = existing_data + data_to_save
                        else:
                            existing_data.append(data_to_save)
                            combined_data = existing_data
                    else:
                        if isinstance(data_to_save, list):
                            combined_data = [existing_data] + data_to_save
                        else:
                            combined_data = [existing_data, data_to_save]

                    with open(filename, 'w', encoding='utf-8') as f:
                        json.dump(combined_data, f, ensure_ascii=False, indent=2)

                except json.JSONDecodeError:
                    # 文件存在但不是有效的JSON，覆盖它
                    with open(filename, 'w', encoding='utf-8') as f:
                        json.dump(data_to_save, f, ensure_ascii=False, indent=2)

            print(f"题目已成功保存到 {filename}")
            return True

        except Exception as e:
            print(f"保存JSON时出错: {str(e)}")
            return False


    def _mulit_generate_questions(self, example_question, example_answer, question_field, question_type):
        for i in range(25):
            questions = self.generate_questions(
                example_question,
                example_answer,
                question_field,
                question_type,
                question_num=1,
                temperature=0.8
            )
            if self.save_questions_to_json(questions):
                print(f"第{i+1}次生成成功")
            else:
                print(f"第{i+1}次生成失败")


    def generate_question_bank(self, example_question, example_answer,question_field):
        self._mulit_generate_questions(example_question, example_answer, question_field, "单选题")
        self._mulit_generate_questions(example_question, example_answer, question_field, "多选题")
        self._mulit_generate_questions(example_question, example_answer, question_field, "判断题")
        self._mulit_generate_questions(example_question, example_answer, question_field, "填空题")
        self._mulit_generate_questions(example_question, example_answer, question_field, "简答题")

if __name__ == "__main__":
    api_key = api
    base_url = url
    model_name = myModel
    generator = QuestionGenerator(api_key, base_url, model_name)
    generator.generate_question_bank("", "", "数学")


