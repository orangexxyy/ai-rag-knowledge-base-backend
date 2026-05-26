# 企业知识库 RAG 项目测试样本表

> 说明：
> - 当前推荐测试接口：`POST /ask_langchain`
> - 当前项目已升级为资料目录入库模式：`KNOWLEDGE_DIR = data/raw_docs`
> - 当前已支持：txt + 文本型 PDF + Excel
> - PDF 已支持 page metadata
> - Excel 已支持 sheet_name / row_number metadata
> - Document Chunker 已支持：
>   - `policy_clause`：通用“xxx制度条款A/B/C”条款级切分
>   - `paragraph_then_overlap`：通用段落 + overlap 切分
> - 当前最终回答模型可通过 `.env` 切换：DeepSeek / Ollama

---

## 1. 测试前准备

### 1.1 推荐接口

```text
POST /ask_langchain
```

### 1.2 资料目录

建议测试目录：

```text
data/raw_docs/
├─ knowledge.txt
├─ employee_handbook_sample.pdf
├─ it_support_policy_sample.pdf
├─ permission_matrix_sample.xlsx
```

### 1.3 重建索引

修改资料、Loader、Processor、Chunker、Router 样本、metadata 结构或版本号后，按需执行：

```powershell
python -c "from app.index_manager import build_and_save_chunk_index; build_and_save_chunk_index()"
```

或者调用：

```text
POST /rebuild_index
```

注意：

```text
如果通过命令行重建索引，已经启动的 uvicorn 服务可能仍然使用旧的 app.state。
测试阶段建议：重建索引后重启服务，或使用 POST /rebuild_index。
```

### 1.4 通用观察字段

```text
data.intent
data.retriever_status
data.answer
data.retrieval_query
data.reference_text
data.used_chunk_count
data.used_chunks_debug
data.used_chunks_debug[].metadata.source_file
data.used_chunks_debug[].metadata.file_type
data.used_chunks_debug[].metadata.page
data.used_chunks_debug[].metadata.sheet_name
data.used_chunks_debug[].metadata.row_number
data.used_chunks_debug[].metadata.chunk_strategy
data.used_chunks_debug[].faiss_score
data.used_chunks_debug[].bm25_score
data.used_chunks_debug[].rrf_score
data.used_chunks_debug[].rerank_score
data.intent_debug
data.answer_source
data.answer_llm_provider
data.answer_llm_model
data.answer_llm_is_local
```

---

## 2. 核心测试样本（C001-C030）

