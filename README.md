# FastAPI + RAG 企业知识库问答后端

## 1. 项目简介

本项目是一个基于 **FastAPI + RAG + Hybrid Retrieval + Semantic Router + DashScope Reranker + Multi-turn Chat** 的企业知识库问答后端项目。

项目面向企业员工手册、制度文档、审批流程、请假制度、差旅报销等内部资料场景，目标是让用户通过自然语言查询企业制度，并让系统基于本地知识库资料进行回答。

完整链路：

```text
用户问题
→ FastAPI 接口
→ SQLite 读取历史
→ 明显 chat 规则兜底
→ Semantic Router 判断 chat / rag
→ 低置信度时 LLM Router Fallback
→ Query Rewrite
→ FAISS + BM25 双轨召回
→ RRF 融合排序
→ DashScope qwen3-rerank 重排
→ 双阈值 + 分差限制 + 金额区间冲突过滤
→ LangChain RAG Chain 基于资料回答
→ SQLite 保存历史
→ 返回 answer + debug 字段
```

---

## 2. 项目定位

本项目用于展示：

- Python 后端接口开发能力
- FastAPI 服务封装能力
- LLM API 调用能力
- Embedding 与向量检索能力
- RAG 工程链路设计能力
- 多轮会话与 SQLite 持久化能力
- 混合检索与重排能力
- Reranker 后处理调优能力
- LangChain 增量接入能力
- 可解释调试字段设计能力

项目定位是：**AI 应用开发 / 大模型应用开发方向的求职展示项目**。

---

## 3. 核心功能

### 3.1 普通聊天与 RAG 问答分流

- 明显问候、感谢、礼貌收尾直接进入 chat。
- 企业制度、员工手册、审批、报销、请假等问题进入 rag。
- 明显 chat 优先于历史，避免“好的，谢谢”被上一轮 RAG 历史带偏。

### 3.2 SQLite 多轮会话持久化

- 使用 `session_id` 区分不同会话。
- 每轮 user / assistant 对话写入 SQLite。
- 服务重启后仍能读取历史。
- 多轮 Query Rewrite 和普通聊天都可以基于历史继续工作。

### 3.3 Semantic Router 语义路由

- 启动时预加载 chat / rag 样本 embedding。
- 用户问题转 embedding 后与样本计算相似度。
- 每类取 top3，计算综合分：

```text
final_score = 0.7 * best_score + 0.3 * top3_avg_score
```

- 结合 `ROUTER_MIN_SCORE` 和 `ROUTER_MARGIN` 判断 chat / rag。

### 3.4 LLM Router Fallback

- 当 Semantic Router 分数不明确时，调用大模型兜底判断 chat / rag。
- 关键词不再直接决定 intent，只作为 debug 信号保留。
- 无历史模糊问题会进入 chat，并追问用户补充信息。

### 3.5 Query Rewrite

多轮短追问会被改写成完整检索问题。

```text
上一轮：报销500到2000元怎么审批？
当前轮：那再高一点呢？
retrieval_query：报销金额超过2000元怎么审批？
```

### 3.6 FAISS + BM25 + RRF 混合检索

- FAISS：负责语义召回。
- BM25：负责关键词、数字、制度名召回。
- RRF：融合两路召回排名。

### 3.7 DashScope qwen3-rerank 检索后重排

- hybrid_search 先召回候选 chunk。
- qwen3-rerank 输入 query + documents。
- 返回 index + relevance_score。
- 系统换算成 0-100 的 rerank_score。
- 重排后再进行阈值过滤与业务规则校验。

### 3.8 Reranker 双阈值 + 分差限制

当前策略：

```python
RERANK_PRIMARY_MIN_SCORE = 60
RERANK_EXTRA_MIN_SCORE = 75
RERANK_EXTRA_MAX_GAP = 20
RERANK_MIN_SCORE = RERANK_PRIMARY_MIN_SCORE
```

含义：

- 第一名 chunk 达到 60 即可保留，避免核心资料被误伤。
- 第二名及以后必须达到 75。
- 第二名及以后还不能和第一名分差超过 20。
- 如果第一名都低于 60，说明整体相关性不足，返回空列表，交给上层返回 low_confidence。

### 3.9 金额区间冲突过滤

针对报销制度中的金额区间问题，增加轻量业务规则校验。

当前将报销金额划分为：

```text
low：500元及以下
middle：500元以上且不超过2000元
high：超过2000元
```

如果 query 和 chunk 的金额区间明确但不一致，则认为冲突，不进入最终 `reference_text`。

示例：

```text
问：报销500到2000元怎么审批？
只保留：500元以上且不超过2000元条款
过滤：500元及以下条款、超过2000元条款
```

