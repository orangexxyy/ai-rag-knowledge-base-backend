# app/routes_langchain.py

from fastapi import APIRouter, Request
import traceback

from app.models import AskRequest
from app.utils import success_response, error_response, is_obvious_chat_message
from app.config import (
    EMBEDDING_MODEL,
    RETURN_DEBUG_INFO,
    MAX_HISTORY_TURNS,
    HYBRID_RECALL_K,
    TOP_K,
    USE_RERANKER,
    RERANK_CANDIDATE_K,
    RERANKER_PROVIDER,
    LLM_PROVIDER,
    MODEL_NAME,
    OLLAMA_MODEL,
)
from app.chat_history_store import get_session_history, save_turn
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
                }
                # 【新增】chat 分支也返回路由调试信息
                if RETURN_DEBUG_INFO:
                    response_data["intent_debug"] = intent_debug

            # 4. rag 分支
            else:
                retrieval_query = rebuild_retrieval_query_with_llm(
                    history_messages, question, max_history_turns=MAX_HISTORY_TURNS
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
                    }
                    response_data.update(build_answer_llm_debug(answer_generated_by_llm=False))

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
