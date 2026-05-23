from app.embedding_api import get_embedding


def normalize_chunk_items(chunks_or_chunk_items: list) -> list[dict]:
    """
    将输入统一转换成 chunk_item 格式。

    为什么需要这个函数？
    - 老链路传进来的是 list[str]
    - 新链路传进来的是 list[dict]，每个 dict 里有 text 和 metadata
    - 为了小步升级，不一次性破坏旧链路，这里做一层兼容

    统一后的格式：
    {
        "text": "chunk 文本",
        "metadata": {...}
    }
    """

    normalized_items = []

    for item in chunks_or_chunk_items:
        # 情况 1：兼容旧链路 list[str]
        if isinstance(item, str):
            text = item.strip()
            metadata = {}

        # 情况 2：新链路 list[dict]
        elif isinstance(item, dict):
            text = str(item.get("text", "")).strip()

            # metadata 必须是 dict，如果不是 dict，就兜底为空字典
            raw_metadata = item.get("metadata", {})
            metadata = raw_metadata.copy() if isinstance(raw_metadata, dict) else {}

        # 情况 3：其他异常类型，直接跳过
        else:
            continue

        # 空文本不进入索引
        if not text:
            continue

        normalized_items.append({
            "text": text,
            "metadata": metadata
        })

    return normalized_items


def build_chunk_records(chunks_or_chunk_items: list) -> list[dict]:
    """
    根据 chunk_items 构建带 embedding 的 chunk_records。

    输入可以是：
    1. 旧格式：list[str]
    2. 新格式：list[dict]，例如：
       {
           "text": "chunk 文本",
           "metadata": {
               "source_file": "knowledge.txt",
               "file_type": "txt",
               "page": None,
               "sheet_name": None,
               "row_number": None
           }
       }

    输出格式：
    {
        "chunk_id": 0,
        "text": "chunk 文本",
        "embedding": [...],
        "metadata": {...}
    }
    """

    chunk_records = []

    # 先统一输入格式
    chunk_items = normalize_chunk_items(chunks_or_chunk_items)

    for idx, item in enumerate(chunk_items):
        chunk_text = item["text"]

        # 每个 record 都复制一份 metadata，避免互相影响
        metadata = item["metadata"].copy()

        # 把全局 chunk_id 也放进 metadata，方便后续 debug / 溯源展示
        metadata["chunk_id"] = idx

        # 调用 embedding 接口，获取当前 chunk 的向量
        # 注意：embedding 只基于 chunk_text 生成，不基于 metadata
        chunk_embedding = get_embedding(chunk_text)

        # 组装成统一结构
        chunk_records.append({
            "chunk_id": idx,
            "text": chunk_text,
            "embedding": chunk_embedding,
            "metadata": metadata
        })

    return chunk_records