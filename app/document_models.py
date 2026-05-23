# app/document_models.py

from dataclasses import dataclass, field
from typing import Any


@dataclass
class Document:
    """
    企业 RAG 中的统一文档结构。

    不管原始资料来自 txt、PDF、Excel，
    最后都先转换成 Document，
    再进入清洗、chunk、embedding、index 流程。
    """

    # 文档正文内容
    text: str

    # 文档元数据
    # 例如：source_file、file_type、page、sheet_name、row_number 等
    metadata: dict[str, Any] = field(default_factory=dict)