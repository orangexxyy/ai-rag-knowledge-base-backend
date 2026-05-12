# app/langchain_client.py

# from langchain_deepseek import ChatDeepSeek
# from app.config import MODEL_NAME


# def get_langchain_chat_model(temperature: float = 0.2) -> ChatDeepSeek:
#     """
#     创建 LangChain 的 DeepSeek 聊天模型对象
#     默认直接读取环境变量里的 DEEPSEEK_API_KEY
#     """

#     return ChatDeepSeek(
#         model=MODEL_NAME,
#         temperature=temperature,
#     )
# app/langchain_client.py

from langchain_deepseek import ChatDeepSeek
from langchain_ollama import ChatOllama

from app.config import (
    MODEL_NAME,
    LLM_PROVIDER,
    DEEPSEEK_TEMPERATURE,
    OLLAMA_BASE_URL,
    OLLAMA_MODEL,
    OLLAMA_TEMPERATURE,
    OLLAMA_TOP_P,
    OLLAMA_NUM_PREDICT,
    OLLAMA_REPEAT_PENALTY,
)


def get_langchain_chat_model(temperature: float | None = None):
    """
    创建 LangChain 聊天模型对象。

    支持：
    - deepseek：云端 DeepSeek
    - ollama：本地 Ollama 模型
    """

    if LLM_PROVIDER == "deepseek":
        final_temperature = (
            DEEPSEEK_TEMPERATURE
            if temperature is None
            else temperature
        )

        return ChatDeepSeek(
            model=MODEL_NAME,
            temperature=final_temperature,
        )

    if LLM_PROVIDER == "ollama":
        final_temperature = (
            OLLAMA_TEMPERATURE
            if temperature is None
            else temperature
        )

        return ChatOllama(
            model=OLLAMA_MODEL,
            base_url=OLLAMA_BASE_URL,
            temperature=final_temperature,
            top_p=OLLAMA_TOP_P,
            num_predict=OLLAMA_NUM_PREDICT,
            repeat_penalty=OLLAMA_REPEAT_PENALTY,
        )

    raise ValueError(
        f"不支持的 LLM_PROVIDER：{LLM_PROVIDER}，"
        "请设置为 'deepseek' 或 'ollama'"
    )