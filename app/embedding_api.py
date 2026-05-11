
from openai import OpenAI
from app.config import (
    DASHSCOPE_API_KEY,
    DASHSCOPE_BASE_URL,
    EMBEDDING_MODEL,
    EMBEDDING_DIMENSIONS
)

# 创建百炼客户端
client = OpenAI(
    api_key=DASHSCOPE_API_KEY,
    base_url=DASHSCOPE_BASE_URL
)


def get_embedding(text: str) -> list[float]:
    """
    把一段文本转换为 embedding 向量

    参数：
        text: 要转换的文本

    返回：
        embedding 向量（float 列表）
    """

    # 防止传入空字符串
    if not text or not text.strip():
        raise ValueError("传入的文本不能为空")

    # 调用 embedding 接口
    response = client.embeddings.create(
        model=EMBEDDING_MODEL,
        input=text,
        dimensions=EMBEDDING_DIMENSIONS,
        encoding_format="float"
    )

    # 取出第一个结果的向量
    embedding = response.data[0].embedding

    return embedding
# import os
# import requests
# # 创建一个测试数据
# def fake_embedding(text: str) -> list[float]:
#     return [0.99, 0.12]


# def openai_embedding(text: str) -> list[float]:
#     """
#     调用 OpenAI embedding API
#     当前先写骨架，等 key 可用后再测试
#     """
#     api_key = os.getenv("OPENAI_API_KEY")

#     if not api_key:
#         raise ValueError("未检测到 OPENAI_API_KEY")

#     url = "https://api.openai.com/v1/embeddings"

#     headers = {
#         "Authorization": f"Bearer {api_key}",
#         "Content-Type": "application/json"
#     }

#     data = {
#         "input": text,
#         "model": "text-embedding-3-small"
#     }

#     response = requests.post(url, headers=headers, json=data, timeout=60)
#     response.raise_for_status()

#     result = response.json()

#     return result["data"][0]["embedding"]


# # 将文本转化为 embedding
# def get_embedding(text: str, mode: str) -> list[float]:
    if mode == "openai":
        return openai_embedding(text=text)

    elif mode == "fake":
        return fake_embedding(text=text)

    else:
        raise ValueError("没有对应的 embedding 模式")