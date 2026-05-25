# scripts/test_pdf_loader.py

import sys
from pathlib import Path

# 把项目根目录加入 Python 搜索路径
PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.append(str(PROJECT_ROOT))

from app.document_loader import load_document
from app.document_processor import process_documents
from app.document_chunker import chunk_documents


def main():
    print("PDF Loader 测试开始...")

    pdf_path = "data/raw_docs/employee_handbook_sample.pdf"

    # 1. 读取 PDF，按 page 转成 Document
    documents = load_document(pdf_path)

    print("读取到 Document 数量：", len(documents))

    first_doc = documents[0]

    print("\n第一页正文前 300 个字符：")
    print(first_doc.text[:300])

    print("\n第一页 metadata：")
    print(first_doc.metadata)

    # 2. 复用现有 Processor
    processed_documents = process_documents(documents)
    print("\n清洗后 Document 数量：", len(processed_documents))

    # 3. 复用现有 Chunker
    chunk_items = chunk_documents(processed_documents)
    print("生成 chunk_items 数量：", len(chunk_items))

    print("\n前 3 个 chunk 预览：")

    for index, item in enumerate(chunk_items[:3]):
        print("\n==============================")
        print("chunk 序号：", index)
        print("text 前 120 个字符：")
        print(item["text"][:120])

        print("\nmetadata：")
        print(item["metadata"])

    print("\nPDF Loader 测试结束。")


if __name__ == "__main__":
    main()