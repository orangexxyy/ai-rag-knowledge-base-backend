# FastAPI + RAG 企业知识库问答后端

## 1. 项目简介

本项目是一个基于 **FastAPI + RAG + Document Ingestion Pipeline + FAISS / BM25 / RRF 混合检索 + DashScope Reranker + LangChain + SQLite 多轮会话 + LLM Provider 可切换** 的企业知识库问答后端项目。

项目面向企业内部知识库场景，例如：

```text
员工手册
请假制度
差旅报销制度
IT 支持制度
账号权限制度
资产管理制度
```

项目目标不是简单调用大模型 API，而是实现一条较完整的企业 RAG 后端链路：

```text
企业资料目录
→ txt / PDF 文档读取
→ 统一 Document(text + metadata)
→ 文档清洗
→ 根据资料结构选择 chunk 策略
→ embedding
→ FAISS / BM25 / RRF 混合检索
→ DashScope qwen3-rerank 重排
→ Prompt 组装
→ 大模型基于资料回答
→ used_chunks_debug 返回来源与调试信息
```

当前推荐演示接口：

```text
POST /ask_langchain
```

---

## 2. 项目定位

本项目用于展示 **AI 应用开发 / 大模型应用开发 / Python 后端 + RAG 工程实践** 能力。

当前重点不是模型训练或算法研究，而是展示真实企业 RAG 项目中更常见的工程能力：

```text
1. 企业资料如何入库
2. txt / PDF 如何进入统一处理流程
3. 为什么需要 Document(text + metadata)
4. 为什么 PDF 不能简单当作 txt 处理
5. 为什么 chunk 不能只按固定长度切
6. metadata 如何贯穿建库、检索和 debug
7. 如何避免资料不足时大模型硬答
8. 如何通过 debug 字段解释检索、重排和回答来源
```

---

## 3. 当前完整问答链路

```text
用户问题
→ FastAPI 接口
→ SQLite 读取会话历史
→ 明显 chat 规则兜底
→ build_route_context()
→ Semantic Router 判断 chat / rag
→ 如果不确定，LLM Router Fallback
→ 如果是 chat：
    → LangChain Chat Chain
    → DeepSeek 或 Ollama 生成 answer
→ 如果是 rag：
    → Query Rewrite 生成 retrieval_query
    → get_embedding(retrieval_query)
    → FAISS 语义召回
    → BM25 关键词召回
    → RRF 融合排序
    → DashScope qwen3-rerank 重排
    → rerank 阈值过滤 / 金额区间冲突过滤 / low_confidence 保护
    → 拼接 reference_text
    → LangChain RAG Chain
    → DeepSeek 或 Ollama 基于资料回答
→ SQLite 保存本轮对话
→ 返回 answer + used_chunks_debug + intent_debug + 模型来源字段
```

---

## 4. 企业资料入库处理链路

项目已经从早期单文件模式：

```text
data/knowledge.txt
→ chunk
→ embedding
→ index
```

升级为资料目录模式：

```text
data/raw_docs/
├─ knowledge.txt
├─ employee_handbook_sample.pdf
├─ it_support_policy_sample.pdf
```

当前正式入库流程：

```text
KNOWLEDGE_DIR = data/raw_docs
→ load_documents_from_dir()
→ 对每个文件调用 load_document()
→ txt：生成 1 个 Document
→ PDF：按 page 生成多个 Document
→ 合并为 list[Document]
→ process_documents()
→ chunk_documents()
→ build_chunk_records()
→ save chunk_index.json
→ build FAISS index
→ 服务启动加载 FAISS / BM25 / chunk_records
```

---

## 5. Document 数据结构

项目使用统一的 `Document` 作为资料入库的中间结构。

示例：

```python
Document(
    text="文档正文内容",
    metadata={
        "source_file": "it_support_policy_sample.pdf",
        "source_path": "data/raw_docs/it_support_policy_sample.pdf",
        "file_type": "pdf",
        "page": 2,
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
1. txt / PDF / Excel 等资料来源不同，但后续处理流程应统一
2. Loader 负责把不同原始文件转换成 Document
3. Processor / Chunker / Index Builder 只面对 list[Document]
4. metadata 用于来源追溯、权限扩展、版本扩展和 debug
```

---

## 6. Document Loader

### 6.1 txt Loader

txt 文件使用 `open(..., encoding="utf-8")` 读取。

特点：

```text
txt 通常是线性文本
整个 txt 文件生成 1 个 Document
metadata.file_type = txt
metadata.page = None
```