### 3.10 low_confidence 低相关保护

如果进入 RAG 后，所有候选资料都低于主资料阈值，系统不会强行保留第一条。

返回：

```text
retriever_status = low_confidence
answer = 资料中没有找到足够相关的内容，建议你补充更具体的问题。
```

### 3.11 LangChain 增量接入

- 保留手写版 `/ask`。
- 新增 `/ask_langchain`。
- 复用已有路由、检索、重排和历史逻辑。
- 用 LangChain 封装最终 chat / rag 回答链。

### 3.12 启动时自动检查 / 自动重建索引

- 服务启动时检查 `chunk_index.json` 和 `chunk_index.faiss` 是否可用。
- 如果索引缺失、知识库内容变化、embedding 模型不一致、chunk 策略不一致或 FAISS 文件加载失败，系统可自动触发重新建库。
- 开发和演示阶段可以减少手动执行 `python app/rebuild.py` 的次数。

---

## 4. 技术栈

```text
Python
FastAPI
DeepSeek API
DashScope Embedding
DashScope qwen3-rerank
FAISS
BM25
RRF
SQLite
LangChain
Docker
```

---

## 5. 推荐演示接口

当前推荐使用：

```text
POST /ask_langchain
```

原因：

- `/ask_langchain` 包含最新的 DashScope qwen3-rerank。
- `/ask_langchain` 支持 low_confidence。
- `/ask_langchain` 返回更完整的调试字段。
- `/ask` 保留为手写版主链，用于展示底层理解。

---

## 6. 核心流程

### 6.1 chat 分支

```text
用户问题
→ 明显 chat 规则兜底 或 Semantic Router 判定为 chat
→ 读取 SQLite 历史
→ LangChain chat chain
→ 返回 answer
→ 保存历史
```

### 6.2 rag 分支

```text
用户问题
→ 读取 SQLite 历史
→ 构造 route_context
→ Semantic Router 判断为 rag
→ 构造 retrieval_query
→ get_embedding(retrieval_query)
→ FAISS 语义召回
→ BM25 关键词召回
→ RRF 融合排序
→ DashScope qwen3-rerank 重排
→ 主资料阈值过滤
→ 补充资料阈值过滤
→ 补充资料分差限制
→ 金额区间冲突过滤
→ 拼接 reference_text
→ LangChain RAG chain
→ 返回 answer + debug
→ 保存历史
```

---

## 7. 关键设计说明

### 7.1 为什么不是所有请求都进入 RAG

不是所有输入都需要查知识库。比如：

```text
你好
谢谢
好的，谢谢
我今天有点焦虑怎么办
我该怎么准备AI应用开发面试
```

这些问题不依赖员工手册。如果全部进入 RAG，会造成不必要的 embedding 成本、检索延迟和知识库污染。

因此项目使用：

```text
明显 chat 规则
→ Semantic Router
→ LLM Router Fallback
```

控制是否进入 RAG。

### 7.2 为什么使用 LLM Router Fallback

旧版低置信度兜底依赖关键词，例如“流程”“审批”“申请”。

问题是关键词太粗，容易误判：

```text
学习RAG项目的流程应该怎么安排？
```

这里的“流程”不是企业制度流程。

因此新版改为：

```text
Semantic Router 不确定
→ LLM Router Fallback 判断 chat / rag
```

只在低置信度时调用大模型，控制延迟和成本。

### 7.3 为什么区分 route_context 和 retrieval_query

两者职责不同：

```text
route_context：给 Router 判断是否需要 RAG
retrieval_query：给检索器查资料
```

route_context 要中性，不能提前被“检索优化”污染。  
retrieval_query 要完整，适合检索。

当前 `route_context` 只保留 user 历史，避免 assistant 上一轮回答污染路由判断。

### 7.4 为什么使用 FAISS + BM25

FAISS 和 BM25 各自擅长不同场景：

```text
FAISS：语义相似
BM25：关键词、数字、制度名
```

单独使用任何一种都有短板，混合检索更稳。

### 7.5 为什么使用 RRF

FAISS 和 BM25 的分数体系不同，不能直接相加。RRF 按排名融合，让两路都命中的资料更容易排前。

### 7.6 为什么 DashScope Reranker 后还需要业务规则

qwen3-rerank 更偏语义相关性排序，能判断 query 和 chunk 是否整体相关，但对金额区间、否定条件、范围冲突等精确业务条件不一定完全可靠。

例如：

```text
问：报销500到2000元怎么审批？
```

“500元及以下”和“超过2000元”条款也包含“报销、金额、审批”等关键词，可能被打较高相关分。

因此项目在 rerank 后增加了：

