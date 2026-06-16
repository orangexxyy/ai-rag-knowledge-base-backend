# scripts/test_pdf_table_ocr_loader.py

import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.append(str(PROJECT_ROOT))

from app.config import OCR_PROVIDER
from app.document_loader import (
    build_pdf_image_placeholder_document,
    build_pdf_table_row_text,
    load_document,
    should_handle_pdf_page_image,
)


def get_sample_pdf_path() -> str | None:
    pdf_files = sorted((PROJECT_ROOT / "data" / "raw_docs").glob("*.pdf"))
    if not pdf_files:
        return None
    return str(pdf_files[0].relative_to(PROJECT_ROOT))


def assert_true(condition: bool, message: str):
    if not condition:
        raise AssertionError(message)


def test_text_pdf_still_loads():
    pdf_path = get_sample_pdf_path()
    if pdf_path is None:
        print("未找到 data/raw_docs/*.pdf，跳过真实 PDF 读取测试。")
        return

    documents = load_document(pdf_path)

    text_docs = [
        doc
        for doc in documents
        if doc.metadata.get("file_type") == "pdf"
        and doc.metadata.get("content_type") == "text"
    ]

    assert_true(text_docs, "文本型 PDF 应继续生成 content_type=text 的 Document")
    assert_true(
        any(doc.metadata.get("page") == 2 for doc in text_docs),
        "文本型 PDF 应继续保留 page metadata",
    )


def test_pdf_without_tables_or_ocr_does_not_crash():
    pdf_path = get_sample_pdf_path()
    if pdf_path is None:
        print("未找到 data/raw_docs/*.pdf，跳过无表格 / OCR 默认关闭读取测试。")
        return

    documents = load_document(pdf_path)

    assert_true(len(documents) > 0, "无表格或 OCR 未启用时，PDF Loader 不应报错")
    assert_true(OCR_PROVIDER == "none", "OCR_PROVIDER 默认值应为 none")


def test_table_row_text_builder():
    text = build_pdf_table_row_text(
        page_number=2,
        table_index=1,
        row_index=3,
        headers=["字段A", "字段B", "字段C"],
        row_values=["值A", "值B", ""],
    )

    assert_true("PDF表格记录：第2页 表格1 第3行" in text, "表格文本应保留页码/表格/行号")
    assert_true("字段A=值A" in text, "表格文本应包含 header=value")
    assert_true("字段B=值B" in text, "表格文本应包含多个有效字段")
    assert_true("字段C=" not in text, "空值字段不应进入表格文本")


def test_default_ocr_none_scan_heuristic():
    assert_true(
        not should_handle_pdf_page_image(
            text="这是一段足够长的普通文本内容，页面里即使有 logo 也不应生成图片占位。",
            image_count=1,
            image_area_ratio=0.05,
        ),
        "普通文本页即使有小图片，也不应生成 image_placeholder",
    )

    assert_true(
        should_handle_pdf_page_image(
            text="",
            image_count=1,
            image_area_ratio=None,
        ),
        "无文本且存在图片时，可作为最小版扫描页候选",
    )

    assert_true(
        should_handle_pdf_page_image(
            text="少量文字",
            image_count=1,
            image_area_ratio=0.9,
        ),
        "文本很少且图片覆盖面积大时，可进入 OCR / 占位逻辑",
    )


def test_image_placeholder_metadata():
    doc = build_pdf_image_placeholder_document(
        file_path="data/raw_docs/mock_scan.pdf",
        page_number=2,
        ocr_provider="none",
        ocr_status="disabled",
        image_count=1,
        image_area_ratio=0.88,
    )

    metadata = doc.metadata

    assert_true(metadata["content_type"] == "image_placeholder", "应标记 content_type")
    assert_true(metadata["page"] == 2, "应保留 page")
    assert_true(metadata["ocr_provider"] == "none", "应保留 ocr_provider")
    assert_true(metadata["ocr_status"] == "disabled", "应保留 ocr_status")
    assert_true(metadata["image_index"] == 1, "应保留 image_index")
    assert_true(metadata["image_area_ratio"] == 0.88, "应保留图片面积占比")
    assert_true("当前未启用 OCR" in doc.text, "占位文本应说明 OCR 边界")


def main():
    print("PDF 表格 + 最小 OCR Loader 测试开始...")

    test_text_pdf_still_loads()
    print("1. 文本型 PDF 仍能生成 text Document：通过")

    test_pdf_without_tables_or_ocr_does_not_crash()
    print("2. 无表格 / OCR 默认关闭不报错：通过")

    test_table_row_text_builder()
    print("3. 表格 row 转自然语言 Document 文本：通过")

    test_default_ocr_none_scan_heuristic()
    print("4. OCR_PROVIDER=none 与扫描页启发式：通过")

    test_image_placeholder_metadata()
    print("5. image_placeholder metadata 字段：通过")

    print("PDF 表格 + 最小 OCR Loader 测试结束。")


if __name__ == "__main__":
    main()
