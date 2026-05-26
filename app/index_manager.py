import json
import os
import hashlib
import faiss  # 【新增】引入 FAISS
import numpy as np  # 【新增】引入 Numpy，FAISS 底层是 C++，需要严格的数据类型
from app.config import (
    CHUNK_INDEX_FILE,
    KNOWLEDGE_FILE,
    KNOWLEDGE_DIR,
    EMBEDDING_MODEL,
    CHUNK_METHOD,
    FAISS_INDEX_FILE,
    DOCUMENT_PIPELINE_VERSION,
    METADATA_SCHEMA_VERSION,
)
from app.index_builder import build_chunk_records
from datetime import datetime
from app.document_loader import load_documents_from_dir, load_document
from app.document_processor import process_documents
from app.document_chunker import chunk_documents


def get_index_status(file_path: str = CHUNK_INDEX_FILE) -> dict:
    """
    获取当前索引状态
    """
    try:
        # 直接复用现有校验逻辑
        load_chunk_records(file_path)

        return {
            "status": "valid",
            "rebuild_required": False,
            "status_reason": "当前索引可正常使用",
        }

    except FileNotFoundError as e:
        return {"status": "missing", "rebuild_required": True, "status_reason": str(e)}

    except ValueError as e:
        return {"status": "invalid", "rebuild_required": True, "status_reason": str(e)}


def load_index_meta(file_path: str = CHUNK_INDEX_FILE) -> dict:
    """
    只读取索引中的 meta 信息
    """
    index_data = load_index_data(file_path)

    if "meta" not in index_data:
        raise ValueError("索引文件格式错误：缺少 meta 字段，请重新建库")

    return index_data["meta"]


def calculate_file_hash(file_path: str) -> str:
    """
    计算文件内容的 sha256 hash
    只要文件内容发生变化，hash 基本就会变化
    """
    with open(file_path, "rb") as f:
        file_bytes = f.read()

    # 计算 sha256
    return hashlib.sha256(file_bytes).hexdigest()


def calculate_dir_hash(dir_path: str) -> str:
    """
    计算资料目录的 hash。

    为什么需要目录 hash？
    - 单文件模式下，只需要检查 knowledge.txt 是否变化
    - 目录模式下，需要检查目录里所有支持文件是否变化
    - 文件内容变化、文件名变化、新增文件、删除文件，都应该让索引失效

    """

    supported_suffixes = {".txt", ".pdf", ".xlsx"}
    dir_path_obj = os.path.abspath(dir_path)

    if not os.path.exists(dir_path_obj):
        raise FileNotFoundError(f"资料目录不存在：{dir_path}")

    if not os.path.isdir(dir_path_obj):
        raise NotADirectoryError(f"路径不是目录：{dir_path}")

    hash_obj = hashlib.sha256()

    file_paths = []

    for root, _, files in os.walk(dir_path_obj):
        for file_name in files:
            file_path = os.path.join(root, file_name)
            suffix = os.path.splitext(file_path)[1].lower()

            if suffix not in supported_suffixes:
                continue

            file_paths.append(file_path)

    # 排序，保证不同系统下 hash 计算顺序稳定
    file_paths.sort()

    for file_path in file_paths:
        # 把相对路径也加入 hash
        # 这样文件重命名 / 移动位置也会影响 hash
        relative_path = os.path.relpath(file_path, dir_path_obj).replace("\\", "/")
        hash_obj.update(relative_path.encode("utf-8"))

        with open(file_path, "rb") as f:
            hash_obj.update(f.read())

    return hash_obj.hexdigest()


def build_index_meta(chunk_records: list[dict]) -> dict:
    """
    生成索引元信息。

    当前已经从单文件知识库升级为资料目录知识库。
    所以 meta 里记录 knowledge_dir 和目录 hash。
    """

    return {
        "embedding_model": EMBEDDING_MODEL,
        # 当前知识来源类型：目录
        "knowledge_source_type": "dir",
        # 当前正式知识库资料目录
        "knowledge_dir": KNOWLEDGE_DIR,
        # 保留旧字段，方便旧接口或旧展示不至于完全空掉
        # 但正式判断以 knowledge_dir 为准
        "knowledge_file": None,
        # 这里现在是“目录 hash”，不是单文件 hash
        "knowledge_hash": calculate_dir_hash(KNOWLEDGE_DIR),
        "knowledge_hash_type": "directory_sha256",
        "chunk_method": CHUNK_METHOD,
        "build_time": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "chunk_count": len(chunk_records),
        "document_pipeline_version": DOCUMENT_PIPELINE_VERSION,
        "metadata_schema_version": METADATA_SCHEMA_VERSION,
    }


def save_chunk_records(chunk_records: list[dict], file_path: str = CHUNK_INDEX_FILE):
    """
    保存 chunk_records 到本地 json 文件（包含元信息）
    """
    index_data = {"meta": build_index_meta(chunk_records), "records": chunk_records}

    with open(file_path, "w", encoding="utf-8") as f:
        json.dump(index_data, f, ensure_ascii=False, indent=2)


def load_index_data(file_path: str = CHUNK_INDEX_FILE) -> dict:
    """
    读取完整索引数据 包括元信息和切好的embedding向量和文本
    """
    if not os.path.exists(file_path):
        raise FileNotFoundError(f"索引文件不存在：{file_path}")

    with open(file_path, "r", encoding="utf-8") as f:
        return json.load(f)


