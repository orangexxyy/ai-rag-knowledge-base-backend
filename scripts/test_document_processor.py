# scripts/test_document_processor.py

import sys
from pathlib import Path

# 把项目根目录加入 Python 搜索路径
PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.append(str(PROJECT_ROOT))

from app.document_loader import load_document
from app.document_processor import process_documents


def main():
    print("Document Processor 测试开始...")

    # 1. 先读取原始 Document
    documents = load_document("data/knowledge.txt")
    print("原始 Document 数量：", len(documents))

    # 2. 再清洗 Document
    processed_documents = process_documents(documents)
    print("清洗后 Document 数量：", len(processed_documents))

    first_doc = processed_documents[0]

    print("\n清洗后正文前 200 个字符：")
    print(first_doc.text[:200])

    print("\n清洗后 metadata：")
    print(first_doc.metadata)

    print("\nDocument Processor 测试结束。")


if __name__ == "__main__":
    main()