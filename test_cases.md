# 企业知识库 RAG 项目测试样本表

> 说明：
> - 本表用于沉淀企业员工手册 / 制度文档 RAG 项目的核心测试样本。
> - 当前推荐测试接口：`POST /ask_langchain`
> - 当前版本已升级：
>   - 关键词兜底 → LLM Router Fallback
>   - LLM Reranker → DashScope qwen3-rerank
>   - 单一 rerank 阈值 → 主资料阈值 + 补充资料阈值 + 分差限制
>   - 新增金额区间冲突过滤：low / middle / high
>   - 全低分资料不强行保留 → low_confidence
>   - route_context 只保留 user 历史
>   - 新增 LLM Provider 切换：DeepSeek 云端模型 / Ollama 本地模型
>   - 新增 answer 模型来源 debug 字段

---

# 1. 测试前准备

## 1.1 推荐接口

```text
POST /ask_langchain
```

## 1.2 请求格式

```json
{
  "question": "事假怎么请？",
  "session_id": "company_test_001"
}
```

## 1.3 通用观察字段

```text
success
message
data.question
data.intent
data.embedding_model
data.framework
data.retriever_status
data.answer
data.answer_source
data.answer_llm_provider
data.answer_llm_model
data.answer_llm_is_local
data.retrieval_query
data.reference_text
data.used_chunk_count
data.history_messages
data.used_chunks_debug
data.intent_debug
error
```

---

# 2. 核心测试样本（C001-C018）

