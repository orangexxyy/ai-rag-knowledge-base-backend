from dataclasses import dataclass
from typing import Any, Callable

from app.config import KNOWLEDGE_DIR
from app.index_manager import get_index_status, load_index_meta


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
    第一阶段只返回只读检索摘要占位结果。

    这里刻意不复制 /ask_langchain 主链路，避免影响 Query Rewrite、reranker、
    memory_summary 和 low_confidence 等既有行为。第二阶段可再接入干净的 RAG tool。
    """
    question = arguments["question"]
    chunk_records = getattr(app_state, "chunk_records", None)
    chunk_count = len(chunk_records) if isinstance(chunk_records, list) else None
    used_chunks_debug_summary = []

    if isinstance(chunk_records, list):
        for item in chunk_records[:3]:
            used_chunks_debug_summary.append(
                {
                    "chunk_id": item.get("chunk_id"),
                    "source": item.get("source"),
                    "metadata": item.get("metadata", {}),
                    "text_preview": (item.get("text") or "")[:120],
                }
            )

    return {
        "status": "not_integrated_first_stage",
        "answer": (
            "第一阶段 /agent_demo 已完成工具调用链路，但 search_knowledge_base "
            "尚未完整接入现有 RAG 主链路；请继续使用 /ask_langchain 获取正式 RAG 答案。"
        ),
        "question": question,
        "retriever_status": "placeholder_read_only_summary",
        "reference_text": None,
        "chunk_count": chunk_count,
        "used_chunks_debug_summary": used_chunks_debug_summary,
    }


def execute_rebuild_index(arguments: dict[str, Any], app_state: Any) -> dict[str, Any]:
    """
    第一阶段不真实重建索引，只返回安全占位结果。

    真实重建会写入索引文件并可能调用 embedding API；在未完成更细的执行确认、
    运行时刷新 app.state、失败回滚设计前，不在 agent demo 中直接触发。
    """
    return {
        "status": "not_implemented_for_safety",
        "rebuild_executed": False,
        "message": (
            "rebuild_index 已通过双层校验，但第一阶段为安全起见未执行真实重建；"
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
        description="Read-only first-stage wrapper for the existing knowledge-base RAG capability.",
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

    第二阶段会替换为真正的 LLM planner strict JSON 输出。
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
