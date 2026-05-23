# scripts/test_document_loader.py

import sys
from pathlib import Path

# 【可直接复制】
# 把项目根目录 rag_project 加入 Python 的模块搜索路径
# 这样脚本无论从哪里运行，都能 import app.xxx
PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.append(str(PROJECT_ROOT))

from app.document_loader import load_document


def main():
    print("测试脚本开始执行...")

    documents = load_document("data/knowledge.txt")

    print("读取到 Document 数量：", len(documents))

    first_doc = documents[0]

    print("正文前 100 个字符：")
    print(first_doc.text[:100])

    print("\nmetadata：")
    print(first_doc.metadata)

    print("测试脚本执行结束。")


if __name__ == "__main__":
    main()