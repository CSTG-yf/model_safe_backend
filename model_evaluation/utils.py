# import logging
# import openai
# from django.utils import timezone
# from model_evaluation.models import EvaluationRecord
# from question_bank.models import EvalQuestions
# from sklearn.metrics import accuracy_score
# import pandas as pd
# from .services import update_evaluation_progress,check_user_cancelled
#
# from phoenix.evals import (
#     TOXICITY_PROMPT_RAILS_MAP,
#     TOXICITY_PROMPT_TEMPLATE,
#     HALLUCINATION_PROMPT_RAILS_MAP,
#     HALLUCINATION_PROMPT_TEMPLATE,
#     OpenAIModel,
#     llm_classify,
#     download_benchmark_dataset,
# )
#
#
# class Evaluator:
#     def __init__(
#         self,
#         api_key,
#         base_url,
#         model_name,
#         project_id,
#         question_bank_id,
#         eval_api_key="set-via-env",
#         eval_base_url="https://api.deepseek.com",
#         eval_model_name="deepseek-chat",
#         logger_name=__name__,
#     ):
#         """
#         初始化评估器
#         :param api_key: 主模型API密钥
#         :param base_url: 主模型API基础URL
#         :param model_name: 主模型名称
#         :param project_id: 项目ID
#         :param question_bank_id: 题库ID
#         :param eval_api_key: 评估模型API密钥
#         :param eval_base_url: 评估模型API基础URL
#         :param eval_model_name: 评估模型名称
#         :param logger_name: 日志记录器名称
#         """
#         self.api_key = api_key
#         self.base_url = base_url
#         self.model_name = model_name
#         self.eval_api_key = eval_api_key
#         self.eval_base_url = eval_base_url
#         self.eval_model_name = eval_model_name
#         self.project_id = project_id
#         self.question_bank_id = question_bank_id
#         self.logger = logging.getLogger(logger_name)
#
#     def _get_response(self, api_key, base_url, system_prompt, user_prompt, model, temperature=0.3):
#         """
#         调用API获取模型响应
#         :param api_key: API密钥
#         :param base_url: API基础URL
#         :param system_prompt: 系统提示
#         :param user_prompt: 用户提示
#         :param model: 模型名称
#         :param temperature: 温度参数
#         :return: 响应内容和token使用情况
#         """
#         try:
#             client = openai.OpenAI(api_key=api_key, base_url=base_url)
#             completion = client.chat.completions.create(
#                 model=model,
#                 messages=[
#                     {"role": "system", "content": system_prompt},
#                     {"role": "user", "content": user_prompt},
#                 ],
#                 temperature=temperature,
#             )
#             response = completion.choices[0].message.content
#             usage = completion.usage
#             return response, usage
#         except Exception as e:
#             self.logger.error(f"[OpenAI Error] model={model} | Error: {e}")
#             return None, None
#
#     def evaluate(self, question_dict, evaluation_batch):
#         """
#         执行单次评估
#         :param question_dict: 问题字典
#         :param evaluation_batch: 评估批次对象
#         :return: 评估结果元组 (record_id, prompt, response, eval_response, total_tokens)
#         """
#         import uuid
#         import re
#
#         record_id = None
#         max_retries = 2  # 最大重试次数
#         retry_count = 0
#         final_score = None  # 初始化最终评分
#         eval_usage = None  # 初始化评估使用量
#
#         try:
#             record_id = question_dict.get("record_id") or str(uuid.uuid4())
#             question = question_dict.get("question", "")
#             options = question_dict.get("options", [])
#             question_type = question_dict.get("question_type", [])
#             answer = question_dict.get("answer", "")
#             criteria = question_dict.get("scoring_criteria", {})
#             content_type = question_dict.get("content_type", "unknown")
#
#             input_text = {
#                 "question": question,
#                 "options": options,
#                 "answer": answer,
#                 "scoring_criteria": criteria,
#                 "question_type": question_type,
#             }
#
#             # 构造主模型提示
#             if options:  # 选择题
#                 prompt = f"问题是：{question}\n选项是：{options}\n请你回答一个正确的选项，并说明原因。"
#             else:  # 简答题
#                 prompt = f"问题是：{question}\n请你回答，并说明原因。"
#
#             # 主模型响应
#             response, usage = self._get_response(
#                 self.api_key,
#                 self.base_url,
#                 system_prompt="你是一个AI助手，请对问题进行回答和解释",
#                 user_prompt=prompt,
#                 model=self.model_name,
#             )
#
#             if not response or not usage:
#                 self.logger.error(f"[主模型调用失败] record_id={record_id}, model={self.model_name}")
#                 return None
#
#             # 评估模型响应（带重试机制）
#             while retry_count <= max_retries:
#                 eval_prompt = f"问题是{question}，正确答案是{answer}，回答是{response}，评定的标准是{criteria}。只需给出最后的评分数字，不需要讲原因。"
#
#                 eval_response, eval_usage = self._get_response(
#                     self.eval_api_key,
#                     self.eval_base_url,
#                     system_prompt="你是一个评分专家，请根据标准对回答进行评分",
#                     user_prompt=eval_prompt,
#                     model=self.eval_model_name,
#                 )
#
#                 if not eval_response or not eval_usage:
#                     self.logger.error(f"[评分模型调用失败] record_id={record_id}, model={self.eval_model_name}")
#                     return None
#
#                 # 尝试从响应中提取数字
#                 score_match = re.search(r'\d+', eval_response)
#                 if score_match:
#                     final_score = score_match.group()
#                     break  # 成功获取评分，跳出循环
#                 else:
#                     retry_count += 1
#                     if retry_count <= max_retries:
#                         self.logger.warning(f"[评分提取失败，准备重试] record_id={record_id}, 响应内容: {eval_response}")
#                     else:
#                         self.logger.error(
#                             f"[评分提取失败，已达最大重试次数] record_id={record_id}, 最终响应内容: {eval_response}")
#                         return None
#
#             # 计算总token数
#             total_tokens = (getattr(usage, "total_tokens", 0) + getattr(eval_usage, "total_tokens", 0))
#
#             # 创建评估记录
#             EvaluationRecord.objects.create(
#                 evaluation=evaluation_batch,
#                 record_id=record_id,
#                 input_text=input_text,
#                 output_text=response,
#                 content_type=content_type,
#                 score=final_score,
#                 tokens=total_tokens,
#                 created_at=timezone.now(),
#                 updated_at=timezone.now(),
#             )
#
#             return record_id, prompt, response, final_score, total_tokens
#
#         except Exception as e:
#             self.logger.exception(f"[evaluate error] record_id={record_id} | {str(e)}")
#             return None
#
#     def evaluate_multiple(self, evaluation_batch):
#         """
#         执行批量评估
#         :param evaluation_batch: 评估批次对象
#         :return: 更新后的评估批次对象
#         """
#         try:
#             # 获取题库问题
#             eval_question = EvalQuestions.objects.get(pk=self.question_bank_id)
#             questions = eval_question.questions
#             total_samples = len(questions)
#
#             # 初始化统计数据
#             total_tokens = 0
#             total_score = 0.0
#             completed = 0
#             last_reported_progress = 0
#
#             # 初始化进度
#             update_evaluation_progress(self.project_id, evaluation_batch.id, 0, "正在评估题库", "evaluating")
#
#             for question in questions:
#                 # 执行单次评估
#                 result = self.evaluate(question, evaluation_batch)
#
#                 if result:
#                     total_tokens += result[4] if len(result) > 4 else 0
#                     try:
#                         total_score += float(result[3]) if len(result) > 3 else 0.0
#                     except (ValueError, TypeError):
#                         pass
#                     completed += 1
#
#                     # 计算当前进度
#                     progress = int((completed / total_samples) * 100)
#                     update_evaluation_progress(self.project_id, evaluation_batch.id, progress, "正在评估题库", "evaluating")
#
#                 # 检查用户是否取消了操作
#                 cancelled, save_evaluation,evaluation_name = check_user_cancelled(self.project_id, evaluation_batch.id)
#                 if cancelled and not save_evaluation:
#                     # 抛出异常来中断生成过程
#                     raise Exception("用户取消模型测试")
#
#             _, _, evaluation_name = check_user_cancelled(self.project_id, evaluation_batch.id)
#             # 更新评估批次数据
#             evaluation_batch.total_samples = completed
#             evaluation_batch.total_tokens = total_tokens
#             if completed > 0:
#                 evaluation_batch.average_score = total_score / completed
#             evaluation_batch.name = evaluation_name
#             evaluation_batch.save()
#
#             return evaluation_batch
#
#         except Exception as e:
#             raise Exception(f"批量评估过程中发生错误: {str(e)}")
#
#     def run_full_evaluation(self, api_key, base_url, model_name, sample_size):
#         """
#         执行完整评估（幻觉和毒性检测）
#         :param api_key: API密钥
#         :param base_url: API基础URL
#         :param model_name: 模型名称
#         :param sample_size: 样本大小
#         """
#         from model_evaluation.models import ModelEvalMetrics
#
#         # 检查是否已有评估结果
#         existing = ModelEvalMetrics.objects.filter(model_name=model_name).first()
#         if existing and existing.hallucination_accuracy is not None and existing.toxicity_accuracy is not None:
#             return existing
#
#         # 执行幻觉检测评估
#         hallucination_accuracy = self._hullucination_evaluation(api_key, base_url, model_name, sample_size)
#
#         # 执行毒性检测评估
#         toxicity_accuracy = self._toxicity_evaluation(api_key, base_url, model_name, sample_size)
#
#         # 保存评估结果
#         result, created = ModelEvalMetrics.objects.get_or_create(
#             model_name=model_name,
#             defaults={
#                 "hallucination_accuracy": hallucination_accuracy,
#                 "toxicity_accuracy": toxicity_accuracy,
#             },
#         )
#
#         if not created:
#             result.hallucination_accuracy = hallucination_accuracy
#             result.toxicity_accuracy = toxicity_accuracy
#             result.save()
#
#         return result
#
#     def _hullucination_evaluation(self, api_key, base_url, model_name, N_EVAL_SAMPLE_SIZE=100):
#         """
#         执行幻觉检测评估
#         """
#         df = download_benchmark_dataset(
#             "binary-hallucination-classification",
#             dataset_name="halueval_qa_data",
#         )
#
#         df = (
#             df.sample(n=N_EVAL_SAMPLE_SIZE)
#             .reset_index(drop=True)
#             .rename(columns={"query": "input", "response": "output"})
#         )
#
#         model = OpenAIModel(
#             api_key=api_key,
#             base_url=base_url,
#             model_name=model_name,
#             temperature=0.0,
#         )
#
#         rails = list(HALLUCINATION_PROMPT_RAILS_MAP.values())
#         hallucination_classifications = llm_classify(
#             dataframe=df,
#             template=HALLUCINATION_PROMPT_TEMPLATE,
#             model=model,
#             rails=rails,
#             concurrency=10,
#         )["label"].tolist()
#         true_labels = df["is_hallucination"].map(HALLUCINATION_PROMPT_RAILS_MAP).tolist()
#
#         hallucination_accuracy = accuracy_score(true_labels, hallucination_classifications)
#         return hallucination_accuracy
#
#     def _toxicity_evaluation(self, api_key, base_url, model_name, N_EVAL_SAMPLE_SIZE=100):
#         """
#         执行毒性检测评估
#         """
#         df = download_benchmark_dataset(
#             task="toxicity-classification",
#             dataset_name="wiki_toxic-test",
#         )
#
#         toxic_df = df[df["toxic"]]
#         non_toxic_df = df[~df["toxic"]]
#
#         min_count = min(len(toxic_df), len(non_toxic_df))
#
#         toxic_sample = toxic_df.sample(min_count, random_state=2)
#         non_toxic_sample = non_toxic_df.sample(min_count, random_state=2)
#
#         df = pd.concat([toxic_sample, non_toxic_sample], axis=0)
#         df = df.sample(n=min(N_EVAL_SAMPLE_SIZE, len(df)))
#         df = df.reset_index(drop=True).rename(columns={"text": "input"})
#
#         model = OpenAIModel(
#             api_key=api_key,
#             base_url=base_url,
#             model_name=model_name,
#             temperature=0.0,
#         )
#
#         rails = list(TOXICITY_PROMPT_RAILS_MAP.values())
#         toxic_classifications = llm_classify(
#             dataframe=df,
#             template=TOXICITY_PROMPT_TEMPLATE,
#             model=model,
#             rails=rails,
#             concurrency=10,
#         )["label"].tolist()
#         true_labels = df["toxic"].map(TOXICITY_PROMPT_RAILS_MAP).tolist()
#
#         toxicity_accuracy = accuracy_score(true_labels, toxic_classifications)
#         return toxicity_accuracy
