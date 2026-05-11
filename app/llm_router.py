import json
import re
import requests

from app.config import (
    DEEPSEEK_API_KEY,
    DEEPSEEK_BASE_URL,
    MODEL_NAME,
    LLM_ROUTER_FAILED_DEFAULT_INTENT,
)


def extract_json_object(text: str) -> dict:
    """
    从大模型输出中提取 JSON 对象。

    作用：
    - 防止模型偶尔包一层 ```json
    - 防止模型前后多输出解释
    """

    content = text.strip()

    # 去掉可能出现的 markdown 代码块
    content = re.sub(r"^```json", "", content, flags=re.IGNORECASE).strip()
    content = re.sub(r"^```", "", content).strip()
    content = re.sub(r"```$", "", content).strip()

    start = content.find("{")
    end = content.rfind("}")

    if start == -1 or end == -1 or end <= start:
        raise ValueError(f"没有找到合法 JSON 对象：{text}")

    json_text = content[start : end + 1]
    return json.loads(json_text)


def llm_route_fallback(route_context: str) -> tuple[str, dict]:
    """
    使用大模型做低置信度路由兜底。

    注意：
    - 只在 Semantic Router 不确定时调用
    - 不负责回答问题
    - 只判断当前请求应该走 chat 还是 rag
    """

    if not DEEPSEEK_API_KEY:
        return LLM_ROUTER_FAILED_DEFAULT_INTENT, {
            "llm_router_success": False,
            "llm_router_reason": "未检测到 DEEPSEEK_API_KEY",
        }

    system_message = {
        "role": "system",
        "content": (
            "你是一个 AI 应用后端的意图路由器。"
            "你的任务不是回答用户问题，而是判断当前请求应该走 chat 还是 rag。"
            "只能输出 JSON，不要输出解释，不要使用 markdown。\n\n"
            "判断标准：\n"
            "1. 如果用户是在普通聊天、问候、感谢、确认、情绪交流、学习建议、职业建议、面试建议，判为 chat。\n"
            "2. 如果用户是在询问本地知识库、企业制度、员工手册、报销、请假、审批、岗位变更、医药文档、药品说明书、SOP、入库验收、冷链管理等资料中可能存在的事实或流程，判为 rag。\n"
            "3. 如果用户问题看起来需要根据资料确认，即使资料可能没有覆盖，也应该判为 rag，让后续 RAG 链路判断是否资料不足。\n"
            "4. 不要只因为历史中出现过 RAG 主题，就把当前礼貌收尾判成 rag。例如“好的，谢谢”“明白了”应该判为 chat。\n"
            "5. 如果当前问题非常模糊，例如“这个情况怎么办”“这个要怎么处理”，并且 route_context 中没有明确历史上下文或领域信息，应判为 chat，让助手追问用户补充信息，而不是贸然进入 rag。\n\n"
            "输出格式必须是：\n"
            '{"intent": "chat", "reason": "一句话说明原因"}\n'
            "或者：\n"
            '{"intent": "rag", "reason": "一句话说明原因"}'
        ),
    }

    user_message = {
        "role": "user",
        "content": (
            "请判断下面这段 route_context 应该走 chat 还是 rag：\n\n" f"{route_context}"
        ),
    }

    payload = {
        "model": MODEL_NAME,
        "messages": [system_message, user_message],
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
        raw_content = result["choices"][0]["message"]["content"]

        parsed = extract_json_object(raw_content)

        intent = parsed.get("intent", "").strip().lower()
        reason = parsed.get("reason", "").strip()

        if intent not in ["chat", "rag"]:
            raise ValueError(f"LLM Router 返回了非法 intent：{intent}")

        return intent, {
            "llm_router_success": True,
            "llm_router_intent": intent,
            "llm_router_reason": reason,
            "llm_router_raw": raw_content,
        }

    except Exception as e:
        return LLM_ROUTER_FAILED_DEFAULT_INTENT, {
            "llm_router_success": False,
            "llm_router_intent": LLM_ROUTER_FAILED_DEFAULT_INTENT,
            "llm_router_reason": f"LLM Router 调用失败，使用默认 intent：{str(e)}",
        }
