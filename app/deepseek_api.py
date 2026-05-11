import requests
from .config import DEEPSEEK_API_KEY, DEEPSEEK_BASE_URL, MODEL_NAME


def classify_intent(question: str) -> str:
    """
    【重点手写】判断用户意图，进行问答分离
    返回 'chat' 表示普通闲聊，返回 'rag' 表示需要查知识库
    """
    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {DEEPSEEK_API_KEY}",
    }

    # 这里的 System Prompt 是灵魂，要明确告诉模型它只能输出两个词
    system_message = {
        "role": "system",
        "content": (
            "你是一个智能路由助手，需要判断用户当前问题应该走普通聊天(chat)还是知识库检索问答(rag)。\n"
            "判断标准如下：\n"
            "1. 如果问题需要依赖本地知识库（员工手册、报销制度、请假制度、审批流程等）才能更好回答，请输出 'rag'。\n"
            "2. 如果问题不依赖本地知识库，大模型直接就可以正常回答，例如问候、感谢、闲聊、学习建议、情绪支持、一般讨论、身份类问题，请输出 'chat'。\n"
            "3. 多轮追问如果结合上下文后仍然是在问制度、流程、规则，也输出 'rag'。\n"
            "4. 只能输出 'chat' 或 'rag'，不要输出任何解释。"
        ),
    }

    user_message = {"role": "user", "content": question}

    payload = {
        "model": MODEL_NAME,
        "messages": [system_message, user_message],
        "temperature": 0.1,  # 温度尽量低，保证输出极其稳定
        "stream": False,
    }

    response = requests.post(
        DEEPSEEK_BASE_URL, headers=headers, json=payload, timeout=30
    )
    response.raise_for_status()

    result = response.json()
    intent = result["choices"][0]["message"]["content"].strip().lower()

    # 兜底容错机制：万一模型发疯输出了别的，默认走 rag
    if intent not in ["chat", "rag"]:
        return "rag"

    return intent


def rewrite_query_with_content(content):
    """
    把“用户问题 + 最近的对话”一起发送给 DeepSeek，
    让模型基于资料生成回答。

    参数：
        content: str
            用户当前提的问题+最近的对话
    返回：
        str
            模型生成的回答内容
    """

    # 请求头：告诉服务端这是 JSON 请求，并携带 API Key
    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {DEEPSEEK_API_KEY}",
    }
    system_message = {
        "role": "system",
        "content": (
            "你是一个专业的查询改写助手，用于知识库检索优化。"
            "请根据用户的历史对话，将当前问题改写为一个完整、清晰、适合用于知识检索的问题。"
            "要求："
            " 1. 必须结合历史对话补全语义"
            " 2. 尽量使用原始表述（不要随意改变“以上/以后”等关键语义）"
            " 3. 保留关键业务词（如：请假、加班、审批等）"
            " 4. 改写后的问题要具体、明确，像用户一次性完整提问"
            " 5. 只输出改写后的问题，不要解释"
            " 6. 尽量使用更接近制度/规范类表达（如：是否需要审批、是否需要申请等）"
            " 7. 如果当前问题是在已有金额区间基础上继续追问更高区间（如“那再高一点呢”），"
            " 请优先改写成“超过上一个区间上限值”的明确问法。"
            " 例如："
            " “500到2000元怎么审批？” + “那再高一点呢？”"
            " 应改写为："
            " “报销金额超过2000元怎么审批？”"
        ),
    }
    user_message = {"role": "user", "content": content}
    payload = {
        "model": MODEL_NAME,
        "messages": [system_message, user_message],
        "temperature": 0.2,
        "stream": False,
    }
    # 向 DeepSeek 发起 POST 请求
    response = requests.post(
        DEEPSEEK_BASE_URL, headers=headers, json=payload, timeout=30
    )

    # 如果 HTTP 状态码不是 200 系列，这里会直接抛异常
    response.raise_for_status()

    # 把响应体解析成 Python 字典
    result = response.json()

    # 从返回结果中取出模型最终回答文本
    answer = result["choices"][0]["message"]["content"]

    return answer


def ask_with_context(question: str, reference_text: str):
    """
    把“用户问题 + 检索到的参考资料”一起发送给 DeepSeek，
    让模型基于资料生成回答。

    参数：
        question: str
            用户当前提的问题
        reference_text: str
            检索到的参考资料文本

    返回：
        str
            模型生成的回答内容
    """

    # 请求头：告诉服务端这是 JSON 请求，并携带 API Key
    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {DEEPSEEK_API_KEY}",
    }

    # system 提示词：
    # 告诉模型它现在的任务是“基于资料回答”，而不是随意乱编
    system_message = {
        "role": "system",
        "content": (
            "你是一个基于资料进行问答的 AI 助手。"
            "请优先根据提供的参考资料回答问题。"
            "如果参考资料中没有明确答案，请明确说明“资料中没有明确提到”。"
            "不要脱离资料随意编造答案。"
        ),
    }

    user_message = {
        "role": "user",
        "content": (
            f"用户的问题是：\n {question}\n\n"
            f"相关的的参考资料是：\n{reference_text}\n\n"
            "请根据相关参考资料回答用户问题。"
        ),
    }

    payload = {
        "model": MODEL_NAME,
        "messages": [system_message, user_message],
        "temperature": 0.2,
        "stream": False,
    }

    # 向 DeepSeek 发起 POST 请求
    response = requests.post(
        DEEPSEEK_BASE_URL, headers=headers, json=payload, timeout=30
    )

    # 如果 HTTP 状态码不是 200 系列，这里会直接抛异常
    response.raise_for_status()

    # 把响应体解析成 Python 字典
    result = response.json()

    # 从返回结果中取出模型最终回答文本
    answer = result["choices"][0]["message"]["content"]

    return answer


def ask_chat_with_history(history_messages: list[dict], question: str) -> str:
    """
    普通聊天：把最近聊天历史 + 当前问题，一起发给大模型
    让模型基于上下文继续多轮对话
    """

    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {DEEPSEEK_API_KEY}",
    }

    # chat 场景下的 system prompt，不要写得像 RAG
    system_message = {
        "role": "system",
        "content": (
            "你是一个有帮助的 AI 助手。"
            "请结合历史聊天内容，理解当前用户问题，并自然地继续对话。"
            "如果历史里有上下文，就利用上下文回答；"
            "如果历史不足，也可以基于当前问题正常回答。"
        ),
    }

    # 复制一份历史，避免直接改原列表
    messages = [system_message]

    # 把历史消息逐条加入 messages
    for msg in history_messages:
        role = msg.get("role")
        content = msg.get("content", "").strip()

        # 只保留合法 role，避免脏数据
        if role not in ["user", "assistant"]:
            continue
        if not content:
            continue

        messages.append({"role": role, "content": content})

    # 最后追加当前用户问题
    messages.append({"role": "user", "content": question.strip()})

    payload = {
        "model": MODEL_NAME,
        "messages": messages,
        "temperature": 0.4,
        "stream": False,
    }

    response = requests.post(
        DEEPSEEK_BASE_URL, headers=headers, json=payload, timeout=30
    )
    response.raise_for_status()

    result = response.json()
    answer = result["choices"][0]["message"]["content"]

    return answer
