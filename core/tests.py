# core/tests.py

from django.test import TestCase

# 导入要测试的类和新的辅助函数
from .one_api_client import OneAPIClient, get_available_models


class OneApiModelConnectivityTest(TestCase):
    """
    集成测试：测试 One-API 的模型列表获取和所有模型的可用性。
    警告：此测试会发起真实的网络请求，并可能产生API调用费用。
    """

    def setUp(self):
        """在每个测试方法运行前执行的准备工作。"""
        # 如果密钥没有被替换，则跳过所有测试，避免无效请求。
        if "YOUR_NEW_SECURE_KEY_HERE" in OneAPIClient.API_KEY:
            self.skipTest("API_KEY is not configured in OneAPIClient. Skipping connectivity tests.")

    def test_fetch_and_verify_model_list(self):
        """
        测试目标1：获取所有能用的模型列表。
        """
        print("\n--- [Test 1] Fetching model list from One-API ---")

        # 调用我们的辅助函数
        self.available_models = get_available_models()

        # 断言我们成功获取到了一个列表
        self.assertIsInstance(self.available_models, list, "get_available_models() should return a list.")

        # 断言列表不为空，这证明我们成功连接到了 One-API 并获取了数据
        self.assertTrue(
            len(self.available_models) > 0,
            "Model list is empty. Check One-API server connection or channel configurations."
        )

        print(f"✅ Success! Found {len(self.available_models)} models: {self.available_models}")

    def test_all_models_are_available(self):
        """
        测试目标2：测试获取到的每个模型的可用性。
        """
        print("\n--- [Test 2] Testing availability of each model ---")

        # 首先，获取模型列表
        models_to_test = get_available_models()

        # 如果上一步就没获取到列表，这个测试就直接失败
        self.assertTrue(
            len(models_to_test) > 0,
            "Cannot test model availability because the initial model list is empty."
        )

        failures = []
        for model_name in models_to_test:
            # 使用 subTest 上下文管理器。
            # 这使得即使一个模型测试失败，整个测试函数也会继续运行，最后统一报告所有失败的子测试。
            with self.subTest(model=model_name):
                print(f"  - Testing model: {model_name}...")
                try:
                    # 为当前循环的模型创建一个客户端实例
                    client = OneAPIClient(model=model_name)

                    # 发起一个非常简单的调用
                    response = client.get_chat_response(
                        system_prompt="You are a test bot.",
                        prompt="Please reply with only the word: 'OK'",
                        temperature=0,
                        max_tokens=5  # 限制输出长度，节省时间和token
                    )

                    # 断言收到了非空的字符串响应
                    self.assertIsInstance(response, str)
                    self.assertTrue(len(response) > 0)
                    print(f"    ✅ OK! Model '{model_name}' is available.")

                except Exception as e:
                    # 如果发生任何异常，记录下来并让这个子测试失败
                    error_message = f"Model '{model_name}' failed availability check. Error: {e}"
                    print(f"    ❌ FAILED! {error_message}")
                    failures.append(error_message)

        # 在所有子测试运行完毕后，如果存在失败，则让整个测试用例失败，并打印所有错误信息
        if failures:
            self.fail("Some models failed the availability test:\n" + "\n".join(failures))