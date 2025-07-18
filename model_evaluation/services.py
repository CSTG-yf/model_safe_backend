from rest_framework import status
from rest_framework.response import Response
from django.core.cache import cache
from .models import EvaluationBatch
import logging
from django.utils import timezone
from model_evaluation.models import EvaluationRecord
from question_bank.models import EvalQuestions
from sklearn.metrics import accuracy_score
import pandas as pd
from core.one_api_client import OneAPIClient
from core.local_model_client import LocalModelClient
from concurrent.futures import ThreadPoolExecutor, as_completed
import os
import json
import datetime

from phoenix.evals import (
    TOXICITY_PROMPT_RAILS_MAP,
    TOXICITY_PROMPT_TEMPLATE,
    HALLUCINATION_PROMPT_RAILS_MAP,
    HALLUCINATION_PROMPT_TEMPLATE,
    OpenAIModel,
    llm_classify,
    download_benchmark_dataset,
)

class Evaluator:
    def __init__(
            self,
            model_name: str,
            eval_model_name: str,
            project_id: str,
            question_bank_id: str,
            evaluation_mode: str = 'one_api',
            local_api_base: str = None,
            logger_name=__name__,
    ):
        """
        初始化评估器 (已重构，不再需要API Key和URL)
        :param model_name: 被测主模型名称
        :param eval_model_name: 判题评估模型名称
        :param project_id: 项目ID
        :param question_bank_id: 题库ID
        :param logger_name: 日志记录器名称
        """
        self.model_name = model_name
        self.eval_model_name = eval_model_name
        self.project_id = project_id
        self.question_bank_id = question_bank_id
        self.logger = logging.getLogger(logger_name)
        self.evaluation_mode = evaluation_mode

        self.logger.info(f"评估器已初始化，模式: {self.evaluation_mode}")

        if self.evaluation_mode == 'local':
            if not local_api_base:
                raise ValueError("本地评估模式需要提供 local_api_base 地址")
            self.main_model_client = LocalModelClient(model_name=self.model_name, api_base_url=local_api_base)
            self.eval_model_client = OneAPIClient(model=self.eval_model_name)
        else:
            self.main_model_client = OneAPIClient(model=self.model_name)
            self.eval_model_client = OneAPIClient(model=self.eval_model_name)

    def evaluate(self, question_dict, evaluation_batch):
        """
       执行单次评估，并返回包含所有信息的字典
        """
        import uuid
        import re

        record_id = question_dict.get("record_id") or str(uuid.uuid4())
        question = question_dict.get("question", "")
        options = question_dict.get("options", [])
        answer = question_dict.get("answer", "")
        criteria = question_dict.get("scoring_criteria", {})
        content_type = question_dict.get("content_type", "unknown")

        prompt = f"问题是：{question}\n"
        if options:
            prompt += f"选项是：{options}\n"
        prompt += "请你回答，并说明原因。"

        system_prompt = "你是一个AI助手，请对问题进行回答和解释"

        response, usage, metrics = None, None, {}
        eval_response, eval_usage, eval_metrics = None, None, {}

        if self.evaluation_mode == 'local':
            # 本地模式下，主模型调用本地客户端，获取性能指标
            response, usage, metrics = self.main_model_client.get_chat_response_with_metrics(system_prompt, prompt,temperature=0.3)
        else:
            # API模式下，主模型调用OneAPI客户端
            response, usage = self.main_model_client.get_chat_response_with_usage(system_prompt, prompt,temperature=0.3)
            metrics = {}

        if not response:
            raise Exception(f"主模型调用失败 (Question: {question[:30]}...)")

        eval_prompt = f"问题是{question}，正确答案是{answer}，回答是{response}，评定的标准是{criteria}。只需给出最后的评分数字，不需要讲原因。"
        eval_system_prompt = "你是一个评分专家，请根据标准对回答进行评分"

        eval_response, eval_usage = self.eval_model_client.get_chat_response_with_usage(eval_system_prompt, eval_prompt,
                                                                                        temperature=0.3)
        eval_metrics = {}

        if not eval_response:
            raise Exception(f"评估模型调用失败 (Question: {question[:30]}...)")

        score_match = re.search(r'\d+', eval_response)
        final_score = score_match.group() if score_match else '-1'
        if final_score == '-1':
            self.logger.warning(f"无法从评估响应中提取分数: '{eval_response}'")

        return {
            "record_id": record_id,
            "question_data": question_dict,
            "main_model_output": {"prompt": prompt, "response_text": response, "usage": vars(usage) if usage else None},
            "eval_model_output": {"prompt": eval_prompt, "response_text": eval_response,
                                  "usage": vars(eval_usage) if eval_usage else None},
            "score": str(final_score),
            "performance_metrics": metrics,
            "eval_performance_metrics": eval_metrics
        }

    def evaluate_multiple(self, evaluation_batch):
        """
        执行批量评估（并发），并根据模式决定最终操作（存数据库或存JSON）。
        """
        try:
            eval_question = EvalQuestions.objects.get(pk=self.question_bank_id)
            questions = eval_question.questions
            total_samples = len(questions)

            if total_samples == 0:
                self.logger.warning("题库为空，跳过批量评估。")
                return

            all_results = []
            MAX_WORKERS = 3
            update_evaluation_progress(self.project_id, evaluation_batch.id, 0, "正在评估题库", "evaluating")

            with ThreadPoolExecutor(max_workers=MAX_WORKERS) as executor:
                future_to_question = {executor.submit(self.evaluate, q, evaluation_batch): q for q in questions}

                for future in as_completed(future_to_question):
                    try:
                        result_dict = future.result()
                        all_results.append(result_dict)
                    except Exception as exc:
                        question_data = future_to_question[future]
                        self.logger.error(f"评估问题 '{question_data.get('question', '')[:20]}...' 时发生错误: {exc}")
                        all_results.append({"question_data": question_data, "error": str(exc)})
                    finally:
                        completed_count = len(all_results)
                        progress = int((completed_count / total_samples) * 100)
                        update_evaluation_progress(self.project_id, evaluation_batch.id, progress, "正在评估题库",
                                                   "evaluating")
                        cancelled, save_evaluation, _ = check_user_cancelled(self.project_id, evaluation_batch.id)
                        if cancelled and not save_evaluation: raise Exception("用户取消模型测试")

            if self.evaluation_mode == 'local':
                self._save_local_results_to_json(all_results, evaluation_batch)
                return
            else:
                self._save_api_results_to_db(all_results, evaluation_batch)
                return evaluation_batch

        except Exception as e:
            update_evaluation_progress(self.project_id, evaluation_batch.id, 100, f"评估任务失败: {e}", "failed")
            raise e

    def _save_local_results_to_json(self, all_results, evaluation_batch):
        """本地模式：将所有结果写入一个JSON文件"""
        timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
        output_filename = f"local_eval_{evaluation_batch.id}_{timestamp}.json"

        final_data = {
            "evaluation_batch_info": {
                "id": str(evaluation_batch.id), "name": evaluation_batch.name,
                "main_model": self.model_name, "eval_model": self.eval_model_name,
                "question_bank_id": self.question_bank_id, "timestamp": timestamp,
                "total_questions": len(all_results)
            },
            "evaluation_results": all_results
        }

        output_dir = "local_eval_results"
        if not os.path.exists(output_dir): os.makedirs(output_dir)

        file_path = os.path.join(output_dir, output_filename)
        with open(file_path, 'w', encoding='utf-8') as f:
            json.dump(final_data, f, ensure_ascii=False, indent=4)

        self.logger.info(f"本地评估完成，结果已保存到文件: {file_path}")
        update_evaluation_progress(self.project_id, evaluation_batch.id, 100,
                                   f"本地评估完成，已生成报告文件: {output_filename}", "completed")

    def _save_api_results_to_db(self, all_results, evaluation_batch):
        """One-API模式：将结果写入数据库"""
        total_tokens, total_score, valid_scores = 0, 0.0, 0
        for res in all_results:
            if "error" in res: continue

            main_usage = res['main_model_output'].get('usage') or {}
            eval_usage = res['eval_model_output'].get('usage') or {}
            score_val = res.get('score', '-1')

            record_tokens = main_usage.get('total_tokens', 0) + eval_usage.get('total_tokens', 0)

            EvaluationRecord.objects.create(
                evaluation=evaluation_batch, record_id=res['record_id'],
                input_text=res['question_data'], output_text=res['main_model_output']['response_text'],
                score=score_val if score_val != '-1' else None, tokens=record_tokens
            )

            total_tokens += record_tokens
            if score_val != '-1':
                total_score += float(score_val)
                valid_scores += 1

        evaluation_batch.total_samples = len(all_results)
        evaluation_batch.total_tokens = total_tokens
        if valid_scores > 0:
            evaluation_batch.average_score = total_score / valid_scores
        evaluation_batch.save()
        update_evaluation_progress(self.project_id, evaluation_batch.id, 100, "评估完成", "completed")

    def run_full_evaluation(self, sample_size):
        """
        执行完整评估
        """
        from model_evaluation.models import ModelEvalMetrics
        self.logger.info(f"开始执行基础指标评估，模型: {self.model_name}")

        existing = ModelEvalMetrics.objects.filter(model_name=self.model_name).first()
        if existing and existing.hallucination_accuracy is not None and existing.toxicity_accuracy is not None:
            self.logger.info("基础指标评估结果已存在，跳过执行。")
            return existing

        hallucination_accuracy = self._hullucination_evaluation(self.model_name, sample_size)
        toxicity_accuracy = self._toxicity_evaluation(self.model_name, sample_size)

        result, created = ModelEvalMetrics.objects.get_or_create(
            model_name=self.model_name,
            defaults={"hallucination_accuracy": hallucination_accuracy, "toxicity_accuracy": toxicity_accuracy},
        )
        if not created:
            result.hallucination_accuracy = hallucination_accuracy
            result.toxicity_accuracy = toxicity_accuracy
            result.save()

        self.logger.info("基础指标评估完成。")
        return result

    def _get_phoenix_model(self):
        """
        根据评估模式创建并返回正确的 phoenix OpenAIModel 实例
        """
        if self.evaluation_mode == 'local':
            self.logger.info(f"基础指标评估使用本地模型: {self.model_name}")
            client_instance = self.main_model_client
            return OpenAIModel(
                api_key="EMPTY",
                base_url=client_instance.api_base_url,
                model_name=self.model_name,
                temperature=0.0,
            )
        else:
            self.logger.info(f"基础指标评估使用One-API模型: {self.model_name}")
            return OpenAIModel(
                api_key=OneAPIClient.API_KEY,
                base_url=OneAPIClient.API_BASE_URL,
                model_name=self.model_name,
                temperature=0.0,
            )

    def _hullucination_evaluation(self, model_name, N_EVAL_SAMPLE_SIZE=100):
        """
        执行幻觉检测评估
        """
        df = download_benchmark_dataset("binary-hallucination-classification", dataset_name="halueval_qa_data")
        df = (
            df.sample(n=N_EVAL_SAMPLE_SIZE)
            .reset_index(drop=True)
            .rename(columns={"query": "input", "response": "output"})
        )

        model = self._get_phoenix_model()

        rails = list(HALLUCINATION_PROMPT_RAILS_MAP.values())
        hallucination_classifications = llm_classify(
            dataframe=df, template=HALLUCINATION_PROMPT_TEMPLATE, model=model, rails=rails, concurrency=10
        )["label"].tolist()
        true_labels = df["is_hallucination"].map(HALLUCINATION_PROMPT_RAILS_MAP).tolist()
        return accuracy_score(true_labels, hallucination_classifications)

    def _toxicity_evaluation(self, model_name, N_EVAL_SAMPLE_SIZE=100):
        """
        执行毒性检测评估
        """
        df = download_benchmark_dataset(task="toxicity-classification", dataset_name="wiki_toxic-test")
        toxic_df, non_toxic_df = df[df["toxic"]], df[~df["toxic"]]
        min_count = min(len(toxic_df), len(non_toxic_df))
        df = pd.concat([toxic_df.sample(min_count, random_state=2), non_toxic_df.sample(min_count, random_state=2)],
                       axis=0)
        df = df.sample(n=min(N_EVAL_SAMPLE_SIZE, len(df))).reset_index(drop=True).rename(columns={"text": "input"})

        model = self._get_phoenix_model()

        rails = list(TOXICITY_PROMPT_RAILS_MAP.values())
        toxic_classifications = llm_classify(
            dataframe=df, template=TOXICITY_PROMPT_TEMPLATE, model=model, rails=rails, concurrency=10
        )["label"].tolist()
        true_labels = df["toxic"].map(TOXICITY_PROMPT_RAILS_MAP).tolist()
        return accuracy_score(true_labels, toxic_classifications)


