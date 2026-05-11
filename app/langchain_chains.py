from langchain_core.messages import HumanMessage, AIMessage
from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder
from app.langchain_client import get_langchain_chat_model


def convert_history_to_lc_messages(history_messages: list[dict]) -> list:
    """
    将存储的历史聊天记录转为langchain可以处理的类型
    """
    lc_messages = []
    for messgae in history_messages:
        role = messgae.get("role")
        content = messgae.get("content").strip()
        if not content:
            continue
        if role == "user":
            lc_messages.append(HumanMessage(content))
        if role == "assistant":

            lc_messages.append(AIMessage(content))

    return lc_messages


def run_chat_chain(history_messages: list[dict], question: str) -> str:
    """
    普通聊天的prompt封装
    """
    prompt = ChatPromptTemplate.from_messages(
        [
            ("system", "你是一个有帮助的 AI 助手。请结合历史聊天内容，自然继续对话。"),
            MessagesPlaceholder("history"),
            ("human", "{question}"),
        ]
    )
    # 创建模型
    model = get_langchain_chat_model()
    chain = prompt | model
    # 发起请求
    response = chain.invoke(
        {
            "history": convert_history_to_lc_messages(history_messages),
            "question": question.strip(),
        }
    )
    return response.content


def run_rag_chain(question: str, reference_text: str) -> str:
    """
    rag聊天的prompt封装
    """
    prompt = ChatPromptTemplate.from_messages(
        [
            (
                "system",
                "你是一个基于资料进行问答的 AI 助手。"
                "请优先根据提供的参考资料回答问题。"
                "如果参考资料中没有明确答案，请明确说明“资料中没有明确提到”。"
                "不要脱离资料随意编造答案。",
            ),
            (
                "human",
                "用户的问题是：\n{question}\n\n"
                "相关参考资料是：\n{reference_text}\n\n"
                "请根据参考资料回答用户问题。",
            ),
        ]
    )
    model = get_langchain_chat_model()
    chain = prompt | model
    response = chain.invoke(
        {
            "question": question,
            "reference_text": reference_text,
        }
    )
    return response.content
