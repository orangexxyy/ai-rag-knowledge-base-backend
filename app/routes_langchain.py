# app/routes_langchain.py

from fastapi import APIRouter, Request
import traceback

from app.models import AskRequest
from app.utils import success_response, error_response, is_obvious_chat_message
from app.config import (
    EMBEDDING_MODEL,
    RETURN_DEBUG_INFO,
    MAX_HISTORY_TURNS,
    ENABLE_MEMORY_SUMMARY,
    HYBRID_RECALL_K,
    TOP_K,
    USE_RERANKER,
    RERANK_CANDIDATE_K,
    RERANKER_PROVIDER,
    LLM_PROVIDER,
    MODEL_NAME,
    OLLAMA_MODEL,
    MEMORY_RECENT_MESSAGES_KEEP,
    MEMORY_SUMMARY_MIN_CHARS,
    MEMORY_SUMMARY_UPDATE_INTERVAL,
)
from app.chat_history_store import (
    get_memory_summary,
    get_session_history,
    save_turn,
    upsert_memory_summary,
)
from app.memory_summary import (
    select_messages_for_summary,
    should_update_memory_summary,
    summarize_session_memory,
)
from app.query_builder import build_route_context, rebuild_retrieval_query_with_llm
from app.semantic_router import semantic_route
from app.embedding_api import get_embedding
from app.hybrid_search import hybrid_search
from app.langchain_chains import run_chat_chain, run_rag_chain
from app.reranker import rerank_chunks_by_llm, rerank_chunks_by_dashscope

router_langchain = APIRouter()


def build_answer_llm_debug(answer_generated_by_llm: bool = True) -> dict:
    """
    构造最终回答模型的调试信息。

    注意：
    - 这里描述的是“最终 answer 由哪个模型生成”
    - 不代表 embedding / reranker / query rewrite 都是本地模型
    """

    # low_confidence 这类答案是系统兜底文本，不是模型生成
    if not answer_generated_by_llm:
        return {
            "answer_source": "system_fallback",
            "answer_llm_provider": None,
            "answer_llm_model": None,
            "answer_llm_is_local": False,
        }

    # Ollama 本地模型
    if LLM_PROVIDER == "ollama":
        return {
            "answer_source": "ollama_local_model",
            "answer_llm_provider": LLM_PROVIDER,
            "answer_llm_model": OLLAMA_MODEL,
            "answer_llm_is_local": True,
        }

    # 默认 DeepSeek 云端模型
    return {
        "answer_source": "deepseek_api",
        "answer_llm_provider": LLM_PROVIDER,
        "answer_llm_model": MODEL_NAME,
        "answer_llm_is_local": False,
    }


def build_memory_debug(
    memory_summary_record: dict | None,
    summary_used_for_query_rewrite: bool = False,
) -> dict:
    """
    构造 memory_summary 调试信息。

    注意：summary_preview 只展示摘要前一小段，避免把完整会话摘要返回给前端。
    """
    summary_text = ""
    summarized_message_count = 0

    if memory_summary_record:
        summary_text = memory_summary_record.get("summary", "") or ""
        summarized_message_count = memory_summary_record.get(
            "summarized_message_count", 0
        )

    return {
        "enabled": ENABLE_MEMORY_SUMMARY,
        "summary_exists": bool(summary_text.strip()),
        "summary_used_for_query_rewrite": summary_used_for_query_rewrite,
        "summarized_message_count": summarized_message_count,
        "summary_preview": summary_text.strip()[:120],
        "summary_updated": False,
        "summary_update_reason": "not_attempted",
        "summary_update_error": None,
    }


def _is_failed_assistant_message(message: dict) -> bool:
    """
    判断 assistant 消息是否属于检索失败 / 兜底回复。

    这些内容不能被写入 summary，避免后续 Query Rewrite 把失败回答当成业务事实。
    """
    if message.get("role") != "assistant":
        return False

    content = message.get("content", "")
    failed_markers = [
        "资料中没有找到足够相关",
        "没有找到足够相关",
        "资料中没有明确提到",
        "未找到相关资料",
        "未检索到相关资料",
        "知识库中没有检索到",
        "没有找到相关知识",
        "建议你补充更具体的问题",
    ]

    return any(marker in content for marker in failed_markers)


