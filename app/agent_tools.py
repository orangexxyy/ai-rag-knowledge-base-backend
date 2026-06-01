from dataclasses import dataclass
from typing import Any, Callable

from app.config import (
    HYBRID_RECALL_K,
    KNOWLEDGE_DIR,
    RERANK_CANDIDATE_K,
    RERANKER_PROVIDER,
    TOP_K,
    USE_RERANKER,
)
from app.embedding_api import get_embedding
from app.hybrid_search import hybrid_search
from app.index_manager import get_index_status, load_index_meta
from app.langchain_chains import run_rag_chain
from app.reranker import rerank_chunks_by_dashscope, rerank_chunks_by_llm


ToolExecutor = Callable[[dict[str, Any], Any], dict[str, Any]]


@dataclass(frozen=True)
class ToolSpec:
    name: str
    description: str
    parameters_schema: dict[str, Any]
    risk_level: str
    executor: ToolExecutor


def execute_get_index_info(arguments: dict[str, Any], app_state: Any) -> dict[str, Any]:
    """只读检查当前知识库索引状态，不触发重建。"""
    index_status = get_index_status()
    chunk_records = getattr(app_state, "chunk_records", None)

    chunk_count = len(chunk_records) if isinstance(chunk_records, list) else None
    index_exists = index_status.get("status") == "valid"
    meta: dict[str, Any] = {}

    try:
        meta = load_index_meta()
        chunk_count = meta.get("chunk_count", chunk_count)
    except Exception as exc:
        meta = {"meta_status": "unavailable", "meta_error": str(exc)}

    return {
        "status": "success",
        "index_exists": index_exists,
        "chunk_count": chunk_count,
        "rebuild_required": index_status.get("rebuild_required"),
        "knowledge_dir": meta.get("knowledge_dir", KNOWLEDGE_DIR),
        "index_status": index_status.get("status"),
        "status_reason": index_status.get("status_reason"),
        "meta": meta,
    }


def execute_search_knowledge_base(
    arguments: dict[str, Any],
    app_state: Any,
) -> dict[str, Any]:
    """
    只读 RAG 工具：复用现有 embedding、hybrid_search、reranker 和 RAG answer chain。

    这里不复制 /ask_langchain 主链路：不处理 session history、Query Rewrite、
    semantic router、memory_summary，也不写入数据库或索引。它只是 Agent 可调用的
    轻量知识库查询工具。
    """
    question = arguments["question"]
    bm25_index = getattr(app_state, "bm25_index", None)
    faiss_index = getattr(app_state, "faiss_index", None)
    chunk_records = getattr(app_state, "chunk_records", None)

    if bm25_index is None or faiss_index is None or not isinstance(chunk_records, list):
        return {
            "success": False,
            "status": "error",
            "answer": "知识库索引尚未加载，无法执行 search_knowledge_base。",
            "retriever_status": "index_not_loaded",
            "reference_text": "",
            "reference_preview": "",
            "used_chunk_count": 0,
            "used_chunks_debug_summary": [],
        }

    try:
        query_embedding = get_embedding(question)
        candidate_top_k = RERANK_CANDIDATE_K if USE_RERANKER else TOP_K
        candidate_chunks = hybrid_search(
            bm25_index=bm25_index,
            faiss_index=faiss_index,
            query=question,
            query_embedding=query_embedding,
            chunk_records=chunk_records,
            recall_k=HYBRID_RECALL_K,
            top_k=candidate_top_k,
        )

        if not candidate_chunks:
            return {
                "success": True,
                "status": "success",
                "answer": "知识库中没有检索到与当前问题相关的内容。",
                "retriever_status": "empty",
                "reference_text": "",
                "reference_preview": "",
                "used_chunk_count": 0,
                "used_chunks_debug_summary": [],
            }

        if RERANKER_PROVIDER == "dashscope":
            selected_chunks = rerank_chunks_by_dashscope(
                query=question,
                chunks=candidate_chunks,
                top_k=TOP_K,
            )
        elif RERANKER_PROVIDER == "llm":
            selected_chunks = rerank_chunks_by_llm(
                query=question,
                chunks=candidate_chunks,
                top_k=TOP_K,
            )
        else:
            selected_chunks = candidate_chunks[:TOP_K]

        if not selected_chunks:
            return {
                "success": True,
                "status": "success",
                "answer": "资料中没有找到足够相关的内容，建议补充更具体的问题。",
                "retriever_status": "low_confidence",
                "reference_text": "",
                "reference_preview": "",
                "used_chunk_count": 0,
                "used_chunks_debug_summary": [],
            }

        reference_text = "\n".join(item["text"] for item in selected_chunks)
        answer = run_rag_chain(question, reference_text)

        return {
            "success": True,
            "status": "success",
            "answer": answer,
            "retriever_status": "matched",
            "reference_text": reference_text,
            "reference_preview": reference_text[:300],
            "used_chunk_count": len(selected_chunks),
            "used_chunks_debug_summary": [
                {
                    "chunk_id": item.get("chunk_id"),
                    "source": item.get("source"),
                    "metadata": item.get("metadata", {}),
                    "faiss_score": item.get("faiss_score"),
                    "bm25_score": item.get("bm25_score"),
                    "rrf_score": item.get("rrf_score"),
                    "rerank_score": item.get("rerank_score"),
                    "reranker_provider": item.get("reranker_provider"),
                    "text_preview": (item.get("text") or "")[:120],
                }
                for item in selected_chunks
            ],
        }
    except Exception as exc:
        return {
            "success": False,
            "status": "error",
            "answer": "search_knowledge_base 执行失败，未修改任何索引或数据。",
            "retriever_status": "error",
            "reference_text": "",
            "reference_preview": "",
            "used_chunk_count": 0,
            "used_chunks_debug_summary": [],
            "error": str(exc),
        }


