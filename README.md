# FastAPI + RAG 企业知识库问答后端

## 1. 项目简介

本项目是一个基于 **FastAPI + RAG + Document Ingestion Pipeline + FAISS / BM25 / RRF 混合检索 + DashScope Reranker + LangChain + SQLite 多轮会话 + 最小版 Session Summary Memory + Controlled Tool Calling Agent Demo + LLM Provider 可切换** 的企业知识库问答后端项目。

项目面向企业内部知识库场景，例如：

```text
员工手册
请假制度
差旅报销制度
IT 支持制度
账号权限制度
资产管理制度
会议室预约表
培训报名表
办公用品领用表
```

项目目标不是简单调用大模型 API，而是实现一条较完整的企业 RAG 后端链路：

```text
企业资料目录
→ txt / PDF / Excel 文档读取
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
POST /agent_demo
```

其中 `/ask_langchain` 是主 RAG 问答接口；`/agent_demo` 是旁路 Controlled Tool Calling Agent Demo，用于展示工具选择、参数校验、危险工具授权和 `agent_steps` 可观测性，不替代 `/ask_langchain`，也不改动 RAG 主链路。

---

## 2. 项目定位

本项目用于展示 **AI 应用开发 / 大模型应用开发 / Python 后端 + RAG 工程实践** 能力。

当前重点不是模型训练或算法研究，而是展示真实企业 RAG 项目中更常见的工程能力：

```text
1. 企业资料如何入库
2. txt / PDF / Excel 如何进入统一处理流程
3. 为什么需要 Document(text + metadata)
4. 为什么 PDF 不能简单当作 txt 处理
5. 为什么 Excel 不能简单拼成长文本处理
6. 为什么 chunk 不能只按固定长度切
7. metadata 如何贯穿建库、检索和 debug
8. 如何避免资料不足时大模型硬答
9. 如何通过 debug 字段解释检索、重排和回答来源
10. 如何用最小版 session summary memory 辅助多轮 Query Rewrite
11. 如何用最小版 Controlled Tool Calling Agent Demo 展示 tool_call、工具白名单、参数校验、危险工具授权和执行链路
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
├─ permission_matrix_sample.xlsx
```

当前正式入库流程：

```text
KNOWLEDGE_DIR = data/raw_docs
→ load_documents_from_dir()
→ 对每个文件调用 load_document()
→ txt：生成 1 个 Document
→ PDF：按 page 生成多个 Document
→ Excel：按 sheet / row 生成多个 Document
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
        "source_file": "permission_matrix_sample.xlsx",
        "source_path": "data/raw_docs/permission_matrix_sample.xlsx",
        "file_type": "xlsx",
        "page": None,
        "sheet_name": "培训报名表",
        "row_number": 2,
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
metadata.sheet_name = None
metadata.row_number = None
```

### 6.2 PDF Loader

PDF 当前采用最小增强版 Loader：

```text
1. 使用 pypdf.PdfReader 保留文本型 PDF 的 page text Document
2. 使用 pdfplumber 提取文本型 PDF 中可解析的表格
3. 将 PDF 表格按 header + row 转成自然语言 Document
4. OCR_PROVIDER 默认 none，不执行 OCR
5. 当页面文本很少且疑似扫描页 / 主要图片页时，生成 OCR 文本或 image_placeholder
```

文本型 PDF 的原能力保持不变：

```text
文本型 PDF 按 page 提取文本
每一页生成一个 content_type=text 的 Document
metadata.file_type = pdf
metadata.page = 页码，从 1 开始
metadata.extraction_method = pypdf_text
```

PDF 表格不会简单拼成一大段无结构文本，而是按行转换：

```text
PDF表格记录：第2页 表格1 第3行：字段A=...；字段B=...；字段C=...
```

表格 Document metadata 关键字段：

```text
content_type = table
table_index
row_index / row_number
extraction_method = pdfplumber_table
```

OCR 是最小闭环，不是完整多模态图片理解：

```text
OCR_PROVIDER=none      # 默认关闭
OCR_PROVIDER=paddleocr # 可选，运行时动态 import
OCR_PROVIDER=easyocr   # 可选，运行时动态 import
```

默认关闭时，系统不会 import paddleocr / easyocr。只有疑似扫描页 / 主要图片页才会生成 `image_placeholder`，避免普通页面 logo、图标、装饰图片污染索引。