def _filter_messages_for_memory_summary(messages: list[dict]) -> list[dict]:
    """
    过滤不适合进入 summary 的消息。

    user 的问题可以保留为后续追问上下文；但 assistant 的失败兜底回复不保留为事实记忆。
    """
    filtered_messages = []

    for message in messages:
        if _is_failed_assistant_message(message):
            continue

        filtered_messages.append(message)

    return filtered_messages


def update_session_memory_summary_after_turn(
    session_id: str,
    memory_debug: dict,
) -> dict:
    """
    在 save_turn 之后尝试增量更新 session memory_summary。

    更新失败不会抛出异常，避免影响当前 /ask_langchain 的正常回答。
    """
    if not ENABLE_MEMORY_SUMMARY:
        memory_debug.update(
            {
                "enabled": False,
                "summary_updated": False,
                "summary_update_reason": "disabled",
                "summary_update_error": None,
            }
        )
        return memory_debug

    try:
        latest_history_messages = get_session_history(session_id)
        latest_summary_record = get_memory_summary(session_id)
        previous_summary = ""
        summarized_message_count = 0

        if latest_summary_record:
            previous_summary = latest_summary_record.get("summary", "") or ""
            summarized_message_count = latest_summary_record.get(
                "summarized_message_count", 0
            )

        decision = should_update_memory_summary(
            history_messages=latest_history_messages,
            summarized_message_count=summarized_message_count,
            enabled=ENABLE_MEMORY_SUMMARY,
        )

        if not decision["should_update"]:
            memory_debug.update(
                {
                    "summary_updated": False,
                    "summary_update_reason": decision["reason"],
                    "summary_update_error": None,
                }
            )
            return memory_debug

        selected_messages = select_messages_for_summary(
            history_messages=latest_history_messages,
            summarized_message_count=summarized_message_count,
        )
        selected_messages = _filter_messages_for_memory_summary(selected_messages)

        if not selected_messages:
            memory_debug.update(
                {
                    "summary_updated": False,
                    "summary_update_reason": "no_valid_messages_for_summary",
                    "summary_update_error": None,
                }
            )
            return memory_debug
        valid_summary_text = "\n".join(
            f"{message.get('role')}: {message.get('content', '').strip()}"
            for message in selected_messages
            if message.get("content", "").strip()
        )
        # 过滤掉 low_confidence / fallback 回复后再次判断阈值，避免为很少的有效上下文调用 summary LLM。
        if len(selected_messages) < MEMORY_SUMMARY_UPDATE_INTERVAL:
            memory_debug.update(
                {
                    "summary_updated": False,
                    "summary_update_reason": "not_enough_valid_messages_for_summary",
                    "summary_update_error": None,
                }
            )
            return memory_debug
        if len(valid_summary_text) < MEMORY_SUMMARY_MIN_CHARS:
            memory_debug.update(
                {
                    "summary_updated": False,
                    "summary_update_reason": "not_enough_valid_chars_for_summary",
                    "summary_update_error": None,
                }
            )
            return memory_debug

        summary_result = summarize_session_memory(
            previous_summary=previous_summary,
            new_messages=selected_messages,
        )

        if not summary_result["success"]:
            memory_debug.update(
                {
                    "summary_updated": False,
                    "summary_update_reason": "summary_generation_failed",
                    "summary_update_error": summary_result["error"],
                }
            )
            return memory_debug

        updated_summary = summary_result["updated_summary"]
        new_summarized_message_count = max(
            summarized_message_count,
            len(latest_history_messages) - MEMORY_RECENT_MESSAGES_KEEP,
        )
        upsert_memory_summary(
            session_id=session_id,
            summary=updated_summary,
            summarized_message_count=new_summarized_message_count,
        )

        memory_debug.update(
            {
                "summary_exists": bool(updated_summary.strip()),
                "summary_updated": True,
                "summary_update_reason": "ready",
                "summary_update_error": None,
                "summarized_message_count": new_summarized_message_count,
                "summary_preview": updated_summary.strip()[:120],
            }
        )
        return memory_debug

    except Exception as exc:
        memory_debug.update(
            {
                "summary_updated": False,
                "summary_update_reason": "summary_update_exception",
                "summary_update_error": str(exc),
            }
        )
        return memory_debug


