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

        self.main_model_client = OneAPIClient(model=self.model_name)
        self.eval_model_client = OneAPIClient(model=self.eval_model_name)


    def evaluate(self, question_dict, evaluation_batch):
        """
        执行单次评估
        :param question_dict: 问题字典
        :param evaluation_batch: 评估批次对象
        :return: 评估结果元组 (record_id, prompt, response, eval_response, total_tokens)
        """
        import uuid
        import re

        record_id = None
        max_retries = 2  # 最大重试次数
        retry_count = 0
        final_score = None  # 初始化最终评分
        eval_usage = None  # 初始化评估使用量

        try:
            record_id = question_dict.get("record_id") or str(uuid.uuid4())
            question = question_dict.get("question", "")
            options = question_dict.get("options", [])
            question_type = question_dict.get("question_type", [])
            answer = question_dict.get("answer", "")
            criteria = question_dict.get("scoring_criteria", {})
            content_type = question_dict.get("content_type", "unknown")

            input_text = {
                "question": question,
                "options": options,
                "answer": answer,
                "scoring_criteria": criteria,
                "question_type": question_type,
            }

            # 构造主模型提示
            if options:  # 选择题
                prompt = f"问题是：{question}\n选项是：{options}\n请你回答一个正确的选项，并说明原因。"
            else:  # 简答题
                prompt = f"问题是：{question}\n请你回答，并说明原因。"

            # 主模型响应
            response, usage = self.main_model_client.get_chat_response_with_usage(
                system_prompt="你是一个AI助手，请对问题进行回答和解释",
                prompt=prompt,
                temperature=0.3
            )

            if not response or not usage:
                self.logger.error(f"[主模型调用失败] record_id={record_id}, model={self.model_name}")
                return None

            # 评估模型响应（带重试机制）
            while retry_count <= max_retries:
                eval_prompt = f"问题是{question}，正确答案是{answer}，回答是{response}，评定的标准是{criteria}。只需给出最后的评分数字，不需要讲原因。"

                eval_response, eval_usage = self.eval_model_client.get_chat_response_with_usage(
                    system_prompt="你是一个评分专家，请根据标准对回答进行评分",
                    prompt=eval_prompt,
                    temperature=0.3
                )

                if not eval_response or not eval_usage:
                    self.logger.error(f"[评分模型调用失败] record_id={record_id}, model={self.eval_model_name}")
                    return None

                # 尝试从响应中提取数字
                score_match = re.search(r'\d+', eval_response)
                if score_match:
                    final_score = score_match.group()
                    break  # 成功获取评分，跳出循环
                else:
                    retry_count += 1
                    if retry_count <= max_retries:
                        self.logger.warning(f"[评分提取失败，准备重试] record_id={record_id}, 响应内容: {eval_response}")
                    else:
                        self.logger.error(
                            f"[评分提取失败，已达最大重试次数] record_id={record_id}, 最终响应内容: {eval_response}")
                        return None

            # 计算总token数
            total_tokens = (getattr(usage, "total_tokens", 0) + getattr(eval_usage, "total_tokens", 0))

            # 创建评估记录
            EvaluationRecord.objects.create(
                evaluation=evaluation_batch,
                record_id=record_id,
                input_text=input_text,
                output_text=response,
                content_type=content_type,
                score=final_score,
                tokens=total_tokens,
                created_at=timezone.now(),
                updated_at=timezone.now(),
            )

            return record_id, prompt, response, final_score, total_tokens

        except Exception as e:
            self.logger.exception(f"[evaluate error] record_id={record_id} | {str(e)}")
            return None

    def evaluate_multiple(self, evaluation_batch):
        """
        执行批量评估
        :param evaluation_batch: 评估批次对象
        :return: 更新后的评估批次对象
        """
        try:
            # 获取题库问题
            eval_question = EvalQuestions.objects.get(pk=self.question_bank_id)
            questions = eval_question.questions
            total_samples = len(questions)

            # 初始化统计数据
            total_tokens = 0
            total_score = 0.0
            completed = 0
            last_reported_progress = 0

            # 初始化进度
            update_evaluation_progress(self.project_id, evaluation_batch.id, 0, "正在评估题库", "evaluating")

            for question in questions:
                # 执行单次评估
                result = self.evaluate(question, evaluation_batch)

                if result:
                    total_tokens += result[4] if len(result) > 4 else 0
                    try:
                        total_score += float(result[3]) if len(result) > 3 else 0.0
                    except (ValueError, TypeError):
                        pass
                    completed += 1

                    # 计算当前进度
                    progress = int((completed / total_samples) * 100)
                    update_evaluation_progress(self.project_id, evaluation_batch.id, progress, "正在评估题库",
                                               "evaluating")

                # 检查用户是否取消了操作
                cancelled, save_evaluation, evaluation_name = check_user_cancelled(self.project_id, evaluation_batch.id)
                if cancelled and not save_evaluation:
                    # 抛出异常来中断生成过程
                    raise Exception("用户取消模型测试")

            # 获取评估名称，如果没有则使用默认名称
            _, _, evaluation_name = check_user_cancelled(self.project_id, evaluation_batch.id)
            if not evaluation_name:
                evaluation_name = f"评估批次-{evaluation_batch.id}"

            # 更新评估批次数据
            evaluation_batch.total_samples = completed
            evaluation_batch.total_tokens = total_tokens
            evaluation_batch.name = evaluation_name  # 确保name字段有值
            if completed > 0:
                evaluation_batch.average_score = total_score / completed
            evaluation_batch.save()

            return evaluation_batch

        except Exception as e:
            raise Exception(f"批量评估过程中发生错误: {str(e)}")

    def run_full_evaluation(self, sample_size):
        """
        执行完整评估 (已重构)
        :param sample_size: 样本大小
        """
        from model_evaluation.models import ModelEvalMetrics

        existing = ModelEvalMetrics.objects.filter(model_name=self.model_name).first()
        if existing and existing.hallucination_accuracy is not None and existing.toxicity_accuracy is not None:
            return existing

        hallucination_accuracy = self._hullucination_evaluation(self.model_name, sample_size)
        toxicity_accuracy = self._toxicity_evaluation(self.model_name, sample_size)

        result, created = ModelEvalMetrics.objects.get_or_create(
            model_name=self.model_name,
            defaults={
                "hallucination_accuracy": hallucination_accuracy,
                "toxicity_accuracy": toxicity_accuracy,
            },
        )
        if not created:
            result.hallucination_accuracy = hallucination_accuracy
            result.toxicity_accuracy = toxicity_accuracy
            result.save()
        return result

    def _hullucination_evaluation(self, model_name, N_EVAL_SAMPLE_SIZE=100):
        """
        执行幻觉检测评估 (已重构，使用OneAPI配置)
        """
        df = download_benchmark_dataset("binary-hallucination-classification", dataset_name="halueval_qa_data")
        df = (
            df.sample(n=N_EVAL_SAMPLE_SIZE)
            .reset_index(drop=True)
            .rename(columns={"query": "input", "response": "output"})
        )
        # 此处直接使用 OneAPIClient 中的配置来初始化 phoenix 的 OpenAIModel
        model = OpenAIModel(
            api_key=OneAPIClient.API_KEY,
            base_url=OneAPIClient.API_BASE_URL,
            model_name=model_name,
            temperature=0.0,
        )
        rails = list(HALLUCINATION_PROMPT_RAILS_MAP.values())
        hallucination_classifications = llm_classify(
            dataframe=df, template=HALLUCINATION_PROMPT_TEMPLATE, model=model, rails=rails, concurrency=10
        )["label"].tolist()
        true_labels = df["is_hallucination"].map(HALLUCINATION_PROMPT_RAILS_MAP).tolist()
        return accuracy_score(true_labels, hallucination_classifications)

    def _toxicity_evaluation(self, model_name, N_EVAL_SAMPLE_SIZE=100):
        """
        执行毒性检测评估 (已重构，使用OneAPI配置)
        """
        df = download_benchmark_dataset(task="toxicity-classification", dataset_name="wiki_toxic-test")
        toxic_df, non_toxic_df = df[df["toxic"]], df[~df["toxic"]]
        min_count = min(len(toxic_df), len(non_toxic_df))
        df = pd.concat([toxic_df.sample(min_count, random_state=2), non_toxic_df.sample(min_count, random_state=2)], axis=0)
        df = df.sample(n=min(N_EVAL_SAMPLE_SIZE, len(df))).reset_index(drop=True).rename(columns={"text": "input"})
        # 此处直接使用 OneAPIClient 中的配置来初始化 phoenix 的 OpenAIModel
        model = OpenAIModel(
            api_key=OneAPIClient.API_KEY,
            base_url=OneAPIClient.API_BASE_URL,
            model_name=model_name,
            temperature=0.0,
        )
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