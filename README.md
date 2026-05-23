# FastAPI + RAG 企业知识库问答后端

## 1. 项目简介

本项目是一个基于 **FastAPI + RAG + Hybrid Retrieval + Semantic Router + DashScope Reranker + LangChain + SQLite 多轮会话 + LLM Provider 可切换 + Document Ingestion Pipeline** 的企业知识库问答后端项目。

项目面向企业员工手册、制度文档、审批流程、请假制度、差旅报销等内部资料场景，目标是让用户通过自然语言查询企业制度，并让系统优先基于本地知识库资料进行回答。

项目不是简单调用大模型 API，而是完整实现了：

```text
企业资料入库
→ 文档清洗
→ metadata 传递
→ chunk 切分
→ embedding
→ FAISS / BM25 混合检索
→ Reranker 重排
→ Prompt 组装
→ 大模型基于资料回答
→ debug 可解释返回
```

当前项目支持两种最终回答模型模式：

```text
1. DeepSeek 云端模型
2. Ollama 本地模型
```

其中：

```text
LLM_PROVIDER=deepseek
→ 使用 DeepSeek 云端模型生成最终 answer

LLM_PROVIDER=ollama
→ 使用 Ollama 本地模型生成最终 answer
```

注意：

```text
当前项目只支持“最终回答模型”在 DeepSeek 和 Ollama 之间切换。
Embedding、Query Rewrite、LLM Router Fallback、DashScope Reranker 等环节仍可能依赖云端 API。
因此当前不是全链路本地化，而是支持最终回答模型本地化。
```

---

## 2. 项目定位

本项目用于展示：

- Python 后端接口开发能力
- FastAPI 服务封装能力
- LLM API 调用能力
- Embedding 与向量检索能力
- RAG 工程链路设计能力
- 企业资料入库与文档预处理能力
- metadata 设计与来源追溯能力
- 多轮会话与 SQLite 持久化能力
- FAISS + BM25 + RRF 混合检索能力
- DashScope qwen3-rerank 检索后重排能力
- Reranker 后处理调优能力
- LangChain 增量接入能力
- DeepSeek 云端模型 / Ollama 本地模型切换能力
- 本地大模型部署与基础推理参数调优能力
- 可解释 debug 字段设计能力

项目定位是：**AI 应用开发 / 大模型应用开发方向的求职展示项目**。

---

## 3. 当前完整链路

推荐演示接口为：

```text
POST /ask_langchain
```

完整链路：

```text
用户问题
→ FastAPI 接口
→ SQLite 读取历史
→ 明显 chat 规则兜底
→ 构造 route_context
→ Semantic Router 判断 chat / rag
→ 低置信度时 LLM Router Fallback
→ 如果是 chat：
    → LangChain Chat Chain
    → DeepSeek 或 Ollama 生成 answer
→ 如果是 rag：
    → Query Rewrite 构造 retrieval_query
    → get_embedding(retrieval_query)
    → FAISS 语义召回
    → BM25 关键词召回
    → RRF 融合排序
    → DashScope qwen3-rerank 重排
    → 主资料阈值过滤
    → 补充资料阈值过滤
    → 分差限制
    → 金额区间冲突过滤
    → 拼接 reference_text
    → LangChain RAG Chain
    → DeepSeek 或 Ollama 基于资料生成 answer
→ SQLite 保存历史
→ 返回 answer + 检索 debug + 路由 debug + 模型来源 debug
```

---

## 4. 企业资料入库处理链路

项目已从早期的：

```text
knowledge.txt
→ chunk
→ embedding
→ FAISS / BM25 索引
```

升级为基础的 **Document Ingestion Pipeline**，用于模拟真实企业 RAG 项目中的资料入库、预处理、metadata 传递和索引构建流程。

当前入库流程如下：

```text
原始资料
→ Document Loader
→ Document(text + metadata)
→ Document Processor
→ cleaned Document(text + metadata)
→ Document Chunker
→ chunk_items(text + metadata)
→ Index Builder
→ chunk_records(text + embedding + metadata)
→ save chunk_index.json
→ build FAISS index
→ BM25 / FAISS / Hybrid Search
→ /ask_langchain 返回命中 chunk 的 debug 信息
```

### 4.1 统一 Document 数据结构

项目新增统一的 `Document` 数据结构，用于承载文档正文和元数据：

```python
Document(
    text="文档正文内容",
    metadata={
        "source_file": "knowledge.txt",
        "source_path": "data/knowledge.txt",
        "file_type": "txt",
        "page": None,
        "sheet_name": None,
        "row_number": None,
        "section_title": None,
        "version": None,
        "permission_level": "internal"
    }
)
```

设计原因：

```text
1. 不同类型资料不能直接进入 chunk
2. txt / PDF / Excel 等资料需要先转换成统一中间结构
3. 后续清洗、chunk、embedding、索引构建都可以围绕 Document 处理
4. metadata 可以用于来源追溯、debug、权限控制和版本管理
```

---

### 4.2 Document Loader

项目新增：

```text
app/document_loader.py
```

当前已实现：

```text
txt 文件读取
```

当前链路：

```text
data/knowledge.txt
→ load_document()
→ list[Document]
```

后续计划扩展：

```text
PDF → 按 page 提取文本，每页生成一个 Document
Excel → 按 sheet / row 提取数据，每行或业务对象生成一个 Document
```

当前阶段不直接把 PDF / Excel 当成长文本处理，而是先设计统一 Document 结构，为后续多类型资料接入打基础。

