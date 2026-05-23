# app/document_loader.py

import os
from pathlib import Path

from app.document_models import Document


def load_txt_document(file_path: str) -> list[Document]:
    """
    读取 txt 文件，并转换成统一 Document 结构。

    为什么返回 list[Document]？
    - PDF 以后会按 page 返回多个 Document
    - Excel 以后会按 sheet / row 返回多个 Document
    - 为了让 txt / PDF / Excel 的返回结构统一，所以 txt 也返回 list
    """

    # 【可直接复制】路径存在性检查
    if not os.path.exists(file_path):
        raise FileNotFoundError(f"文件不存在：{file_path}")

    # 【可直接复制】读取 txt 文件
    with open(file_path, "r", encoding="utf-8") as f:
        text = f.read()

    # 【重点手写】组装 metadata
    metadata = {
        "source_file": Path(file_path).name,   # 文件名，例如 knowledge.txt
        "source_path": file_path,              # 文件路径，例如 data/knowledge.txt
        "file_type": "txt",                   # 文件类型
        "page": None,                          # txt 没有页码
        "sheet_name": None,                    # txt 没有 sheet
        "row_number": None,                    # txt 没有行号概念
        "section_title": None,                 # 后面可以从标题中提取
        "version": None,                       # 后面可以扩展版本管理
        "permission_level": "internal",        # 当前先默认内部资料
    }

    # 【重点手写】返回统一 Document 列表
    return [
        Document(
            text=text,
            metadata=metadata,
        )
    ]



def load_document(file_path: str) -> list[Document]:
    """
    根据文件后缀选择对应 loader。

    当前先支持 txt。
    后续会扩展：
    - .pdf
    - .xlsx
    """

    suffix = Path(file_path).suffix.lower()

    if suffix == ".txt":
        return load_txt_document(file_path)

    # 这里先明确抛错，而不是偷偷忽略
    # 这样调试时更容易发现当前不支持哪些文件
    raise ValueError(f"暂不支持的文件类型：{suffix}")