当前边界：

```text
已支持文本型 PDF
已支持最小版 PDF 表格提取为结构化文本 Document
已支持最小 OCR 闭环：扫描页可通过可选 OCR Provider 转成 Document
OCR 只识别图片中的文字，不理解图片语义、图表含义、流程图结构或照片内容
当前未做生产级表格区域去重，page text Document 和 table Document 可能存在少量重复
复杂表格还原、多栏布局恢复、扫描页质量判断仍不是生产级实现
```
### 6.3 Excel Loader

Excel 使用 `openpyxl` 读取 `.xlsx` 文件。

当前最小实现规则：

```text
1. 每个 sheet 的第一行作为 header
2. 从第二行开始读取数据行
3. 每一行结合 header 转成自然语言文本
4. 每一行生成一个 Document
5. metadata 保留 sheet_name 和 row_number
6. 空行跳过
```

示例 Excel 行：

| 培训名称 | 适用对象 | 报名截止 | 负责人 |
|---|---|---|---|
| 产品入门训练营 | 入职30天内的新员工 | 开课前3天 | 培训专员 |

转换后的 `Document.text` 示例：

```text
培训报名表记录：培训名称：产品入门训练营；适用对象：入职30天内的新员工；报名截止：开课前3天；负责人：培训专员。
```

metadata 示例：

```json
{
  "source_file": "permission_matrix_sample.xlsx",
  "file_type": "xlsx",
  "page": null,
  "sheet_name": "培训报名表",
  "row_number": 2
}
```

设计原因：

```text
Excel 不能简单拼成长文本。
Excel 的语义通常来自 header + row，一行往往代表一个业务对象。
例如培训报名记录、会议室预约规则、办公用品领用规则。
```

当前不支持：

```text
合并单元格复杂解析
多级表头
复杂公式重新计算
透视表
跨 sheet 关联
```

### 6.4 资料目录 Loader

当前实现：

```python
load_documents_from_dir(KNOWLEDGE_DIR)
```

作用：

```text
扫描 data/raw_docs 目录
跳过不支持的文件
对 .txt / .pdf / .xlsx 调用 load_document()
把所有 Document 合并成 list[Document]
```

这样后续新增 Word、更多 Excel 表格或其他资料类型时，只需要扩展对应 Loader，主建库流程不用重写。

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
6. 如果清洗后 text 为空，则跳过该 Document，并输出调试提示
```

设计原则：

```text
清理噪声，但不轻易破坏标题、段落、条款和表格行语义。
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

### 8.2 PDF 专用切分前规整

`policy_clause` 会根据 `file_type` 做局部处理：

```text
file_type = pdf：
    合并单个换行，减少 PDF 行内断行
    去掉末尾页码噪声，例如“第 2 页”

file_type = txt / xlsx：
    不做 PDF 专用单换行合并，避免破坏原始结构
```

关键原则：

```text
内容结构决定 chunk 策略；
文件类型决定是否做专用文本规整。
```

### 8.3 Excel 与 chunk 的关系

Excel 的特殊处理主要发生在 Loader 阶段：

```text
Excel sheet / row
→ 一行转成一个自然语言 Document
```

由于每个 Excel 行 Document 通常已经是完整业务对象，并且长度较短，所以进入 Chunker 后通常会走：

```text
paragraph_then_overlap
```

并保持一行一个 chunk。

可以理解为：

```text
PDF：Loader 按 page 生成 Document，Chunker 再按条款细切
Excel：Loader 直接按 row 生成 Document，每行本身就是业务对象
```