def execute_rebuild_index(arguments: dict[str, Any], app_state: Any) -> dict[str, Any]:
    """
    仍然不真实重建索引，只返回安全占位结果。

    真实重建会写入索引文件并可能调用 embedding API；在未完成更细的执行确认、
    运行时刷新 app.state、失败回滚设计前，不在 agent demo 中直接触发。
    """
    return {
        "status": "not_implemented_for_safety",
        "rebuild_executed": False,
        "message": (
            "rebuild_index 已通过双层校验，但当前阶段为安全起见未执行真实重建；"
            "后续可复用现有 build_and_save_chunk_index 并补充运行时状态刷新。"
        ),
    }


TOOL_REGISTRY: dict[str, ToolSpec] = {
    "get_index_info": ToolSpec(
        name="get_index_info",
        description="Read-only inspection of the current knowledge-base index status.",
        parameters_schema={
            "type": "object",
            "properties": {},
            "required": [],
            "additionalProperties": False,
        },
        risk_level="low",
        executor=execute_get_index_info,
    ),
    "search_knowledge_base": ToolSpec(
        name="search_knowledge_base",
        description="Read-only RAG tool for answering a knowledge-base question.",
        parameters_schema={
            "type": "object",
            "properties": {"question": {"type": "string"}},
            "required": ["question"],
            "additionalProperties": False,
        },
        risk_level="low",
        executor=execute_search_knowledge_base,
    ),
    "rebuild_index": ToolSpec(
        name="rebuild_index",
        description="Dangerous tool for rebuilding the knowledge-base index after backend authorization.",
        parameters_schema={
            "type": "object",
            "properties": {"confirm": {"type": "boolean"}},
            "required": ["confirm"],
            "additionalProperties": False,
        },
        risk_level="dangerous",
        executor=execute_rebuild_index,
    ),
}