```text
双阈值
分差限制
金额区间冲突过滤
```

这不是替代 reranker，而是在 reranker 之后补业务精确条件校验。

### 7.7 LLM Router Fallback 和 low_confidence 的区别

| 机制 | 触发阶段 | 作用 |
|---|---|---|
| LLM Router Fallback | Router 阶段 | 当 Semantic Router 不确定 chat/rag 时，请大模型兜底判断 |
| low_confidence | RAG 检索 / rerank 阶段 | 已经决定进入 RAG，但资料相关度不足时，不基于弱相关资料硬答 |

---

## 8. 当前配置

核心配置示例：

```python
TOP_K = 2
HYBRID_RECALL_K = 10

USE_RERANKER = True
RERANKER_PROVIDER = "dashscope"
DASHSCOPE_RERANK_MODEL = "qwen3-rerank"
RERANK_CANDIDATE_K = 6

RERANK_PRIMARY_MIN_SCORE = 60
RERANK_EXTRA_MIN_SCORE = 75
RERANK_EXTRA_MAX_GAP = 20
RERANK_MIN_SCORE = RERANK_PRIMARY_MIN_SCORE

ROUTER_MIN_SCORE = 0.45
ROUTER_MARGIN = 0.03
BEST_SCORE_WEIGHT = 0.7
AVG_TOP_SCORE_WEIGHT = 0.3

USE_LLM_ROUTER_FALLBACK = True
USE_KEYWORD_ROUTER_FALLBACK = False
LLM_ROUTER_FAILED_DEFAULT_INTENT = "chat"

USE_ASSISTANT_HISTORY = False
MAX_HISTORY_TURNS = 5

AUTO_REBUILD_INDEX_ON_STARTUP = True
```

---

## 9. 启动方式

### 9.1 安装依赖

```bash
pip install -r requirements.txt
```

### 9.2 配置环境变量

Windows PowerShell 临时设置：

```powershell
$env:DEEPSEEK_API_KEY="你的DeepSeekKey"
$env:DASHSCOPE_API_KEY="你的百炼Key"
```

Windows PowerShell 永久设置：

```powershell
setx DEEPSEEK_API_KEY "你的DeepSeekKey"
setx DASHSCOPE_API_KEY "你的百炼Key"
```

设置后重新打开终端。

### 9.3 建库方式

手动建库：

```bash
python app/rebuild.py
```

如果已经开启：

```python
AUTO_REBUILD_INDEX_ON_STARTUP = True
```

那么知识库内容变化、索引文件缺失或 FAISS 索引损坏时，直接重启服务即可自动检查并重建索引。

### 9.4 启动服务

```bash
uvicorn app.main:app --reload
```

接口文档：

```text
http://127.0.0.1:8000/docs
```

---

## 10. API 说明

### 10.1 POST /ask_langchain

推荐演示接口。

请求：

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
retrieval_query
reference_text
used_chunk_count
history_messages
used_chunks_debug
intent_debug
```

### 10.2 POST /ask

手写版接口。保留用于展示手写 RAG 主链。最新 DashScope reranker 与 low_confidence 主要接入在 `/ask_langchain`。

### 10.3 GET /index_info

查看索引信息。

### 10.4 POST /rebuild_index

手动重建索引。

---

## 11. 调试字段说明

### 11.1 intent_debug

用于解释路由判断：

```text
intent
route_strategy
decision_reason
chat_final_score
rag_final_score
score_gap_rag_minus_chat
top_chat_matches
top_rag_matches
domain_keyword_detected
fallback_used
route_decision_source
llm_router_debug
router_min_score
router_margin
```

### 11.2 used_chunks_debug

用于解释检索和重排结果：

```text
text
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

## 12. 典型测试样本

### 12.1 普通 chat 不进 RAG

```json
{
  "question": "你好",
  "session_id": "demo_company_001"
}
```

预期：

```text
intent = chat
不返回 reference_text
```

### 12.2 制度问题进入 RAG

```json
{
  "question": "事假怎么请？",
  "session_id": "demo_company_002"
}
```

预期：

```text
intent = rag
retriever_status = matched
reference_text 命中事假条款 / 请假总则
```

### 12.3 金额区间过滤：500元及以下

```json
{
  "question": "报销500元以下谁审批？",
  "session_id": "demo_company_003"
}
```

预期：

```text
只保留 500元及以下 条款
过滤 500-2000 元和超过 2000 元条款
```

### 12.4 金额区间过滤：500-2000元

```json
{
  "question": "报销500到2000元怎么审批？",
  "session_id": "demo_company_004"
}
```

预期：

```text
只保留 500元以上且不超过2000元 条款
过滤 500元及以下 和 超过2000元 条款
```