---

### 4.3 Document Processor

项目新增：

```text
app/document_processor.py
```

Document Processor 负责在 chunk 前进行基础文本清洗。

当前已实现：

```text
1. 统一 Windows / Linux / Mac 换行符
2. 去掉每行首尾空格
3. 压缩连续空格和 tab
4. 压缩过多空行
5. 保留必要的段落和条款结构
6. 清洗 text 的同时保留 metadata
```

设计原则：

```text
清理噪声，但不破坏标题、段落和条款边界。
```

原因：

```text
制度文档、员工手册、审批流程等资料通常依赖标题、自然段和条款边界。
如果清洗时直接删除所有换行，会导致条款黏连，影响后续 chunk 和检索效果。
```

---

### 4.4 Document Chunker

项目新增：

```text
app/document_chunker.py
```

Document Chunker 负责将清洗后的 Document 切分为带 metadata 的 chunk_items。

输入：

```python
Document(
    text="员工手册正文...",
    metadata={
        "source_file": "knowledge.txt",
        "file_type": "txt"
    }
)
```

输出：

```python
{
    "text": "切分后的 chunk 文本",
    "metadata": {
        "source_file": "knowledge.txt",
        "source_path": "data/knowledge.txt",
        "file_type": "txt",
        "page": None,
        "sheet_name": None,
        "row_number": None,
        "section_title": None,
        "version": None,
        "permission_level": "internal",
        "doc_index": 0,
        "chunk_index_in_document": 0,
        "chunk_char_length": 102
    }
}
```

设计原因：

```text
chunk 不应该只返回字符串 list[str]。
企业 RAG 需要知道每个 chunk 来自哪个文件、哪一页、哪个 sheet、哪一行。
因此 chunk 阶段必须继续传递 metadata。
```

当前 chunk 策略仍然复用项目已有的：

```text
paragraph_then_overlap
```

含义：

```text
1. 优先按自然段 / 空行 / 条款边界切分
2. 如果单个段落过长，再使用 fixed_size + overlap 二次切分
3. 尽量保留制度条款语义完整性
4. 同时控制 chunk 长度，避免过长文本影响 embedding 和检索
```

---

### 4.5 Index Builder 升级

项目修改：

```text
app/index_builder.py
```

原始 chunk_record 结构：

```python
{
    "chunk_id": 0,
    "text": "chunk 文本",
    "embedding": [...]
}
```

升级后 chunk_record 结构：

```python
{
    "chunk_id": 0,
    "text": "chunk 文本",
    "embedding": [...],
    "metadata": {
        "source_file": "knowledge.txt",
        "source_path": "data/knowledge.txt",
        "file_type": "txt",
        "page": None,
        "sheet_name": None,
        "row_number": None,
        "section_title": None,
        "version": None,
        "permission_level": "internal",
        "doc_index": 0,
        "chunk_index_in_document": 0,
        "chunk_char_length": 102,
        "chunk_id": 0
    }
}
```

设计原因：

```text
1. text 用于 embedding 和检索
2. embedding 用于 FAISS 向量检索
3. metadata 用于来源追溯、debug、权限控制和版本管理
4. chunk_id 用于定位具体命中的资料片段
```

---

### 4.6 Index Manager 接入新版入库链路

项目修改：

```text
app/index_manager.py
```

原始建库流程：

```text
load_knowledge_text()
→ split_text_to_chunks()
→ build_chunk_records()
→ save_chunk_records()
→ build FAISS index
```

新版建库流程：

```text
load_document(KNOWLEDGE_FILE)
→ process_documents()
→ chunk_documents()
→ build_chunk_records()
→ save_chunk_records()
→ build FAISS index
```

这样项目不再只依赖单一 `knowledge.txt → 字符串切分` 的方式，而是开始具备真实企业 RAG 项目中常见的资料入库处理链路。

---

### 4.7 metadata 贯穿检索链路

项目已将 metadata 继续传递到检索结果中。

涉及文件：

```text
app/faiss_retriever.py
app/bm25_retriever.py
app/hybrid_search.py
app/routes_langchain.py
```

现在 FAISS / BM25 检索结果不仅返回：

```text
text
score
rank
```

还会返回：

```text
chunk_id
metadata
```

`/ask_langchain` 的 `used_chunks_debug` 示例：

```json
{
  "text": "请假制度条款C（事假）：事假为员工处理个人事务所使用的无薪假期。事假原则上需提前申请，紧急情况可事后补充，但需获得直属主管认可。",
  "chunk_id": 11,
  "metadata": {
    "source_file": "knowledge.txt",
    "source_path": "data/knowledge.txt",
    "file_type": "txt",
    "page": null,
    "sheet_name": null,
    "row_number": null,
    "section_title": null,
    "version": null,
    "permission_level": "internal",
    "doc_index": 0,
    "chunk_index_in_document": 11,
    "chunk_char_length": 64,
    "chunk_id": 11
  },
  "faiss_score": 0.5854,
  "bm25_score": 3.0983,
  "faiss_rank": 1,
  "bm25_rank": 1,
  "rrf_score": 0.0163,
  "source": "both",
  "rerank_score": 72.48,
  "reranker_provider": "dashscope"
}
```

这样可以在调试和面试展示中说明：

```text
系统不仅知道命中了哪段文本，还知道这段文本来自哪个文件、什么类型、在文档中的位置。
```

---

### 4.8 索引版本校验与自动重建

项目新增配置：

