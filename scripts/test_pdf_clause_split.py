# scripts/test_pdf_clause_split.py

import re
import sys
from pathlib import Path

# 把项目根目录加入 Python 搜索路径
PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.append(str(PROJECT_ROOT))

from app.document_loader import load_document
from app.document_processor import process_documents


def split_policy_clauses(text: str) -> list[str]:
    """
    测试用：按制度条款标题切分文本。

    核心思路：
    1. 先找到所有“条款标题”的位置
    2. 从当前标题切到下一个标题之前
    3. 每一段就是一个独立条款

    注意：
    - 这是测试函数，先验证思路
    - 暂时还不接入正式 document_chunker.py
    """

    if not text:
        return []

    # 【重点理解】
    # PDF 抽取文本经常会在句子中间断行。
    # 这里先做测试级处理：把单个换行合并掉。
    #
    # 例如：
    # 直属主\n管  →  直属主管
    # 调休申\n请  →  调休申请
    #
    # 这一步不是最终生产级清洗，只是为了验证条款切分效果。
    text = re.sub(r"(?<!\n)\n(?!\n)", "", text)

    # 【重点理解】
    # 这里不是判断“是否包含事假”，而是识别“条款标题边界”。
    #
    # 能匹配：
    # 请假制度条款A（年假）：
    # 请假制度条款B（病假）：
    # 请假制度条款C（事假）：
    # 请假制度条款D（调休假）：
    # 差旅报销制度条款A：
    title_pattern = re.compile(
        r"(请假制度条款[A-Z]（[^）]+）：|差旅报销制度条款[A-Z]：)"
    )

    # finditer 会返回每个标题在全文中的位置
    matches = list(title_pattern.finditer(text))

    print("\n【调试】识别到的条款标题：")
    for m in matches:
        print("-", m.group(), "位置：", m.start())

    # 如果没有找到条款标题，就退回整段文本
    if not matches:
        cleaned_text = text.strip()
        return [cleaned_text] if cleaned_text else []

    clauses = []

    for index, match in enumerate(matches):
        # 当前标题开始位置
        start = match.start()

        # 下一个标题开始位置
        # 如果已经是最后一个标题，就切到全文结尾
        if index + 1 < len(matches):
            end = matches[index + 1].start()
        else:
            end = len(text)

        clause = text[start:end].strip()

        if clause:
            clauses.append(clause)

    return clauses


def main():
    pdf_path = "data/raw_docs/employee_handbook_sample.pdf"

    documents = load_document(pdf_path)
    processed_documents = process_documents(documents)

    print("Document 数量：", len(processed_documents))

    for doc in processed_documents:
        # 只看第 2 页，因为第 2 页是请假制度
        if doc.metadata.get("page") != 2:
            continue

        print("\n=== PDF 第 2 页原文 ===")
        print(doc.text)

        clauses = split_policy_clauses(doc.text)

        print("\n=== 按条款切分结果 ===")
        print("条款数量：", len(clauses))

        for index, clause in enumerate(clauses):
            print("\n------------------------------")
            print("条款序号：", index)
            print(clause)


if __name__ == "__main__":
    main()