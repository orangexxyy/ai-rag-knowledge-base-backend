# app/document_chunker.py

from app.document_models import Document
from app.knowledge import split_text_to_chunks


def chunk_documents(documents: list[Document]) -> list[dict]:
    """
    将 Document 列表切分成带 metadata 的 chunk_items。

    输入：
    - documents: 清洗后的 Document 列表

    输出：
    - chunk_items: 每个元素都是一个 dict，格式为：
      {
          "text": "chunk 文本",
          "metadata": {
              "source_file": "...",
              "file_type": "...",
              "page": ...,
              "sheet_name": ...,
              "row_number": ...,
              "chunk_index_in_document": 0
          }
      }

    为什么不直接返回 list[str]？
    - 因为企业 RAG 需要来源追溯
    - PDF 需要保留 page
    - Excel 需要保留 sheet_name / row_number
    - 后续回答时需要知道 chunk 来自哪里
    """

    chunk_items = []

    for doc_index, doc in enumerate(documents):
        # 1. 防御性处理：跳过空文档
        if not doc.text or not doc.text.strip():
            continue

        # 2. 复用现有 chunk 策略
        # 当前项目中 split_text_to_chunks 会根据 config.py 的 CHUNK_METHOD 自动选择策略
        chunks = split_text_to_chunks(doc.text)

        # 3. 给每个 chunk 继承原始 Document 的 metadata
        for chunk_index, chunk_text in enumerate(chunks):
            if not chunk_text or not chunk_text.strip():
                continue

            # 【重点】
            # 必须 copy 一份，避免多个 chunk 共用同一个 metadata 对象
            metadata = doc.metadata.copy()

            # 当前 Document 在本次 documents 列表中的位置
            metadata["doc_index"] = doc_index

            # 当前 chunk 在这个 Document 内部的编号
            # 例如：PDF 第 3 页被切成 2 个 chunk，则编号为 0、1
            metadata["chunk_index_in_document"] = chunk_index

            # 当前 chunk 的字符长度，方便调试 chunk 是否过长或过短
            metadata["chunk_char_length"] = len(chunk_text)

            chunk_items.append(
                {
                    "text": chunk_text.strip(),
                    "metadata": metadata,
                }
            )

    return chunk_items