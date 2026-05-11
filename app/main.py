# 启动 fastapi

import faiss
import sys
from fastapi import FastAPI
from contextlib import asynccontextmanager

from app.index_manager import load_chunk_records, build_and_save_chunk_index
from app.config import (
    CHUNK_INDEX_FILE,
    FAISS_INDEX_FILE,
    AUTO_REBUILD_INDEX_ON_STARTUP,
)
from app.semantic_router import build_intent_router
from app.chat_history_store import init_chat_db
from app.routes_langchain import router_langchain
from app.routes import router
from app.bm25_retriever import build_bm25_index


def load_indexes_with_auto_rebuild():
    """
    启动时加载 chunk_records 和 FAISS index。

    如果索引缺失 / 失效 / FAISS 文件损坏：
    - 开启 AUTO_REBUILD_INDEX_ON_STARTUP 时，自动重建索引
    - 关闭 AUTO_REBUILD_INDEX_ON_STARTUP 时，直接抛出异常
    """

    try:
        print("🔍 正在检查知识库索引...")

        chunk_records = load_chunk_records(CHUNK_INDEX_FILE)
        faiss_index = faiss.read_index(FAISS_INDEX_FILE)

        print("✅ 知识库索引有效，已成功加载")
        return chunk_records, faiss_index

    except Exception as e:
        print(f"⚠️ 知识库索引加载失败：{e}")

        if not AUTO_REBUILD_INDEX_ON_STARTUP:
            print("❌ 当前未开启自动重建索引，服务终止启动")
            raise

        print("🔧 已开启自动重建索引，正在重新建库...")

        chunk_records = build_and_save_chunk_index(CHUNK_INDEX_FILE)
        faiss_index = faiss.read_index(FAISS_INDEX_FILE)

        print("✅ 自动重建索引完成，并已重新加载到内存")
        return chunk_records, faiss_index


@asynccontextmanager
async def lifespan(app: FastAPI):
    print("🚀 系统启动中：正在把知识库资源加载进内存...")

    try:
        print("🗂️ 正在初始化聊天历史数据库...")
        init_chat_db()
        print("✅ 聊天历史数据库初始化完成！")

        # 1. 自动检查 / 自动重建 / 加载 chunk_records + FAISS index
        chunk_records, faiss_index = load_indexes_with_auto_rebuild()

        # 2. 挂载 chunk_records
        app.state.chunk_records = chunk_records

        # 3. 构建并挂载 BM25 索引
        app.state.bm25_index = build_bm25_index(chunk_records)

        # 4. 挂载 FAISS 索引
        app.state.faiss_index = faiss_index

        # 5. 构建并挂载 Semantic Router 意图样本
        app.state.intent_router = build_intent_router()

    except Exception as e:
        print(f"❌ [致命错误] 系统启动失败，原因: {e}")
        sys.exit(1)

    print("✅ 底层引擎装载完毕！开放网关，开始处理用户请求！")

    yield

    print("🛑 收到停机指令：正在释放内存和数据库连接...")


app = FastAPI(title="RAG AI PROJECT", lifespan=lifespan)

app.include_router(router=router)
app.include_router(router=router_langchain)