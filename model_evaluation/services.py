from typing import Dict, List, Optional
import logging
from question_bank.models import EvalQuestions
from .utils import run_full_evaluation, Evaluator
from .models import ModelAPI, ModelEvaluationHALUCINATION_TOXICITY, EvaluationBatch, EvaluationRecord

logger = logging.getLogger(__name__)

class ModelEvaluationService:
    @staticmethod
    def trigger_evaluation(
        model_config: Dict[str, str],
        eval_model_config: Dict[str, str],
        question_bank_id: int,
        sample_size: int = 100
    ) -> Dict:
        """
        触发模型评估，包括问题评估、幻觉评估和毒性评估
        
        Args:
            model_config: 待评估模型的配置
                - name: 模型名称
                - api_key: API密钥
                - base_url: API基础URL
            eval_model_config: 评估模型的配置（用于评分）
                - name: 模型名称
                - api_key: API密钥
                - base_url: API基础URL
            question_bank_id: 要评估的题库ID
            sample_size: 幻觉和毒性评估的样本数量
            
        Returns:
            Dict: 包含评估状态和批次ID的字典
        """
        try:
            required_fields = ['name', 'api_key', 'base_url']
            for config in [model_config, eval_model_config]:
                for field in required_fields:
                    if field not in config:
                        raise ValueError(f"Missing required field: {field}")

            try:
                eval_questions = EvalQuestions.objects.get(question_bank_id=question_bank_id)
            except EvalQuestions.DoesNotExist:
                raise ValueError(f"Question bank with ID {question_bank_id} not found")

            batch = EvaluationBatch.objects.create(
                name=f"Comprehensive Evaluation {model_config['name']}",
                model_name=model_config['name'],
                question_bank_id=str(question_bank_id)
            )

            questions = []
            for q in eval_questions.questions:
                question_data = [
                    str(q.get('question_id', '')),  # record_id
                    q.get('source', ''),            # source
                    q.get('content_type', ''),      # content_type
                    q.get('question_type', ''),     # question_type
                    q.get('question', ''),          # question
                    q.get('options', []),           # options
                    q.get('answer', ''),            # answer
                    q.get('scoring_criteria', '')   # scoring_criteria
                ]
                questions.append(question_data)

            evaluator = Evaluator(
                api_key=model_config['api_key'],
                base_url=model_config['base_url'],
                model_name=model_config['name'],
                eval_api_key=eval_model_config['api_key'],
                eval_base_url=eval_model_config['base_url'],
                eval_model_name=eval_model_config['name'],
                question_bank_id=question_bank_id
            )
            evaluator.evaluate_multiple(questions)

            run_full_evaluation(
                api_key=model_config['api_key'],
                base_url=model_config['base_url'],
                model_name=model_config['name'],
                sample_size=sample_size
            )

            return {
                'status': 'success',
                'batch_id': batch.id,
                'message': 'Evaluation started successfully'
            }

        except Exception as e:
            logger.error(f"Error triggering evaluation: {str(e)}")
            return {
                'status': 'error',
                'message': f"Failed to start evaluation: {str(e)}"
            }

    @staticmethod
    def get_evaluation_summary(batch_id: int) -> Dict:
        """
        获取评估的总数据，包括问题评估统计和幻觉毒性评估结果
        
        Args:
            batch_id: 评估批次ID
            
        Returns:
            Dict: 包含评估总数据的字典
        """
        try:
            batch = EvaluationBatch.objects.get(id=batch_id)
            
            hallucination_toxicity = ModelEvaluationHALUCINATION_TOXICITY.objects.get(
                model_name=batch.model_name
            )

            eval_questions = EvalQuestions.objects.get(question_bank_id=batch.question_bank_id)

            return {
                'status': 'success',
                'batch_id': batch_id,
                'model_name': batch.model_name,
                'question_bank_id': batch.question_bank_id,
                'question_bank_title': eval_questions.exam_title,
                'question_evaluation': {
                    'total_questions': batch.total_records,
                    'average_score': batch.average_score,
                    'total_tokens': batch.total_tokens
                },
                'hallucination_evaluation': {
                    'accuracy': hallucination_toxicity.hallucination_accuracy
                },
                'toxicity_evaluation': {
                    'accuracy': hallucination_toxicity.toxicity_accuracy
                }
            }

        except Exception as e:
            logger.error(f"Error getting evaluation summary: {str(e)}")
            return {
                'status': 'error',
                'message': f"Failed to get evaluation summary: {str(e)}"
            }

    @staticmethod
    def get_evaluation_details(batch_id: int) -> Dict:
        """
        获取评估的详细结果，包括每个问题的具体评估记录
        
        Args:
            batch_id: 评估批次ID
            
        Returns:
            Dict: 包含详细评估记录的字典
        """
        try:
            batch = EvaluationBatch.objects.get(id=batch_id)
            
            records = EvaluationRecord.objects.filter(question_bank_id=batch.question_bank_id)
            
            details = []
            for record in records:
                details.append({
                    'record_id': record.record_id,
                    'input': record.input,
                    'output': record.output,
                    'score': record.score,
                    'tokens': record.tokens,
                    'created_at': record.created_at
                })

            return {
                'status': 'success',
                'batch_id': batch_id,
                'total_records': len(details),
                'details': details
            }

        except Exception as e:
            logger.error(f"Error getting evaluation details: {str(e)}")
            return {
                'status': 'error',
                'message': f"Failed to get evaluation details: {str(e)}"
            }

    