def get_tool_schemas() -> list[dict[str, Any]]:
    """提供给 planner 的工具 schema，不暴露后端 executor。"""
    return [
        {
            "name": tool.name,
            "description": tool.description,
            "parameters_schema": tool.parameters_schema,
            "risk_level": tool.risk_level,
        }
        for tool in TOOL_REGISTRY.values()
    ]


def fake_plan_tool_call(question: str) -> dict[str, Any]:
    """
    第一阶段临时 planner：只用于验证后端 tool_call 执行链路。

    第二阶段保留为 fallback；真实 Agent 演示可通过 AGENT_PLANNER_PROVIDER=llm 切换。
    """
    normalized = (question or "").strip().lower()

    if any(keyword in normalized for keyword in ["重建", "rebuild"]):
        return {"tool_name": "rebuild_index", "arguments": {"confirm": True}}

    if any(
        keyword in normalized
        for keyword in ["状态", "索引", "检查知识库", "index", "status"]
    ):
        return {"tool_name": "get_index_info", "arguments": {}}

    return {
        "tool_name": "search_knowledge_base",
        "arguments": {"question": question},
    }


def validate_tool_name(tool_call: dict[str, Any]) -> dict[str, Any]:
    """校验工具名必须来自后端固定白名单。"""
    tool_name = tool_call.get("tool_name")

    if tool_name not in TOOL_REGISTRY:
        return {
            "valid": False,
            "error_code": "unknown_tool",
            "message": f"Unknown tool_name: {tool_name}",
        }

    return {"valid": True, "tool": TOOL_REGISTRY[tool_name]}


def validate_tool_arguments(tool_name: str, arguments: Any) -> dict[str, Any]:
    """按最小 JSON schema 校验 tool_call.arguments，阻止任意参数进入 executor。"""
    tool = TOOL_REGISTRY[tool_name]
    schema = tool.parameters_schema

    if not isinstance(arguments, dict):
        return {
            "valid": False,
            "error_code": "invalid_arguments_type",
            "message": "tool_call.arguments must be an object",
        }

    properties = schema.get("properties", {})
    required = schema.get("required", [])

    for key in required:
        if key not in arguments:
            return {
                "valid": False,
                "error_code": "missing_required_argument",
                "message": f"Missing required argument: {key}",
            }

    if schema.get("additionalProperties") is False:
        unknown_keys = sorted(set(arguments) - set(properties))
        if unknown_keys:
            return {
                "valid": False,
                "error_code": "unknown_argument",
                "message": f"Unknown arguments: {unknown_keys}",
            }

    for key, value in arguments.items():
        expected_type = properties.get(key, {}).get("type")
        if expected_type == "string" and not isinstance(value, str):
            return {
                "valid": False,
                "error_code": "invalid_argument_type",
                "message": f"Argument {key} must be string",
            }
        if expected_type == "boolean" and not isinstance(value, bool):
            return {
                "valid": False,
                "error_code": "invalid_argument_type",
                "message": f"Argument {key} must be boolean",
            }

    return {"valid": True, "arguments": arguments}


def validate_dangerous_tool_authorization(
    tool_name: str,
    arguments: dict[str, Any],
    allow_rebuild_index: bool,
) -> dict[str, Any]:
    """危险工具双层校验：模型语义确认 + 后端请求授权必须同时成立。"""
    tool = TOOL_REGISTRY[tool_name]

    if tool.risk_level != "dangerous":
        return {"valid": True, "status": "not_required"}

    if tool_name == "rebuild_index":
        confirm = arguments.get("confirm") is True
        if confirm and allow_rebuild_index:
            return {"valid": True, "status": "authorized"}

        return {
            "valid": False,
            "status": "blocked",
            "error_code": "dangerous_tool_requires_backend_authorization",
            "message": (
                "rebuild_index requires tool_call.arguments.confirm == true "
                "and request.allow_rebuild_index == true"
            ),
        }

    return {
        "valid": False,
        "status": "blocked",
        "error_code": "unsupported_dangerous_tool",
        "message": f"Unsupported dangerous tool: {tool_name}",
    }
