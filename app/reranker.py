# app/reranker.py

import json
import re
import requests
import os
from openai import OpenAI
from app.config import (
    DEEPSEEK_API_KEY,
    DEEPSEEK_BASE_URL,
    MODEL_NAME,
    RERANK_MIN_SCORE,
    RERANK_PRIMARY_MIN_SCORE,
    RERANK_EXTRA_MIN_SCORE,
    RERANK_EXTRA_MAX_GAP,
    DASHSCOPE_API_KEY,
    DASHSCOPE_RERANK_BASE_URL,
    DASHSCOPE_RERANK_MODEL,
)


def extract_json_array(text: str) -> list[dict]:
    """
    从大模型输出中提取 JSON 数组。

    作用：
    - 防止模型偶尔包一层 ```json
    - 防止模型前后多输出一点解释
    """

    content = text.strip()

    # 去掉可能出现的 markdown 代码块标记
    content = re.sub(r"^```json", "", content, flags=re.IGNORECASE).strip()
    content = re.sub(r"^```", "", content).strip()
    content = re.sub(r"```$", "", content).strip()

    # 找到第一个 [ 和最后一个 ]
    start = content.find("[")
    end = content.rfind("]")

    if start == -1 or end == -1 or end <= start:
        raise ValueError(f"没有找到合法 JSON 数组：{text}")

    json_text = content[start : end + 1]
    return json.loads(json_text)

def rerank_chunks_by_dashscope(
    query: str,
    chunks: list[dict],
    top_k: int,
    primary_min_score: int = RERANK_PRIMARY_MIN_SCORE,
    extra_min_score: int = RERANK_EXTRA_MIN_SCORE,
    extra_max_gap: int = RERANK_EXTRA_MAX_GAP,
) -> list[dict]:
    """
    使用阿里云百炼 qwen3-rerank 对候选 chunk 做二次排序和过滤。

    当前策略：
    - 第一名 chunk：达到 primary_min_score 即可保留
    - 第二名及之后：必须达到 extra_min_score 才保留

    为什么这样设计：
    - 避免明确问题被过高阈值误伤
    - 同时过滤第二条及以后容易混入的弱相关资料
    """

    if not chunks:
        return []

    if not DASHSCOPE_API_KEY:
        raise ValueError("未检测到 DASHSCOPE_API_KEY，请先配置百炼 API Key")

    client = OpenAI(
        api_key=DASHSCOPE_API_KEY,
        base_url=DASHSCOPE_RERANK_BASE_URL,
    )

    documents = [item["text"] for item in chunks]

    try:
        result = client.post(
            "/reranks",
            body={
                "model": DASHSCOPE_RERANK_MODEL,
                "query": query,
                "documents": documents,
                "top_n": len(documents),
            },
            cast_to=object,
        )

        rerank_results = result.get("results", [])

        reranked_chunks = []

        for row in rerank_results:
            original_index = int(row["index"])
            relevance_score = float(row["relevance_score"])
            score_100 = relevance_score * 100

            if original_index < 0 or original_index >= len(chunks):
                continue

            new_item = chunks[original_index].copy()
            new_item["rerank_score"] = score_100
            new_item["rerank_reason"] = (
                f"DashScope {DASHSCOPE_RERANK_MODEL} relevance_score="
                f"{relevance_score:.4f}"
            )
            new_item["reranker_provider"] = "dashscope"
            reranked_chunks.append(new_item)

        # 按 rerank_score 从高到低排序
        reranked_chunks = sorted(
            reranked_chunks,
            key=lambda x: x.get("rerank_score", 0),
            reverse=True,
        )

        if not reranked_chunks:
            return []

        selected_chunks = []

        # 1. 第一名使用较低阈值，避免核心资料被误伤
        first_chunk = reranked_chunks[0]
        first_score = first_chunk.get("rerank_score", 0)

        if first_score >= primary_min_score:
            selected_chunks.append(first_chunk)
        else:
            # 第一名都低于主阈值，说明整体相关性确实不足
            return []

        # 2. 第二名及以后使用更严格的“双条件”
        # 条件 1：分数必须达到补充资料最低分
        # 条件 2：不能和第一名差距过大
        for item in reranked_chunks[1:]:
            if len(selected_chunks) >= top_k:
                break

            score = item.get("rerank_score", 0)
            score_gap = first_score - score
            chunk_text = item.get("text", "")

            if score < extra_min_score:
                continue

            if score_gap > extra_max_gap:
                continue

            # 金额区间冲突过滤：
            # 分数虽然高，但如果金额条件和问题冲突，也不进入 reference_text
            if is_amount_range_conflict(query, chunk_text):
                continue

            selected_chunks.append(item)

        return selected_chunks[:top_k]

    except Exception as e:
        # DashScope reranker 失败时，不让整个 RAG 链路失败
        fallback_chunks = []

        for item in chunks[:top_k]:
            new_item = item.copy()
            new_item["rerank_score"] = None
            new_item["rerank_reason"] = f"dashscope_reranker_failed: {str(e)}"
            new_item["reranker_provider"] = "dashscope_failed"
            fallback_chunks.append(new_item)

        return fallback_chunks

