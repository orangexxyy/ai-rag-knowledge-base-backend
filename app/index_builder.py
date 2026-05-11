from app.embedding_api import get_embedding


def build_chunk_records(chunks: list[str]) -> list[dict]:
    """
    根据知识块列表构建带 embedding 的 chunk_records
    """
    chunk_records = []

    for idx, chunk_text in enumerate(chunks):
        # 调用 embedding 接口，获取当前 chunk 的向量
        chunk_embedding = get_embedding(chunk_text)

        # 组装成统一结构
        chunk_records.append({
            "chunk_id": idx,
            "text": chunk_text,
            "embedding": chunk_embedding
        })

    return chunk_records