def load_chunk_records(file_path: str = CHUNK_INDEX_FILE) -> list[dict]:
    """
    读取索引中的 records，并做基础有效性检查
    """
    index_data = load_index_data(file_path)

    if "meta" not in index_data:
        raise ValueError("索引文件格式错误：缺少 meta 字段，请重新建库")

    if "records" not in index_data:
        raise ValueError("索引文件格式错误：缺少 records 字段，请重新建库")

    meta = index_data["meta"]
    records = index_data["records"]

    # 1. 检查 embedding 模型
    index_model = meta.get("embedding_model")
    if index_model != EMBEDDING_MODEL:
        raise ValueError(
            f"索引模型不匹配：索引使用的是 {index_model}，当前配置是 {EMBEDDING_MODEL}，请重新建库"
        )

    # 2. 检查知识来源类型
    index_source_type = meta.get("knowledge_source_type")

    if index_source_type != "dir":
        raise ValueError(
            f"索引知识来源类型不匹配："
            f"索引使用的是 {index_source_type}，"
            f"当前配置是 dir，请重新建库"
        )

    # 3. 检查知识目录路径
    index_knowledge_dir = meta.get("knowledge_dir")

    if index_knowledge_dir != KNOWLEDGE_DIR:
        raise ValueError(
            f"索引知识目录不匹配："
            f"索引使用的是 {index_knowledge_dir}，"
            f"当前配置是 {KNOWLEDGE_DIR}，"
            f"请重新建库"
        )

    # 4. 检查切块方式
    index_chunk_method = meta.get("chunk_method")
    if index_chunk_method != CHUNK_METHOD:
        raise ValueError(
            f"索引切块方式不匹配：索引使用的是 {index_chunk_method}，当前配置是 {CHUNK_METHOD}，请重新建库"
        )

    # 5. 检查资料目录内容 hash
    index_knowledge_hash = meta.get("knowledge_hash")
    current_knowledge_hash = calculate_dir_hash(KNOWLEDGE_DIR)

    if index_knowledge_hash != current_knowledge_hash:
        raise ValueError(
            "索引资料目录内容已变化：当前资料目录内容与建库时不一致，请重新建库"
        )

    # 6. 检查文档处理流程版本
    index_document_pipeline_version = meta.get("document_pipeline_version")

    if index_document_pipeline_version != DOCUMENT_PIPELINE_VERSION:
        raise ValueError(
            f"索引文档处理流程版本不匹配："
            f"索引使用的是 {index_document_pipeline_version}，"
            f"当前配置是 {DOCUMENT_PIPELINE_VERSION}，"
            f"请重新建库"
        )

    # 7. 检查 metadata 结构版本
    index_metadata_schema_version = meta.get("metadata_schema_version")

    if index_metadata_schema_version != METADATA_SCHEMA_VERSION:
        raise ValueError(
            f"索引 metadata 结构版本不匹配："
            f"索引使用的是 {index_metadata_schema_version}，"
            f"当前配置是 {METADATA_SCHEMA_VERSION}，"
            f"请重新建库"
        )

    return records


def build_and_save_chunk_index(file_path: str = CHUNK_INDEX_FILE) -> list[dict]:
    """
    执行建库流程：

    新版企业资料入库链路：
    1. Document Loader：读取原始资料，转成统一 Document
    2. Document Processor：清洗 Document.text，保留 metadata
    3. Document Chunker：切成带 metadata 的 chunk_items
    4. Index Builder：生成 embedding，构建 chunk_records
    5. 保存 chunk_index.json
    6. 构建并保存 FAISS 索引
    """

    print("🚀 开始新版资料目录入库与索引构建流程...")

    # 1. 批量读取资料目录：data/raw_docs -> list[Document]
    documents = load_documents_from_dir(KNOWLEDGE_DIR)
    print(f"📁 Document Directory Loader 完成，Document 数量：{len(documents)}")

    # 2. 清洗资料：list[Document] -> cleaned list[Document]
    processed_documents = process_documents(documents)
    print(
        f"🧹 Document Processor 完成，清洗后 Document 数量：{len(processed_documents)}"
    )

    # 3. 切块：cleaned Documents -> chunk_items(text + metadata)
    chunk_items = chunk_documents(processed_documents)
    print(f"✂️ Document Chunker 完成，chunk_items 数量：{len(chunk_items)}")

    if not chunk_items:
        raise ValueError("没有生成任何 chunk_items，请检查知识文件内容或文档处理逻辑")

    # 4. 构建带 embedding 的 chunk_records
    chunk_records = build_chunk_records(chunk_items)
    print(f"🧠 Index Builder 完成，chunk_records 数量：{len(chunk_records)}")

    if not chunk_records:
        raise ValueError(
            "没有生成任何 chunk_records，请检查 embedding 或 chunk 构建逻辑"
        )

    # 5. 保存 chunk_records 到本地 JSON
    save_chunk_records(chunk_records, file_path)
    print(f"💾 chunk_index.json 保存完成：{file_path}")

    # 6. 构建 FAISS 索引
    embeddings = [item["embedding"] for item in chunk_records]

    # 将 Python 列表转换为 Numpy 矩阵，FAISS 要求 float32
    embedding_matrix = np.array(embeddings, dtype=np.float32)

    # 归一化向量：让内积检索近似等价于余弦相似度
    faiss.normalize_L2(embedding_matrix)

    # 获取向量维度
    dimension = embedding_matrix.shape[1]

    # 当前使用 HNSW 图索引
    index = faiss.IndexHNSWFlat(dimension, 32)

    # 把向量加入 FAISS 索引
    index.add(embedding_matrix)

    # 保存 FAISS 索引到本地
    faiss.write_index(index, FAISS_INDEX_FILE)
    print(f"📦 FAISS 索引保存完成：{FAISS_INDEX_FILE}")

    print("✅ 新版资料入库与索引构建流程完成！")

    return chunk_records