### 12.5 金额区间过滤：超过2000元

```json
{
  "question": "报销金额超过2000元怎么审批？",
  "session_id": "demo_company_005"
}
```

预期：

```text
只保留超过 2000 元审批条款
过滤 500元及以下 和 500-2000 元条款
```

### 12.6 多轮 Query Rewrite

第一轮：

```json
{
  "question": "报销500到2000元怎么审批？",
  "session_id": "demo_company_006"
}
```

第二轮：

```json
{
  "question": "那再高一点呢？",
  "session_id": "demo_company_006"
}
```

预期：

```text
retrieval_query 接近：报销金额超过2000元怎么审批？
reference_text 只保留超过2000元条款
```

### 12.7 无历史模糊问题

```json
{
  "question": "这个情况应该怎么处理？",
  "session_id": "demo_company_007"
}
```

预期：

```text
route_strategy = llm_fallback_chat
answer 追问用户补充具体情况
```

### 12.8 低相关资料保护

```json
{
  "question": "公司年终奖发放规则是什么？",
  "session_id": "demo_company_008"
}
```

预期：

```text
intent = rag
retriever_status = low_confidence
used_chunk_count = 0
不基于弱相关资料硬答
```

---

## 13. 当前限制

当前项目仍是求职展示型 Demo，不是生产级系统。

限制包括：

1. 知识库主要是测试资料。
2. SQLite 是本地单机持久化。
3. 没有用户登录、权限、文档 ACL。
4. 没有生产级日志、监控、告警。
5. 没有真实 PDF / Word / 表格解析。
6. 没有自动化测试体系。
7. DashScope rerank 是外部 API，会有网络延迟和调用成本。
8. `/ask` 与 `/ask_langchain` 两条链路并存，最新能力主要在 `/ask_langchain`。

---

## 14. 项目亮点

可以在简历 / 面试中提炼为：

1. 实现 FastAPI + RAG 企业知识库问答后端。
2. 支持 SQLite 多轮会话持久化。
3. 使用明显 chat 规则 + Semantic Router + LLM Router Fallback 做 chat/rag 分流。
4. 使用 Query Rewrite 提升多轮短追问检索稳定性。
5. 使用 FAISS + BM25 + RRF 实现混合检索。
6. 使用 DashScope qwen3-rerank 进行检索后重排。
7. 使用双阈值 + 分差限制平衡主资料召回与补充资料过滤。
8. 增加金额区间冲突过滤，解决报销区间类资料噪音问题。
9. 使用 low_confidence 避免弱相关资料硬答。
10. 使用 LangChain 增量接入最终回答链。
11. 增加启动时索引自动检查与自动重建机制。
12. 返回完整 debug 字段，便于解释路由、检索、重排过程。

---

## 15. 项目表达

```text
我做了一个基于 FastAPI 的 RAG 企业知识库问答后端项目。它不是简单调用大模型 API，而是完整实现了从用户请求进入、chat/rag 分流、多轮历史管理、Query Rewrite、混合检索、reranker 重排到最终回答的链路。

项目里我用 SQLite 做最小会话持久化，用 route_context 和 retrieval_query 区分路由输入和检索输入。检索部分采用 FAISS + BM25 双轨召回，并用 RRF 做融合排序。

Router 方面，我先用明显 chat 规则处理问候和礼貌收尾，再用小样本 Embedding Semantic Router 做高置信分流；当 Semantic Router 不确定时，再调用 LLM Router fallback 判断 chat/rag，而不是所有请求都调用大模型。

Reranker 方面，我最早用 LLM Reranker 验证重排逻辑，后续接入阿里云百炼 qwen3-rerank。接入后我发现专门 rerank API 更偏语义相关性排序，对金额区间这类精确业务条件仍然需要后处理，所以增加了双阈值、分差限制和金额区间冲突过滤。

现在系统既能保留核心资料，又能过滤同主题但金额区间不匹配的噪音资料。如果所有资料相关性都不足，就返回 low_confidence，避免基于弱相关资料硬答。
```

---

## 16. 一句话总结

```text
这是一个基于 FastAPI 的企业知识库 RAG 问答后端项目，已实现明显 chat 规则兜底、Semantic Router、LLM Router Fallback、SQLite 多轮会话、Query Rewrite、FAISS + BM25 + RRF 混合检索、DashScope qwen3-rerank 检索后重排、双阈值与分差过滤、金额区间冲突过滤、low_confidence 低相关资料保护、启动时索引自动检查 / 自动重建、LangChain 增量接入和调试可解释化链路，可用于展示 AI 应用开发 / 大模型应用开发中的 RAG 工程实践能力。
```