| case_id | 模块 | session_id | 历史前置 | 当前问题 | 预期 intent / 状态 | 预期关键点 | 建议重点观察 | 是否通过 | 备注 |
|---|---|---|---|---|---|---|---|---|---|
| C001 | 明显 chat 规则兜底 | `company_c001` | 无 | 你好 | chat | 新会话问候不应进入 RAG | `intent=chat`；不应返回 `reference_text` | 是 | 验证基础 chat 规则。 |
| C002 | chat 历史上下文 | `company_c002` | 你好我是橘子 | 我叫什么名字 | chat | 应基于历史回答“橘子” | `history_messages`、`answer` | 是 | 验证普通聊天多轮能力。 |
| C003 | SQLite 持久化 | `company_c003` | 1）你好我是橘子；2）服务重启 | 我叫什么名字 | chat | 重启后仍能答出“橘子” | 是否证明历史来自 SQLite | 是 | 验证 SQLite 最小持久化。 |
| C004 | 制度问题进入 RAG | `company_c004` | 无 | 事假怎么请？ | rag / matched | 应命中事假条款，不能因为高阈值误伤成 low_confidence | `reference_text`、`used_chunks_debug.rerank_score` | 是 | 验证主资料阈值 60 的价值。 |
| C005 | 金额区间：500元及以下 | `company_c005` | 无 | 报销500元以下谁审批？ | rag / matched | 只保留 500元及以下 条款 | `reference_text` 不应包含 500-2000 / 超过2000 | 是 | 金额区间 low。 |
| C006 | 金额区间：500-2000元 | `company_c006` | 无 | 报销500到2000元怎么审批？ | rag / matched | 只保留 500元以上且不超过2000元 条款 | `reference_text` 不应包含 500元及以下 / 超过2000 | 是 | 金额区间 middle，重点回归。 |
| C007 | 金额区间：超过2000元 | `company_c007` | 无 | 报销金额超过2000元怎么审批？ | rag / matched | 只保留超过2000元条款 | `reference_text` 不应包含 500元及以下 / 500-2000 | 是 | 金额区间 high。 |
| C008 | 多轮 Query Rewrite | `company_c008` | 报销500到2000元怎么审批？ | 那再高一点呢？ | rag / matched | retrieval_query 应改写为超过2000元审批问题 | `retrieval_query`、`reference_text` | 是 | 多轮 RAG 关键样本。 |
| C009 | route_context / retrieval_query 分层 | `company_c009` | 报销500到2000元怎么审批？ | 那再高一点呢？ | rag / matched | 路由用 user 历史，检索用 LLM 改写问题 | `intent_debug`、`retrieval_query` | 是 | 验证链路设计。 |
| C010 | FAISS + BM25 + RRF | `company_c010` | 无 | 报销500元以下谁审批？ | rag / matched | 双轨检索返回调试字段 | `faiss_score`、`bm25_score`、`rrf_score`、`source` | 是 | 验证混合检索。 |
| C011 | 无历史模糊问题 | `company_c011` | 无 | 这个情况应该怎么处理？ | chat | LLM Router Fallback 应判 chat 并追问补充 | `route_strategy=llm_fallback_chat`、`fallback_used`、`llm_router_debug` | 是 | 路由层保底。 |
| C012 | 低相关资料保护 | `company_c012` | 无 | 公司年终奖发放规则是什么？ | rag / low_confidence | 明确像制度问题，但资料不足，不硬答 | `retriever_status=low_confidence`、`used_chunk_count=0`、`answer_source=system_fallback` | 是 | 检索层保底。 |
| C013 | 知识库未覆盖不胡编 | `company_c013` | 无 | 怎么提公司职位？ | rag / matched 或 low_confidence | 不应给通用晋升建议，不编造内部流程 | `answer`、`reference_text`、`retriever_status` | 是 | 回归测试，不一定适合现场演示。 |
| C014 | 调试能力 / 可解释性 | `company_c014` | 无 | 怎么请假？ | rag / matched | 返回路由、检索、重排调试字段 | `intent_debug`、`used_chunks_debug` | 是 | 面试展示价值高。 |
| C015 | answer 模型来源字段 | `company_c015` | 无 | 事假怎么请？ | rag / matched | 返回最终 answer 模型来源 | `answer_source`、`answer_llm_provider`、`answer_llm_model`、`answer_llm_is_local` | 是 | 新增模型来源 debug。 |
| C016 | Ollama 本地模型回答 | `company_c016` | `.env: LLM_PROVIDER=ollama` | 事假怎么请？ | rag / matched | 最终回答模型应为本地 Ollama | `answer_source=ollama_local_model`、`answer_llm_is_local=true` | 是 | 本地模型模式。 |
| C017 | DeepSeek 云端模型回答 | `company_c017` | `.env: LLM_PROVIDER=deepseek` | 事假怎么请？ | rag / matched | 最终回答模型应为 DeepSeek | `answer_source=deepseek_api`、`answer_llm_is_local=false` | 是 | 云端模型模式。 |
| C018 | low_confidence 模型来源 | `company_c018` | 无 | 公司年终奖发放规则是什么？ | rag / low_confidence | 系统兜底答案不是模型生成 | `answer_source=system_fallback`、`answer_llm_provider=null` | 是 | 新增严谨性测试。 |

---

# 3. Router 专项测试（R001-R010）

| case_id | 模块 | session_id | 历史前置 | 当前问题 | 预期 intent | 预期关键点 | 建议重点观察 | 是否通过 | 备注 |
|---|---|---|---|---|---|---|---|---|---|
| R001 | 明显 chat | `company_r001` | 无 | 你好 | chat | 不进入 RAG | `intent` | 是 | 问候。 |
| R002 | 普通学习建议 | `company_r002` | 无 | 我今天有点焦虑，应该怎么调整学习节奏？ | chat | 不查员工手册 | `intent_debug` | 是 | 学习陪伴类。 |
| R003 | 明确制度问题 | `company_r003` | 无 | 事假怎么请？ | rag | 高置信语义判为 RAG | `route_strategy=semantic_clear_rag` | 是 | 制度问答。 |
| R004 | 普通面试建议 | `company_r004` | 无 | 我该怎么准备 AI 应用开发岗位面试？ | chat | 不误进员工手册 | `intent`、`intent_debug` | 是 | 职业建议。 |
| R005 | “流程”泛化误判修复 | `company_r005` | 无 | 学习 RAG 项目的流程应该怎么安排？ | chat | 学习流程不是公司制度流程 | `route_strategy` | 是 | 旧版曾误判。 |
| R006 | 多轮报销追问 | `company_r006` | 报销500到2000元怎么审批？ | 那再高一点呢？ | rag | 根据 user 历史判断仍为 RAG | `retrieval_query` | 是 | 多轮检索。 |
| R007 | 多轮请假切换 | `company_r007` | 病假超过1天需要什么？ | 那事假呢？ | rag | 应切换到事假资料 | `retrieval_query`、`reference_text` | 是 | 制度类型切换。 |
| R008 | RAG 后礼貌收尾 | `company_r008` | 事假怎么请？ | 好的，谢谢 | chat | 明显 chat 规则优先于历史 | `intent` | 是 | 礼貌收尾关键样本。 |
| R009 | LLM Router Fallback | `company_r009` | 无 | 这个情况应该怎么处理？ | chat | Semantic Router 不确定时触发 LLM Router | `llm_router_debug` | 是 | 路由层保底。 |
| R010 | 关键词仅作 debug | `company_r010` | 无 | 事假怎么请？ | rag | 关键词命中不等于关键词兜底 | `domain_keyword_detected`、`fallback_used`、`route_decision_source` | 是 | 关键词不再直接兜底。 |