```python
DOCUMENT_PIPELINE_VERSION = "v1"
METADATA_SCHEMA_VERSION = "v1"
```

作用：

```text
不仅根据 knowledge_hash 判断资料内容是否变化，
还根据文档处理流程版本和 metadata 结构版本判断是否需要重新建库。
```

解决的问题：

```text
如果只判断原始知识文件 hash，那么当 document_loader、document_processor、
document_chunker 或 metadata 结构发生变化时，系统可能不会自动发现旧索引已经过期。
```

现在索引 meta 中会记录：

```json
{
  "document_pipeline_version": "v1",
  "metadata_schema_version": "v1"
}
```

当当前配置版本与索引中保存的版本不一致时，系统会判定索引无效，并触发重新建库或提示重新建库。

---

## 5. 核心功能

### 5.1 普通聊天与 RAG 问答分流

系统不会让所有问题都进入 RAG。

例如：

```text
你好
谢谢
好的，谢谢
我今天有点焦虑怎么办
我该怎么准备 AI 应用开发岗位面试
```

这类问题不依赖员工手册，进入普通 chat 分支。

例如：

```text
事假怎么请？
报销500到2000元怎么审批？
病假超过1天需要什么？
员工内部调岗怎么申请？
```

这类问题更可能依赖企业制度资料，进入 RAG 分支。

当前分流策略：

```text
明显 chat 规则
→ Semantic Router
→ LLM Router Fallback
```

---

### 5.2 SQLite 多轮会话持久化

项目使用 SQLite 保存多轮对话历史。

能力包括：

```text
1. 使用 session_id 区分不同会话
2. 每轮 user / assistant 消息写入 SQLite
3. 服务重启后仍可读取历史
4. 普通 chat 可以基于历史继续回答
5. RAG 多轮追问可以结合历史构造 retrieval_query
```

示例：

```text
第一轮：
你好，我叫橘子

第二轮：
我叫什么名字？

预期：
系统可以基于 SQLite 历史回答“橘子”
```

---

### 5.3 Semantic Router 语义路由

系统启动时会预加载 chat / rag 样本，并生成 embedding。

用户请求进入后：

```text
1. 将 route_context 转为 embedding
2. 分别与 chat 样本、rag 样本计算相似度
3. 各取 top3
4. 计算综合分
```

当前综合分公式：

```text
final_score = 0.7 * best_score + 0.3 * top3_avg_score
```

判断依据：

```text
ROUTER_MIN_SCORE
ROUTER_MARGIN
```

如果 rag 分数明显高于 chat，则进入 RAG。  
如果 chat 分数明显高于 rag，则进入普通聊天。  
如果分数不明确，则进入 LLM Router Fallback。

---

### 5.4 LLM Router Fallback

当 Semantic Router 不确定时，系统会调用大模型做兜底判断。

LLM Router 的任务不是回答问题，而是判断当前请求应该走：

```text
chat
```

还是：

```text
rag
```

这样可以避免单纯依赖关键词造成误判。

例如：

```text
学习 RAG 项目的流程应该怎么安排？
```

虽然包含“流程”，但它不是企业制度流程，应该走 chat。

---

### 5.5 route_context 与 retrieval_query 分层

项目明确区分：

```text
route_context
retrieval_query
```

二者职责不同：

```text
route_context：
用于判断当前问题是否需要 RAG。
要求尽量中性，不提前被“检索优化”污染。

retrieval_query：
用于真正查询知识库。
要求语义完整，更适合 embedding 检索。
```

多轮示例：

```text
第一轮：
报销500到2000元怎么审批？

第二轮：
那再高一点呢？
```

系统会把第二轮改写为类似：

```text
报销金额超过2000元怎么审批？
```

然后再进入检索。

---

### 5.6 FAISS + BM25 + RRF 混合检索

项目使用双轨召回：

```text
FAISS：语义召回
BM25：关键词、数字、制度名召回
```

原因：

```text
FAISS 擅长语义相似
BM25 擅长精确关键词、数字、金额、制度名
```

融合方式：

```text
RRF：Reciprocal Rank Fusion
```

RRF 按排名融合，不直接相加原始分数，避免 FAISS 分数和 BM25 分数体系不同导致的问题。

---

### 5.7 DashScope qwen3-rerank 检索后重排

Hybrid Search 会先召回候选 chunk。

然后系统调用：

```text
DashScope qwen3-rerank
```

输入：

```text
query + candidate documents
```

输出：

```text
index + relevance_score
```

系统将 relevance_score 换算为 0-100 分的 rerank_score，用于后续过滤和排序。

---

### 5.8 Reranker 双阈值 + 分差限制

当前策略：

```python
RERANK_PRIMARY_MIN_SCORE = 60
RERANK_EXTRA_MIN_SCORE = 75
RERANK_EXTRA_MAX_GAP = 20
RERANK_MIN_SCORE = RERANK_PRIMARY_MIN_SCORE
```

含义：

```text
第一名 chunk：
达到 60 分即可保留，避免核心资料被误伤。

第二名及之后：
必须达到 75 分，并且不能和第一名分差超过 20。

如果第一名都低于 60：
说明整体资料相关性不足，返回 low_confidence。
```

这样可以避免：

```text
1. 阈值太高导致核心资料被误伤
2. 阈值太低导致弱相关资料进入 reference_text
```

---

### 5.9 金额区间冲突过滤

针对报销制度中的金额区间问题，项目增加了轻量业务规则过滤。

