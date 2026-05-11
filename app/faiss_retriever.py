# retriever.py
import faiss
import numpy as np
from app.config import TOP_K



def find_relevant_chunks_by_faiss(
    faiss_index,
    query_embedding: list[float],
    chunk_records: list[dict],
    top_k: int = TOP_K
) -> list[dict]:
    try:
        faiss_index!=None
        print(f"✅ FAISS 索引已成功加载至内存")
        # ---------------------------------------------------------
        # 【工程优化：动态识别引擎并调优】
        # ---------------------------------------------------------
        # 1. 探测是否是 HNSW 引擎
        if hasattr(faiss_index, 'hnsw'):
            faiss_index.hnsw.efSearch = 32
            print("🔧 引擎识别为 HNSW，已设置寻路深度 efSearch=32")
            
        # 2. 探测是否是 IVFPQ (或 IVF) 引擎
        elif hasattr(faiss_index, 'nprobe'):
            # nprobe 决定了提问时要查几个堆。默认是 1。
            # 改成 10 意味着：去最像的 10 个堆里翻代号，精度大幅提升！
            faiss_index.nprobe = 10 
            print("🔧 引擎识别为 IVFPQ，已设置跨堆搜索 nprobe=10")
        
    except Exception as e:
        faiss_index = None
        print(f"⚠️ 警告: FAISS 索引未找到或加载失败: {str(e)}")

    # 防御性编程：检查索引是否真的加载成功了
    if faiss_index is None:
        raise RuntimeError("全局 FAISS 索引未加载，请先执行建库操作！")

    # 1. 转换向量格式
    query_vector = np.array([query_embedding], dtype=np.float32)
    faiss.normalize_L2(query_vector)

    # 2. 直接使用内存中的全局索引进行检索（纯 CPU 计算，速度极快） distances, indices都是这样的二维数组[[0.3,0.4,0.5]] [0]是为了让数据从[[0.3,0.4,0.5]] 变成[0.3,0.4,0.5] 
    distances, indices = faiss_index.search(query_vector, top_k)

    # 3. 组装结果
    scored_chunks = []
    for i, chunk_idx in enumerate(indices[0]):
        if chunk_idx == -1:
            continue

        scored_chunks.append({
            "text": chunk_records[chunk_idx]["text"],
            "faiss_score": float(distances[0][i])
        })


    return scored_chunks