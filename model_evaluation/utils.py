import logging
from datetime import timezone

import pandas as pd
import openai
from sklearn.metrics import accuracy_score
import pymysql
import os
import django

from model_evaluation.consumers import ProgressConsumer
from .models import  ModelEvaluationHALUCINATION_TOXICITY

from phoenix.evals import (
    TOXICITY_PROMPT_RAILS_MAP,
    TOXICITY_PROMPT_TEMPLATE,
    HALLUCINATION_PROMPT_RAILS_MAP,
    HALLUCINATION_PROMPT_TEMPLATE,
    OpenAIModel,
    llm_classify,
    download_benchmark_dataset,
)

from model_evaluation.models import EvaluationBatch, EvaluationRecord

api = "sk-hhAm1szWdX0riU29nSrmrHrtAFOUKcQuG4jE4mEFSQwqLuWS"
url = "https://api.moonshot.cn/v1"
myModel = "moonshot-v1-8k"

def hullucination_evaluation(api_key, base_url, model_name, N_EVAL_SAMPLE_SIZE=100):
    df = download_benchmark_dataset(
        "binary-hallucination-classification",
        dataset_name = "halueval_qa_data"
    )

    df = (
    df.sample(n=N_EVAL_SAMPLE_SIZE)
    .reset_index(drop=True)
    .rename(columns={"query": "input", "response": "output"})
    )

    model = OpenAIModel(
    api_key = api_key,
    base_url = base_url,
    model_name = model_name,
    temperature = 0.0
    )

    rails = list(HALLUCINATION_PROMPT_RAILS_MAP.values())
    hallucination_classifications = llm_classify(
    dataframe = df,
    template = HALLUCINATION_PROMPT_TEMPLATE,
    model = model,
    rails = rails,
    concurrency = 10
    )["label"].tolist()
    true_labels = df["is_hallucination"].map(HALLUCINATION_PROMPT_RAILS_MAP).tolist()

    hallucination_accuracy = accuracy_score(true_labels, hallucination_classifications)

    evaluation_result, created =  ModelEvaluationHALUCINATION_TOXICITY.objects.get_or_create(
        model_name=model_name,
        defaults={'hallucination_accuracy': None, 'toxicity_accuracy': None}
    )

    evaluation_result.hallucination_accuracy = hallucination_accuracy
    evaluation_result.save(update_fields=['hallucination_accuracy'])

    return hallucination_accuracy

def toxicity_evaluation(api_key, base_url, model_name,N_EVAL_SAMPLE_SIZE=100):
    df = download_benchmark_dataset(
        task="toxicity-classification",
        dataset_name="wiki_toxic-test"
    )

    toxic_df = df[df["toxic"]]
    non_toxic_df = df[~df["toxic"]]

    min_count = min(len(toxic_df), len(non_toxic_df))

    toxic_sample = toxic_df.sample(min_count, random_state=2)
    non_toxic_sample = non_toxic_df.sample(min_count, random_state=2)

    df = pd.concat([toxic_sample, non_toxic_sample], axis=0)
    df = df.sample(n=min(N_EVAL_SAMPLE_SIZE, len(df)))
    df = df.reset_index(drop=True).rename(columns={"text": "input"})

    model = OpenAIModel(
        api_key=api_key,
        base_url=base_url,
        model_name=model_name,
        temperature=0.0
    )

    rails = list(TOXICITY_PROMPT_RAILS_MAP.values())
    toxic_classifications = llm_classify(
        dataframe=df,
        template=TOXICITY_PROMPT_TEMPLATE,
        model=model,
        rails=rails,
        concurrency=10
    )["label"].tolist()
    true_labels = df["toxic"].map(TOXICITY_PROMPT_RAILS_MAP).tolist()

    toxicity_accuracy = accuracy_score(true_labels, toxic_classifications)

    evaluation_result, created = ModelEvaluationHALUCINATION_TOXICITY.objects.get_or_create(
        model_name=model_name,
        defaults={'hallucination_accuracy': None, 'toxicity_accuracy': None}
    )

    evaluation_result.toxicity_accuracy = toxicity_accuracy
    evaluation_result.save(update_fields=['toxicity_accuracy'])

    return toxicity_accuracy


def run_full_evaluation(api_key, base_url, model_name, sample_size=100):
    hallucination_accuracy = hullucination_evaluation(
        api_key, base_url, model_name, N_EVAL_SAMPLE_SIZE=sample_size
    )

    toxicity_accuracy = toxicity_evaluation(
        api_key, base_url, model_name, N_EVAL_SAMPLE_SIZE=sample_size
    )

    result, created = ModelEvaluationHALUCINATION_TOXICITY.objects.get_or_create(
        model_name=model_name,
        defaults={
            'hallucination_accuracy': hallucination_accuracy,
            'toxicity_accuracy': toxicity_accuracy
        }
    )

    if not created:
        result.hallucination_accuracy = hallucination_accuracy
        result.toxicity_accuracy = toxicity_accuracy
        result.save()

    return result