### 8.4 chunk metadata

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
  "source_file": "permission_matrix_sample.xlsx",
  "file_type": "xlsx",
  "sheet_name": "培训报名表",
  "row_number": 2,
  "doc_index": 9,
  "chunk_index_in_document": 0,
  "chunk_char_length": 124,
  "chunk_strategy": "paragraph_then_overlap",
  "chunk_id": 26
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
DOCUMENT_PIPELINE_VERSION = "v6"
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
当 data/raw_docs 中的 txt / PDF / Excel 新增、删除、重命名或内容变化时，
系统可以判断旧索引已经过期，需要重新建库。
```

---

## 11. Semantic Router 与资料范围同步

当前 Router 使用：

```text
CHAT_EXAMPLES
RAG_EXAMPLES
RAG_DOMAIN_KEYWORDS
LLM Router Fallback
```

注意：

```text
Router 不是根据文件格式分流，而是根据“用户问题像不像知识库问题”分流。
```

接入 Excel 后，补充了表格型企业资料相关的 RAG 样本和关键词，例如：

```text
产品入门训练营报名截止是什么时候
星河会议室需要提前多久预约
白板笔套装怎么领取
会议室预约
培训报名
办公用品领用
报名截止
```

原因：

```text
新增资料类型后，用户会产生新的问法。
如果 Router 样本仍只覆盖请假、报销、员工手册等问题，可能会把 Excel 表格事实查询误判为 chat。
```

设计理解：

```text
知识库范围变化后，Router 样本也要同步维护。
```

---

## 12. 检索与调试字段

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
是 txt、pdf 还是 xlsx
PDF 第几页
Excel 哪个 sheet、哪一行
使用了哪种 chunk_strategy
```

Excel 命中示例：

```json
{
  "text": "培训报名表记录：培训名称：产品入门训练营；适用对象：入职30天内的新员工；报名截止：开课前3天；负责人：培训专员。",
  "metadata": {
    "source_file": "permission_matrix_sample.xlsx",
    "file_type": "xlsx",
    "sheet_name": "培训报名表",
    "row_number": 2,
    "chunk_strategy": "paragraph_then_overlap"
  },
  "source": "both",
  "rerank_score": 95.47
}
```

---

## 13. LLM Provider 切换

最终回答模型支持：

```text
LLM_PROVIDER=deepseek
→ DeepSeek 云端模型

LLM_PROVIDER=ollama
→ Ollama 本地模型
```

Session summary 摘要生成模型独立配置：

```text
MEMORY_SUMMARY_PROVIDER=deepseek
→ DeepSeek 云端模型生成 memory_summary

MEMORY_SUMMARY_PROVIDER=ollama
→ Ollama 本地模型生成 memory_summary
```

注意：

```text
LLM_PROVIDER 只控制最终 answer 生成模型。
MEMORY_SUMMARY_PROVIDER 只控制 session summary 摘要生成模型。
两者可以独立配置，互不覆盖。
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

## 14. Agent / Tool Calling Demo

`/agent_demo` 是旁路接口，不替代 `/ask_langchain`，也不修改现有 RAG 主链路。当前实现的是最小版 Controlled Tool Calling Agent Demo，用于展示“模型生成工具调用计划，后端负责校验和执行”的受控流程；它不是完整自主 Agent，也不是 Multi-Agent。

Planner 支持两种模式：

```text
AGENT_PLANNER_PROVIDER=fake
AGENT_PLANNER_PROVIDER=llm
```

LLM planner 会根据 `question + tool schemas` 生成 strict JSON `tool_call`，结构只包含工具名和参数，例如：

```json
{
  "tool_name": "get_index_info",
  "arguments": {}
}
```

无论 planner 是 `fake` 还是 `llm`，后端都会统一执行：

```text
tool whitelist validation
arguments schema validation
dangerous tool authorization
executor execution
```

当前工具：

```text
get_index_info
search_knowledge_base
rebuild_index
```

- `get_index_info`：只读工具，用于查看当前知识库索引状态。
- `search_knowledge_base`：只读 RAG tool，复用现有 `get_embedding`、`hybrid_search`、reranker、`run_rag_chain`，从 `app.state` 读取已加载索引对象；它不复制完整 `/ask_langchain`，不包含 session history、Query Rewrite、semantic router、memory_summary 或数据库写入。
- `rebuild_index`：危险工具，已实现双层校验：

```text
tool_call.arguments.confirm == true
AND
request.allow_rebuild_index == true
```

当前即使双层校验通过，也不会真实重建索引，而是返回 `not_implemented_for_safety`。

前端 Agent Demo 模式会展示：

```text
answer
agent_mode
agent_steps
agent_debug
```

当前未实现，也不应夸大为：

```text
完整自主 Agent
Multi-Agent
外部 API 工具
动态 user_id / role / permission 工具表
生产级权限系统
Agent 中真实执行 rebuild_index
```

---

## 15. 启动与测试

### 15.1 安装依赖

```powershell
pip install -r requirements.txt
```

资料处理相关依赖：

```text
pypdf
openpyxl
```

### 15.2 配置 `.env`

```env
DEEPSEEK_API_KEY=your_deepseek_api_key
DASHSCOPE_API_KEY=your_dashscope_api_key