当前金额区间划分：

```text
low：500元及以下
middle：500元以上且不超过2000元
high：超过2000元
```

如果 query 和 chunk 的金额区间明确但不一致，则认为冲突，不进入最终 reference_text。

示例：

```text
问：报销500到2000元怎么审批？

应该保留：
500元以上且不超过2000元条款

应该过滤：
500元及以下条款
超过2000元条款
```

这个设计说明：

```text
Reranker 可以判断语义相关性，
但对金额区间、范围冲突这类业务精确条件，
仍然需要后处理规则补充。
```

---

### 5.10 low_confidence 低相关保护

如果进入 RAG 后，所有候选资料都低于主资料阈值，系统不会强行让大模型基于弱相关资料回答。

返回示例：

```text
retriever_status = low_confidence
answer = 资料中没有找到足够相关的内容，建议你补充更具体的问题。
used_chunk_count = 0
```

这样可以避免：

```text
资料不足时硬答
弱相关资料误导模型
模型编造企业制度
```

---

### 5.11 LangChain 增量接入

项目保留手写版接口：

```text
POST /ask
```

同时新增推荐演示接口：

```text
POST /ask_langchain
```

`/ask_langchain` 的特点：

```text
1. 复用原有 chat/rag 分流逻辑
2. 复用 SQLite 历史
3. 复用 Query Rewrite
4. 复用 FAISS + BM25 + RRF
5. 复用 DashScope Reranker
6. 只把最终 chat / rag 回答模型封装为 LangChain Chain
```

这样可以体现：

```text
不是为了用框架重写项目，
而是在已有工程链路上增量接入 LangChain。
```

---

### 5.12 DeepSeek / Ollama 本地模型切换

项目新增 LLM Provider 配置层。

核心配置：

```python
LLM_PROVIDER = os.getenv("LLM_PROVIDER", "deepseek").lower()

DEEPSEEK_TEMPERATURE = float(os.getenv("DEEPSEEK_TEMPERATURE", "0.2"))

OLLAMA_BASE_URL = os.getenv("OLLAMA_BASE_URL", "http://localhost:11434")
OLLAMA_MODEL = os.getenv("OLLAMA_MODEL", "qwen3-4b-instruct-local")
OLLAMA_TEMPERATURE = float(os.getenv("OLLAMA_TEMPERATURE", "0.3"))
OLLAMA_TOP_P = float(os.getenv("OLLAMA_TOP_P", "0.8"))
OLLAMA_NUM_PREDICT = int(os.getenv("OLLAMA_NUM_PREDICT", "512"))
OLLAMA_REPEAT_PENALTY = float(os.getenv("OLLAMA_REPEAT_PENALTY", "1.15"))
```

切换方式：

```text
LLM_PROVIDER=deepseek
→ 最终回答模型使用 DeepSeek

LLM_PROVIDER=ollama
→ 最终回答模型使用本地 Ollama 模型
```

---

### 5.13 模型来源 debug 字段

为了让演示时能直观看出当前 answer 是由哪个模型生成，接口返回中新增：

```text
answer_source
answer_llm_provider
answer_llm_model
answer_llm_is_local
```

当使用 Ollama 本地模型时：

```json
{
  "answer_source": "ollama_local_model",
  "answer_llm_provider": "ollama",
  "answer_llm_model": "qwen3-4b-instruct-local",
  "answer_llm_is_local": true
}
```

当使用 DeepSeek 云端模型时：

```json
{
  "answer_source": "deepseek_api",
  "answer_llm_provider": "deepseek",
  "answer_llm_model": "deepseek-chat",
  "answer_llm_is_local": false
}
```

当 low_confidence 系统兜底时：

```json
{
  "answer_source": "system_fallback",
  "answer_llm_provider": null,
  "answer_llm_model": null,
  "answer_llm_is_local": false
}
```

---

## 6. 技术栈

```text
Python
FastAPI
Pydantic
SQLite
DeepSeek API
DashScope Embedding
DashScope qwen3-rerank
FAISS
BM25
RRF
LangChain
Ollama
Qwen3-4B-Instruct GGUF
python-dotenv
jieba
rank-bm25
requests
```

---

## 7. 项目结构示例

```text
rag_project/
├─ app/
│  ├─ main.py
│  ├─ config.py
│  ├─ models.py
│  ├─ routes.py
│  ├─ routes_langchain.py
│  ├─ deepseek_api.py
│  ├─ embedding_api.py
│  ├─ langchain_client.py
│  ├─ langchain_chains.py
│  ├─ query_builder.py
│  ├─ semantic_router.py
│  ├─ llm_router.py
│  ├─ hybrid_search.py
│  ├─ faiss_retriever.py
│  ├─ bm25_retriever.py
│  ├─ reranker.py
│  ├─ knowledge.py
│  ├─ document_models.py
│  ├─ document_loader.py
│  ├─ document_processor.py
│  ├─ document_chunker.py
│  ├─ index_builder.py
│  ├─ index_manager.py
│  ├─ chat_history_store.py
│  └─ utils.py
├─ scripts/
│  ├─ test_document_loader.py
│  ├─ test_document_processor.py
│  ├─ test_document_chunker.py
│  └─ test_index_builder_metadata.py
├─ data/
│  ├─ knowledge.txt
│  ├─ chunk_index.json
│  ├─ chunk_index.faiss
│  └─ chat_history.db
├─ .env
├─ .env.example
├─ .gitignore
├─ requirements.txt
├─ README.md
└─ test_cases.md
```

