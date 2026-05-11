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

---

# 1. 核心测试样本（C001-C014）

| case_id | 模块 | session_id | 历史前置 | 当前问题 | 预期 intent / 状态 | 预期关键点 | 建议重点观察 | 是否通过 | 备注 |
|---|---|---|---|---|---|---|---|---|---|
| C001 | 明显 chat 规则兜底 | `company_c001` | 无 | 你好 | chat | 新会话问候不应进入 RAG | `intent` 是否为 `chat`；是否无 `reference_text` | 是 | 验证基础 chat 规则。 |
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
| C012 | 低相关资料保护 | `company_c012` | 无 | 公司年终奖发放规则是什么？ | rag / low_confidence | 明确像制度问题，但资料不足，不硬答 | `retriever_status=low_confidence`、`used_chunk_count=0` | 是 | 检索层保底。 |
| C013 | 知识库未覆盖不胡编 | `company_c013` | 无 | 怎么提公司职位？ | rag / matched 或 low_confidence | 不应给通用晋升建议，不编造内部流程 | `answer`、`reference_text`、`retriever_status` | 是 | 回归测试，不一定适合现场演示。 |
| C014 | 调试能力 / 可解释性 | `company_c014` | 无 | 怎么请假？ | rag / matched | 返回路由、检索、重排调试字段 | `intent_debug`、`used_chunks_debug` | 是 | 面试展示价值高。 |

---

# 2. Router 专项测试（R001-R010）

| case_id | 模块 | session_id | 历史前置 | 当前问题 | 预期 intent | 预期关键点 | 建议重点观察 | 是否通过 | 备注 |
|---|---|---|---|---|---|---|---|---|---|
| R001 | 明显 chat | `company_r001` | 无 | 你好 | chat | 不进入 RAG | `intent` | 是 | 问候。 |
| R002 | 普通学习建议 | `company_r002` | 无 | 我今天有点焦虑，应该怎么调整学习节奏？ | chat | 不查员工手册 | `intent_debug` | 是 | 学习陪伴类。 |
| R003 | 明确制度问题 | `company_r003` | 无 | 事假怎么请？ | rag | 高置信语义判为 RAG | `route_strategy=semantic_clear_rag` | 是 | 制度问答。 |
| R004 | 普通面试建议 | `company_r004` | 无 | 我该怎么准备AI应用开发岗位面试？ | chat | 不误进员工手册 | `intent`、`intent_debug` | 是 | 职业建议。 |
| R005 | “流程”泛化误判修复 | `company_r005` | 无 | 学习RAG项目的流程应该怎么安排？ | chat | 学习流程不是公司制度流程 | `route_strategy` | 是 | 旧版曾误判。 |
| R006 | 多轮报销追问 | `company_r006` | 报销500到2000元怎么审批？ | 那再高一点呢？ | rag | 根据 user 历史判断仍为 RAG | `retrieval_query` | 是 | 多轮检索。 |
| R007 | 多轮请假切换 | `company_r007` | 病假超过1天需要什么？ | 那事假呢？ | rag | 应切换到事假资料 | `retrieval_query`、`reference_text` | 是 | 制度类型切换。 |
| R008 | RAG 后礼貌收尾 | `company_r008` | 事假怎么请？ | 好的，谢谢 | chat | 明显 chat 规则优先于历史 | `intent` | 是 | 礼貌收尾关键样本。 |
| R009 | LLM Router Fallback | `company_r009` | 无 | 这个情况应该怎么处理？ | chat | Semantic Router 不确定时触发 LLM Router | `llm_router_debug` | 是 | 路由层保底。 |
| R010 | 关键词仅作 debug | `company_r010` | 无 | 事假怎么请？ | rag | 关键词命中不等于关键词兜底 | `domain_keyword_detected`、`fallback_used`、`route_decision_source` | 是 | 关键词不再直接兜底。 |

---

# 3. DashScope Reranker 专项测试（D001-D009）

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
| D009 | 全低分保护 | `company_d009` | 公司年终奖发放规则是什么？ | 资料不足时 low_confidence | `retriever_status` | 是 | 不硬答。 |

---

# 4. 推荐现场演示样本

面试现场建议少而精，优先演示：

```text
1. 事假怎么请？                            → 制度 RAG 基础能力
2. 报销500到2000元怎么审批？                → 金额区间过滤 middle
3. 报销500到2000元怎么审批？→那再高一点呢？  → Query Rewrite + 金额区间过滤 high
4. 这个情况应该怎么处理？                   → LLM Router Fallback
5. 公司年终奖发放规则是什么？                → low_confidence
```

---

# 5. 当前测试结论

当前企业知识库 RAG 项目已经验证：

1. chat/rag 分流稳定。
2. 多轮历史和 SQLite 持久化有效。
3. Query Rewrite 能处理短追问。
4. FAISS + BM25 + RRF 混合检索正常工作。
5. DashScope qwen3-rerank 已接入。
6. Reranker 后处理已从单一阈值升级为主阈值 + 补充阈值 + 分差限制。
7. 报销金额区间已增加 low / middle / high 冲突过滤。
8. LLM Router Fallback 能处理语义不明确问题。
9. low_confidence 能避免弱相关资料硬答。
10. 调试字段能解释路由、检索、重排过程。

---

# 6. 项目表达

```text
我为这个 RAG 项目沉淀了 test_cases，不只是功能跑通，而是覆盖了 chat/rag 分流、多轮 Query Rewrite、SQLite 历史、FAISS + BM25 + RRF 混合检索、DashScope qwen3-rerank、LLM Router fallback、low_confidence 低相关资料保护，以及金额区间业务规则过滤。

接入 qwen3-rerank 后，我发现专门 rerank API 更偏语义相关性排序，对“报销金额区间”这类精确业务条件仍可能把同主题但区间不匹配的条款打高分。于是我增加了主资料阈值、补充资料阈值、分差限制，以及 low / middle / high 金额区间冲突过滤，避免 500元及以下、500-2000元、超过2000元条款互相污染 reference_text。
```