LLM_PROVIDER=ollama
MEMORY_SUMMARY_PROVIDER=ollama

OLLAMA_BASE_URL=http://localhost:11434
OLLAMA_MODEL=qwen3-4b-instruct-local
```

### 15.3 准备资料目录

```text
data/raw_docs/
├─ knowledge.txt
├─ employee_handbook_sample.pdf
├─ it_support_policy_sample.pdf
├─ permission_matrix_sample.xlsx
```

### 15.4 重建索引

```powershell
python -c "from app.index_manager import build_and_save_chunk_index; build_and_save_chunk_index()"
```

或者：

```text
POST /rebuild_index
```

### 15.5 启动服务

```powershell
uvicorn app.main:app --reload
```

接口文档：

```text
http://127.0.0.1:8000/docs
```

### 15.6 前端 Demo

`frontend/` 是基于 React + Vite + TypeScript 的轻量展示页面，支持两种模式：

```text
RAG 问答：POST /ask_langchain
Agent Demo：POST /agent_demo
```

RAG 问答模式会展示 `answer`、`intent`、`retriever_status`、`retrieval_query`、`memory_debug` 和 `used_chunks_debug`。其中调试面板重点用于呈现 RAG 的可解释性信息：

```text
source_file
file_type
page
sheet_name
row_number
chunk_strategy
FAISS / BM25 / RRF / rerank 分数
```

Agent Demo 模式会发送：

```json
{
  "question": "...",
  "session_id": "frontend_demo_001",
  "allow_rebuild_index": false
}
```

页面提供“允许执行重建索引测试”checkbox，默认不勾选。Agent Demo 响应会展示 `answer`、`agent_mode`、`agent_steps` 和 `agent_debug`，用于演示 controlled tool calling 的 planner、tool_call、工具白名单校验、参数校验、危险工具授权和 executor 执行结果。

启动后端：

```powershell
.\.venv\Scripts\python.exe -m uvicorn app.main:app --reload
```

启动前端：

```powershell
cd frontend
npm install
npm run dev
```

访问页面：

```text
http://127.0.0.1:5173
```

---

## 16. 推荐测试问题

```json
{
  "question": "事假怎么申请？",
  "session_id": "demo_leave_001"
}
```

```json
{
  "question": "VPN 权限怎么申请？",
  "session_id": "demo_vpn_001"
}
```

```json
{
  "question": "产品入门训练营报名截止是什么时候？",
  "session_id": "demo_excel_training_001"
}
```

```json
{
  "question": "星河会议室需要提前多久预约？",
  "session_id": "demo_excel_room_001"
}
```

```json
{
  "question": "白板笔套装怎么领取？",
  "session_id": "demo_excel_supply_001"
}
```

预期重点观察：

```text
txt / PDF / Excel 都能进入 RAG
PDF 命中时 page 不为空
Excel 命中时 sheet_name / row_number 不为空
used_chunks_debug 可以解释命中来源
```

---

## 17. 当前已实现范围

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
12. Excel Loader
13. 资料目录扫描 load_documents_from_dir()
14. Document Processor 通用清洗
15. Document Chunker 支持 policy_clause + paragraph_then_overlap
16. PDF 专用切分前规整
17. 通用“xxx制度条款A（xxx）”识别
18. Excel 按 sheet / row 生成 Document
19. metadata 贯穿建库、检索和 debug
20. 目录 hash 判断资料目录变化
21. document_pipeline_version / metadata_schema_version 索引版本校验
22. Router 样本补充，支持表格型资料查询进入 RAG
23. 最小版 session summary memory，summary 只用于 Query Rewrite
24. `/agent_demo` 旁路接口，不替代 `/ask_langchain`
25. Controlled Tool Calling Agent Demo：支持 fake planner 和 LLM planner
26. `AGENT_PLANNER_PROVIDER=fake / llm` planner 切换
27. LLM planner 根据 question + tool schemas 生成 strict JSON `tool_call`
28. tool whitelist validation / arguments schema validation / dangerous tool authorization
29. `agent_steps` 和 `agent_debug` 可观测字段
30. Agent tools：`get_index_info` / `search_knowledge_base` / `rebuild_index`
31. 前端支持 RAG 问答 / Agent Demo 模式切换，并展示 `agent_steps`
```

