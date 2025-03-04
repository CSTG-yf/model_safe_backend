import json
import os
import requests

# 读取 One API 配置
ONE_API_BASE_URL = os.getenv("ONE_API_BASE_URL", "http://your-one-api-url.com")
ONE_API_KEY = os.getenv("ONE_API_KEY", "your-api-key")


def call_one_api(system_prompt, user_prompt, model="qwen-max", max_tokens=1000):
    """
    通过 One API 代理 qwen-max 进行 AI 题目生成
    :param system_prompt: 系统指令
    :param user_prompt: 用户输入
    :param model: 选择的 AI 模型（默认 qwen-max）
    :param max_tokens: 生成的最大 token 数
    :return: AI 生成的 JSON 题目
    """
    url = f"{ONE_API_BASE_URL}/v1/chat/completions"
    headers = {
        "Authorization": f"Bearer {ONE_API_KEY}",
        "Content-Type": "application/json"
    }
    data = {
        "model": model,
        "messages": [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt}
        ],
        "temperature": 0.7,
        "response_format": "json",
        "max_tokens": max_tokens
    }

    try:
        response = requests.post(url, json=data, headers=headers)
        response_data = response.json()

        if "choices" in response_data and response_data["choices"]:
            return json.loads(response_data["choices"][0]["message"]["content"])
        else:
            return {"error": "One API 返回数据格式错误"}

    except json.JSONDecodeError as e:
        print("原始返回内容：", response.text)
        print("JSON解析错误：", str(e))
        return None

    except requests.exceptions.RequestException as e:
        return {"error": f"请求 One API 失败: {str(e)}"}
