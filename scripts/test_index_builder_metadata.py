# scripts/test_index_builder_metadata.py

import sys
from pathlib import Path

# 把项目根目录加入 Python 搜索路径
PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.append(str(PROJECT_ROOT))

from app.document_loader import load_document
from app.document_processor import process_documents
from app.document_chunker import chunk_documents
import app.index_builder as index_builder


def fake_get_embedding(text: str) -> list[float]:
    """
    测试用 fake embedding。

    目的：
    - 不调用真实 embedding API
    - 不消耗 token / 费用
    - 只验证 chunk_record 结构是否正确
    """
    return [0.1, 0.2, 0.3]


def main():
    print("Index Builder metadata 测试开始...")

    # 1. 临时替换真实 get_embedding
    index_builder.get_embedding = fake_get_embedding

    # 2. 走完整资料处理前半段
    documents = load_document("data/knowledge.txt")
    processed_documents = process_documents(documents)
    chunk_items = chunk_documents(processed_documents)

    print("chunk_items 数量：", len(chunk_items))

    # 3. 只取前 3 个 chunk 测试，避免输出太多
    sample_chunk_items = chunk_items[:3]

    # 4. 构建 chunk_records
    chunk_records = index_builder.build_chunk_records(sample_chunk_items)

    print("chunk_records 数量：", len(chunk_records))

    print("\n前 3 个 chunk_record 预览：")

    for record in chunk_records:
        print("\n==============================")
        print("chunk_id：", record["chunk_id"])
        print("text 前 100 个字符：")
        print(record["text"][:100])

        print("\nembedding：")
        print(record["embedding"])

        print("\nmetadata：")
        print(record["metadata"])

    print("\nIndex Builder metadata 测试结束。")


if __name__ == "__main__":
    main()