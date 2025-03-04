from .one_api_client import call_one_api
from .prompt_templates import get_system_prompt, get_user_prompt

def generate_test_question(sub_label):
    """
    生成 AI 题目
    :param sub_label: 标签数据
    :return: AI 生成的 JSON 题目
    """
    system_prompt = get_system_prompt(sub_label)
    user_prompt = get_user_prompt(sub_label)
    return call_one_api(system_prompt, user_prompt)