---

# 4. DashScope Reranker 专项测试（D001-D009）

| case_id | 模块 | session_id | 当前问题 | 预期结果 | 重点观察 | 是否通过 | 备注 |
|---|---|---|---|---|---|---|---|
| D001 | API 连通性 | `company_d001` | 事假怎么请？ | qwen3-rerank 返回 index / relevance_score / usage | 本地测试脚本结果 | 是 | 验证百炼 rerank 可用。 |
| D002 | 主资料阈值 | `company_d002` | 事假怎么请？ | 至少保留一条事假核心资料，不误伤成 low_confidence | `rerank_score`、`used_chunk_count` | 是 | 防止统一高阈值误伤。 |
| D003 | 补充资料阈值 | `company_d003` | 报销金额超过2000元怎么审批？ | 第二条补充资料低于阈值时被过滤 | `used_chunks_debug` | 是 | 过滤弱相关补充资料。 |
| D004 | 分差限制 | `company_d004` | 报销金额超过2000元怎么审批？ | 如果第二条与第一名分差过大，应被过滤 | `rerank_score` 差值 | 是 | 处理同主题但不够核心资料。 |
| D005 | 金额区间 low | `company_d005` | 报销500元以下谁审批？ | 只保留 low 条款 | `reference_text` | 是 | 金额区间冲突过滤。 |
| D006 | 金额区间 middle | `company_d006` | 报销500到2000元怎么审批？ | 只保留 middle 条款 | `reference_text` | 是 | 最重要金额回归样本。 |
| D007 | 金额区间 high | `company_d007` | 报销金额超过2000元怎么审批？ | 只保留 high 条款 | `reference_text` | 是 | 金额区间冲突过滤。 |
| D008 | 多轮金额区间 | `company_d008` | 先问 500-2000，再问“那再高一点呢？” | 第二轮只保留 high 条款 | `retrieval_query`、`reference_text` | 是 | Query Rewrite + 金额过滤组合。 |
| D009 | 全低分保护 | `company_d009` | 公司年终奖发放规则是什么？ | 资料不足时 low_confidence | `retriever_status`、`answer_source=system_fallback` | 是 | 不硬答。 |

---

# 5. LLM Provider 切换专项测试（L001-L008）

> 目标：验证最终回答模型可以通过 `.env` 在 DeepSeek 云端模型和 Ollama 本地模型之间切换。

---

## L001：Ollama 本地模型普通 chat

### 配置

`.env`：

```env
LLM_PROVIDER=ollama
OLLAMA_MODEL=qwen3-4b-instruct-local
OLLAMA_BASE_URL=http://localhost:11434
```

修改 `.env` 后重启服务：

```powershell
uvicorn app.main:app --reload
```

### 请求

```json
{
  "question": "你好，请用一句话介绍 FastAPI",
  "session_id": "company_l001"
}
```

### 预期

