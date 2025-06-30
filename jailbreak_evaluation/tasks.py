import hashlib
from concurrent.futures import ThreadPoolExecutor
from celery import shared_task
from .utils import ModelHandler, JailbreakWorkflow, JailbreakService


def process_item(item, session_id, session_name, project_id, mode):
    try:
        model = ModelHandler()  # 每个线程有自己的ModelHandler实例
        workflow = JailbreakWorkflow().workflow
        
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
            "mode": int(mode)
        }
        
        for step in workflow.stream(initial_state):
            initial_state.update(step)
            
    except Exception as e:
        print(f"处理项目失败: {e}")

@shared_task
def run_jailbreak_workflow(model_name, ev_time, project_id, mode):
    print("进入run_jailbreak_workflow")
    print(f"收到的参数：{model_name},{ev_time},{project_id},{mode}")
    session_id = hashlib.sha256((str(project_id) + model_name + '_' + ev_time + '_' + str(mode)).encode()).hexdigest()
    session_name = str(project_id) + '_' + model_name + '_' + ev_time + '_' + str(mode)
    data = JailbreakService.get_simple_questions()
    
    # 根据Key数量设置最大线程数
    with ThreadPoolExecutor(max_workers= 5) as executor:
        futures = []
        for item in data:
            futures.append(executor.submit(
                process_item,
                item, session_id, session_name, project_id, mode
            ))
        
        for future in futures:
            future.result()