from app.faiss_retriever import find_relevant_chunks_by_faiss
from app.bm25_retriever import find_relevant_chunks_by_bm25
from app.config import RRF_K,FAISS_WEIGHT,BM25_WEIGHT

def hybrid_search(
    bm25_index,
    faiss_index,
    query: str,
    query_embedding: list[float],
    chunk_records: list[dict],
    recall_k: int,
    top_k: int
) -> list[dict]:
    """
    双轨混合检索：
    - FAISS：语义检索
    - BM25：关键词检索
    - RRF：融合排序
    """

    # 1. 两边先各自召回更多候选
    faiss_results = find_relevant_chunks_by_faiss(
        faiss_index=faiss_index,
        query_embedding=query_embedding,
        chunk_records=chunk_records,
        top_k=recall_k
    )
    bm25_results = find_relevant_chunks_by_bm25(
        query=query,
        bm25_index=bm25_index,
        chunk_records=chunk_records,
        top_k=recall_k
    )

    # 2. 融合结果表
    merged_results = {}

    # 3. 处理 FAISS 结果
    for rank, doc in enumerate(faiss_results):
        text = doc["text"]
        faiss_score = doc["faiss_score"]
        rrf_score = 1.0 / (RRF_K + rank + 1)

        if text not in merged_results:
            merged_results[text] = {
                "text": text,
                "faiss_score": faiss_score,
                "bm25_score": None,
                "faiss_rank": rank,
                "bm25_rank": None,
                "rrf_score": rrf_score * FAISS_WEIGHT,
            }
        else:
            merged_results[text]["faiss_score"] = faiss_score
            merged_results[text]["faiss_rank"] = rank
            merged_results[text]["rrf_score"] += rrf_score * FAISS_WEIGHT

    # 4. 处理 BM25 结果
    for rank, doc in enumerate(bm25_results):
        text = doc["text"]
        bm25_score = doc["bm25_score"]
        rrf_score = 1.0 / (RRF_K + rank + 1)

        if text not in merged_results:
            merged_results[text] = {
                "text": text,
                "faiss_score": None,
                "bm25_score": bm25_score,
                "faiss_rank": None,
                "bm25_rank": rank,
                "rrf_score": rrf_score * BM25_WEIGHT,
            }
        else:
            merged_results[text]["bm25_score"] = bm25_score
            merged_results[text]["bm25_rank"] = rank
            merged_results[text]["rrf_score"] += rrf_score * BM25_WEIGHT

    # 5. 补 source 字段
    for text, item in merged_results.items():
        faiss_hit = item["faiss_score"] is not None
        bm25_hit = item["bm25_score"] is not None

        if faiss_hit and bm25_hit:
            item["source"] = "both"
        elif faiss_hit:
            item["source"] = "faiss"
        else:
            item["source"] = "bm25"

    # 6. 排序并取前 top_k
    sorted_results = sorted(
        merged_results.values(),
        key=lambda x: x["rrf_score"],
        reverse=True
    )

    return sorted_results[:top_k]