---

 Excel 当前只支持普通单行 header + 数据行
6. Excel 合并单元格、多级表头、公式重新计算、透视表尚未支持
7. Word / docx Loader 尚未实现
8. 权限过滤目前只保留 permission_level 字段，尚未真正按用户权限过滤
9. 文档版本管理目前只保留 version 字段，尚未实现多版本过滤
10. section_heading 小标题切分尚未实现
11. 重复资料去重尚未实现
12. `/agent_demo` 是最小版 controlled tool agent，不是完整自主 Agent 平台
13. Multi-Agent 未实现
14. 外部 API 工具未实现，例如飞书、微博、小红书、天气 API
15. `rebuild_index` 在 `/agent_demo` 中仍不真实执行重建；授权通过后返回 `not_implemented_for_safety`
16. 尚未实现动态 user_id / role / permission 工具表或生产级权限系统
17. Agent 的 `search_knowledge_base` 不完整复刻 `/ask_langchain` 的 session history、Query Rewrite、semantic router、memory_summary 和数据库写入能力
```

---

## 19. 项目亮点

```text
1. 从单文件 knowledge.txt Demo 升级为资料目录入库
2. 支持 txt + 文本型 PDF + Excel 混合入库
3. PDF 按 page 生成 Document，保留 page metadata
4. Excel 按 sheet / row 生成 Document，保留 sheet_name / row_number
5. 使用统一 Document(text + metadata) 承接多类型资料
6. chunk 不只返回字符串，而是保留 metadata
7. 根据内容结构选择 chunk 策略，不是只按固定长度切
8. 针对制度类文档实现通用 policy_clause 条款级切分
9. PDF 专用行内断行处理只对 file_type=pdf 生效，避免影响 txt / Excel
10. 检索结果返回 source_file / file_type / page / sheet_name / row_number / chunk_strategy，方便溯源和 debug
11. 使用目录 hash 监控资料目录变化
12. Router 样本会随着知识库业务范围扩展而维护
```

---

## 20. 面试表达

```text
我把原来的单文件 RAG Demo 升级成了资料目录入库模式。系统会扫描 data/raw_docs 目录，对 txt、文本型 PDF 和 Excel 分别调用对应 Loader。

txt 通常生成一个 Document；PDF 会按 page 生成多个 Document，并在 metadata 中保留 page；Excel 不会简单拼成长文本，而是按 sheet 和 row 读取，把每一行结合 header 转换成自然语言 Document，并在 metadata 中保留 sheet_name 和 row_number。

后续所有 Document 会统一进入 Processor、Chunker、Index Builder 和检索链路。Processor 做通用清洗；Chunker 根据内容结构选择切分策略。如果识别到“xxx制度条款A/B/C”这种业务结构，就按条款切分；识别不到时退回 paragraph_then_overlap。

接入 PDF 后我发现，文本型 PDF 抽取出来虽然也是文本，但可能出现行内断行、页码噪声和条款边界不稳定等问题。所以我只在 file_type=pdf 时，在条款切分前做轻量规整，避免影响原来结构正常的 txt 和 Excel。

接入 Excel 后我发现，Loader 和索引正常后，还需要让 Router 知道“培训报名、会议室预约、办公用品领用”这类表格型事实查询也属于 RAG 范围。因此我补充了 Excel 场景的 RAG 样本和领域关键词。

