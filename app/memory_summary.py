import requests

from app.config import (
    DEEPSEEK_API_KEY,
    DEEPSEEK_BASE_URL,
    ENABLE_MEMORY_SUMMARY,
    MEMORY_RECENT_MESSAGES_KEEP,
    MEMORY_SUMMARY_MAX_CHARS,
    MEMORY_SUMMARY_MIN_CHARS,
    MEMORY_SUMMARY_MIN_MESSAGES,
    MEMORY_SUMMARY_UPDATE_INTERVAL,
    MODEL_NAME,
)


def _clean_message(message: dict) -> dict | None:
    role = message.get("role")
    content = message.get("content", "").strip()

    if role not in ["user", "assistant"]:
        return None
    if not content:
        return None

    return {
        "role": role,
        "content": content,
    }


def _format_messages(messages: list[dict]) -> str:
    parts = []

    for message in messages:
        clean_message = _clean_message(message)
        if clean_message is None:
            continue

        parts.append(f"{clean_message['role']}: {clean_message['content']}")

    return "\n".join(parts)


def select_messages_for_summary(
    history_messages: list[dict],
    summarized_message_count: int,
    recent_messages_keep: int = MEMORY_RECENT_MESSAGES_KEEP,
) -> list[dict]:
    """
    选择尚未被 summary 覆盖的历史消息，并保留最近若干条原始消息不参与压缩。
    """
    if summarized_message_count < 0:
        summarized_message_count = 0
    if recent_messages_keep < 0:
        recent_messages_keep = 0

    total_count = len(history_messages)
    end_index = max(summarized_message_count, total_count - recent_messages_keep)

    selected_messages = []
    for message in history_messages[summarized_message_count:end_index]:
        clean_message = _clean_message(message)
        if clean_message is not None:
            selected_messages.append(clean_message)

    return selected_messages


def should_update_memory_summary(
    history_messages: list[dict],
    summarized_message_count: int,
    enabled: bool = ENABLE_MEMORY_SUMMARY,
    min_messages: int = MEMORY_SUMMARY_MIN_MESSAGES,
    update_interval: int = MEMORY_SUMMARY_UPDATE_INTERVAL,
    min_chars: int = MEMORY_SUMMARY_MIN_CHARS,
    recent_messages_keep: int = MEMORY_RECENT_MESSAGES_KEEP,
) -> dict:
    """
    根据总消息数、新增未摘要消息数和字符数判断是否需要更新 session summary。
    """
    total_count = len(history_messages)
    candidate_messages = select_messages_for_summary(
        history_messages=history_messages,
        summarized_message_count=summarized_message_count,
        recent_messages_keep=recent_messages_keep,
    )
    candidate_text = _format_messages(candidate_messages)
    candidate_message_count = len(candidate_messages)
    candidate_char_count = len(candidate_text)

    if not enabled:
        should_update = False
        reason = "disabled"
    elif total_count < min_messages:
        should_update = False
        reason = "not_enough_total_messages"
    elif candidate_message_count < update_interval:
        should_update = False
        reason = "not_enough_new_messages"
    elif candidate_char_count < min_chars:
        should_update = False
        reason = "not_enough_new_chars"
    else:
        should_update = True
        reason = "ready"

    return {
        "should_update": should_update,
        "reason": reason,
        "total_message_count": total_count,
        "summarized_message_count": summarized_message_count,
        "candidate_message_count": candidate_message_count,
        "candidate_char_count": candidate_char_count,
    }


def build_memory_summary_prompt(
    previous_summary: str | None,
    new_messages: list[dict],
    max_chars: int = MEMORY_SUMMARY_MAX_CHARS,
) -> str:
    """
    构造增量 summary prompt：previous_summary + 新增对话 -> updated_summary。
    """
    previous_summary_text = (previous_summary or "").strip()
    new_messages_text = _format_messages(new_messages)

    if not previous_summary_text:
        previous_summary_text = "None"
    if not new_messages_text:
        new_messages_text = "None"

    return f"""
You are maintaining a minimal session memory summary for a RAG application.

This summary is only used later as auxiliary context for Query Rewrite.
It must not be treated as knowledge-base reference material.

Rules:
1. Keep only information useful for understanding future follow-up questions, user intent, references, constraints, entities, unresolved tasks, or important context.
2. Do not keep greetings, thanks, filler, repeated explanations, or irrelevant small talk.
3. Do not add external knowledge.
4. Do not infer or fabricate facts.
5. Do not write policy answers or knowledge-base content unless the conversation explicitly contained it.
6. Ignore templated failed-answer text such as "资料中没有找到足够相关的内容", "建议你补充更具体的问题", "资料中没有明确提到", and "未找到相关资料".
7. Do not summarize assistant low-confidence or retrieval-fallback replies as facts.
8. If the user's questions show a continuous topic, keep the user's topic or intent, such as "用户询问过事假申请", but do not keep "the assistant said there was not enough information".
9. The summary is only for future Query Rewrite context and must not influence reference_text or final factual answers directly.
10. Keep the updated summary around {max_chars} characters or fewer.
11. Return only the updated summary text. Do not add labels or explanations.

Previous summary:
{previous_summary_text}

New conversation messages:
{new_messages_text}

Updated summary:
""".strip()


def _call_deepseek_for_summary(prompt: str) -> str:
    """
    调用 DeepSeek 生成 session summary。

    注意：summary 生成默认使用 DeepSeek API，和最终 answer 的 LLM_PROVIDER 切换是两条独立路径。
    """
    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {DEEPSEEK_API_KEY}",
    }
    payload = {
        "model": MODEL_NAME,
        "messages": [
            {
                "role": "system",
                "content": "You are a careful conversation summarization assistant.",
            },
            {
                "role": "user",
                "content": prompt,
            },
        ],
        "temperature": 0.2,
        "stream": False,
    }

    response = requests.post(
        DEEPSEEK_BASE_URL,
        headers=headers,
        json=payload,
        timeout=30,
    )
    response.raise_for_status()

    result = response.json()
    return result["choices"][0]["message"]["content"].strip()


def summarize_session_memory(
    previous_summary: str | None,
    new_messages: list[dict],
    max_chars: int = MEMORY_SUMMARY_MAX_CHARS,
    llm_call=None,
) -> dict:
    """
    生成 updated session summary，并在 LLM 调用失败时返回 error 而不是抛出异常。
    """
    if not new_messages:
        return {
            "success": False,
            "updated_summary": (previous_summary or "").strip(),
            "error": "no_new_messages",
        }

    prompt = build_memory_summary_prompt(
        previous_summary=previous_summary,
        new_messages=new_messages,
        max_chars=max_chars,
    )

    try:
        # 默认走 DeepSeek；测试时可以通过 llm_call 注入假模型，避免真实网络调用。
        call_model = llm_call or _call_deepseek_for_summary
        updated_summary = call_model(prompt).strip()

        if len(updated_summary) > max_chars:
            updated_summary = updated_summary[:max_chars].rstrip()

        return {
            "success": True,
            "updated_summary": updated_summary,
            "error": None,
        }

    except Exception as exc:
        return {
            "success": False,
            "updated_summary": (previous_summary or "").strip(),
            "error": str(exc),
        }
