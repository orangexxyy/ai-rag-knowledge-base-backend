# app/document_chunker.py

import re

from app.document_models import Document
from app.knowledge import split_text_to_chunks


def prepare_text_for_policy_clause_split(
    text: str,
    file_type: str | None = None,
) -> str:
    """
    为 policy_clause 条款级切分准备文本。

    注意：
    - 这不是通用清洗函数
    - 通用清洗仍然由 document_processor.py 负责
    - 这里是“条款切分策略内部”的局部文本规整

    为什么需要 file_type？
    - PDF 抽取文本时，可能出现行内断行：
      直属主\n管 → 直属主管
      调休申\n请 → 调休申请
    - txt 通常本身就是线性文本，不应该随便合并单换行
    """

    if not text:
        return ""

    # 【重点】
    # 只有 PDF 才做更激进的单换行合并。
    # 这样可以避免影响原来结构正常的 txt。
    if file_type == "pdf":
        # 合并单个换行，减少 PDF 抽取产生的行内断行问题
        # 例如：直属主\n管 → 直属主管
        text = re.sub(r"(?<!\n)\n(?!\n)", "", text)

        # 去掉 PDF 页脚中的页码噪声，例如：第 2 页
        # 因为 page 已经保存在 metadata["page"] 里，不需要混进 chunk 文本
        text = re.sub(r"第\s*\d+\s*页\s*$", "", text)

    return text.strip()


def split_policy_clauses(
    text: str,
    file_type: str | None = None,
) -> list[str]:
    """
    按制度条款标题切分文本。

    这一步不是判断是否包含“事假”这种关键词，
    而是识别业务结构边界。

    当前支持的标题格式示例：
    - 请假制度条款A（年假）：
    - 请假制度条款B（病假）：
    - 请假制度条款C（事假）：
    - 差旅报销制度条款A：
    - 差旅报销制度条款B：

    核心逻辑：
    1. 找到所有条款标题的位置
    2. 从当前标题切到下一个标题之前
    3. 每一段作为一个独立 chunk
    """

    prepared_text = prepare_text_for_policy_clause_split(
        text=text,
        file_type=file_type,
    )

    if not prepared_text:
        return []

    # 【重点】
    # 这里识别的是“条款标题结构”，不是写死某个具体业务词。
    title_pattern = re.compile(
       r"([\u4e00-\u9fa5A-Za-z0-9]+制度条款[A-Z](?:（[^）]+）)?：)"
    )

    matches = list(title_pattern.finditer(prepared_text))

    # 没有识别到条款标题，就说明当前文本不适合 policy_clause
    if not matches:
        return []

    clauses = []

    for index, match in enumerate(matches):
        # 当前条款标题开始位置
        start = match.start()

        # 下一个条款标题开始位置
        # 如果当前是最后一个标题，就切到全文结尾
        if index + 1 < len(matches):
            end = matches[index + 1].start()
        else:
            end = len(prepared_text)

        clause = prepared_text[start:end].strip()

        if clause:
            clauses.append(clause)

    return clauses


def get_chunks_for_document(doc: Document) -> tuple[list[str], str]:
    """
    根据 Document 内容选择 chunk 策略。

    当前策略优先级：

    1. policy_clause
       如果文本中存在“制度条款A/B/C...”这种结构，
       优先按条款切分。

    2. paragraph_then_overlap
       如果识别不到条款结构，
       退回项目原来的通用 chunk 策略。

    注意：
    - file_type 不是直接决定 chunk 策略
    - file_type 只决定 policy_clause 前是否做 PDF 专用文本准备
    """

    file_type = doc.metadata.get("file_type")

    # 1. 优先尝试制度条款级切分
    clause_chunks = split_policy_clauses(
        text=doc.text,
        file_type=file_type,
    )

    if clause_chunks:
        return clause_chunks, "policy_clause"

    # 2. 如果没有条款结构，退回原来的通用切分策略
    return split_text_to_chunks(doc.text), "paragraph_then_overlap"


def chunk_documents(documents: list[Document]) -> list[dict]:
    """
    将 Document 列表切分成带 metadata 的 chunk_items。

    输入：
    - documents: 清洗后的 Document 列表

    输出：
    - chunk_items: 每个元素都是：
      {
          "text": "chunk 文本",
          "metadata": {
              "source_file": "...",
              "file_type": "...",
              "page": ...,
              "sheet_name": ...,
              "row_number": ...,
              "doc_index": 0,
              "chunk_index_in_document": 0,
              "chunk_char_length": 100,
              "chunk_strategy": "policy_clause"
          }
      }

    为什么不直接返回 list[str]？
    - 企业 RAG 需要来源追溯
    - PDF 需要保留 page
    - Excel 后续需要保留 sheet_name / row_number
    - debug 和面试展示需要看到 chunk 来源
    """

    chunk_items = []

    for doc_index, doc in enumerate(documents):
        # 1. 防御性处理：跳过空文档
        if not doc.text or not doc.text.strip():
            continue

        # 2. 根据 Document 内容结构选择 chunk 策略
        chunks, chunk_strategy = get_chunks_for_document(doc)

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
            # 例如 PDF 第 2 页有 4 个条款 chunk，则编号为 0、1、2、3
            metadata["chunk_index_in_document"] = chunk_index

            # 当前 chunk 的字符长度，方便 debug
            metadata["chunk_char_length"] = len(chunk_text)

            # 当前 chunk 使用的切分策略
            # 可能是 policy_clause，也可能是 paragraph_then_overlap
            metadata["chunk_strategy"] = chunk_strategy

            chunk_items.append(
                {
                    "text": chunk_text.strip(),
                    "metadata": metadata,
                }
            )

    return chunk_items