| case_id | 模块 | session_id | 当前问题 | 预期 intent / 状态 | 预期关键点 | 建议重点观察 | 是否通过 | 备注 |
|---|---|---|---|---|---|---|---|---|
| C001 | 明显 chat | `company_c001` | 你好 | chat | 不进入 RAG | `intent=chat` | 是 | 问候测试 |
| C002 | chat 历史 | `company_c002` | 我叫什么名字？ | chat | 能基于历史回答 | `history_messages` | 是 | 需先写入“我是橘子” |
| C003 | SQLite 持久化 | `company_c003` | 我叫什么名字？ | chat | 服务重启后历史仍存在 | SQLite 历史 | 是 | 多轮持久化 |
| C004 | 制度 RAG | `company_c004` | 事假怎么申请？ | rag / matched | 命中事假条款 | `reference_text`、`chunk_strategy` | 是 | PDF / txt 均可能命中 |
| C005 | 金额区间 low | `company_c005` | 报销500元以下谁审批？ | rag / matched | 只保留 low 条款 | `reference_text` | 是 | 金额区间过滤 |
| C006 | 金额区间 middle | `company_c006` | 报销500到2000元怎么审批？ | rag / matched | 只保留 middle 条款 | `reference_text` | 是 | 重点回归 |
| C007 | 金额区间 high | `company_c007` | 报销金额超过2000元怎么审批？ | rag / matched | 只保留 high 条款 | `reference_text` | 是 | 金额区间过滤 |
| C008 | 多轮 Query Rewrite | `company_c008` | 那再高一点呢？ | rag / matched | 应改写为超过2000元审批 | `retrieval_query` | 是 | 前置问题：500-2000 |
| C009 | route_context / retrieval_query 分层 | `company_c009` | 那再高一点呢？ | rag / matched | 路由和检索职责分离 | `intent_debug`、`retrieval_query` | 是 | 前置问题：500-2000 |
| C010 | 混合检索 | `company_c010` | 报销500元以下谁审批？ | rag / matched | FAISS + BM25 + RRF | `source`、`rrf_score` | 是 | 双轨召回 |
| C011 | 模糊问题 | `company_c011` | 这个情况应该怎么处理？ | chat | 不强行查知识库 | `intent_debug` | 是 | LLM Router Fallback |
| C012 | low_confidence | `company_c012` | 公司年终奖发放规则是什么？ | rag / low_confidence | 资料不足不硬答 | `answer_source=system_fallback` | 是 | 防胡编 |
| C013 | 未覆盖制度 | `company_c013` | 怎么提公司职位？ | rag / matched 或 low_confidence | 不编造内部流程 | `answer`、`reference_text` | 是 | 回归测试 |
| C014 | debug 可解释性 | `company_c014` | 怎么请假？ | rag / matched | 返回路由、检索、重排 debug | `intent_debug`、`used_chunks_debug` | 是 | 面试展示 |
| C015 | 模型来源字段 | `company_c015` | 事假怎么申请？ | rag / matched | 返回 answer 模型来源 | `answer_llm_provider` | 是 | 模型来源 |
| C016 | Ollama 模式 | `company_c016` | 事假怎么申请？ | rag / matched | 使用本地 Ollama 生成 answer | `answer_source=ollama_local_model` | 是 | `.env: LLM_PROVIDER=ollama` |
| C017 | DeepSeek 模式 | `company_c017` | 事假怎么申请？ | rag / matched | 使用 DeepSeek 生成 answer | `answer_source=deepseek_api` | 是 | `.env: LLM_PROVIDER=deepseek` |
| C018 | system_fallback 来源 | `company_c018` | 公司年终奖发放规则是什么？ | rag / low_confidence | 兜底答案不是模型生成 | `answer_llm_provider=null` | 是 | 严谨性测试 |
| C019 | PDF page 溯源 | `company_c019` | 事假怎么申请？ | rag / matched | 命中员工手册 PDF 第 2 页 | `file_type=pdf`、`page=2` | 是 | 可能也命中 txt，视资料重复情况 |
| C020 | PDF 条款级 chunk | `company_c020` | 事假怎么申请？ | rag / matched | reference_text 应只包含事假条款 | `chunk_strategy=policy_clause` | 是 | 验证 policy_clause |
| C021 | IT 支持 PDF | `company_c021` | VPN 权限怎么申请？ | rag / matched | 命中 it_support_policy_sample.pdf 第 2 页 | `source_file`、`page=2` | 是 | 不同内容 PDF |
| C022 | 通用制度条款识别 | `company_c022` | VPN 权限怎么申请？ | rag / matched | 应命中账号权限制度条款C | `chunk_strategy=policy_clause` | 是 | 正则已泛化 |
| C023 | PDF 第 1 页测试 | `company_c023` | 打印机故障应该怎么处理？ | rag / matched | 命中 IT 支持 PDF 第 1 页 | `source_file=it_support_policy_sample.pdf`、`page=1` | 是 | PDF page 测试 |
| C024 | PDF 第 3 页测试 | `company_c024` | 离职时办公设备怎么归还？ | rag / matched | 命中 IT 支持 PDF 第 3 页 | `source_file=it_support_policy_sample.pdf`、`page=3` | 是 | 资产归还测试 |
| C025 | Excel 培训报名表 | `company_c025` | 产品入门训练营报名截止是什么时候？ | rag / matched | 命中培训报名表第 2 行 | `file_type=xlsx`、`sheet_name`、`row_number` | 是 | Excel 核心测试 |
| C026 | Excel 会议室预约表 | `company_c026` | 星河会议室需要提前多久预约？ | rag / matched | 命中会议室预约表对应行 | `sheet_name=会议室预约表` | 是 | Excel row 检索 |
| C027 | Excel 办公用品领用表 | `company_c027` | 白板笔套装怎么领取？ | rag / matched | 命中办公用品领用表对应行 | `sheet_name=办公用品领用表` | 是 | Excel row 检索 |
| C028 | Excel Router 样本修复 | `company_c028` | 产品入门训练营报名截止是什么时候？ | rag / matched | 不应被误判为 chat | `intent_debug.route_strategy` | 是 | Router 与资料范围同步 |
| C029 | Excel metadata 溯源 | `company_c029` | 产品入门训练营负责人是谁？ | rag / matched | 返回 sheet_name / row_number | `used_chunks_debug[].metadata` | 是 | Excel 来源追溯 |
| C030 | 混合资料目录 | `company_c030` | 访客胸牌离场时需要怎么处理？ | rag / matched | 命中 Excel 办公用品或资源记录 | `source_file=permission_matrix_sample.xlsx` | 是 | 多类型资料共存 |