def rerank_chunks_by_llm(
    query: str,
    chunks: list[dict],
    top_k: int,
    min_score: int = RERANK_MIN_SCORE,
) -> list[dict]:
    """
    使用 LLM 对候选 chunk 做二次排序和过滤。

    参数：
    - query: 检索问题 / retrieval_query
    - chunks: hybrid_search 召回的候选 chunk
    - top_k: 最终保留多少条
    - min_score: 最低保留分数

    返回：
    - rerank 后的 chunk 列表
    """

    if not chunks:
        return []

    # 1. 把候选 chunk 编号，交给模型判断
    candidates_text = ""

    for index, item in enumerate(chunks):
        candidates_text += f"\n\n[候选资料 {index}]\n{item['text']}"

    system_message = {
        "role": "system",
        "content": (
            "你是一个 RAG reranker。"
            "你的任务不是回答用户问题，而是判断每条候选资料是否适合用来回答用户问题。"
            "请严格按照相关性打分。"
            "如果资料能直接、完整回答问题，给 80-100 分。"
            "如果资料只能部分帮助回答问题，给 60-79 分。"
            "如果资料只是同主题、只是出现关键词、但不能直接回答问题，给 20-59 分。"
            "如果资料无关，给 0-19 分。"
            "必须只输出 JSON 数组，不要输出解释，不要使用 markdown。"
        ),
    }

    user_message = {
        "role": "user",
        "content": (
            f"用户问题：\n{query}\n\n"
            f"候选资料如下：\n{candidates_text}\n\n"
            "请对每条候选资料打分，并输出 JSON 数组。\n"
            "输出格式必须是：\n"
            "[\n"
            "  {\"index\": 0, \"score\": 95, \"reason\": \"能直接回答问题\"},\n"
            "  {\"index\": 1, \"score\": 35, \"reason\": \"只是出现关键词，但不能直接回答问题\"}\n"
            "]\n"
            "要求：\n"
            "1. index 必须对应候选资料编号\n"
            "2. score 必须是 0 到 100 的整数\n"
            "3. reason 用一句中文简短说明\n"
            "4. 必须覆盖所有候选资料\n"
            "5. 不要输出 JSON 数组以外的任何内容"
        ),
    }

    payload = {
        "model": MODEL_NAME,
        "messages": [system_message, user_message],
        "temperature": 0.1,
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
            timeout=60,
        )
        response.raise_for_status()

        result = response.json()
        raw_content = result["choices"][0]["message"]["content"]

        rerank_items = extract_json_array(raw_content)

        # 2. 建立 index -> score/reason 的映射
        score_map = {}
        reason_map = {}

        for row in rerank_items:
            index = int(row.get("index"))
            score = int(row.get("score", 0))
            reason = str(row.get("reason", ""))

            score_map[index] = score
            reason_map[index] = reason

        # 3. 给原 chunk 补充 rerank_score / rerank_reason
        reranked_chunks = []

        for index, item in enumerate(chunks):
            new_item = item.copy()
            new_item["rerank_score"] = score_map.get(index, 0)
            new_item["rerank_reason"] = reason_map.get(index, "reranker 未返回原因")
            reranked_chunks.append(new_item)

        # 4. 按 rerank_score 从高到低排序
        reranked_chunks = sorted(
            reranked_chunks,
            key=lambda x: x.get("rerank_score", 0),
            reverse=True,
        )

        # 5. 分数过滤
        filtered_chunks = [
            item for item in reranked_chunks
            if item.get("rerank_score", 0) >= min_score
        ]

        # 6. 兜底：如果全被过滤掉，至少保留 rerank 后第一条
        if not filtered_chunks and reranked_chunks:
            filtered_chunks = [reranked_chunks[0]]

        return filtered_chunks[:top_k]

    except Exception as e:
        # 兜底策略：
        # reranker 失败时，不让整个 RAG 链路失败，直接返回原始前 top_k 条
        fallback_chunks = []

        for item in chunks[:top_k]:
            new_item = item.copy()
            new_item["rerank_score"] = None
            new_item["rerank_reason"] = f"reranker_failed: {str(e)}"
            fallback_chunks.append(new_item)

        return fallback_chunks
def detect_reimbursement_amount_bucket(text: str) -> str | None:
    """
    识别报销金额区间类型。

    返回：
    - "low"：500元及以下
    - "middle"：500元以上且不超过2000元
    - "high"：超过2000元
    - None：没有识别到明确金额区间
    """

    # 去除空格，清理文本以便后续精确匹配
    clean_text = text.replace(" ", "")

    # 1. 低金额区间：500元及以下
    if (
        "500元及以下" in clean_text
        or "500元以下" in clean_text
        or "不超过500元" in clean_text
        or "500以下" in clean_text
    ):
        return "low"

    # 2. 中间金额区间：500元以上且不超过2000元
    # 注意：一定要放在 high 前面
    # 因为“不超过2000”里面也包含“超过2000”这几个字，先匹配 middle 可以拦截误判
    if (
        "500到2000" in clean_text
        or "500-2000" in clean_text
        or "500元以上且不超过2000" in clean_text
        or "500元以上不超过2000" in clean_text
        or "500元以上且不超过2000元" in clean_text
    ):
        return "middle"

    # 3. 高金额区间：超过2000元
    if (
        "超过2000" in clean_text
        or "2000元以上" in clean_text
        or "2000以上" in clean_text
    ):
        return "high"

    return None


def is_amount_range_conflict(query: str, chunk_text: str) -> bool:
    """
    判断报销金额区间是否冲突。

    作用：
    - qwen3-rerank 更偏语义相关性
    - 对金额区间这种精确业务条件，补一层规则过滤
    """

    query_bucket = detect_reimbursement_amount_bucket(query)
    chunk_bucket = detect_reimbursement_amount_bucket(chunk_text)

    # 如果问题或资料没有明确金额区间，就不做强过滤，交给大模型/重排序模型处理
    if query_bucket is None or chunk_bucket is None:
        return False

    # 如果金额区间明确且不同，就认为发生冲突
    return query_bucket != chunk_bucket