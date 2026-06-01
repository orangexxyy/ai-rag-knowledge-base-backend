from fastapi import APIRouter, Request

from app.agent_planner import plan_tool_call
from app.agent_tools import (
    TOOL_REGISTRY,
    validate_dangerous_tool_authorization,
    validate_tool_arguments,
    validate_tool_name,
)
from app.models import AgentDemoRequest
from app.utils import success_response


router_agent = APIRouter()


def _make_step(step: int, stage: str, status: str, **kwargs):
    data = {"step": step, "stage": stage, "status": status}
    data.update(kwargs)
    return data


@router_agent.post("/agent_demo")
def agent_demo(request_data: AgentDemoRequest, request: Request):
    """
    Controlled tool calling agent demo.

    第二阶段支持 fake / llm planner，但无论 planner 来源是什么，
    后续都必须经过白名单、参数 schema、危险工具授权和 executor 链路。
    """
    question = request_data.question
    allow_rebuild_index = request_data.allow_rebuild_index
    agent_steps = []

    planner_result = plan_tool_call(question)
    agent_steps.append(
        _make_step(
            step=1,
            stage="planner",
            status="planned" if planner_result["success"] else "failed",
            planner_type=planner_result["provider"],
            tool_call=planner_result["tool_call"],
            raw_output=planner_result["raw_output"],
            error=planner_result["error"],
        )
    )
    if not planner_result["success"]:
        return success_response(
            message="/agent_demo planner failed",
            data={
                "answer": "planner 未能生成合法的 strict JSON tool_call，未执行任何工具。",
                "agent_mode": f"controlled_tool_calling_{planner_result['provider']}_planner",
                "agent_steps": agent_steps,
                "agent_debug": _build_agent_debug(
                    allow_rebuild_index=allow_rebuild_index,
                    blocked=True,
                    planner_provider=planner_result["provider"],
                    planner_error=planner_result["error"],
                ),
            },
        )

    tool_call = planner_result["tool_call"]
    name_validation = validate_tool_name(tool_call)
    agent_steps.append(
        _make_step(
            step=2,
            stage="tool_whitelist_validation",
            status="passed" if name_validation["valid"] else "failed",
            result={k: v for k, v in name_validation.items() if k != "tool"},
        )
    )
    if not name_validation["valid"]:
        return success_response(
            message="/agent_demo tool call blocked by whitelist",
            data={
                "answer": "工具名不在后端白名单中，未执行任何工具。",
                "agent_mode": f"controlled_tool_calling_{planner_result['provider']}_planner",
                "agent_steps": agent_steps,
                "agent_debug": _build_agent_debug(
                    allow_rebuild_index=allow_rebuild_index,
                    blocked=True,
                    planner_provider=planner_result["provider"],
                ),
            },
        )

    tool_name = tool_call["tool_name"]
    arguments = tool_call.get("arguments", {})
    argument_validation = validate_tool_arguments(tool_name, arguments)
    agent_steps.append(
        _make_step(
            step=3,
            stage="arguments_schema_validation",
            status="passed" if argument_validation["valid"] else "failed",
            result=argument_validation,
        )
    )
    if not argument_validation["valid"]:
        return success_response(
            message="/agent_demo tool call blocked by argument validation",
            data={
                "answer": "工具参数不符合 schema，未执行任何工具。",
                "agent_mode": f"controlled_tool_calling_{planner_result['provider']}_planner",
                "agent_steps": agent_steps,
                "agent_debug": _build_agent_debug(
                    allow_rebuild_index=allow_rebuild_index,
                    blocked=True,
                    planner_provider=planner_result["provider"],
                ),
            },
        )

    # 危险工具仍然必须经过模型语义确认 + 后端 request-level 授权双层校验。
    authorization = validate_dangerous_tool_authorization(
        tool_name=tool_name,
        arguments=argument_validation["arguments"],
        allow_rebuild_index=allow_rebuild_index,
    )
    agent_steps.append(
        _make_step(
            step=4,
            stage="dangerous_tool_authorization",
            status=authorization["status"],
            result=authorization,
        )
    )
    if not authorization["valid"]:
        return success_response(
            message="/agent_demo dangerous tool blocked",
            data={
                "answer": "检测到危险工具调用请求，但后端授权未通过，未执行重建索引。",
                "agent_mode": f"controlled_tool_calling_{planner_result['provider']}_planner",
                "agent_steps": agent_steps,
                "agent_debug": _build_agent_debug(
                    allow_rebuild_index=allow_rebuild_index,
                    blocked=True,
                    planner_provider=planner_result["provider"],
                ),
            },
        )

    tool = TOOL_REGISTRY[tool_name]
    try:
        execution_result = tool.executor(
            argument_validation["arguments"],
            request.app.state,
        )
        execution_status = execution_result.get("status", "success")
    except Exception as exc:
        execution_result = {
            "status": "error",
            "error_code": "tool_execution_exception",
            "message": str(exc),
        }
        execution_status = "error"

    agent_steps.append(
        _make_step(
            step=5,
            stage="tool_execution",
            status=execution_status,
            tool_name=tool_name,
            result=execution_result,
        )
    )

    return success_response(
        message="/agent_demo executed",
        data={
            "answer": _build_answer(tool_name, execution_result),
            "agent_mode": f"controlled_tool_calling_{planner_result['provider']}_planner",
            "agent_steps": agent_steps,
            "agent_debug": _build_agent_debug(
                allow_rebuild_index=allow_rebuild_index,
                blocked=False,
                planner_provider=planner_result["provider"],
                tool_name=tool_name,
                execution_status=execution_status,
            ),
        },
    )


def _build_agent_debug(
    allow_rebuild_index: bool,
    blocked: bool,
    planner_provider: str = "fake",
    tool_name: str | None = None,
    execution_status: str | None = None,
    planner_error: dict | None = None,
) -> dict:
    return {
        "agent_type": "controlled_tool_calling_agent_demo",
        "planner": planner_provider,
        "planner_note": "fake is kept as fallback; llm provider requires strict JSON tool_call output.",
        "planner_error": planner_error,
        "executor_policy": "backend_whitelist_schema_validation_and_dangerous_tool_authorization",
        "available_tools": list(TOOL_REGISTRY.keys()),
        "allow_rebuild_index": allow_rebuild_index,
        "blocked": blocked,
        "tool_name": tool_name,
        "execution_status": execution_status,
    }


def _build_answer(tool_name: str, execution_result: dict) -> str:
    if tool_name == "get_index_info":
        return "已完成知识库索引状态检查。"
    if tool_name == "search_knowledge_base":
        return execution_result.get("answer", "已完成知识库查询工具调用。")
    if tool_name == "rebuild_index":
        return execution_result.get("message", "已完成 rebuild_index 工具调用。")
    return "已完成工具调用。"
