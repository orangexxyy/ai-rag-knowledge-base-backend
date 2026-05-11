import json
import os
import hashlib
import faiss       # 【新增】引入 FAISS
import numpy as np # 【新增】引入 Numpy，FAISS 底层是 C++，需要严格的数据类型
from app.config import CHUNK_INDEX_FILE,KNOWLEDGE_FILE,EMBEDDING_MODEL,CHUNK_METHOD,FAISS_INDEX_FILE
from app.knowledge import load_knowledge_text,split_text_to_chunks
from app.index_builder import build_chunk_records
from datetime import datetime



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
            "status_reason": "当前索引可正常使用"
        }

    except FileNotFoundError as e:
        return {
            "status": "missing",
            "rebuild_required": True,
            "status_reason": str(e)
        }

    except ValueError as e:
        return {
            "status": "invalid",
            "rebuild_required": True,
            "status_reason": str(e)
        }

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

def build_index_meta(chunk_records: list[dict]) -> dict:
    """
    生成索引元信息
    """
    return {
        "embedding_model": EMBEDDING_MODEL,
        "knowledge_file": KNOWLEDGE_FILE,
        "knowledge_hash": calculate_file_hash(KNOWLEDGE_FILE),
        "chunk_method": CHUNK_METHOD,
        "build_time": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "chunk_count": len(chunk_records)
    }

def save_chunk_records(chunk_records: list[dict], file_path: str = CHUNK_INDEX_FILE):
    """
    保存 chunk_records 到本地 json 文件（包含元信息）
    """
    index_data = {
        "meta": build_index_meta(chunk_records),
        "records": chunk_records
    }

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

    # 2. 检查知识文件路径
    index_knowledge_file = meta.get("knowledge_file")
    if index_knowledge_file != KNOWLEDGE_FILE:
        raise ValueError(
            f"索引知识文件不匹配：索引使用的是 {index_knowledge_file}，当前配置是 {KNOWLEDGE_FILE}，请重新建库"
        )

    # 3. 检查切块方式
    index_chunk_method = meta.get("chunk_method")
    if index_chunk_method != CHUNK_METHOD:
        raise ValueError(
            f"索引切块方式不匹配：索引使用的是 {index_chunk_method}，当前配置是 {CHUNK_METHOD}，请重新建库"
        )

    # 4. 检查知识文件内容 hash
    index_knowledge_hash = meta.get("knowledge_hash")
    current_knowledge_hash = calculate_file_hash(KNOWLEDGE_FILE)

    if index_knowledge_hash != current_knowledge_hash:
        raise ValueError(
            "索引知识内容已变化：当前知识文件内容与建库时不一致，请重新建库"
        )

    return records

def build_and_save_chunk_index(file_path: str = CHUNK_INDEX_FILE) -> list[dict]:
    """
    执行建库流程：
    1. 读取知识库
    2. 切块
    3. 构建 chunk_records
    4. 保存到本地 json
    5. 构建 FAISS 索引
    """
    # 读取知识库
    text = load_knowledge_text()
    
    #将知识库切块
    chunks= split_text_to_chunks(text)

    # 构建带 embedding 的 chunk_records
    chunk_records = build_chunk_records(chunks)
    
    # 保存到本地文件
    save_chunk_records(chunk_records, file_path)
    
    # ---------------------------------------------------------
    # 5. 【重点手写】构建 FAISS 索引
    # ---------------------------------------------------------
    # 提取所有的 embedding，组成一个二维列表
    embeddings = [item["embedding"] for item in chunk_records]
    
    # 将 Python 列表转换为 Numpy 矩阵，类型必须严格指定为 float32
    embedding_matrix = np.array(embeddings, dtype=np.float32)
    
    # 归一化向量（为了让 FAISS 的内积计算直接等于我们之前的余弦相似度）
    faiss.normalize_L2(embedding_matrix)

    # 获取向量维度（取矩阵的第二维）定义数据长度
    dimension = embedding_matrix.shape[1]
    
    # 创建基于内积（Inner Product）的平铺索引 根据数据长度建表
    # index = faiss.IndexFlatIP(dimension)
    #这是图结构索引
    index = faiss.IndexHNSWFlat(dimension, 32)
    
    # 将向量矩阵添加到索引中 将数据插入表中
    index.add(embedding_matrix)
    
    # 将 FAISS 索引持久化写入磁盘 将表存储到本地文件中
    faiss.write_index(index, FAISS_INDEX_FILE)

    return chunk_records


    """
    【Day 44 实战】构建 IVF + PQ 压缩索引
    解决：当向量数据量极大，内存无法完全装下原始 float32 向量时的存储问题。
    """
    # 1. 提取并准备数据
    embeddings = [item["embedding"] for item in chunk_records]
    data = np.array(embeddings, dtype=np.float32)
    faiss.normalize_L2(data) # 归一化，确保后续使用内积等同于余弦相似度
    
    dimension = data.shape[1]
    
    # 2. 配置参数 (这是调优的核心)
    # nlist: 划分多少个“堆”（聚类中心）。
    # 经验公式：nlist 通常设为 4*sqrt(N)，N是数据总量。
    nlist = 100  
    
    # m: 把向量切成多少段。必须能被维度（如 768）整除。
    # m 越大，压缩率越低，但精度越高。
    m = 8        
    
    # nbits: 每段量化后的比特数，默认 8（即 256 种模板）。一般不动。
    nbits = 8    

    # 3. 初始化索引结构
    # quantizer（量化器）：用来决定 query 属于哪个“堆”的工具
    quantizer = faiss.IndexFlatIP(dimension) 
    index = faiss.IndexIVFPQ(quantizer, dimension, nlist, m, nbits)

    # 4. 【核心步骤】训练索引
    # 重点：IVF 需要通过训练确定“堆中心”，PQ 需要通过训练确定“零件模板”
    if not index.is_trained:
        print(f"🚀 开始训练索引（当前数据量：{len(data)}）...")
        index.train(data)
    
    # 5. 添加数据（此时才真正将向量转为“代号”存入内存）
    index.add(data)
    
    # 6. 持久化存储
    os.makedirs(os.path.dirname(index_path), exist_ok=True)
    faiss.write_index(index, index_path)
    
    print(f"✅ IVFPQ 索引构建完成！文件路径：{index_path}")
    print(f"📈 参数状态: 堆数(nlist)={nlist}, 切段数(m)={m}")
    return index_path