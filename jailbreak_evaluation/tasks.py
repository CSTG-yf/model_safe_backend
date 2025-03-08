from celery import shared_task
from .utils import ModelHandler,JailbreakWorkflow,JailbreakService


@shared_task
def run_jailbreak_workflow():   #后期添加一次可以run多个flow，同时测试多个llm
    print("进入run_jailbreak_workflow")
    model = ModelHandler()
    workflow = JailbreakWorkflow().workflow
    data = JailbreakService.get_all_questions()
    for item in data:
        print("本次的题目:",item)
        initial_state = {
            "category_index": item["category_index"],
            "title_index": item["title_index"],
            "prompt_num": item["prompt_num"],
            "current_question": "",
            "answer": "",
            "score": 0,
            "cycle_count": 0,
            "history": [],
            "evaluation": [],
            "objective": item["prompt"],
            "starting_string": item["starting_string"],
            "params": {"model_handler": model},
            "should_send_update": False
        }
        for step in workflow.stream(initial_state):
            initial_state["category_index"] = item["category_index"]
            initial_state["title_index"] = item["title_index"]
            initial_state["prompt_num"] = item["prompt_num"]
            for key, value in step.items():
                for sub_key, sub_value in value.items():
                    initial_state[sub_key] = sub_value