---

## 3. Document Ingestion 专项测试（I001-I015）

| case_id | 模块 | 测试方式 | 预期结果 | 重点观察 | 是否通过 | 备注 |
|---|---|---|---|---|---|---|
| I001 | txt Loader | `scripts/test_document_loader.py` | 读取 knowledge.txt 成 1 个 Document | `file_type=txt` | 是 | 单文件 txt |
| I002 | Processor | `scripts/test_document_processor.py` | 清洗后 Document 数量不变或过滤空 Document | 空格 / 空行处理 | 是 | 通用清洗 |
| I003 | Chunker | `scripts/test_document_chunker.py` | chunk_items 携带 metadata | `chunk_char_length` | 是 | chunk 不再是 list[str] |
| I004 | Index Builder metadata | `scripts/test_index_builder_metadata.py` | chunk_records 保存 metadata | `metadata.chunk_id` | 是 | metadata 入库 |
| I005 | PDF Loader | `scripts/test_pdf_loader.py` | PDF 每页生成 Document | `page=1/2/3` | 是 | 文本型 PDF |
| I006 | PDF 条款切分测试 | `scripts/test_pdf_clause_split.py` | 第 2 页切出 A/B/C/D | 条款数量 | 是 | 测试 policy_clause |
| I007 | 目录 Loader | `scripts/test_document_dir_loader.py` | txt + pdf + xlsx 合并为 list[Document] | Document 总数 | 是 | 批量扫描 |
| I008 | 正式目录建库 | 手动重建索引 | meta 记录 `knowledge_source_type=dir` | `knowledge_dir`、目录 hash | 是 | 正式链路 |
| I009 | PDF 专用规整 | 问 “事假怎么申请？” | `直属主\n管` 被规整为 `直属主管` | reference_text | 是 | 仅 PDF 专用处理 |
| I010 | 通用 policy_clause | 问 “VPN 权限怎么申请？” | 命中账号权限制度条款C | `chunk_strategy=policy_clause` | 是 | 泛化条款识别 |
| I011 | Excel Loader | `scripts/test_excel_loader.py` | Excel 行转 Document | `file_type=xlsx` | 是 | Excel 单测 |
| I012 | Excel sheet metadata | `scripts/test_excel_loader.py` | metadata 有 sheet_name | `sheet_name` | 是 | 工作表来源 |
| I013 | Excel row metadata | `scripts/test_excel_loader.py` | metadata 有 row_number | `row_number` | 是 | 原始行号 |
| I014 | Excel 目录 hash | 修改 / 新增 xlsx 后重建 | 目录 hash 变化 | `knowledge_hash_type=directory_sha256` | 是 | .xlsx 纳入 hash |
| I015 | Excel 正式 RAG | `/ask_langchain` | Excel 问题 matched | `source_file=permission_matrix_sample.xlsx` | 是 | 主链路测试 |