说明：

```text
knowledge.py 当前仍保留，用于复用已有 chunk 切分函数。
后续可进一步将 chunk 相关函数迁移到 chunking.py 或 document_chunker.py 中。
```

---

## 8. 环境准备

### 8.1 Python 版本

推荐：

```text
Python 3.10+
```

Windows 下建议使用虚拟环境。

创建虚拟环境：

```powershell
python -m venv .venv
```

激活虚拟环境：

```powershell
.\.venv\Scripts\Activate.ps1
```

如果 PowerShell 阻止脚本运行，可以执行：

```powershell
Set-ExecutionPolicy -ExecutionPolicy RemoteSigned -Scope CurrentUser
```

然后重新激活虚拟环境。

---

### 8.2 安装 Python 依赖

```powershell
pip install -r requirements.txt
```

注意：

```text
凡是项目代码里 import 的第三方 Python 包，都应该安装到当前项目虚拟环境中。
```

例如：

```text
fastapi
uvicorn
python-dotenv
langchain-ollama
langchain-deepseek
faiss-cpu
rank-bm25
jieba
openai
requests
```

---

### 8.3 安装 Ollama

如果需要使用本地模型，需要先安装 Ollama。

官方下载地址：

```text
https://ollama.com/download
```

Windows 安装后验证：

```powershell
ollama --version
```

检查本地服务：

```text
http://localhost:11434
```

如果页面显示：

```text
Ollama is running
```

说明 Ollama 服务已启动。

---

## 9. 配置文件

### 9.1 `.env`

项目根目录创建 `.env`。

示例：

```env
# =========================
# API Keys
# =========================
DEEPSEEK_API_KEY=your_deepseek_api_key
DASHSCOPE_API_KEY=your_dashscope_api_key

# =========================
# LLM Provider
# 可选：deepseek / ollama
# =========================
LLM_PROVIDER=deepseek

# =========================
# DeepSeek
# =========================
DEEPSEEK_TEMPERATURE=0.2

# =========================
# Ollama Local Model
# =========================
OLLAMA_BASE_URL=http://localhost:11434
OLLAMA_MODEL=qwen3-4b-instruct-local
OLLAMA_TEMPERATURE=0.3
OLLAMA_TOP_P=0.8
OLLAMA_NUM_PREDICT=512
OLLAMA_REPEAT_PENALTY=1.15
```

如果要切换到本地模型：

```env
LLM_PROVIDER=ollama
```

如果要切回 DeepSeek：

```env
LLM_PROVIDER=deepseek
```

修改 `.env` 后，建议：

```text
Ctrl + C 停止服务
重新 uvicorn app.main:app --reload
```

不要只依赖 `--reload` 自动重启。

---

### 9.2 `.env.example`

`.env` 不应该提交到 GitHub。

可以提交 `.env.example`：

```env
# =========================
# API Keys
# =========================
DEEPSEEK_API_KEY=your_deepseek_api_key
DASHSCOPE_API_KEY=your_dashscope_api_key

# =========================
# LLM Provider
# 可选：deepseek / ollama
# =========================
LLM_PROVIDER=deepseek

# =========================
# DeepSeek
# =========================
DEEPSEEK_TEMPERATURE=0.2

# =========================
# Ollama Local Model
# =========================
OLLAMA_BASE_URL=http://localhost:11434
OLLAMA_MODEL=qwen3-4b-instruct-local
OLLAMA_TEMPERATURE=0.3
OLLAMA_TOP_P=0.8
OLLAMA_NUM_PREDICT=512
OLLAMA_REPEAT_PENALTY=1.15
```

---

### 9.3 `.gitignore`

确保 `.gitignore` 中包含：

```gitignore
.env
data/chat_history.db
__pycache__/
.venv/
```

如果不想提交本地索引文件，也可以加入：

```gitignore
data/chunk_index.json
data/chunk_index.faiss
```

如果希望演示时开箱即用，也可以保留测试索引文件。根据 GitHub 展示策略决定。

---

## 10. 启动方式

### 10.1 激活虚拟环境

```powershell
cd D:\software\Code\rag_project
.\.venv\Scripts\Activate.ps1
```

---

### 10.2 重建索引

如果修改了以下内容，建议重建索引：

```text
1. data/knowledge.txt 内容
2. chunk 策略
3. embedding 模型
4. document_loader / document_processor / document_chunker 逻辑
5. metadata 结构
6. DOCUMENT_PIPELINE_VERSION
7. METADATA_SCHEMA_VERSION
```

手动重建：

```powershell
python -c "from app.index_manager import build_and_save_chunk_index; build_and_save_chunk_index()"
```

也可以通过接口：

```text
POST /rebuild_index
```

---

### 10.3 启动 FastAPI

```powershell
uvicorn app.main:app --reload
```

接口文档：

```text
http://127.0.0.1:8000/docs
```

---

### 10.4 DeepSeek 模式启动

`.env`：

```env
LLM_PROVIDER=deepseek
```

启动：

```powershell
uvicorn app.main:app --reload
```

预期返回字段：

```json
{
  "answer_source": "deepseek_api",
  "answer_llm_provider": "deepseek",
  "answer_llm_model": "deepseek-chat",
  "answer_llm_is_local": false
}
```

---

### 10.5 Ollama 本地模型模式启动

先确认 Ollama 正常：

```powershell
ollama list
```

能看到：

```text
qwen3-4b-instruct-local
```

`.env`：

