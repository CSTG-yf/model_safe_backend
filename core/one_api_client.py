import json
import os
from openai import OpenAI

# 读取 One API 配置
ONE_API_BASE_URL = os.getenv("ONE_API_BASE_URL", "http://localhost:3000")
ONE_API_KEY = os.getenv("ONE_API_KEY", "sk-es41LZPUJEKhVm4A64BaB9AfF1F848F2A42167Ec817513Bc")

# 初始化 OpenAI 客户端
client = OpenAI(
    api_key=ONE_API_KEY,  # 使用 One API 的令牌
    base_url=f"{ONE_API_BASE_URL}/v1"  # One API 的中转地址
)

def call_one_api(system_prompt, user_prompt, model="qwen-max", max_tokens=1000):
    """
    通过 One API 代理 qwen-max 进行 AI 题目生成
    :param system_prompt: 系统指令
    :param user_prompt: 用户输入
    :param model: 选择的 AI 模型（默认 qwen-max）
    :param max_tokens: 生成的最大 token 数
    :return: AI 生成的 JSON 题目
    """
    try:
        # 调用 OpenAI 客户端
        response = client.chat.completions.create(
            model=model,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt}
            ],
            temperature=0.7,
            response_format={"type": "json_object"},  # 确保返回 JSON 格式
            max_tokens=max_tokens
        )

        # 解析返回内容
        if response.choices:
            return json.loads(response.choices[0].message.content)
        else:
            return {"error": "One API 返回数据格式错误"}

    except json.JSONDecodeError as e:
        print("JSON 解析错误：", str(e))
        print("原始返回内容：", response.choices[0].message.content)
        return None
    except Exception as e:
        return {"error": f"请求 One API 失败: {str(e)}"}