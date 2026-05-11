# app/knowledge.py

import re
from app.config import (
    KNOWLEDGE_FILE,
    CHUNK_METHOD,
    CHUNK_SIZE,
    CHUNK_OVERLAP,
)


def load_knowledge_text() -> str:
    """
    读取本地知识库文本
    """
    with open(KNOWLEDGE_FILE, "r", encoding="utf-8") as file:
        return file.read()


def split_by_blank_line(text: str) -> list[str]:
    """
    按空行切分文本

    适合：
    - 制度条款
    - FAQ
    - 排版规整的员工手册
    """
    chunks = re.split(r"\n\s*\n", text.strip())
    return [chunk.strip() for chunk in chunks if chunk.strip()]


def split_one_text_by_fixed_size_overlap(
    text: str,
    chunk_size: int = CHUNK_SIZE,
    chunk_overlap: int = CHUNK_OVERLAP,
) -> list[str]:
    """
    对单段文本做固定长度 + overlap 切分

    注意：
    - 这个函数只负责切“单个长段落”
    - 不建议直接拿整篇文档调用它
    """

    if chunk_size <= 0:
        raise ValueError("chunk_size 必须大于 0")

    if chunk_overlap < 0:
        raise ValueError("chunk_overlap 不能小于 0")

    if chunk_overlap >= chunk_size:
        raise ValueError("chunk_overlap 必须小于 chunk_size，否则会导致死循环")

    clean_text = text.strip()

    if not clean_text:
        return []

    chunks = []
    start = 0
    step = chunk_size - chunk_overlap

    while start < len(clean_text):
        end = start + chunk_size
        chunk = clean_text[start:end].strip()

        if chunk:
            chunks.append(chunk)

        if end >= len(clean_text):
            break

        start += step

    return chunks


def split_by_fixed_size_overlap(text: str) -> list[str]:
    """
    整篇文本直接固定长度 + overlap 切分

    注意：
    - 这次测试已经说明，它不适合当前员工手册条款类资料作为默认方案
    - 保留它主要是为了实验对比
    """
    clean_text = text.strip()
    clean_text = re.sub(r"\n\s*\n+", "\n", clean_text)
    clean_text = re.sub(r"[ \t]+", " ", clean_text)

    return split_one_text_by_fixed_size_overlap(
        clean_text,
        chunk_size=CHUNK_SIZE,
        chunk_overlap=CHUNK_OVERLAP,
    )


def split_by_paragraph_then_overlap(text: str) -> list[str]:
    """
    推荐方案：
    先按空行切出自然段落 / 条款，
    如果某个段落过长，再对这个段落做 fixed_size + overlap 二次切分。

    这样可以同时保留：
    - 条款边界
    - 可控 chunk 长度
    """

    paragraphs = split_by_blank_line(text)

    final_chunks = []

    for paragraph in paragraphs:
        # 情况 1：段落不长，直接保留
        if len(paragraph) <= CHUNK_SIZE:
            final_chunks.append(paragraph)
            continue

        # 情况 2：段落太长，再做二次切分
        sub_chunks = split_one_text_by_fixed_size_overlap(
            paragraph,
            chunk_size=CHUNK_SIZE,
            chunk_overlap=CHUNK_OVERLAP,
        )

        final_chunks.extend(sub_chunks)

    return final_chunks


def split_text_to_chunks(text: str) -> list[str]:
    """
    统一切片入口

    根据 config.py 中的 CHUNK_METHOD 选择具体切片策略。
    """

    if CHUNK_METHOD == "blank_line_split":
        return split_by_blank_line(text)

    if CHUNK_METHOD == "fixed_size_overlap":
        return split_by_fixed_size_overlap(text)

    if CHUNK_METHOD == "paragraph_then_overlap":
        return split_by_paragraph_then_overlap(text)

    raise ValueError(f"不支持的 CHUNK_METHOD：{CHUNK_METHOD}")