### 6.2 PDF Loader

PDF 使用 `pypdf.PdfReader` 读取文本型 PDF。

特点：

```text
文本型 PDF 按 page 提取文本
每一页生成一个 Document
metadata.file_type = pdf
metadata.page = 页码，从 1 开始
```

设计原因：

```text
PDF 命中后需要知道来源页码。
如果整份 PDF 合成一个 Document，后续只能知道来自哪个 PDF，无法知道第几页。
```

当前支持：

```text
文本型 PDF
page 级 metadata
```

当前不支持：

```text
扫描型 PDF OCR
复杂 PDF 表格结构还原
多栏版面恢复
页眉页脚智能过滤
```

### 6.3 资料目录 Loader

当前新增：

```python
load_documents_from_dir(KNOWLEDGE_DIR)
```

作用：

```text
扫描 data/raw_docs 目录
跳过不支持的文件
对 .txt / .pdf 调用 load_document()
把所有 Document 合并成 list[Document]
```

这样后续新增 Excel 时，只需要扩展对应 Loader，主建库流程不用重写。

---

## 7. Document Processor

`document_processor.py` 负责通用、保守的文本清洗。

当前处理：

```text
1. 统一 Windows / Linux / Mac 换行符
2. 去掉每行首尾空格
3. 压缩连续空格和 tab
4. 压缩过多空行
5. 清洗 text 的同时保留 metadata
```

设计原则：

```text
清理噪声，但不轻易破坏标题、段落和条款边界。
```

说明：

```text
PDF 抽取后可能出现 “直属主\n管” 这类行内断行。
通用 Processor 不会无差别删除所有单换行，因为对 txt / Excel 转文本来说，单换行可能本身代表结构。
```

因此，PDF 条款级切分前的局部规整放在 `document_chunker.py` 的策略内部处理。

---

## 8. Document Chunker

当前 chunk 策略不是简单固定长度切分，而是：

```text
先看内容结构
再选择切分方式
```

当前策略优先级：

```text
1. policy_clause
   如果识别到 “xxx制度条款A/B/C...” 结构，按条款切分

2. paragraph_then_overlap
   如果识别不到条款结构，退回原来的段落 + overlap 策略
```

### 8.1 policy_clause 条款级切分

当前已从特定规则升级为通用制度条款识别。

支持类似：

```text
请假制度条款C（事假）：
差旅报销制度条款B：
账号权限制度条款C（VPN 申请）：
资产管理制度条款D（离职归还）：
```

核心思想：

```text
不是判断是否包含“事假”或“VPN”这种关键词
而是识别“制度条款A/B/C”这类业务标题边界
从当前条款标题切到下一个条款标题之前
```

例如 PDF 第 2 页原本可能是一个大块：

```text
账号权限制度条款A（账号开通）：...
账号权限制度条款B（密码重置）：...
账号权限制度条款C（VPN 申请）：...
账号权限制度条款D（权限变更）：...
```

现在会切成多个独立 chunk：

```text
chunk 1：账号开通
chunk 2：密码重置
chunk 3：VPN 申请
chunk 4：权限变更
```

### 8.2 PDF 专用切分前规整

`policy_clause` 会根据 `file_type` 做局部处理：

```text
file_type = pdf：
    合并单个换行，减少 PDF 行内断行
    去掉末尾页码噪声，例如“第 2 页”

file_type = txt：
    不做 PDF 专用单换行合并，避免破坏 txt 原始结构
```

关键原则：

```text
内容结构决定 chunk 策略；
文件类型决定是否做专用文本规整。
```

### 8.3 chunk metadata

每个 chunk 会继续保留原始 Document 的 metadata，并补充：

```text
doc_index
chunk_index_in_document
chunk_char_length
chunk_strategy
chunk_id
```

示例：

```json
{
  "source_file": "it_support_policy_sample.pdf",
  "file_type": "pdf",
  "page": 2,
  "doc_index": 1,
  "chunk_index_in_document": 2,
  "chunk_char_length": 74,
  "chunk_strategy": "policy_clause",
  "chunk_id": 3
}
```

---

## 9. Index Builder

`index_builder.py` 负责：

```text
chunk_items(text + metadata)
→ 调用 embedding
→ chunk_records(text + embedding + metadata)
```

输出结构：

```python
{
    "chunk_id": 0,
    "text": "chunk 文本",
    "embedding": [...],
    "metadata": {...}
}
```

说明：

