# app/langchain_client.py

from langchain_deepseek import ChatDeepSeek
from app.config import MODEL_NAME


def get_langchain_chat_model(temperature: float = 0.2) -> ChatDeepSeek:
    """
    创建 LangChain 的 DeepSeek 聊天模型对象
    默认直接读取环境变量里的 DEEPSEEK_API_KEY
    """

    return ChatDeepSeek(
        model=MODEL_NAME,
        temperature=temperature,
    )