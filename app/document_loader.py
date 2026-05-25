# app/document_loader.py

import os
from pathlib import Path

from pypdf import PdfReader

from app.document_models import Document


def load_documents_from_dir(dir_path: str) -> list[Document]:
    """
    从目录中批量读取企业资料文件，并转换成统一 Document 列表。

    当前支持：
    - .txt
    - .pdf

    后续可扩展：
    - .xlsx
    - .docx

    为什么放在 document_loader.py？
    - Loader 层负责“资料读取”
    - index_manager 只负责调用它，不应该自己遍历和解析各种文件
    """

    dir_path_obj = Path(dir_path)

    if not dir_path_obj.exists():
        raise FileNotFoundError(f"资料目录不存在：{dir_path}")

    if not dir_path_obj.is_dir():
        raise NotADirectoryError(f"路径不是目录：{dir_path}")

    all_documents = []

    # 当前支持的文件后缀
    supported_suffixes = {".txt", ".pdf"}

    # 遍历目录下的文件
    for file_path in sorted(dir_path_obj.iterdir(), key=lambda p: p.name.lower()):
        # 跳过子目录
        if not file_path.is_file():
            continue

        suffix = file_path.suffix.lower()

        # 跳过不支持的文件类型
        if suffix not in supported_suffixes:
            print(f"⚠️ 跳过不支持的文件：{file_path}")
            continue

        print(f"📄 正在读取资料文件：{file_path}")

        # 复用已有 load_document()
        documents = load_document(str(file_path))

        all_documents.extend(documents)

    if not all_documents:
        raise ValueError(f"资料目录中没有读取到任何支持的文档：{dir_path}")

    return all_documents

def load_txt_document(file_path: str) -> list[Document]:
    """
    读取 txt 文件，并转换成统一 Document 结构。
    """

    if not os.path.exists(file_path):
        raise FileNotFoundError(f"文件不存在：{file_path}")

    with open(file_path, "r", encoding="utf-8") as f:
        text = f.read()

    metadata = {
        "source_file": Path(file_path).name,
        "source_path": file_path,
        "file_type": "txt",
        "page": None,
        "sheet_name": None,
        "row_number": None,
        "section_title": None,
        "version": None,
        "permission_level": "internal",
    }

    return [
        Document(
            text=text,
            metadata=metadata,
        )
    ]


def load_pdf_document(file_path: str) -> list[Document]:
    """
    读取文本型 PDF，并按 page 转换成 Document 列表。

    当前最小版本：
    - 只支持文本型 PDF
    - 一页生成一个 Document
    - metadata.page 从 1 开始
    """

    if not os.path.exists(file_path):
        raise FileNotFoundError(f"文件不存在：{file_path}")

    reader = PdfReader(file_path)

    documents = []

    for page_index, page in enumerate(reader.pages):
        page_number = page_index + 1

        # extract_text() 可能返回 None，所以用空字符串兜底
        text = page.extract_text() or ""

        # 空页或扫描页暂时跳过
        if not text.strip():
            continue

        metadata = {
            "source_file": Path(file_path).name,
            "source_path": file_path,
            "file_type": "pdf",
            "page": page_number,
            "sheet_name": None,
            "row_number": None,
            "section_title": None,
            "version": None,
            "permission_level": "internal",
        }

        documents.append(
            Document(
                text=text,
                metadata=metadata,
            )
        )

    if not documents:
        raise ValueError(
            f"PDF 未提取到任何文本，可能是扫描型 PDF 或空文件，当前版本暂不支持 OCR：{file_path}"
        )

    return documents


def load_document(file_path: str) -> list[Document]:
    """
    根据文件后缀选择对应 loader。
    """

    suffix = Path(file_path).suffix.lower()

    if suffix == ".txt":
        return load_txt_document(file_path)

    if suffix == ".pdf":
        return load_pdf_document(file_path)

    raise ValueError(f"暂不支持的文件类型：{suffix}")