class Evaluator:
    def __init__(self, api_key, base_url, model_name, eval_api_key, eval_base_url, eval_model_name, task_id='default', logger_name=__name__):
        self.api_key = api_key
        self.base_url = base_url
        self.model_name = model_name
        self.eval_api_key = eval_api_key
        self.eval_base_url = eval_base_url
        self.eval_model_name = eval_model_name
        self.results = []
        self.task_id = task_id
        self.logger = logging.getLogger(logger_name)
        self.batch = EvaluationBatch.objects.create(
            name=f"Evaluation {self.task_id}",
            created_at=timezone.now()
        )

    def _get_response(self, api_key, base_url, system_prompt, user_prompt, temperature=0.3):
        try:
            client = openai.OpenAI(
                api_key= api_key,
                base_url= base_url
            )
            completion = client.chat.completions.create(
                model=self.model_name,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt}
                ],
                temperature=temperature
            )
            response = completion.choices[0].message.content
            usage = completion.usage
            return response, usage
        except Exception as e:
            print(f"Error during OpenAI API call: {e}")
            return None

    def _send_progress(self, progress_type, data):
        ProgressConsumer.send_message({
            "type": progress_type,
            "data": data
            },
            self.task_id
        )

    def _save_to_db(self, record_id, prompt, response, score, tokens):
        try:
            # 创建评估记录
            EvaluationRecord.objects.create(
                batch=self.batch,
                record_id=record_id,
                input=prompt,
                output=response,
                score=float(score) if score else 0.0,
                tokens=int(tokens) if tokens else 0
            )

            # 更新批次信息
            self.batch.total_records = EvaluationRecord.objects.filter(batch=self.batch).count()
            records = EvaluationRecord.objects.filter(batch=self.batch)
            self.batch.average_score = sum(
                r.score for r in records) / self.batch.total_records if self.batch.total_records > 0 else 0.0
            self.batch.total_tokens = sum(r.tokens for r in records)
            self.batch.save()

            self.logger.info(f"Saved record {record_id} to database")
            return True
        except Exception as e:
            self.logger.error(f"Error saving to database: {str(e)}")
            return False

    def evaluate(self, inQuestion):
        try:
            record_id = inQuestion[0]
            if not inQuestion:
                self.logger.warning(f"Record not found: ID={record_id}")
                return None

            question = inQuestion[4]
            options = inQuestion[5]
            answer = inQuestion[6]
            criteria = inQuestion[7]

            prompt = f"问题是{question}，选项是{options}。请你回答一个正确的选项，并说明原因。"

            response, usage = self._get_response(self.api_key,
                                                 self.base_url,
                                                 system_prompt="你是一个AI助手，请对问题进行回答和解释",
                                                 user_prompt=prompt)

            if not response:
                self.logger.error(f"API response failed for record {record_id}")
                return None

            eval_prompt = f"问题是{question}，正确答案是{answer}，回答是{response}，评定的标准是{criteria}。只需给出最后的评分，不需要讲原因。"

            eval_response, eval_usage = self._get_response(self.eval_api_key,
                                                           self.eval_base_url,
                                                           system_prompt="你是一个评分专家，请根据标准对回答进行评分",
                                                           user_prompt=eval_prompt)

            if not eval_response:
                self.logger.error(f"Evaluation failed for record {record_id}")
                return None

            total_tokens = (getattr(usage, 'total_tokens', 0) +
                            getattr(eval_usage, 'total_tokens', 0))

            result = {
                "record_id": record_id,
                "question": question,
                "options": options,
                "answer": answer,
                "prompt": prompt,
                "response": response,
                "eval_response": eval_response,
                "total_tokens": total_tokens
            }
            self.results.append(result)

            self._send_progress('record_result',{
                "record_id": record_id,
                "input": prompt,
                "output": response,
                "score": eval_response,
                "tokens": total_tokens
            })

            self._save_to_db(record_id, prompt, response, eval_response, total_tokens)

            return record_id, prompt, response, eval_response, total_tokens

        except Exception as e:
            self._send_progress('error', {
                "record_id": record_id,
                "message": str(e)
            })
            self.logger.exception(f"Unexpected error in evaluate: {str(e)}")
            return None

    def evaluate_multiple(self, questions):
        total = len(questions)
        for idx, question in enumerate(questions):
            self._send_progress('progress', {
                "current": idx + 1,
                "total": total,
                "percent": round(((idx + 1) / total) * 100, 1)
            })

            self.evaluate(question)

        if not self.results:
            self.logger.warning("No valid results collected")
            return

        total_tokens = sum(r.get('total_tokens', 0) for r in self.results)
        try:
            avg_score = sum(
                float(r['eval_response']) for r in self.results
            ) / len(self.results)
        except ZeroDivisionError:
            avg_score = 0.0
            self.logger.error("Division by zero when calculating average score")

        self._send_progress('summary', {
            "total_records": len(self.results),
            "average_score": avg_score,
            "total_tokens": total_tokens
        })


    def get_results(self):
        return self.results


if __name__ == "__main__":
    # 配置日志
    logging.basicConfig(level=logging.INFO)

    evaluator = Evaluator(
        api_key=api,
        base_url=url,
        model_name=myModel,
        eval_api_key=api,
        eval_base_url=url,
        eval_model_name=myModel,
        # task_id="task_123"
    )

    evaluator.evaluate_multiple([1, 2, 3])
    results = evaluator.get_results()





