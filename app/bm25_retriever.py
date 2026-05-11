import jieba
from rank_bm25 import BM25Okapi
from app.config import TOP_K

# 定义一个极简的“停用词表” (Stop Words)
# BM25 靠词频打分，如果不把这些废话过滤掉，搜“我的合同”时，系统会被“的”字带偏。
STOP_WORDS = {"的", "了", "和", "是", "在", "我", "有", "就", "不", "人", "都", "一", "一个", "上", "也", "很", "到", "说", "要", "去", "你", "会", "着", "没有", "看", "好", "自己", "这"}

def tokenize(text: str) -> list[str]:
    """
    1. 分词器 (Tokenizer)
    把长句子切碎。比如 "我要查合同" -> ["我", "要", "查", "合同"]
    """
    words = jieba.lcut(text)
    # 过滤掉空格和无意义的停用词
    return [w for w in words if w.strip() and w not in STOP_WORDS]

def build_bm25_index(chunk_records: list[dict]) -> BM25Okapi:
    """
    2. 构建 BM25 内存索引
    注意：BM25 算法极其轻量，几十万条数据在内存中构建也只需几秒，
    所以我们不需要像 FAISS 那样把它存成磁盘文件，直接每次启动时在内存里建好就行。
    """
    print("📚 正在构建 BM25 词法索引...")
    # 把知识库里的每一段文本，都切成词的数组
    tokenized_corpus = [tokenize(record["text"]) for record in chunk_records]
    
    # 喂给 BM25Okapi 建立倒排索引
    bm25 = BM25Okapi(tokenized_corpus)
    print("✅ BM25 索引构建完成！")
    return bm25

def find_relevant_chunks_by_bm25(
    query: str,
    bm25_index: BM25Okapi,
    chunk_records: list[dict],
    top_k: int = TOP_K
) -> list[dict]:
    """
    3. 核心检索函数
    用切碎的问题去知识库里“抠字眼”
    """
    # 先把用户的问题也切碎
    tokenized_query = tokenize(query)
    
    # 获取知识库中所有片段的 BM25 分数
    scores = bm25_index.get_scores(tokenized_query)
    
    scored_chunks = []
    for idx, score in enumerate(scores):
        scored_chunks.append({
            "text": chunk_records[idx]["text"],
            "bm25_score": float(score)
        })

    scored_chunks.sort(key=lambda x: x["bm25_score"], reverse=True)
    
    return scored_chunks[:top_k]