```text
intent = chat
framework = langchain
answer_source = ollama_local_model
answer_llm_provider = ollama
answer_llm_model = qwen3-4b-instruct-local
answer_llm_is_local = true
```

### 是否通过

```text
是
```

---

## L002：Ollama 本地模型 RAG 问答

### 配置

`.env`：

```env
LLM_PROVIDER=ollama
```

### 请求

```json
{
  "question": "事假怎么请？",
  "session_id": "company_l002"
}
```

### 预期

```text
intent = rag
retriever_status = matched
reference_text 命中事假条款
answer_source = ollama_local_model
answer_llm_provider = ollama
answer_llm_is_local = true
```

### 是否通过

```text
是
```

---

## L003：DeepSeek 云端模型普通 chat

### 配置

`.env`：

```env
LLM_PROVIDER=deepseek
```

修改 `.env` 后需要重启服务。

### 请求

```json
{
  "question": "你好，请用一句话介绍 FastAPI",
  "session_id": "company_l003"
}
```

### 预期

```text
intent = chat
framework = langchain
answer_source = deepseek_api
answer_llm_provider = deepseek
answer_llm_model = deepseek-chat
answer_llm_is_local = false
```

### 是否通过

```text
是
```

---

## L004：DeepSeek 云端模型 RAG 问答

### 配置

`.env`：

```env
LLM_PROVIDER=deepseek
```

### 请求

```json
{
  "question": "事假怎么请？",
  "session_id": "company_l004"
}
```

### 预期

```text
intent = rag
retriever_status = matched
answer_source = deepseek_api
answer_llm_provider = deepseek
answer_llm_model = deepseek-chat
answer_llm_is_local = false
```

### 是否通过

```text
是
```

---

## L005：低相关资料时不显示为本地模型生成

### 配置

`.env`：

```env
LLM_PROVIDER=ollama
```

### 请求

```json
{
  "question": "公司年终奖发放规则是什么？",
  "session_id": "company_l005"
}
```

### 预期

```text
intent = rag
retriever_status = low_confidence
answer_source = system_fallback
answer_llm_provider = null
answer_llm_model = null
answer_llm_is_local = false
```

### 是否通过

```text
是
```

---

## L006：切换 `.env` 后必须重启服务

### 操作

1. `.env` 设置：

```env
LLM_PROVIDER=ollama
```

2. 启动服务并测试，确认返回：

```text
answer_llm_provider = ollama
```

3. 修改 `.env`：

```env
LLM_PROVIDER=deepseek
```

4. 不重启服务，直接请求。

5. 再 Ctrl + C 停止服务，重新启动后请求。

### 预期

```text
不重启服务时，可能仍然沿用旧配置。
重启服务后，LLM_PROVIDER 才稳定切换为 deepseek。
```

### 是否通过

```text
是
```

---

## L007：本地模型名错误

### 配置

`.env`：

```env
LLM_PROVIDER=ollama
OLLAMA_MODEL=wrong-model-name
```

### 请求

```json
{
  "question": "事假怎么请？",
  "session_id": "company_l007"
}
```

### 预期

```text
接口返回 error
控制台显示 Ollama model not found 或类似错误
```

### 是否通过

```text
可选
```

### 备注

该测试用于验证错误配置时是否容易定位问题，不建议现场演示。

---

## L008：模型来源字段现场演示

### 配置 A

```env
LLM_PROVIDER=ollama
```

请求：

```json
{
  "question": "怎么请事假？",
  "session_id": "company_l008_ollama"
}
```

预期：

```text
answer_llm_is_local = true
```

### 配置 B

```env
LLM_PROVIDER=deepseek
```

请求：

```json
{
  "question": "怎么请事假？",
  "session_id": "company_l008_deepseek"
}
```

预期：

```text
answer_llm_is_local = false
```

### 是否通过

```text
是
```

### 备注

这是最适合面试展示“云端 / 本地模型切换”的测试样本。

---

# 6. 推荐现场演示样本

面试现场建议少而精，优先演示：

