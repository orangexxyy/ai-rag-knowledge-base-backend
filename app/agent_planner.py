import json
from typing import Any

import requests

from app.agent_tools import fake_plan_tool_call, get_tool_schemas
from app.config import (
    AGENT_PLANNER_PROVIDER,
    DEEPSEEK_API_KEY,
    DEEPSEEK_BASE_URL,
    MODEL_NAME,
)


def parse_strict_tool_call(raw_output: str) -> dict[str, Any]:
    """
    解析 LLM planner 的 strict JSON 输出。

    这里故意不做 Markdown code fence 提取；只要混入自然语言或多余字段，
    就视为 planner_parse_error，后端不会执行任何工具。
    """
    try:
        parsed = json.loads(raw_output.strip())
    except json.JSONDecodeError as exc:
        raise ValueError(f"planner output is not valid JSON: {exc}") from exc

    if not isinstance(parsed, dict):
        raise ValueError("planner output must be a JSON object")

    expected_keys = {"tool_name", "arguments"}
    actual_keys = set(parsed.keys())
    if actual_keys != expected_keys:
        raise ValueError(
            f"planner output must contain only {sorted(expected_keys)}, got {sorted(actual_keys)}"
        )

    if not isinstance(parsed["tool_name"], str):
        raise ValueError("tool_name must be string")

    if not isinstance(parsed["arguments"], dict):
        raise ValueError("arguments must be object")

    return parsed


def plan_tool_call(question: str, provider: str | None = None) -> dict[str, Any]:
    """根据配置选择 fake planner 或 LLM planner，并统一返回结构化 planner result。"""
    selected_provider = (provider or AGENT_PLANNER_PROVIDER or "fake").lower()

    if selected_provider == "fake":
        return {
            "success": True,
            "provider": "fake",
            "tool_call": fake_plan_tool_call(question),
            "raw_output": None,
            "error": None,
        }

    if selected_provider != "llm":
        return {
            "success": False,
            "provider": selected_provider,
            "tool_call": None,
            "raw_output": None,
            "error": {
                "error_code": "unsupported_planner_provider",
                "message": f"Unsupported AGENT_PLANNER_PROVIDER: {selected_provider}",
            },
        }

    return _plan_tool_call_with_llm(question)


def _plan_tool_call_with_llm(question: str) -> dict[str, Any]:
    """调用真实 LLM planner，要求模型只返回 strict JSON tool_call。"""
    if not DEEPSEEK_API_KEY:
        return {
            "success": False,
            "provider": "llm",
            "tool_call": None,
            "raw_output": None,
            "error": {
                "error_code": "planner_api_key_missing",
                "message": "DEEPSEEK_API_KEY is not configured for LLM planner",
            },
        }

    tool_schemas = get_tool_schemas()
    system_prompt = (
        "You are a controlled tool-call planner.\n"
        "Return strict JSON only. Do not use Markdown. Do not add natural language.\n"
        "The JSON object must contain exactly two keys: tool_name and arguments.\n"
        "You do not execute tools. Backend executor will validate whitelist, schema, and authorization.\n"
        "Dangerous tools cannot be authorized by you. If user semantically asks to rebuild index, "
        "you may set rebuild_index arguments.confirm to true, but backend request authorization is still required.\n"
        "Available tools:\n"
        f"{json.dumps(tool_schemas, ensure_ascii=False)}"
    )
    user_prompt = f"User question: {question}"

    payload = {
        "model": MODEL_NAME,
        "messages": [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt},
        ],
        "temperature": 0,
        "stream": False,
    }
    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {DEEPSEEK_API_KEY}",
    }

    try:
        response = requests.post(
            DEEPSEEK_BASE_URL,
            headers=headers,
            json=payload,
            timeout=30,
        )
        response.raise_for_status()
        result = response.json()
        raw_output = result["choices"][0]["message"]["content"]
    except Exception as exc:
        return {
            "success": False,
            "provider": "llm",
            "tool_call": None,
            "raw_output": None,
            "error": {
                "error_code": "planner_llm_call_failed",
                "message": str(exc),
            },
        }

    try:
        tool_call = parse_strict_tool_call(raw_output)
    except ValueError as exc:
        return {
            "success": False,
            "provider": "llm",
            "tool_call": None,
            "raw_output": raw_output,
            "error": {
                "error_code": "planner_parse_error",
                "message": str(exc),
            },
        }

    return {
        "success": True,
        "provider": "llm",
        "tool_call": tool_call,
        "raw_output": raw_output,
        "error": None,
    }
