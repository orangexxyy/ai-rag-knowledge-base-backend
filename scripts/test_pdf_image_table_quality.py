# scripts/test_pdf_image_table_quality.py

import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.append(str(PROJECT_ROOT))

from app.document_loader import (
    build_pdf_image_table_documents_with_quality_gate,
    evaluate_table_extraction_quality,
)


def assert_true(condition: bool, message: str):
    if not condition:
        raise AssertionError(message)


def test_low_confidence_image_table_needs_review():
    low_quality_rows = [
        ["", "", ""],
        ["AC-101", "", "北门员工通道"],
        ["AC-205", "研发楼二层闸机"],
        ["", "", ""],
    ]

    result = evaluate_table_extraction_quality(
        table_rows=low_quality_rows,
        ocr_confidence=0.45,
        required_headers=["设备编号", "安装区域", "巡检频率"],
    )

    assert_true(
        result["status"] == "needs_human_review",
        "低可信图片表格应进入人工复核",
    )
    assert_true(result["score"] < 0.7, "低可信结果分数应低于可靠阈值")
    assert_true(result["reasons"], "低可信结果必须返回 review reasons")
    assert_true(
        any("OCR 平均置信度较低" in reason for reason in result["reasons"]),
        "应识别 OCR 平均置信度过低",
    )
    assert_true(
        any("表头缺失" in reason for reason in result["reasons"]),
        "应识别表头缺失",
    )
    assert_true(
        any("行列数不一致" in reason for reason in result["reasons"]),
        "应识别行列数不一致",
    )
    assert_true(
        any("空单元格比例过高" in reason for reason in result["reasons"]),
        "应识别空单元格比例过高",
    )
    assert_true(
        any("关键字段缺失" in reason for reason in result["reasons"]),
        "应识别关键字段缺失",
    )


def test_low_confidence_image_table_builds_review_document_only():
    low_quality_rows = [
        ["", "", ""],
        ["AC-101", "", "北门员工通道"],
        ["AC-205", "研发楼二层闸机"],
        ["", "", ""],
    ]

    documents = build_pdf_image_table_documents_with_quality_gate(
        file_path="data/raw_docs/pdf_table_ocr_fixture_unique.pdf",
        page_number=2,
        table_rows=low_quality_rows,
        ocr_confidence=0.45,
        required_headers=["设备编号", "安装区域", "巡检频率"],
        extraction_method="mock_image_table_ocr",
    )

    reliable_table_docs = [
        doc for doc in documents if doc.metadata.get("content_type") == "table"
    ]
    review_docs = [
        doc
        for doc in documents
        if doc.metadata.get("content_type") == "image_table_review_required"
    ]

    assert_true(not reliable_table_docs, "低可信结果不应生成可靠 table Document")
    assert_true(len(review_docs) == 1, "低可信结果应生成一个人工复核 Document")

    review_doc = review_docs[0]
    metadata = review_doc.metadata

    assert_true(
        metadata["human_review_required"] is True,
        "metadata.human_review_required 应为 True",
    )
    assert_true(metadata["review_reason"], "review_reason 不应为空")
    assert_true(
        metadata["extraction_quality_score"] < 0.7,
        "应保留低可信 extraction_quality_score",
    )
    assert_true(metadata["ocr_confidence"] == 0.45, "应保留 ocr_confidence")
    assert_true(
        metadata["table_structure_score"] is not None,
        "应保留 table_structure_score",
    )
    assert_true(
        "未作为可靠知识入库" in review_doc.text,
        "review 文本应说明不会作为可靠知识入库",
    )


def main():
    print("PDF 图片表格抽取质量门控测试开始...")

    test_low_confidence_image_table_needs_review()
    print("1. evaluate_table_extraction_quality 低可信判断：通过")

    test_low_confidence_image_table_builds_review_document_only()
    print("2. 低可信图片表格只生成人工复核 Document：通过")

    print("PDF 图片表格抽取质量门控测试结束。")


if __name__ == "__main__":
    main()