```text
1. 事假怎么请？
   → 制度 RAG 基础能力

2. 报销500到2000元怎么审批？
   → 金额区间过滤 middle

3. 报销500到2000元怎么审批？ → 那再高一点呢？
   → Query Rewrite + 金额区间过滤 high

4. 这个情况应该怎么处理？
   → LLM Router Fallback

5. 公司年终奖发放规则是什么？
   → low_confidence

6. LLM_PROVIDER=ollama / deepseek 分别请求“事假怎么请？”
   → 展示 answer_llm_is_local true / false
```

---

# 7. 当前测试结论

当前企业知识库 RAG 项目已经验证：

1. chat/rag 分流稳定。
2. 明显 chat 规则可以避免问候、感谢、礼貌收尾误入 RAG。
3. SQLite 多轮历史持久化有效。
4. Query Rewrite 能处理短追问。
5. route_context 和 retrieval_query 分层有效。
6. FAISS + BM25 + RRF 混合检索正常工作。
7. DashScope qwen3-rerank 已接入。
8. Reranker 后处理已从单一阈值升级为主阈值 + 补充阈值 + 分差限制。
9. 报销金额区间已增加 low / middle / high 冲突过滤。
10. LLM Router Fallback 能处理语义不明确问题。
11. low_confidence 能避免弱相关资料硬答。
12. `/ask_langchain` 能返回路由、检索、重排和模型来源 debug 字段。
13. DeepSeek 云端模型模式可用。
14. Ollama 本地模型模式可用。
15. `.env` 可控制最终回答模型来源。
16. 本地模型与云端模型可以在不修改业务代码的情况下切换。

---

# 8. 当前测试注意事项

## 8.1 修改 `.env` 后要重启服务

修改：

```env
LLM_PROVIDER=ollama
```

或：

```env
LLM_PROVIDER=deepseek
```

后，建议：

```text
Ctrl + C 停止 uvicorn
重新执行 uvicorn app.main:app --reload
```

原因：

```text
.env 配置在 Python 进程启动时读取。
只修改 .env 不一定触发稳定重载。
```

---

## 8.2 不要把“本地模型模式”说成“全链路本地化”

当前本地化的是：

```text
最终 answer 生成模型
```

仍然可能使用云端的部分：

```text
DashScope Embedding
DashScope qwen3-rerank
DeepSeek Query Rewrite
DeepSeek LLM Router Fallback
```

准确表达：

```text
项目支持最终回答模型在 DeepSeek 云端模型和 Ollama 本地模型之间切换。
```

不准确表达：

```text
项目已经全链路本地化。
```

---

## 8.3 本地模型效果需要看模型版本

当前推荐使用：

```text
qwen3-4b-instruct-local
```

原因：

```text
Instruct / non-thinking 版本更适合普通问答和 RAG 最终回答。
```

不建议用默认 thinking 版本做最终演示，因为可能出现：

```text
输出 <think>
回答后继续续写
停止符不稳定
```

---

# 9. 项目表达版本

```text
我为这个 RAG 项目沉淀了 test_cases，不只是功能跑通，而是覆盖了 chat/rag 分流、多轮 Query Rewrite、SQLite 历史、FAISS + BM25 + RRF 混合检索、DashScope qwen3-rerank、LLM Router fallback、low_confidence 低相关资料保护，以及金额区间业务规则过滤。

接入 qwen3-rerank 后，我发现专门 rerank API 更偏语义相关性排序，对“报销金额区间”这类精确业务条件仍可能把同主题但区间不匹配的条款打高分。于是我增加了主资料阈值、补充资料阈值、分差限制，以及 low / middle / high 金额区间冲突过滤，避免 500元及以下、500-2000元、超过2000元条款互相污染 reference_text。

后续我又补充了本地模型部署与切换测试。项目通过 .env 中的 LLM_PROVIDER 控制最终回答模型来源，可以在 DeepSeek 云端模型和 Ollama 本地模型之间切换。接口返回中增加 answer_llm_provider、answer_llm_model、answer_llm_is_local 等字段，方便直观看出当前 answer 是由云端模型还是本地模型生成。
```