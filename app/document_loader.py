# app/document_loader.py

import os
from pathlib import Path
from datetime import date, datetime
from openpyxl import load_workbook
from pypdf import PdfReader

from app.document_models import Document



def format_excel_cell_value(value) -> str:
    
    """
    将 Excel 单元格值转换成适合拼接进文本的字符串。

    为什么要单独封装？
    - Excel 单元格可能是字符串、数字、日期、空值
    - RAG 最终需要的是稳定的文本
    """

    if value is None:
        return ""

    # 日期类型转成 yyyy-mm-dd，避免直接 str() 出现不稳定格式
    if isinstance(value, datetime):
        return value.strftime("%Y-%m-%d %H:%M:%S")

    if isinstance(value, date):
        return value.strftime("%Y-%m-%d")

    return str(value).strip()


def build_excel_row_text(
    sheet_name: str,
    headers: list[str],
    row_values: list[str],
) -> str:
    """
    将 Excel 的一行数据转换成自然语言文本。

    输入：
    - headers: 第一行表头
    - row_values: 当前行数据

    输出示例：
    权限申请记录：系统名称：VPN；权限类型：远程访问权限；申请条件：远程办公或出差。
    """

    field_texts = []

    for header, value in zip(headers, row_values):
        # 表头或值为空，就跳过，避免生成“字段：”
        if not header or not value:
            continue

        field_texts.append(f"{header}：{value}")

    # 如果这一行没有任何有效字段，返回空字符串
    if not field_texts:
        return ""

    # sheet_name 通常有业务含义，比如“权限申请表”“资产台账”
    return f"{sheet_name}记录：" + "；".join(field_texts) + "。"


def load_excel_document(file_path: str) -> list[Document]:
    """
    读取 xlsx 文件，并按 sheet / row 转换成 Document 列表。

    当前最小版本规则：
    - 每个 sheet 的第一行作为表头
    - 从第二行开始，每一行生成一个 Document
    - 空行跳过
    - metadata 保留 sheet_name 和 row_number

    当前暂不支持：
    - 合并单元格
    - 多级表头
    - 复杂透视表
    - 公式重新计算
    """

    if not os.path.exists(file_path):
        raise FileNotFoundError(f"文件不存在：{file_path}")

    # data_only=True 表示如果单元格是公式，读取公式计算后的缓存值
    workbook = load_workbook(file_path, data_only=True)

    documents = []

    for sheet in workbook.worksheets:
        sheet_name = sheet.title

        # 如果 sheet 少于 2 行，说明没有数据行
        if sheet.max_row < 2:
            continue

        # 1. 读取第一行作为表头
        header_cells = next(
            sheet.iter_rows(min_row=1, max_row=1, values_only=True)
        )

        headers = []

        for index, value in enumerate(header_cells):
            header = format_excel_cell_value(value)

            # 如果表头为空，给一个兜底字段名，避免数据完全丢失
            if not header:
                header = f"字段{index + 1}"

            headers.append(header)

        # 2. 从第二行开始读取数据
        for row_number, row in enumerate(
            sheet.iter_rows(min_row=2, values_only=True),
            start=2,
        ):
            row_values = [format_excel_cell_value(value) for value in row]

            # 跳过整行为空的数据
            if not any(row_values):
                continue

            text = build_excel_row_text(
                sheet_name=sheet_name,
                headers=headers,
                row_values=row_values,
            )

            if not text.strip():
                continue

            metadata = {
                "source_file": Path(file_path).name,
                "source_path": file_path,
                "file_type": "xlsx",
                "page": None,
                "sheet_name": sheet_name,
                "row_number": row_number,
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
        raise ValueError(f"Excel 未读取到有效数据行：{file_path}")

    return documents

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
    supported_suffixes = {".txt", ".pdf", ".xlsx"}

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

    if suffix == ".xlsx":
        return load_excel_document(file_path)

    raise ValueError(f"暂不支持的文件类型：{suffix}")