```text
embedding 只基于 text 生成
metadata 不参与 embedding
metadata 用于来源追溯、debug、权限扩展和版本扩展
```

当前仍保留旧输入兼容：

```text
list[str] → 自动转换成 {"text": ..., "metadata": {}}
```

这是为了小步升级，避免一次性破坏旧测试脚本。

---

## 10. Index Manager 与索引版本校验

当前正式建库已从单文件 `KNOWLEDGE_FILE` 升级为资料目录 `KNOWLEDGE_DIR`。

配置示例：

```python
KNOWLEDGE_DIR = "data/raw_docs"
DOCUMENT_PIPELINE_VERSION = "v5"
METADATA_SCHEMA_VERSION = "v1"
```

索引 meta 会记录：

```text
knowledge_source_type = dir
knowledge_dir = data/raw_docs
knowledge_hash_type = directory_sha256
knowledge_hash = 资料目录 hash
document_pipeline_version
metadata_schema_version
```

目录 hash 的作用：

```text
当 data/raw_docs 中的 txt / PDF 新增、删除、重命名或内容变化时，
系统可以判断旧索引已经过期，需要重新建库。
```

---

## 11. 检索与调试字段

当前 `/ask_langchain` 的 `used_chunks_debug` 会返回：

```text
text
chunk_id
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

metadata 可以用于判断：

```text
命中的 chunk 来自哪个文件
是 txt 还是 pdf
PDF 第几页
使用了哪种 chunk_strategy
```

示例：

```json
{
  "text": "账号权限制度条款C（VPN 申请）：员工因远程办公、出差或临时外部访问需要使用 VPN 时，应说明访问目的、预计使用时长和所需系统范围。VPN 权限默认按最小权限原则开通，到期后自动回收。",
  "metadata": {
    "source_file": "it_support_policy_sample.pdf",
    "file_type": "pdf",
    "page": 2,
    "chunk_strategy": "policy_clause"
  },
  "source": "both",
  "rerank_score": 93.8
}
```

---

## 12. LLM Provider 切换

最终回答模型支持：

```text
LLM_PROVIDER=deepseek
→ DeepSeek 云端模型

LLM_PROVIDER=ollama
→ Ollama 本地模型
```

注意：

```text
当前只表示最终 answer 生成模型可切换。
Embedding、Query Rewrite、Semantic Router、DashScope Reranker 等环节仍可能依赖云端 API。
因此当前不是全链路本地化。
```

返回字段：

```text
answer_source
answer_llm_provider
answer_llm_model
answer_llm_is_local
```

---

## 13. 启动与测试

### 13.1 安装依赖

```powershell
pip install -r requirements.txt
```

PDF 处理依赖：

```text
pypdf
```

### 13.2 配置 `.env`

```env
DEEPSEEK_API_KEY=your_deepseek_api_key
DASHSCOPE_API_KEY=your_dashscope_api_key

LLM_PROVIDER=ollama