```env
LLM_PROVIDER=ollama
OLLAMA_MODEL=qwen3-4b-instruct-local
OLLAMA_BASE_URL=http://localhost:11434
```

启动：

```powershell
uvicorn app.main:app --reload
```

预期返回字段：

```json
{
  "answer_source": "ollama_local_model",
  "answer_llm_provider": "ollama",
  "answer_llm_model": "qwen3-4b-instruct-local",
  "answer_llm_is_local": true
}
```

---

## 11. 索引构建与检查

项目使用本地知识库文件：

```text
data/knowledge.txt
```

索引文件：

```text
data/chunk_index.json
data/chunk_index.faiss
```

手动重建索引接口：

```text
POST /rebuild_index
```

查看索引信息：

```text
GET /index_info
```

返回内容包括：

```text
embedding_model
knowledge_file
chunk_method
document_pipeline_version
metadata_schema_version
chunk_count
build_time
knowledge_hash
index_status
```

如果启动时报索引缺失、索引无效、处理流程版本不匹配或 metadata 结构版本不匹配，需要先重建索引。

---

## 12. API 说明

### 12.1 POST /ask_langchain

推荐演示接口。

请求示例：

```json
{
  "question": "事假怎么请？",
  "session_id": "user_001"
}
```

返回字段可能包括：

```text
question
intent
embedding_model
framework
retriever_status
answer
answer_source
answer_llm_provider
answer_llm_model
answer_llm_is_local
retrieval_query
reference_text
used_chunk_count
history_messages
used_chunks_debug
intent_debug
error
```

其中 `used_chunks_debug` 会包含：

```text
chunk_id
text
metadata
faiss_score
bm25_score
faiss_rank
bm25_rank
rrf_score
source
rerank_score
rerank_reason
reranker_provider
```

---

### 12.2 POST /ask

手写版接口。

保留用于展示底层 RAG 理解。  
最新的 LangChain、本地模型来源字段、DashScope reranker、metadata debug 和 low_confidence 主要推荐在 `/ask_langchain` 中演示。

---

### 12.3 GET /index_info

查看当前索引信息。

返回内容包括：

```text
embedding_model
knowledge_file
chunk_method
document_pipeline_version
metadata_schema_version
chunk_count
build_time
knowledge_hash
index_status
```

---

### 12.4 POST /rebuild_index

手动重建知识库索引。

适用场景：

```text
1. knowledge.txt 修改后
2. chunk 策略修改后
3. embedding 模型修改后
4. 文档处理流程版本变化后
5. metadata 结构版本变化后
6. 索引文件缺失或损坏后
```

---

## 13. 调试字段说明

### 13.1 intent_debug

解释为什么走 chat 或 rag。

常见字段：

```text
intent
route_strategy
decision_reason
chat_final_score
rag_final_score
score_gap_rag_minus_chat
best_chat_score
best_chat_example
best_rag_score
best_rag_example
top_chat_matches
top_rag_matches
domain_keyword_hit
domain_keyword_detected
fallback_used
route_decision_source
llm_router_debug
router_min_score
router_margin
```

---

### 13.2 used_chunks_debug

解释检索、融合、重排结果。

常见字段：

```text
chunk_id
text
metadata
faiss_score
bm25_score
faiss_rank
bm25_rank
rrf_score
source
rerank_score
rerank_reason
reranker_provider
```

metadata 示例：

```json
{
  "source_file": "knowledge.txt",
  "source_path": "data/knowledge.txt",
  "file_type": "txt",
  "page": null,
  "sheet_name": null,
  "row_number": null,
  "section_title": null,
  "version": null,
  "permission_level": "internal",
  "doc_index": 0,
  "chunk_index_in_document": 11,
  "chunk_char_length": 64,
  "chunk_id": 11
}
```

---

### 13.3 answer model debug

解释最终 answer 的模型来源。

```text
answer_source
answer_llm_provider
answer_llm_model
answer_llm_is_local
```

示例：

```json
{
  "answer_source": "ollama_local_model",
  "answer_llm_provider": "ollama",
  "answer_llm_model": "qwen3-4b-instruct-local",
  "answer_llm_is_local": true
}
```

---

## 14. 典型测试样本

### 14.1 普通 chat 不进 RAG

请求：

```json
{
  "question": "你好",
  "session_id": "demo_chat_001"
}
```

预期：

```text
intent = chat
不返回 reference_text
answer_source 显示当前最终回答模型来源
```

---

### 14.2 制度问题进入 RAG

请求：

```json
{
  "question": "事假怎么请？",
  "session_id": "demo_rag_001"
}
```

预期：

```text
intent = rag
retriever_status = matched
reference_text 命中事假条款
answer 根据资料回答
used_chunks_debug 中包含 chunk_id 和 metadata
```

---

### 14.3 metadata 来源追溯测试

请求：

```json
{
  "question": "事假怎么请？",
  "session_id": "demo_metadata_001"
}
```

重点观察：

```text
used_chunks_debug[0].chunk_id
used_chunks_debug[0].metadata.source_file
used_chunks_debug[0].metadata.file_type
used_chunks_debug[0].metadata.chunk_index_in_document
```

预期：

```text
metadata 能显示命中 chunk 来自 knowledge.txt，file_type 为 txt。
```

---

### 14.4 金额区间过滤：500元以下

请求：

```json
{
  "question": "报销500元以下谁审批？",
  "session_id": "demo_amount_low"
}
```

预期：

