# scripts/test_document_dir_loader.py

import sys
from pathlib import Path

# 把项目根目录加入 Python 搜索路径
PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.append(str(PROJECT_ROOT))

from app.document_loader import load_documents_from_dir
from app.document_processor import process_documents
from app.document_chunker import chunk_documents


def main():
    print("资料目录 Loader 测试开始...")

    docs_dir = "data/raw_docs"

    # 1. 批量读取目录中的 txt / pdf
    documents = load_documents_from_dir(docs_dir)
    print("读取到 Document 总数：", len(documents))

    print("\n前 5 个 Document metadata：")
    for index, doc in enumerate(documents[:5]):
        print("\n------------------------------")
        print("Document 序号：", index)
        print(doc.metadata)
        print("正文前 100 个字符：")
        print(doc.text[:100])

    # 2. 复用通用清洗
    processed_documents = process_documents(documents)
    print("\n清洗后 Document 总数：", len(processed_documents))

    # 3. 复用 chunk
    chunk_items = chunk_documents(processed_documents)
    print("生成 chunk_items 总数：", len(chunk_items))

    print("\n前 5 个 chunk metadata：")
    for index, item in enumerate(chunk_items[:5]):
        print("\n==============================")
        print("chunk 序号：", index)
        print("text 前 120 个字符：")
        print(item["text"][:120])
        print("metadata：")
        print(item["metadata"])

    print("\n资料目录 Loader 测试结束。")


if __name__ == "__main__":
    main()