OLLAMA_BASE_URL=http://localhost:11434
OLLAMA_MODEL=qwen3-4b-instruct-local
```

### 13.3 准备资料目录

```text
data/raw_docs/
├─ knowledge.txt
├─ employee_handbook_sample.pdf
├─ it_support_policy_sample.pdf
```

### 13.4 重建索引

```powershell
python -c "from app.index_manager import build_and_save_chunk_index; build_and_save_chunk_index()"
```

或者：

```text
POST /rebuild_index
```

### 13.5 启动服务

```powershell
uvicorn app.main:app --reload
```

接口文档：

```text
http://127.0.0.1:8000/docs
```

---

## 14. 推荐测试问题

### 14.1 员工手册 / txt 或员工手册 PDF

```json
{
  "question": "事假怎么申请？",
  "session_id": "demo_leave_001"
}
```

预期：

```text
retriever_status = matched
reference_text 命中事假条款
metadata.source_file = knowledge.txt 或 employee_handbook_sample.pdf
metadata.file_type = txt 或 pdf
如果命中 PDF，则 metadata.page = 2
chunk_strategy = policy_clause
```

### 14.2 IT 支持 PDF

```json
{
  "question": "VPN 权限怎么申请？",
  "session_id": "demo_vpn_001"
}
```

预期：

```text
retriever_status = matched
metadata.source_file = it_support_policy_sample.pdf
metadata.file_type = pdf
metadata.page = 2
chunk_strategy = policy_clause
reference_text 应主要包含“账号权限制度条款C（VPN 申请）”
```

### 14.3 PDF 第 1 页

```json
{
  "question": "打印机故障应该怎么处理？",
  "session_id": "demo_printer_001"
}
```

预期：

```text
命中 it_support_policy_sample.pdf
file_type = pdf
page = 1
```

### 14.4 PDF 第 3 页

```json
{
  "question": "离职时办公设备怎么归还？",
  "session_id": "demo_asset_return_001"
}
```

预期：

```text
命中 it_support_policy_sample.pdf
file_type = pdf
page = 3
```

---

## 15. 当前已实现范围

已实现：

```text
1. FastAPI RAG 问答接口
2. SQLite 多轮会话持久化
3. chat / rag 分流
4. Query Rewrite
5. FAISS + BM25 + RRF 混合检索
6. DashScope qwen3-rerank
7. low_confidence 低相关保护
8. DeepSeek / Ollama 最终回答模型切换
9. 统一 Document 数据结构
10. txt Loader
11. 文本型 PDF Loader
12. 资料目录扫描 load_documents_from_dir()
13. Document Processor 通用清洗
14. Document Chunker 支持 policy_clause + paragraph_then_overlap
15. PDF 专用切分前规整
16. 通用“xxx制度条款A（xxx）”识别
17. metadata 贯穿建库、检索和 debug
18. 目录 hash 判断资料目录变化
19. document_pipeline_version / metadata_schema_version 索引版本校验
```

---

## 16. 当前限制

当前仍是求职展示型项目，不是生产级企业知识库系统。

当前限制：

```text
1. PDF 仅支持文本型 PDF
2. 扫描型 PDF OCR 尚未实现
3. 复杂 PDF 表格结构还原尚未实现
4. 多栏 PDF 版面恢复尚未实现
5. Excel Loader 尚未实现
6. Word / docx Loader 尚未实现
7. 权限过滤目前只保留 permission_level 字段，尚未真正按用户权限过滤
8. 文档版本管理目前只保留 version 字段，尚未实现多版本过滤
9. section_heading 小标题切分尚未实现
10. 重复资料去重尚未实现
```

---

## 17. 项目亮点

```text
1. 从单文件 knowledge.txt Demo 升级为资料目录入库
2. 支持 txt + 文本型 PDF 混合入库
3. PDF 按 page 生成 Document，保留 page metadata
4. 使用统一 Document(text + metadata) 承接多类型资料
5. chunk 不只返回字符串，而是保留 metadata
6. 根据内容结构选择 chunk 策略，不是只按固定长度切
7. 针对制度类文档实现通用 policy_clause 条款级切分
8. PDF 专用行内断行处理只对 file_type=pdf 生效，避免影响 txt
9. 检索结果返回 source_file / file_type / page / chunk_strategy，方便溯源和 debug
10. 使用目录 hash 监控资料目录变化
```

---

## 18. 面试表达

```text
我把原来的单文件 RAG Demo 升级成了资料目录入库模式。系统会扫描 data/raw_docs 目录，对 txt 和文本型 PDF 分别调用对应 Loader。txt 通常生成一个 Document，PDF 会按 page 生成多个 Document，并在 metadata 中保留 source_file、file_type 和 page。

后续所有 Document 会统一进入 Processor、Chunker、Index Builder 和检索链路。Processor 做通用清洗；Chunker 根据内容结构选择切分策略。如果识别到“xxx制度条款A/B/C”这种业务结构，就按条款切分；识别不到时退回 paragraph_then_overlap。

接入 PDF 后我发现，文本型 PDF 抽取出来虽然也是文本，但可能出现行内断行、页码噪声和条款边界不稳定等问题。所以我只在 file_type=pdf 时，在条款切分前做轻量规整，比如合并单个换行、去掉页码，避免影响原来结构正常的 txt。

这样系统不仅能回答问题，还能通过 used_chunks_debug 解释命中的资料来自哪个文件、PDF 第几页、使用了哪种 chunk_strategy。
```

---

## 19. 一句话总结

```text
这是一个基于 FastAPI 的企业知识库 RAG 后端项目，已实现资料目录入库、txt + 文本型 PDF 解析、统一 Document 数据结构、metadata 贯穿建库与检索、结构化 chunk 策略、FAISS + BM25 + RRF 混合检索、DashScope Reranker、low_confidence 保护、SQLite 多轮会话和 DeepSeek / Ollama 最终回答模型切换，可用于展示 AI 应用开发中的 RAG 工程实践能力。
```
