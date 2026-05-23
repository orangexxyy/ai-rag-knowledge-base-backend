# scripts/test_document_chunker.py

import sys
from pathlib import Path

# 把项目根目录加入 Python 搜索路径
PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.append(str(PROJECT_ROOT))

from app.document_loader import load_document
from app.document_processor import process_documents
from app.document_chunker import chunk_documents


def main():
    print("Document Chunker 测试开始...")

    # 1. 读取原始 Document
    documents = load_document("data/knowledge.txt")
    print("原始 Document 数量：", len(documents))

    # 2. 清洗 Document
    processed_documents = process_documents(documents)
    print("清洗后 Document 数量：", len(processed_documents))

    # 3. 切成带 metadata 的 chunk_items
    chunk_items = chunk_documents(processed_documents)
    print("生成 chunk_items 数量：", len(chunk_items))

    print("\n前 3 个 chunk 预览：")

    for index, item in enumerate(chunk_items[:3]):
        print("\n==============================")
        print("chunk 序号：", index)
        print("chunk 文本前 120 个字符：")
        print(item["text"][:120])

        print("\nchunk metadata：")
        print(item["metadata"])

    print("\nDocument Chunker 测试结束。")


if __name__ == "__main__":
    main()