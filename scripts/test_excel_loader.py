# scripts/test_excel_loader.py

import sys
from pathlib import Path

# 把项目根目录加入 Python 搜索路径
PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.append(str(PROJECT_ROOT))

from app.document_loader import load_document
from app.document_processor import process_documents
from app.document_chunker import chunk_documents


def main():
    print("Excel Loader 测试开始...")

    excel_path = "data/raw_docs/permission_matrix_sample.xlsx"

    # 1. 读取 Excel，按 row 转成 Document
    documents = load_document(excel_path)

    print("读取到 Document 数量：", len(documents))

    print("\n前 5 个 Document：")
    for index, doc in enumerate(documents[:5]):
        print("\n------------------------------")
        print("Document 序号：", index)
        print("text：")
        print(doc.text)
        print("metadata：")
        print(doc.metadata)

    # 2. 走通用清洗
    processed_documents = process_documents(documents)
    print("\n清洗后 Document 数量：", len(processed_documents))

    # 3. 走 chunker
    chunk_items = chunk_documents(processed_documents)
    print("生成 chunk_items 数量：", len(chunk_items))

    print("\n前 5 个 chunk：")
    for index, item in enumerate(chunk_items[:5]):
        print("\n==============================")
        print("chunk 序号：", index)
        print("text：")
        print(item["text"])
        print("metadata：")
        print(item["metadata"])

    print("\nExcel Loader 测试结束。")


if __name__ == "__main__":
    main()