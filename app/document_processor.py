# app/document_processor.py

import re

from app.document_models import Document


def clean_text(text: str) -> str:
    """
    清洗原始文本。

    当前是最小可行版本，先做三件事：
    1. 统一换行符
    2. 去掉每行首尾空格
    3. 压缩过多空行

    注意：
    - 不要把所有换行都删掉
    - 因为当前 chunk 策略还依赖空行 / 段落边界
    """

    if not text:
        return ""

    # 【可直接复制】统一 Windows / Linux / Mac 换行
    text = text.replace("\r\n", "\n").replace("\r", "\n")

    # 【重点理解】逐行 strip，去掉每行首尾空格，但保留换行结构
    lines = [line.strip() for line in text.split("\n")]

    # 重新拼回文本
    text = "\n".join(lines)

    # 【可直接复制】把连续多个空格 / tab 压缩成一个空格
    text = re.sub(r"[ \t]+", " ", text)

    # 【重点理解】三个及以上换行压缩成两个换行
    # 这样可以减少脏空行，但仍然保留段落分隔
    text = re.sub(r"\n{3,}", "\n\n", text)

    return text.strip()


def process_documents(documents: list[Document]) -> list[Document]:
    """
    批量处理 Document。

    输入：
    - 原始 Document 列表

    输出：
    - 清洗后的 Document 列表

    重点：
    - 只清洗 text
    - metadata 必须保留
    """

    processed_documents = []

    for doc in documents:
        cleaned_text = clean_text(doc.text)

        # 如果清洗后是空文本，直接跳过
        if not cleaned_text:
            print("⚠️ 清洗后为空，跳过 Document：", doc.metadata)
            continue

        # 【重点理解】
        # metadata.copy() 是为了避免后续修改新 Document 的 metadata 时，
        # 意外影响原始 Document 的 metadata。
        new_doc = Document(
            text=cleaned_text,
            metadata=doc.metadata.copy(),
        )

        processed_documents.append(new_doc)

    return processed_documents