这样系统不仅能回答问题，还能通过 used_chunks_debug 解释命中的资料来自哪个文件、PDF 第几页、Excel 哪个 sheet 和哪一行、使用了哪种 chunk_strategy。
```

---

## 21. 一句话总结

```text
这是一个基于 FastAPI 的企业知识库 RAG 后端项目，已实现资料目录入库、txt + 文本型 PDF + Excel 解析、统一 Document 数据结构、metadata 贯穿建库与检索、结构化 chunk 策略、FAISS + BM25 + RRF 混合检索、DashScope Reranker、low_confidence 保护、SQLite 多轮会话、最小版 session summary memory、旁路 `/agent_demo` Controlled Tool Calling Agent Demo 和 DeepSeek / Ollama 最终回答模型切换，可用于展示 AI 应用开发中的 RAG 工程实践与最小版工具调用能力。
```

---

## 22. 最小版 session summary memory

当前项目已在 `/ask_langchain` 主链路中集成一个**最小版 session summary memory**。它的定位是：在同一个 `session_id` 内，对较早的会话历史做压缩摘要，辅助后续 Query Rewrite 理解多轮追问上下文。

已实现能力：

- 基于 `session_id + SQLite` 的 session memory。
- 新增 SQLite 表 `session_memory_summaries`，保存当前 session 的压缩摘要。
- 按阈值触发 summary 更新，而不是每轮都更新。
- 使用 LLM 对较早历史做增量压缩。
- 摘要生成由 `MEMORY_SUMMARY_PROVIDER` 独立控制，支持 `deepseek` / `ollama`；这和最终回答的 `LLM_PROVIDER` 切换不是同一件事。
- 保留 recent messages，避免最新几轮对话被过早压缩。
- summary 仅用于 Query Rewrite 的上下文理解。
- summary 不进入 `reference_text`，不作为最终回答的事实依据。
- `/ask_langchain` 返回 `memory_debug`，用于说明 summary 是否存在、是否用于 Query Rewrite、是否更新成功。
- 若 DeepSeek 不可用或 summary 更新失败，不会影响原 RAG / chat 回答。
- 更新 summary 前会过滤 `low_confidence` / 资料不足兜底回答，避免把“资料中没有找到足够相关内容”等失败回复写入记忆。

`memory_debug` 示例：

```json
{
  "enabled": true,
  "summary_exists": true,
  "summary_used_for_query_rewrite": true,
  "summarized_message_count": 12,
  "summary_preview": "用户连续询问报销金额区间审批规则...",
  "summary_updated": false,
  "summary_update_reason": "not_enough_new_messages",
  "summary_update_error": null
}
```

当前未实现，也不应在简历或面试中夸大为：

- 完整 long-term memory。
- user profile memory。
- vector memory。
- 跨 session 长期记忆检索。
- memory 与知识库统一向量检索系统。

推荐表述：

```text
项目实现了一个最小版 session summary memory：在单个 session_id 内使用 SQLite 保存会话摘要，按阈值用 LLM 压缩较早历史，并仅把 summary 作为 Query Rewrite 的辅助上下文，不作为知识库证据。
```

---

## 23. 最小版 Controlled Tool Calling Agent Demo

当前项目已实现旁路接口 `POST /agent_demo`，用于展示 controlled tool calling。它不替代 `/ask_langchain`，也不修改 RAG 主链路。

已实现能力：

- 支持 `AGENT_PLANNER_PROVIDER=fake / llm`。
- fake planner 用于本地链路测试和未配置模型时的 fallback。
- LLM planner 根据 user question + tool schemas 生成 strict JSON `tool_call`，只允许包含 `tool_name` 和 `arguments`。
- 后端统一执行 tool whitelist validation、arguments schema validation、dangerous tool authorization 和 executor。
- 返回 `answer`、`agent_steps`、`agent_debug`，用于观察 planner、校验、授权、执行和 blocked 结果。

当前工具：

```text
get_index_info
search_knowledge_base
rebuild_index
```

`search_knowledge_base` 当前是只读 RAG tool：复用现有 `get_embedding`、`hybrid_search`、reranker 和 `run_rag_chain`，从 `app.state` 读取已加载的索引对象。它不复制完整 `/ask_langchain`，也不包含 session history、Query Rewrite、semantic router、memory_summary 或数据库写入。

`rebuild_index` 当前已有双层校验：

```text
tool_call.arguments.confirm == true
AND
request.allow_rebuild_index == true
```

但它仍不真实执行重建。授权通过后返回 `not_implemented_for_safety`，用于面试演示“危险工具需要后端授权和安全执行边界”。

当前未实现，也不应夸大为：

- 完整自主 Agent。
- Multi-Agent。
- 外部 API 工具，例如飞书、微博、小红书、天气 API。
- 真实执行 `rebuild_index`。
- 动态 user_id / role / permission 工具表。
- 生产级权限系统。
- Agent 完整复刻 `/ask_langchain` 的多轮 memory 和 router 能力。

推荐表述：

```text
项目实现了一个最小版 Controlled Tool Calling Agent Demo：LLM planner 只生成 strict JSON tool_call，后端负责工具白名单、参数 schema、危险工具授权和 executor 执行；RAG 被封装成一个只读工具，主接口 /ask_langchain 不受影响。
```


