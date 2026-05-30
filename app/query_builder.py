from app.deepseek_api import rewrite_query_with_content
from app.config import USE_ASSISTANT_HISTORY


def build_route_context(
    history_messages: list[dict], question: str, max_history_turns: int
) -> str:
    """
    构造给 intent router 使用的上下文文本。

    注意：
    - 这里只拼接历史，不做 LLM 改写。
    - 目前只使用 user 历史，避免 assistant 回答噪声影响路由判断。
    """
    recent_messages = history_messages[-max_history_turns:] if history_messages else []

    history_parts = []

    for message in recent_messages:
        role = message.get("role", "")
        content = message.get("content", "").strip()

        if role not in ["user"]:
            continue
        if not content:
            continue

        history_parts.append(f"{role}: {content}")

    history_text = "\n".join(history_parts)

    if not history_text:
        return question.strip()

    return f"""
历史对话：
{history_text}

当前问题：
{question.strip()}
""".strip()


def rebuild_retrieval_query_with_llm(
    history_messages: list[dict],
    question: str,
    max_history_turns,
    memory_summary: str | None = None,
) -> str:
    """
    构造用于 RAG 检索的 retrieval_query。

    memory_summary 是可选的会话摘要上下文，只用于帮助 Query Rewrite
    理解多轮追问，不是知识库资料，也不是最终回答的事实依据。
    """
    recent_messages = history_messages[-max_history_turns:] if history_messages else []

    history_parts = []
    for msg in recent_messages:
        if USE_ASSISTANT_HISTORY:
            role = msg.get("role", "")
            content = msg.get("content", "").strip()

            if not content:
                continue

            # 保留 role，方便改写模型理解“谁说的”。
            history_parts.append(f"{role}: {content}")
        else:
            if msg.get("role") != "user":
                continue

            content = msg.get("content", "").strip()

            if not content:
                continue

            # 默认只保留 user 历史，减少 assistant 回答对检索问题的干扰。
            history_parts.append(f"user: {content}")

    history_text = "\n".join(history_parts)
    memory_summary_text = (memory_summary or "").strip()

    # memory_summary 为空时保持旧行为：没有历史就直接返回原问题，不触发 LLM rewrite。
    if not history_text and not memory_summary_text:
        return question.strip()

    # 没有 memory_summary 时使用原来的 prompt 结构，确保旧调用路径不变。
    if not memory_summary_text:
        retrieval_query = f"""
历史对话：
{history_text}

当前问题：
{question.strip()}
"""
        query = rewrite_query_with_content(content=retrieval_query)

        return query

    # memory_summary 只帮助 Query Rewrite 理解更早的会话上下文，
    # 不能作为知识库资料、reference_text 或事实依据。
    memory_summary_section = ""
    if memory_summary_text:
        memory_summary_section = f"""
会话摘要上下文：
{memory_summary_text}

注意：
上述会话摘要只用于理解用户追问的上下文，不是知识库资料，不是事实依据。
最终回答仍必须依赖后续检索得到的 reference_text。
""".strip()

    history_section = ""
    if history_text:
        history_section = f"""
历史对话：
{history_text}
""".strip()

    retrieval_query = f"""
{memory_summary_section}

{history_section}

当前问题：
{question.strip()}
""".strip()

    query = rewrite_query_with_content(content=retrieval_query)

    return query
