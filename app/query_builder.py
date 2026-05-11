from app.deepseek_api import rewrite_query_with_content
from app.config import USE_ASSISTANT_HISTORY


def build_route_context(
    history_messages: list[dict], question: str, max_history_turns: int
) -> str:
    """
    构造给 intent 路由使用的上下文文本

    注意：
    - 这里只做历史拼接
    - 不做 LLM 改写
    - 目的是避免在路由阶段就把问题提前“rag 化”
    """

    # 1. 只取最近几条历史，避免历史太长导致路由被噪声影响
    recent_messages = history_messages[-max_history_turns:] if history_messages else []

    history_parts = []

    for message in recent_messages:
        # 【修复点 1】用 get 更安全，避免脏数据缺字段时报错
        role = message.get("role", "")
        content = message.get("content", "").strip()

        # 【修复点 2】这里应该是 assistant，不是 asssitant
        # if role not in ["user", "assistant"]:
        if role not in ["user"]:
            continue

        # 【修复点 3】空内容应该跳过，而不是写一个无效的 content
        if not content:
            continue

        history_parts.append(f"{role}: {content}")

    history_text = "\n".join(history_parts)

    # 2. 如果没有历史，直接用当前问题做路由
    if not history_text:
        return question.strip()

    # 3. 有历史时，把历史和当前问题都交给 router
    return f"""
历史对话：
{history_text}

当前问题：
{question.strip()}
""".strip()

def rebuild_retrieval_query_with_llm(
    history_messages: list[dict], question: str, max_history_turns
) -> str:
    """
    构造用于 RAG 检索的问题字符串

    参数说明：
    - history_messages: 最近的历史消息列表，格式例如：
      [{"role": "user", "content": "..."}, {"role": "assistant", "content": "..."}]
    - question: 用户当前问题
    - max_history_turns: 最多参考最近几条历史消息（这里先按消息条数处理）

    返回：
    - 一个更适合做 embedding 检索的字符串
    """
    # 1. 只取最近几条历史，避免一下子拼太多噪声
    recent_messages = history_messages[-max_history_turns:] if history_messages else []

    # 2. 把历史消息拼成文本
    history_parts = []
    for msg in recent_messages:

        if USE_ASSISTANT_HISTORY:
            role = msg.get("role", "")
            content = msg.get("content", "").strip()

            if not content:
                continue

            # 这里保留 role，方便让检索问题里还有“谁说的”这个上下文
            history_parts.append(f"{role}: {content}")
        else:
            if msg.get("role") != "user":
                continue

            content = msg.get("content", "").strip()

            if not content:
                continue

            # 这里只保留 user 历史，并显式标注为 user，方便保留“谁说的”这个上下文
            history_parts.append(f"user: {content}")

    history_text = "\n".join(history_parts)

    # 3. 如果没有历史，就直接返回当前问题
    if not history_text:
        return question.strip()

    # 4. 如果有历史，就拼成一个更完整的检索问题
    retrieval_query = f"""
历史对话：
{history_text}

当前问题：
{question.strip()}
"""
    query = rewrite_query_with_content(content=retrieval_query)

    return query