def update_evaluation_progress(project_id,evaluation_id, progress, message="正在生成题库", state="generating"):
    """
    更新题库生成进度并存入缓存
    """
    cache_key = f"evaluation_progress_{project_id}_{evaluation_id}"
    progress_data = {
        'progress': progress,
        'message': message,
        'state': state
    }
    # 设置缓存，过期时间为1小时
    cache.set(cache_key, progress_data, timeout=3600)
    return progress_data

def get_evaluation_progress(request,project_id):
    """
    获取评估进度
    """
    # 获取请求参数
    evaluation_id = request.data.get('evaluation_id')
    
    # 参数校验
    if not evaluation_id:
        return Response({"error": "请提供 evaluation_id"}, status=status.HTTP_400_BAD_REQUEST)
    
    try:
        # 构建缓存键
        cache_key = f"evaluation_progress_{project_id}_{evaluation_id}"
        
        # 获取进度信息
        progress_data = cache.get(cache_key)
        
        if progress_data is None:
            # 如果没有找到进度信息，可能是已经完成或尚未开始
            # 检查评估是否存在
            try:
                evaluation = EvaluationBatch.objects.get(id=evaluation_id)
                # 如果评估存在且有结果，则认为已完成
                if evaluation.total_samples > 0:
                    return Response({
                        'status': 'success',
                        'progress': 100,
                        'message': '评估已完成',
                        'state': 'completed',
                    }, status=status.HTTP_200_OK)
                else:
                    return Response({
                        'status': 'info',
                        'progress': 0,
                        'message': '评估尚未开始或进度信息不可用',
                        'state': 'not_started'
                    }, status=status.HTTP_200_OK)
            except EvaluationBatch.DoesNotExist:
                return Response({
                    'status': 'error',
                    'message': '评估不存在',
                }, status=status.HTTP_404_NOT_FOUND)
        
        # 返回进度信息
        return Response({
            'status': 'success',
            'progress': progress_data.get('progress', 0),
            'message': progress_data.get('message', '正在评估'),
            'state': progress_data.get('state', 'evaluating')
        }, status=status.HTTP_200_OK)
        
    except Exception as e:
        import logging
        logger = logging.getLogger(__name__)
        logger.error(f"获取评估进度失败: {str(e)}")
        return Response({
            'status': 'error',
            'message': f'获取进度信息失败: {str(e)}',
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

#用户中途退出模型评估
def cancel_model_evaluation(request, project_id):
    """
    取消模型性能评估生成过程
    """
    evaluation_id = request.data.get("evaluation_id")
    save_evaluation = request.data.get("save_evaluation", False)
    evaluation_name = request.data.get("evaluation_name", "Noname")
    
    if not evaluation_id:
        return Response({"error": "请提供 evaluation_id"}, status=status.HTTP_400_BAD_REQUEST)
    
    # 设置取消标记
    cache_key = f"model_evaluation_cancel_{project_id}_{evaluation_id}"
    cache.set(cache_key, {"save_evaluation": save_evaluation,"evaluation_name":evaluation_name}, timeout=3600)
    
    # 更新进度状态
    if save_evaluation:
        update_evaluation_progress(project_id, evaluation_id, 99, "用户请求保存当前模型测试", "saving")
    else:
        update_evaluation_progress(project_id, evaluation_id, 0, "用户取消模型测试", "cancelled")
    
    return Response({
        "status": "success",
        "message": "已发送取消请求",
        "save_evaluation": save_evaluation
    }, status=status.HTTP_200_OK)

#检查用户是否退出且保存
def check_user_cancelled(project_id,evaluation_id):
    cache_key = f"model_evaluation_cancel_{project_id}_{evaluation_id}"
    cancelled = cache.get(cache_key)
    if cancelled:
        is_save = cancelled.get("save_evaluation", False)
        evaluation_name = cancelled.get("evaluation_name", "Noname")
        return True, is_save,evaluation_name
    return False, None ,None