```text
只保留 500元及以下 条款
过滤 500-2000 元和超过 2000 元条款
```

---

### 14.5 金额区间过滤：500-2000元

请求：

```json
{
  "question": "报销500到2000元怎么审批？",
  "session_id": "demo_amount_middle"
}
```

预期：

```text
只保留 500元以上且不超过2000元 条款
```

---

### 14.6 金额区间过滤：超过2000元

请求：

```json
{
  "question": "报销金额超过2000元怎么审批？",
  "session_id": "demo_amount_high"
}
```

预期：

```text
只保留超过 2000 元审批条款
```

---

### 14.7 多轮 Query Rewrite

第一轮：

```json
{
  "question": "报销500到2000元怎么审批？",
  "session_id": "demo_multi_turn_amount"
}
```

第二轮：

```json
{
  "question": "那再高一点呢？",
  "session_id": "demo_multi_turn_amount"
}
```

预期：

```text
retrieval_query 接近：报销金额超过2000元怎么审批？
reference_text 只保留超过2000元条款
```

---

### 14.8 无历史模糊问题

请求：

```json
{
  "question": "这个情况应该怎么处理？",
  "session_id": "demo_uncertain_001"
}
```

预期：

```text
intent = chat
route_strategy = llm_fallback_chat
answer 追问用户补充具体情况
```

---

### 14.9 低相关资料保护

请求：

```json
{
  "question": "公司年终奖发放规则是什么？",
  "session_id": "demo_low_confidence_001"
}
```

预期：

```text
intent = rag
retriever_status = low_confidence
used_chunk_count = 0
answer_source = system_fallback
不基于弱相关资料硬答
```

---

### 14.10 本地模型切换测试

`.env`：

```env
LLM_PROVIDER=ollama
```

请求：

```json
{
  "question": "怎么请事假？",
  "session_id": "demo_ollama_001"
}
```

预期：

```json
{
  "answer_source": "ollama_local_model",
  "answer_llm_provider": "ollama",
  "answer_llm_model": "qwen3-4b-instruct-local",
  "answer_llm_is_local": true
}
```

---

### 14.11 DeepSeek 模型切换测试

`.env`：

```env
LLM_PROVIDER=deepseek
```

请求：

```json
{
  "question": "怎么请事假？",
  "session_id": "demo_deepseek_001"
}
```

预期：

```json
{
  "answer_source": "deepseek_api",
  "answer_llm_provider": "deepseek",
  "answer_llm_model": "deepseek-chat",
  "answer_llm_is_local": false
}
```

---

## 15. 当前已实现范围

已实现：

```text
1. FastAPI + RAG 企业知识库问答接口
2. SQLite 多轮会话持久化
3. 明显 chat 规则 + Semantic Router + LLM Router Fallback
4. route_context / retrieval_query 分层
5. Query Rewrite 支持多轮短追问
6. FAISS + BM25 + RRF 混合检索
7. DashScope qwen3-rerank 检索后重排
8. Reranker 双阈值 + 分差限制
9. 金额区间冲突过滤
10. low_confidence 低相关资料保护
11. LangChain 增量接入最终回答链
12. DeepSeek / Ollama 最终回答模型切换
13. answer 模型来源 debug 字段
14. 统一 Document 数据结构
15. txt 文件进入新版 Document Pipeline
16. chunk 前基础文本清洗
17. chunk 后继续保留 metadata
18. chunk_records 保存 text、embedding、metadata
19. 正式建库流程接入 Document Loader / Processor / Chunker
20. FAISS / BM25 / Hybrid Search 检索结果保留 metadata
21. /ask_langchain 的 used_chunks_debug 返回 chunk_id 和 metadata
22. index meta 增加 document_pipeline_version 和 metadata_schema_version
23. 处理逻辑或 metadata 结构变化时，可以通过版本号触发索引失效和重新建库
```

---

## 16. 当前限制

当前项目仍是求职展示型 Demo，不是生产级企业知识库系统。

当前限制包括：

```text
1. 当前只完成 txt 文件进入新版入库链路
2. PDF Loader 尚未实现
3. Excel Loader 尚未实现
4. OCR 尚未实现
5. 复杂 PDF 表格结构还原尚未实现
6. Excel 合并单元格、复杂多表头处理尚未实现
7. 权限过滤目前只保留 permission_level 字段，尚未真正做用户权限控制
8. 文档版本管理目前只保留 version 字段，尚未实现多版本文档过滤
9. 最终自然语言回答中尚未展示来源页码 / sheet / row
10. 当前 metadata 主要用于 debug 展示和后续扩展基础
11. SQLite 是本地单机持久化
12. DashScope embedding 和 reranker 是外部 API，会有网络延迟和调用成本
13. 当前只支持最终回答模型切换为本地 Ollama，不代表全链路本地化
14. `/ask` 与 `/ask_langchain` 两条链路并存，最新能力主要推荐在 `/ask_langchain` 演示
```

---

## 17. 后续扩展计划

下一阶段计划补充：

```text
1. PDF Loader
   - 文本型 PDF 按 page 提取文本
   - 每页生成一个 Document
   - metadata.page 生效
   - 复用现有 Processor / Chunker / Index Builder / Retriever

2. Excel Loader
   - 按 sheet 读取
   - 按 row 或业务对象转成自然语言文本
   - metadata.sheet_name / row_number 生效
   - 避免把 Excel 简单当成长文本处理

3. 来源展示
   - 在最终回答中展示 source_file
   - PDF 展示 page
   - Excel 展示 sheet_name 和 row_number

4. 权限与版本扩展
   - 基于 permission_level 做检索前过滤
   - 基于 version / effective_date 做版本管理

5. 自动化测试
   - 将现有手动 test_cases 逐步沉淀为 pytest
   - 验证 chat/rag 分流、RAG 命中、low_confidence、metadata 返回等关键链路
```