---

## 4. Router 专项测试（R001-R015）

| case_id | 模块 | session_id | 当前问题 | 预期 intent | 预期关键点 | 是否通过 |
|---|---|---|---|---|---|---|
| R001 | 明显 chat | `company_r001` | 你好 | chat | 不进入 RAG | 是 |
| R002 | 普通学习建议 | `company_r002` | 我今天有点焦虑，应该怎么调整学习节奏？ | chat | 不查员工手册 | 是 |
| R003 | 明确制度问题 | `company_r003` | 事假怎么申请？ | rag | 高置信判为 RAG | 是 |
| R004 | 普通面试建议 | `company_r004` | 我该怎么准备 AI 应用开发岗位面试？ | chat | 不误进知识库 | 是 |
| R005 | “流程”泛化误判修复 | `company_r005` | 学习 RAG 项目的流程应该怎么安排？ | chat | 学习流程不是公司制度流程 | 是 |
| R006 | 多轮报销追问 | `company_r006` | 那再高一点呢？ | rag | 根据历史判断仍为 RAG | 是 |
| R007 | 多轮请假切换 | `company_r007` | 那事假呢？ | rag | 应切换到事假资料 | 是 |
| R008 | RAG 后礼貌收尾 | `company_r008` | 好的，谢谢 | chat | 明显 chat 规则优先 | 是 |
| R009 | LLM Router Fallback | `company_r009` | 这个情况应该怎么处理？ | chat | 触发 fallback | 是 |
| R010 | 关键词仅作 debug | `company_r010` | 事假怎么申请？ | rag | 关键词不是直接兜底 | 是 |
| R011 | Excel 培训报名 | `company_r011` | 产品入门训练营报名截止是什么时候？ | rag | 不误判 chat | 是 |
| R012 | Excel 会议室预约 | `company_r012` | 星河会议室需要提前多久预约？ | rag | 表格型资料查询进入 RAG | 是 |
| R013 | Excel 办公用品 | `company_r013` | 白板笔套装怎么领取？ | rag | 表格型资料查询进入 RAG | 是 |
| R014 | Excel 表格负责人 | `company_r014` | 产品入门训练营负责人是谁？ | rag | 表格事实查询进入 RAG | 是 |
| R015 | 普通学习训练营问题 | `company_r015` | 我想参加 AI 训练营应该怎么选？ | chat | 不应因为“训练营”泛化误判 | 待测 | 防止过度 RAG |

---

## 5. Reranker 专项测试（D001-D010）

| case_id | 模块 | session_id | 当前问题 | 预期结果 | 重点观察 | 是否通过 |
|---|---|---|---|---|---|---|
| D001 | API 连通性 | `company_d001` | 事假怎么申请？ | qwen3-rerank 正常返回 | `rerank_score` | 是 |
| D002 | 主资料阈值 | `company_d002` | 事假怎么申请？ | 核心资料不被误伤 | `rerank_score >= 60` | 是 |
| D003 | 补充资料阈值 | `company_d003` | 报销金额超过2000元怎么审批？ | 弱相关补充资料过滤 | `used_chunks_debug` | 是 |
| D004 | 分差限制 | `company_d004` | 报销金额超过2000元怎么审批？ | 分差过大资料过滤 | `rerank_score` 差值 | 是 |
| D005 | 金额 low | `company_d005` | 报销500元以下谁审批？ | 只保留 low 条款 | `reference_text` | 是 |
| D006 | 金额 middle | `company_d006` | 报销500到2000元怎么审批？ | 只保留 middle 条款 | `reference_text` | 是 |
| D007 | 金额 high | `company_d007` | 报销金额超过2000元怎么审批？ | 只保留 high 条款 | `reference_text` | 是 |
| D008 | 多轮金额 | `company_d008` | 那再高一点呢？ | 只保留 high 条款 | `retrieval_query` | 是 |
| D009 | 全低分保护 | `company_d009` | 公司年终奖发放规则是什么？ | low_confidence | `answer_source=system_fallback` | 是 |
| D010 | Excel 行记录重排 | `company_d010` | 产品入门训练营报名截止是什么时候？ | Excel 行记录高分保留 | `rerank_score`、`sheet_name` | 是 |