def mark_memory_summary_disabled(memory_debug: dict) -> dict:
    """
    ENABLE_MEMORY_SUMMARY=False 时只补充 debug，不进入 summary 读取或更新流程。
    """
    memory_debug.update(
        {
            "enabled": False,
            "summary_updated": False,
            "summary_update_reason": "disabled",
            "summary_update_error": None,
        }
    )
    return memory_debug


@router_langchain.post("/ask_langchain")
def ask_question_langchain(request_data: AskRequest, request: Request):
    """
    LangChain 版问答接口
    目标：
    - 保留当前主项目的 chat/rag 分流思路
    - 保留当前 hybrid_search / SQLite / rewrite 逻辑
    - 只把最终模型调用改成 LangChain
    """
    bm25_index = request.app.state.bm25_index
    faiss_index = request.app.state.faiss_index
    chunk_records = request.app.state.chunk_records
    intent_router = request.app.state.intent_router

    question = request_data.question
    session_id = request_data.session_id

    try:
        history_messages = get_session_history(session_id)
        history_messages_snapshot = [msg.copy() for msg in history_messages]
        # 本阶段只读取已有 summary，并把它作为 Query Rewrite 的辅助上下文。
        # summary 不会进入 reference_text，也不会作为最终回答的事实依据。
        memory_summary_record = (
            get_memory_summary(session_id) if ENABLE_MEMORY_SUMMARY else None
        )
        memory_summary_text = ""
        if memory_summary_record:
            memory_summary_text = memory_summary_record.get("summary", "").strip()
        base_memory_debug = build_memory_debug(memory_summary_record)

        # 1. 明显 chat 规则兜底
        if is_obvious_chat_message(question):
            intent = "chat"
            answer = run_chat_chain(history_messages, question)

            response_data = {
                "question": question,
                "intent": intent,
                "embedding_model": EMBEDDING_MODEL,
                "framework": "langchain",
                "answer": answer,
                "memory_debug": base_memory_debug,
            }

        else:
            # 2. 先做 route_context，再走语义路由
            route_context = build_route_context(
                history_messages, question, MAX_HISTORY_TURNS
            )
            intent, intent_debug = semantic_route(route_context, intent_router)

            # 3. chat 分支
            if intent == "chat":
                answer = run_chat_chain(history_messages, question)

                response_data = {
                    "question": question,
                    "intent": intent,
                    "embedding_model": EMBEDDING_MODEL,
                    "framework": "langchain",
                    "history_messages": history_messages_snapshot,
                    "answer": answer,
                    "memory_debug": base_memory_debug,
                }
                # 【新增】chat 分支也返回路由调试信息
                if RETURN_DEBUG_INFO:
                    response_data["intent_debug"] = intent_debug

            # 4. rag 分支
            else:
                memory_summary_for_rewrite = (
                    memory_summary_text if memory_summary_text else None
                )
                memory_debug = build_memory_debug(
                    memory_summary_record,
                    summary_used_for_query_rewrite=bool(memory_summary_for_rewrite),
                )
                retrieval_query = rebuild_retrieval_query_with_llm(
                    history_messages,
                    question,
                    max_history_turns=MAX_HISTORY_TURNS,
                    memory_summary=memory_summary_for_rewrite,
                )

                query_embedding = get_embedding(retrieval_query)

                # 4. 先用 hybrid_search 召回候选资料
                # 如果启用 reranker，就先多召回几条候选，让 reranker 有选择空间
                candidate_top_k = RERANK_CANDIDATE_K if USE_RERANKER else TOP_K

                relevant_chunks = hybrid_search(
                    bm25_index=bm25_index,
                    faiss_index=faiss_index,
                    query=retrieval_query,
                    query_embedding=query_embedding,
                    chunk_records=chunk_records,
                    recall_k=HYBRID_RECALL_K,
                    top_k=candidate_top_k,
                )

                if not relevant_chunks:
                    return error_response(
                        message="没有找到相关知识",
                        data={
                            "question": question,
                            "framework": "langchain",
                            "retriever_status": "empty",
                            "memory_debug": memory_debug,
                        },
                        error="知识库中没有检索到与当前问题相关的内容",
                    )

                # 5. reranker 二次排序和过滤

                if RERANKER_PROVIDER == "dashscope":
                    filtered_chunks = rerank_chunks_by_dashscope(
                        query=retrieval_query,
                        chunks=relevant_chunks,
                        top_k=TOP_K,
                    )
                elif RERANKER_PROVIDER == "llm":
                    filtered_chunks = rerank_chunks_by_llm(
                        query=retrieval_query,
                        chunks=relevant_chunks,
                        top_k=TOP_K,
                    )
                else:
                    # 未知 provider 时，退回原始 top_k，避免接口直接挂掉
                    filtered_chunks = relevant_chunks[:TOP_K]

                if not filtered_chunks:
                    answer = "资料中没有找到足够相关的内容，建议你补充更具体的问题。"

                    response_data = {
                        "question": question,
                        "intent": intent,
                        "embedding_model": EMBEDDING_MODEL,
                        "framework": "langchain",
                        "retriever_status": "low_confidence",
                        "answer": answer,
                        "memory_debug": memory_debug,
                    }
                    response_data.update(
                        build_answer_llm_debug(answer_generated_by_llm=False)
                    )

                    if RETURN_DEBUG_INFO:
                        response_data.update(
                            {
                                "retrieval_query": retrieval_query,
                                "reference_text": "",
                                "used_chunk_count": 0,
                                "history_messages": history_messages_snapshot,
                                "used_chunks_debug": [],
                                "intent_debug": intent_debug,
                            }
                        )

                    save_turn(session_id=session_id, question=question, answer=answer)
                    if ENABLE_MEMORY_SUMMARY:
                        response_data["memory_debug"] = (
                            update_session_memory_summary_after_turn(
                                session_id=session_id,
                                memory_debug=response_data["memory_debug"],
                            )
                        )
                    else:
                        response_data["memory_debug"] = mark_memory_summary_disabled(
                            response_data["memory_debug"]
                        )

                    return success_response(
                        message="LangChain 问答成功",
                        data=response_data,
                    )
                reference_text = "\n".join([item["text"] for item in filtered_chunks])

                answer = run_rag_chain(retrieval_query, reference_text)

                response_data = {
                    "question": question,
                    "intent": intent,
                    "embedding_model": EMBEDDING_MODEL,
                    "framework": "langchain",
                    "retriever_status": "matched",
                    "answer": answer,
                    "memory_debug": memory_debug,
                }

                if RETURN_DEBUG_INFO:
                    response_data.update(
                        {
                            "retrieval_query": retrieval_query,
                            "reference_text": reference_text,
                            "used_chunk_count": len(filtered_chunks),
                            "history_messages": history_messages_snapshot,
                            "used_chunks_debug": [
                                {
                                    "text": item["text"],
                                    "chunk_id": item.get("chunk_id"),
                                    "metadata": item.get("metadata", {}),
                                    "faiss_score": item.get("faiss_score"),
                                    "bm25_score": item.get("bm25_score"),
                                    "faiss_rank": (
                                        item["faiss_rank"] + 1
                                        if item.get("faiss_rank") is not None
                                        else None
                                    ),
                                    "bm25_rank": (
                                        item["bm25_rank"] + 1
                                        if item.get("bm25_rank") is not None
                                        else None
                                    ),
                                    "rrf_score": item.get("rrf_score"),
                                    "source": item.get("source"),
                                    "rerank_score": item.get("rerank_score"),
                                    "rerank_reason": item.get("rerank_reason"),
                                    "reranker_provider": item.get("reranker_provider"),
                                }
                                for item in filtered_chunks
                            ],
                            "intent_debug": intent_debug,
                        }
                    )
        response_data.update(build_answer_llm_debug(answer_generated_by_llm=True))

        save_turn(session_id=session_id, question=question, answer=answer)
        if ENABLE_MEMORY_SUMMARY:
            response_data["memory_debug"] = update_session_memory_summary_after_turn(
                session_id=session_id,
                memory_debug=response_data["memory_debug"],
            )
        else:
            response_data["memory_debug"] = mark_memory_summary_disabled(
                response_data["memory_debug"]
            )

        return success_response(
            message="LangChain 问答成功",
            data=response_data,
        )

    except Exception as e:
        traceback.print_exc()
        return error_response(
            message="LangChain 链路异常，请检查控制台红字",
            data={
                "question": question,
                "framework": "langchain",
                "retriever_status": "error",
            },
            error=str(e),
        )
