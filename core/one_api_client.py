# core/one_api_client.py

import os
from openai import OpenAI
import json
from typing import Tuple, Any

def get_available_models() -> list[str]:

    print("Attempting to fetch all available models from One-API...")
    try:
        client = OpenAI(
            api_key=OneAPIClient.API_KEY,
            base_url=OneAPIClient.API_BASE_URL,
        )
        models_response = client.models.list()
        # 提取并返回所有模型的 ID 列表
        return [model.id for model in models_response.data]
    except Exception as e:
        print(f"Failed to fetch model list: {e}")
        # 如果出错，返回一个空列表
        return []

class OneAPIClient:

    API_BASE_URL = "http://116.62.42.87:3000/v1"
    API_KEY = "sk-d90BKltXKj0ufwuw6bA9C51a5f08478dAb85269d93B5E956"

    def __init__(self, model: str):
        """
        初始化客户端。

        Args:
            model (str): 此客户端实例将要使用的模型名称, e.g., "qwen-max"。
        """
        self.model = model

        # 检查常量是否已配置
        if not self.API_KEY or "YOUR_NEW_SECURE_KEY_HERE" in self.API_KEY:
            raise ValueError("Please replace 'sk-YOUR_NEW_SECURE_KEY_HERE' with your actual new API key.")

        # 每个实例都使用类中定义的固定配置来创建客户端
        self.client = OpenAI(
            api_key=self.API_KEY,
            base_url=self.API_BASE_URL,
        )
        print(f"OneAPIClient for model '{self.model}' initialized.")

    def get_chat_response(self, system_prompt: str, prompt: str, **kwargs) -> str:

        params = {
            "model": self.model,
            "messages": [{"role": "system", "content": system_prompt}, {"role": "user", "content": prompt}],
            **kwargs
        }
        try:
            completion = self.client.chat.completions.create(**params)
            return completion.choices[0].message.content
        except Exception as e:
            print(f"Error calling model '{self.model}': {e}")
            raise

    def get_chat_response_with_usage(self, system_prompt: str, prompt: str, **kwargs) -> Tuple[str, Any]:
        """
        这个新方法会同时返回响应内容和token用量(usage)对象。
        它不会影响到调用 get_chat_response 的旧代码。
        """
        params = {
            "model": self.model,
            "messages": [{"role": "system", "content": system_prompt}, {"role": "user", "content": prompt}],
            **kwargs
        }
        try:
            completion = self.client.chat.completions.create(**params)
            # 同时返回响应内容和usage信息
            return completion.choices[0].message.content, completion.usage
        except Exception as e:
            print(f"Error calling model '{self.model}': {e}")
            # 发生错误时返回 None, None 以便上层处理
            return None, None