---

## 6. LLM Provider 切换测试（L001-L008）

| case_id | 模块 | 配置 | 当前问题 | 预期结果 | 是否通过 |
|---|---|---|---|---|---|
| L001 | Ollama chat | `LLM_PROVIDER=ollama` | 你好，请用一句话介绍 FastAPI | `answer_source=ollama_local_model` | 是 |
| L002 | Ollama RAG | `LLM_PROVIDER=ollama` | 事假怎么申请？ | `answer_llm_is_local=true` | 是 |
| L003 | DeepSeek chat | `LLM_PROVIDER=deepseek` | 你好，请用一句话介绍 FastAPI | `answer_source=deepseek_api` | 是 |
| L004 | DeepSeek RAG | `LLM_PROVIDER=deepseek` | 事假怎么申请？ | `answer_llm_is_local=false` | 是 |
| L005 | low_confidence 来源 | `LLM_PROVIDER=ollama` | 公司年终奖发放规则是什么？ | `answer_source=system_fallback` | 是 |
| L006 | 切换配置重启 | ollama → deepseek | 任意问题 | 重启后配置生效 | 是 |
| L007 | 错误模型名 | `OLLAMA_MODEL=wrong-model-name` | 事假怎么申请？ | 返回错误，便于定位 | 可选 |
| L008 | 现场演示 | ollama / deepseek | 怎么请事假？ | 展示本地 / 云端切换 | 是 |

---

## 7. 推荐现场演示样本

建议面试现场少而精：

```text
1. 事假怎么申请？
   → 展示制度 RAG、policy_clause、metadata 来源追溯

2. VPN 权限怎么申请？
   → 展示不同内容 PDF、page=2、通用制度条款切分

3. 产品入门训练营报名截止是什么时候？
   → 展示 Excel sheet / row 溯源

4. 星河会议室需要提前多久预约？
   → 展示 Excel 表格行转 Document

5. 报销500到2000元怎么审批？ → 那再高一点呢？
   → 展示多轮 Query Rewrite

6. 公司年终奖发放规则是什么？
   → 展示 low_confidence 防胡编

7. LLM_PROVIDER=ollama / deepseek 分别请求同一个 RAG 问题
   → 展示最终回答模型来源切换
```

---

## 8. 当前测试结论

当前企业知识库 RAG 项目已经验证：

```text
1. chat/rag 分流稳定
2. SQLite 多轮历史有效
3. Query Rewrite 能处理短追问
4. FAISS + BM25 + RRF 混合检索正常
5. DashScope qwen3-rerank 正常
6. low_confidence 能避免资料不足时硬答
7. txt 文件可以进入 Document Pipeline
8. 文本型 PDF 可以按 page 进入 Document Pipeline
9. Excel 可以按 sheet / row 进入 Document Pipeline
10. 资料目录扫描可以同时读取 txt + pdf + xlsx
11. policy_clause 可以对通用“xxx制度条款A/B/C”结构做条款级切分
12. Excel 行记录可以通过 header + row 转成自然语言 Document
13. used_chunks_debug 可以追溯 source_file / file_type / page / sheet_name / row_number / chunk_strategy
14. DeepSeek / Ollama 最终回答模型切换正常
15. Router 样本需要随着知识库业务范围同步维护
```
