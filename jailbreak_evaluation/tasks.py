import hashlib
import logging
from concurrent.futures import ThreadPoolExecutor
from celery import shared_task
from .utils import ModelHandler, JailbreakWorkflow, JailbreakService


logger = logging.getLogger(__name__)


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
            
    except Exception:
        logger.exception(
            "Failed to process jailbreak item category=%s title=%s prompt=%s",
            item["category_index"],
            item["title_index"],
            item["prompt_num"],
        )

@shared_task
def run_jailbreak_workflow(model_name, ev_time, project_id, mode):
    logger.info(
        "Starting jailbreak workflow model=%s ev_time=%s project_id=%s mode=%s",
        model_name,
        ev_time,
        project_id,
        mode,
    )
    session_id = hashlib.sha256((str(project_id) + model_name + '_' + ev_time + '_' + str(mode)).encode()).hexdigest()
    session_name = str(project_id) + '_' + model_name + '_' + ev_time + '_' + str(mode)
    data = JailbreakService.get_simple_questions()
    
    # 使用线程池并发处理每个item
    with ThreadPoolExecutor(max_workers=min(2, len(data))) as executor:  # 最多4个线程或数据项数量
        futures = []
        for item in data:
            futures.append(executor.submit(
                process_item,
                item, session_id, session_name, project_id, mode
            ))
        
        # 等待所有任务完成
        for future in futures:
            try:
                future.result()  # 获取结果，如有异常会抛出
            except Exception:
                logger.exception("Jailbreak workflow future failed")
