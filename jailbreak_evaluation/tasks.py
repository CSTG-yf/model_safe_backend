import hashlib

from celery import shared_task
from .utils import ModelHandler,JailbreakWorkflow,JailbreakService


@shared_task
def run_jailbreak_workflow(model_name, ev_time,project_id,mode):   #后期添加一次可以run多个flow，同时测试多个llm
    print("进入run_jailbreak_workflow")
    session_id = hashlib.sha256((model_name + '_' + ev_time).encode()).hexdigest()
    session_name = model_name + '_' + ev_time
    model = ModelHandler()
    workflow = JailbreakWorkflow().workflow
    data = JailbreakService.get_all_questions()
    for item in data:
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
            "session_id": session_id,
            "session_name": session_name,
            "project_id": project_id,
            "mode": mode
        }
        for step in workflow.stream(initial_state):
            initial_state["category_index"] = item["category_index"]
            initial_state["title_index"] = item["title_index"]
            initial_state["prompt_num"] = item["prompt_num"]
            for key, value in step.items():
                for sub_key, sub_value in value.items():
                    initial_state[sub_key] = sub_value