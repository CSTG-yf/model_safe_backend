from django.test import TestCase
from core.one_api_client import call_one_api

class OneApiTestCase(TestCase):
    def test_call_one_api_success(self):

        system_prompt = "你是一个数学题目生成器，生成一道数学题，用json格式返回"
        user_prompt = "请生成一道数学题"

        result = call_one_api(system_prompt, user_prompt)
        print(result)  # 打印返回结果，便于调试
