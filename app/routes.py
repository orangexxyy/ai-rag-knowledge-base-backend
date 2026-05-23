from fastapi import APIRouter, Request
import traceback
from .models import AskRequest
from .utils import success_response, error_response
from .deepseek_api import ask_with_context, classify_intent, ask_chat_with_history
from .config import (
    EMBEDDING_MODEL,
    CHUNK_INDEX_FILE,
    TOP_K,
    RETURN_DEBUG_INFO,
    MAX_HISTORY_TURNS,
    HYBRID_RECALL_K,
)
from .index_manager import build_and_save_chunk_index
from app.index_manager import build_and_save_chunk_index, load_index_meta
from app.utils import success_response, error_response, is_obvious_chat_message
from app.index_manager import get_index_status
from app.embedding_api import get_embedding
from app.query_builder import rebuild_retrieval_query_with_llm, build_route_context
from app.hybrid_search import hybrid_search
from app.semantic_router import semantic_route
from app.chat_history_store import get_session_history, append_message, save_turn

# 创建路由对象
router = APIRouter()
from fastapi import APIRouter

router = APIRouter()


@router.get("/index_info")
def get_index_info():
    """
    查看当前索引的元信息
    """
    try:
        meta = load_index_meta(CHUNK_INDEX_FILE)

        return success_response(
            message="索引信息获取成功",
            data={
                "embedding_model": meta.get("embedding_model"),
                "knowledge_file": meta.get("knowledge_file"),
                "chunk_method": meta.get("chunk_method"),
                "chunk_count": meta.get("chunk_count"),
                "build_time": meta.get("build_time"),
                "knowledge_hash": meta.get("knowledge_hash"),
                "index_status": get_index_status(CHUNK_INDEX_FILE),
                "document_pipeline_version": meta.get("document_pipeline_version"),
                "metadata_schema_version": meta.get("metadata_schema_version"),
            },
        )

    except FileNotFoundError as e:
        return error_response(
            message="知识索引不存在",
            data={"retriever_status": "index_not_found", "rebuild_required": True},
            error=str(e),
        )

    except ValueError as e:
        return error_response(
            message="知识索引无效",
            data={"retriever_status": "invalid_index", "rebuild_required": True},
            error=str(e),
        )


@router.post("/rebuild_index")
def rebuild_index():
    """
    手动重建知识索引
    """
    try:
        # 1. 执行重建索引
        build_and_save_chunk_index(CHUNK_INDEX_FILE)

        # 2. 读取重建后的 meta 信息
        meta = load_index_meta(CHUNK_INDEX_FILE)

        # 3. 返回重建结果摘要
        return success_response(
            message="索引重建成功",
            data={
                "embedding_model": meta.get("embedding_model"),
                "knowledge_file": meta.get("knowledge_file"),
                "chunk_method": meta.get("chunk_method"),
                "chunk_count": meta.get("chunk_count"),
                "build_time": meta.get("build_time"),
            },
        )

    except Exception as e:
        return error_response(
            message="索引重建失败",
            data={"retriever_status": "rebuild_failed"},
            error=str(e),
        )


@router.post("/ask")
def ask_question(request_data: AskRequest, request: Request):
    """
    本地知识库问答接口
    流程：
    1. 接收用户问题
    2. 读取本地知识文件
    3. 把知识文本切成多个块
    4. 检索最相关的知识块
    5. 把相关知识和问题一起发给模型
    6. 返回 question / reference / answer
    """

    # 获取内存中的参数
    bm25_index = request.app.state.bm25_index
    faiss_index = request.app.state.faiss_index
    chunk_records = request.app.state.chunk_records
    intent_router = request.app.state.intent_router
    # 解析入参
    question = request_data.question
    session_id = request_data.session_id

    try:
        # 获取用户最近聊天记录
        history_messages = get_session_history(session_id)
        # 专门给调试返回用的历史记录，避免后面被污染
        history_messages_snapshot = [msg.copy() for msg in history_messages]
        if is_obvious_chat_message(question):
            intent = "chat"
            retrieval_query = question.strip()
            answer = ask_chat_with_history(history_messages, question)
            response_data = {
                "question": question,
                "intent": intent,
                "embedding_model": EMBEDDING_MODEL,
                "answer": answer,
            }
        else:

            # 将当前问题和最近的聊天记录组合形成完整的语义表达文本
            route_context = build_route_context(
                history_messages, question, MAX_HISTORY_TURNS
            )
            # 获取用户聊天的目的
            intent, intent_debug = semantic_route(route_context, intent_router)
            # 这里必须再分一次
            if intent == "chat":
                answer = ask_chat_with_history(history_messages, question)
                response_data = {
                    "question": question,
                    "intent": intent,
                    "history_messages": history_messages,
                    "embedding_model": EMBEDDING_MODEL,
                    "answer": answer,
                }
            else:
                # 将当前问题和最近的聊天记录组合形成完整的语义表达文本
                retrieval_query = rebuild_retrieval_query_with_llm(
                    history_messages, question, max_history_turns=MAX_HISTORY_TURNS
                )
                # 将问题转化成为embedding向量
                query_embedding = get_embedding(retrieval_query)

                # 4. 找出最相关的知识块
                relevant_chunks = hybrid_search(
                    bm25_index,
                    faiss_index,
                    retrieval_query,
                    query_embedding,
                    chunk_records,
                    HYBRID_RECALL_K,
                    TOP_K,
                )

                # 如果一个相关块都没找到，就给一个明确提示
                if not relevant_chunks:
                    return error_response(
                        message="没有找到相关知识",
                        error="知识库中没有检索到与当前问题相关的内容",
                    )

                # 5. 把多个相关块拼成一个参考资料字符串
                filtered_chunks = [relevant_chunks[0]]
                for item in relevant_chunks[1:]:
                    filtered_chunks.append(item)
                reference_texts = "\n".join([item["text"] for item in filtered_chunks])

                # 6. 把“问题 + 参考资料”一起发给 DeepSeek
                answer = ask_with_context(retrieval_query, reference_texts)
                # 先准备基础返回数据
                response_data = {
                    "question": question,
                    "intent": intent,
                    "embedding_model": EMBEDDING_MODEL,
                    "retriever_status": "matched",
                    "rebuild_required": False,
                    "answer": answer,
                }

                # -----------------------------
                # 如果开启调试模式，再补充调试字段
                # -----------------------------
                if RETURN_DEBUG_INFO:
                    response_data.update(
                        {
                            "reference_text": reference_texts,
                            "used_chunk_rrf_scores": [
                                item["rrf_score"] for item in filtered_chunks
                            ],
                            "used_chunk_count": len(filtered_chunks),
                            "retrieval_query": retrieval_query,
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
                                }
                                for item in filtered_chunks
                            ],
                            "intent_debug": intent_debug,
                        }
                    )
        # 将现在的聊天记录保存进用户历史记录中
        save_turn(session_id=session_id, question=question, answer=answer)
        # 7. 按统一格式返回结果
        return success_response(
            data=response_data,
            message="问答成功",
        )

    except Exception as e:
        response_data = {
            "question": question,
            "model": EMBEDDING_MODEL,
            "retriever_status": "rejected_low_score",
            "rebuild_required": False,
        }
        traceback.print_exc()
        # 立即阻断并返回错误信息
        return error_response(
            message="检索异常，请检查控制台红字",
            data={"question": question, "retriever_status": "error"},
            error=str(e),
        )