---

## 18. 项目亮点

可以在简历 / 面试中提炼为：

1. 实现 FastAPI + RAG 企业知识库问答后端。
2. 支持 SQLite 多轮会话持久化。
3. 使用明显 chat 规则 + Semantic Router + LLM Router Fallback 做 chat/rag 分流。
4. 使用 route_context / retrieval_query 分层，避免路由和检索职责混淆。
5. 使用 Query Rewrite 提升多轮短追问检索稳定性。
6. 使用 FAISS + BM25 + RRF 实现混合检索。
7. 使用 DashScope qwen3-rerank 进行检索后重排。
8. 使用双阈值 + 分差限制平衡主资料召回与补充资料过滤。
9. 增加金额区间冲突过滤，解决报销区间类资料噪音问题。
10. 使用 low_confidence 避免弱相关资料硬答。
11. 使用 LangChain 增量接入最终回答链。
12. 支持 DeepSeek 云端模型 / Ollama 本地模型切换。
13. 通过 .env 管理模型提供方和推理参数，避免硬编码。
14. 返回完整 debug 字段，便于解释路由、检索、重排和模型来源。
15. 新增基础 Document Ingestion Pipeline，模拟企业资料入库处理流程。
16. 将 txt 资料转换为统一 Document，并在清洗、chunk、索引和检索中保留 metadata。
17. 支持在 used_chunks_debug 中查看命中 chunk 的来源文件、文件类型和文档内位置。
18. 增加 document_pipeline_version / metadata_schema_version，解决处理逻辑变化但原始资料 hash 不变时旧索引不失效的问题。

---

## 19. 项目表达版本

```text
我做了一个基于 FastAPI 的 RAG 企业知识库问答后端项目。它不是简单调用大模型 API，而是完整实现了从用户请求进入、chat/rag 分流、多轮历史管理、Query Rewrite、混合检索、reranker 重排到最终回答的链路。

项目里我用 SQLite 做最小会话持久化，用 route_context 和 retrieval_query 区分路由输入和检索输入。检索部分采用 FAISS + BM25 双轨召回，并用 RRF 做融合排序。

Router 方面，我先用明显 chat 规则处理问候和礼貌收尾，再用小样本 Embedding Semantic Router 做高置信分流；当 Semantic Router 不确定时，再调用 LLM Router fallback 判断 chat/rag，而不是所有请求都调用大模型。

Reranker 方面，我接入了阿里云百炼 qwen3-rerank。接入后我发现专门 rerank API 更偏语义相关性排序，对金额区间这类精确业务条件仍然需要后处理，所以增加了主资料阈值、补充资料阈值、分差限制和金额区间冲突过滤。

资料入库方面，我把原来的 knowledge.txt 单文件 RAG Demo，升级成了一个基础的企业资料入库链路。现在项目中新增了 Document Loader、Document Processor 和 Document Chunker。Loader 负责把原始资料转换成统一 Document；Processor 负责清洗文本但保留 metadata；Chunker 负责按当前 chunk 策略切分文本，同时让每个 chunk 继承原始 Document 的 metadata。

Index Builder 现在会把 text、embedding 和 metadata 一起写入 chunk_records。检索命中后，FAISS / BM25 / Hybrid Search 也会继续保留 metadata，并在 /ask_langchain 的 used_chunks_debug 中返回。这样系统不仅能回答问题，还能解释命中的资料来自哪个文件、什么类型、在文档中的位置。

另外，我给项目补充了 LLM Provider 配置层，支持通过 .env 在 DeepSeek 云端模型和 Ollama 本地模型之间切换最终回答模型。接口返回中会展示 answer_llm_provider、answer_llm_model 和 answer_llm_is_local，方便演示当前回答来源。
```

---

## 20. 准确表述与避免夸大

可以说：

```text
当前项目已实现基础 Document Ingestion Pipeline，并支持 txt 文件进入新版入库链路。
```

可以说：

```text
metadata 已经贯穿建库、检索和 debug 返回，为后续 PDF / Excel 来源追溯打基础。
```

可以说：

```text
项目支持最终回答模型在 DeepSeek 云端模型和 Ollama 本地模型之间切换。
```

不要说：

```text
项目已经完整支持 PDF / Excel 文档解析。
```

不要说：

```text
项目已经实现生产级权限控制和文档版本管理。
```

不要说：

```text
项目已经全链路本地化。
```

更准确的说法是：

```text
PDF / Excel Loader、OCR、复杂表格结构还原、权限过滤和版本管理是后续可扩展方向。
```

---

## 21. 一句话总结

```text
这是一个基于 FastAPI 的企业知识库 RAG 问答后端项目，已实现 Document Ingestion Pipeline、metadata 贯穿建库与检索、chat/rag 分流、SQLite 多轮会话、Query Rewrite、FAISS + BM25 + RRF 混合检索、DashScope qwen3-rerank 检索后重排、低相关保护、LangChain 增量接入、DeepSeek / Ollama 最终回答模型切换和调试可解释化链路，可用于展示 AI 应用开发 / 大模型应用开发中的 RAG 工程实践能力。
```