# 企业知识库 RAG 项目阶段测试结果记录（evaluation_v2）

> 测试日期：2026-05-26  
> 项目阶段：企业资料入库与预处理增强阶段  
> 当前目标：验证 `txt + 文本型 PDF + Excel` 是否能够统一进入 RAG 主链路，并在检索结果中保留来源追溯信息。  
> 说明：本文是阶段性人工测试结果整理，不等同于完整自动化测试报告。详细测试样本表见 `test_cases.md`。

---

## 1. 当前测试版本能力概览

当前项目已经从早期的单文件知识库模式：

```text
data/knowledge.txt
→ chunk
→ embedding
→ index
```

升级为资料目录入库模式：

```text
data/raw_docs/
├─ knowledge.txt
├─ employee_handbook_sample.pdf
├─ it_support_policy_sample.pdf
├─ permission_matrix_sample.xlsx
```

当前已验证的资料类型：

```text
txt
文本型 PDF
Excel .xlsx
```

当前已验证的主链路：

```text
资料目录
→ load_documents_from_dir()
→ txt / PDF / Excel Loader
→ list[Document]
→ process_documents()
→ chunk_documents()
→ build_chunk_records()
→ FAISS / BM25 / RRF
→ DashScope qwen3-rerank
→ LangChain RAG Chain
→ used_chunks_debug 返回来源与调试字段
```

---

## 2. 测试环境说明

当前测试主要通过：

```text
POST /ask_langchain
```

进行人工接口测试。

当前最终回答模型测试过：

```text
LLM_PROVIDER=ollama
```

返回中可观察字段包括：

```text
intent
retriever_status
answer
retrieval_query
reference_text
used_chunks_debug
used_chunks_debug[].metadata.source_file
used_chunks_debug[].metadata.file_type
used_chunks_debug[].metadata.page
used_chunks_debug[].metadata.sheet_name
used_chunks_debug[].metadata.row_number
used_chunks_debug[].metadata.chunk_strategy
faiss_score
bm25_score
rrf_score
rerank_score
intent_debug
answer_source
answer_llm_provider
answer_llm_model
answer_llm_is_local
```

---

## 3. 核心测试结果汇总

| case_id | 测试问题 | 测试目标 | 实际结果 | 关键证据 | 是否通过 |
|---|---|---|---|---|---|
| E001 | 事假怎么申请？ | 验证制度类资料问答、PDF / txt 命中、条款级 chunk | 成功回答事假申请规则 | `chunk_strategy=policy_clause`，可命中事假条款 | 是 |
| E002 | VPN 权限怎么申请？ | 验证不同内容 PDF 是否进入正式索引 | 成功命中 IT 支持 PDF 第 2 页 | `source_file=it_support_policy_sample.pdf`，`file_type=pdf`，`page=2` | 是 |
| E003 | VPN 权限怎么申请？ | 验证通用制度条款识别 | 泛化正则后，可命中 `账号权限制度条款C（VPN 申请）` | `chunk_strategy=policy_clause` | 是 |
| E004 | 产品入门训练营报名截止是什么时候？ | 验证 Excel 行记录能否被检索 | 成功回答“开课前3天” | `source_file=permission_matrix_sample.xlsx`，`sheet_name=培训报名表`，`row_number=2` | 是 |
| E005 | 星河会议室需要提前多久预约？ | 验证 Excel 会议室预约表 | 成功命中会议室预约表对应行 | `file_type=xlsx`，`sheet_name=会议室预约表` | 是 |
| E006 | 白板笔套装怎么领取？ | 验证 Excel 办公用品领用表 | 成功命中办公用品领用表对应行 | `file_type=xlsx`，`sheet_name=办公用品领用表` | 是 |
| E007 | 产品入门训练营报名截止是什么时候？ | 验证 Router 对 Excel 表格型问题的分流 | 补充 Router 样本后稳定进入 RAG | `intent=rag`，不再误判为 chat | 是 |
| E008 | 公司年终奖发放规则是什么？ | 验证 low_confidence 防胡编 | 资料不足时不硬答 | `retriever_status=low_confidence`，`answer_source=system_fallback` | 是 |
| E009 | 报销500到2000元怎么审批？ | 验证金额区间检索与过滤 | 成功命中 middle 区间报销条款 | `reference_text` 聚焦 500-2000 元区间 | 是 |
| E010 | 报销500到2000元怎么审批？ → 那再高一点呢？ | 验证多轮 Query Rewrite | 短追问可改写为更高金额审批问题 | `retrieval_query` 指向超过 2000 元审批 | 是 |

---

## 4. 典型测试结果摘要

### 4.1 Excel：培训报名表命中测试

测试问题：

```text
产品入门训练营报名截止是什么时候？
```

实际回答摘要：

```text
产品入门训练营的报名截止时间是开课前3天。
```

实际命中的参考资料：

```text
培训报名表记录：培训名称：产品入门训练营；适用对象：入职30天内的新员工；报名条件：完成入职资料确认并通过基础业务测验；报名截止：开课前3天；负责人：培训专员；培训形式：线下集中培训；记录要求：签到记录和课后小测需归档；备注：缺席需参加下一期补训。
```

关键 metadata：

```json
{
  "source_file": "permission_matrix_sample.xlsx",
  "file_type": "xlsx",
  "sheet_name": "培训报名表",
  "row_number": 2,
  "chunk_strategy": "paragraph_then_overlap"
}
```

测试结论：

```text
Excel 文件已经正式进入 RAG 主链路。
系统可以从 Excel 行记录中检索到答案，并追溯到具体 sheet 和 row。
```

---

### 4.2 PDF：VPN 权限申请测试

测试问题：

```text
VPN 权限怎么申请？
```

实际测试结论：

```text
系统可以命中 it_support_policy_sample.pdf 第 2 页的账号权限制度内容。
通用 policy_clause 正则泛化后，可识别“账号权限制度条款C（VPN 申请）”这类非请假 / 非报销制度条款。
```

关键 metadata 预期：

```json
{
  "source_file": "it_support_policy_sample.pdf",
  "file_type": "pdf",
  "page": 2,
  "chunk_strategy": "policy_clause"
}
```

测试结论：

```text
文本型 PDF 的 page metadata、PDF 断行规整、通用制度条款切分均已生效。
```

---

### 4.3 Router：Excel 表格型问题误判修复

曾出现的问题：

```text
产品入门训练营报名截止是什么时候？
```

一开始曾被 Router 判断为：

```text
intent = chat
route_strategy = semantic_clear_chat
```

原因分析：

```text
原始 Router 样本主要覆盖请假、报销、员工手册、医药 SOP 等问题。
接入 Excel 后，新增了“培训报名、会议室预约、办公用品领用”等表格型企业资料问题。
这些问题的问法没有被旧 RAG_EXAMPLES 和 RAG_DOMAIN_KEYWORDS 覆盖。
```

修复方式：

```text
补充 Excel 场景的 RAG_EXAMPLES 和 RAG_DOMAIN_KEYWORDS。
例如：
- 产品入门训练营报名截止是什么时候
- 星河会议室需要提前多久预约
- 白板笔套装怎么领取
- 培训报名
- 会议室预约
- 办公用品领用
- 报名截止
```

修复后结果：

```text
Excel 表格型事实查询可以稳定进入 RAG。
```

测试结论：

```text
Router 不是根据文件格式分流，而是根据“问题是否属于知识库范围”分流。
当知识库业务范围变化时，Router 样本也需要同步维护。
```

---

## 5. Document Ingestion 专项测试记录

### 5.1 txt Loader

测试内容：

```text
读取 knowledge.txt
```

结果：

```text
txt 文件可生成 Document。
metadata.file_type = txt
metadata.page = None
metadata.sheet_name = None
metadata.row_number = None
```

测试结论：

```text
txt 线性文本读取正常。
```

---

### 5.2 PDF Loader

测试内容：

```text
读取 employee_handbook_sample.pdf / it_support_policy_sample.pdf
```

结果：

```text
文本型 PDF 可按 page 生成多个 Document。
metadata.file_type = pdf
metadata.page = 1 / 2 / 3 ...
```

测试结论：

```text
PDF page 级溯源正常。
```

---

### 5.3 Excel Loader

测试内容：

```text
读取 permission_matrix_sample.xlsx
```

结果：

```text
Excel Loader 测试开始
读取到 Document 数量：15
清洗后 Document 数量：15
生成 chunk_items 数量：15
```

其中一条 Document 示例：

```text
会议室预约表记录：资源名称：星河会议室；资源类型：大型会议室；容纳人数：18；适用场景：月度经营复盘、跨部门评审、项目里程碑会议；可预约时段：工作日 09:00-18:00；预约提前量：至少提前2个工作日；审批人：行政前台；取消规则：会议开始前4小时可取消；备注：使用后需恢复桌椅并关闭投影设备。
```

关键 metadata：

```json
{
  "source_file": "permission_matrix_sample.xlsx",
  "file_type": "xlsx",
  "sheet_name": "会议室预约表",
  "row_number": 2
}
```

测试结论：

```text
Excel 已按 sheet / row 转成自然语言 Document，并保留 sheet_name / row_number。
```

---

## 6. 当前已验证的工程能力

当前阶段已验证：

```text
1. 资料目录扫描支持 txt / pdf / xlsx
2. txt 可以作为线性文本进入 Document Pipeline
3. 文本型 PDF 可以按 page 进入 Document Pipeline
4. Excel 可以按 sheet / row 进入 Document Pipeline
5. Document Processor 可以统一清洗文本，并跳过清洗后为空的 Document
6. Document Chunker 可以根据内容结构选择 policy_clause 或 paragraph_then_overlap
7. PDF 专用断行规整只在 file_type=pdf 时生效，避免影响 txt / Excel
8. Excel 行记录可以通过 header + row 转为自然语言文本
9. chunk_records 保存 text + embedding + metadata
10. used_chunks_debug 可以追溯 source_file / file_type / page / sheet_name / row_number / chunk_strategy
11. Router 样本可随知识库资料范围扩展而维护
12. low_confidence 可避免资料不足时硬答
```

---

## 7. 当前发现过的问题与处理

### 7.1 PDF 抽取后条款混在同一页

问题：

```text
PDF 第 2 页中年假、病假、事假、调休假多个条款被放在同一个 page Document 中。
如果直接按段落或固定长度 chunk，可能导致检索结果不够聚焦。
```

处理：

```text
增加 policy_clause 策略，识别“xxx制度条款A/B/C”结构，按条款边界切分。
```

结果：

```text
“事假怎么申请？”可以命中独立事假条款。
```

---

### 7.2 IT 支持 PDF 没有走 policy_clause

问题：

```text
早期 policy_clause 只识别请假制度和差旅报销制度，导致“账号权限制度条款C（VPN 申请）”无法按条款切分。
```

处理：

```text
将正则泛化为通用“xxx制度条款A（xxx）”结构。
```

结果：

```text
VPN 权限申请可以命中独立账号权限条款。
```

---

### 7.3 Excel 问题被 Router 误判为 chat

问题：

```text
“产品入门训练营报名截止是什么时候？”曾被判断为 chat。
```

处理：

```text
补充 Excel / 表格型资料相关 RAG_EXAMPLES 和 RAG_DOMAIN_KEYWORDS。
```

结果：

```text
Excel 表格型事实查询可稳定进入 RAG。
```

---

### 7.4 命令行重建索引后服务可能仍使用旧内存索引

问题：

```text
命令行执行 build_and_save_chunk_index() 只更新磁盘索引文件。
如果 uvicorn 服务已启动，app.state 中的 chunk_records / FAISS / BM25 可能仍是旧索引。
```

处理建议：

```text
测试阶段建议：
1. 使用 POST /rebuild_index 让服务内部刷新索引
或
2. 命令行重建索引后重启 uvicorn
```

---

## 8. 当前限制

当前仍是求职展示型项目，不是生产级企业知识库系统。

当前限制：

```text
1. PDF 仅支持文本型 PDF
2. 扫描型 PDF OCR 尚未实现
3. 复杂 PDF 表格结构还原尚未实现
4. 多栏 PDF 版面恢复尚未实现
5. Excel 当前只支持普通单行 header + 数据行
6. Excel 合并单元格、多级表头、公式重新计算、透视表尚未支持
7. Word / docx Loader 尚未实现
8. 权限过滤目前只保留 permission_level 字段，尚未真正按用户权限过滤
9. 文档版本管理目前只保留 version 字段，尚未实现多版本过滤
10. 重复资料去重尚未实现
11. 当前测试主要为人工接口测试，尚未形成完整自动化测试体系
```

---

## 9. 当前阶段结论

当前企业知识库 RAG 项目已经完成企业资料入库第一阶段能力：

```text
txt + 文本型 PDF + Excel
→ 统一 Document(text + metadata)
→ 通用清洗
→ 结构化 chunk
→ embedding
→ 混合检索
→ reranker
→ 大模型回答
→ 来源可追溯
```

这说明项目已经不再只是基于 `knowledge.txt` 的 RAG Demo，而是具备了更接近真实企业知识库的多类型资料接入能力。

---

## 10. 面试表达

```text
我在项目中补充了企业资料入库与预处理能力。系统现在会扫描 data/raw_docs 目录，支持 txt、文本型 PDF 和 Excel。

txt 通常作为线性文本读取；PDF 按 page 生成 Document，并在 metadata 中保留 page；Excel 不会简单拼成长文本，而是按 sheet 和 row 读取，把每一行结合 header 转换成自然语言 Document，并保留 sheet_name 和 row_number。

后续所有 Document 会进入统一的 Processor、Chunker、Index Builder 和检索链路。Processor 负责通用清洗，Chunker 会根据内容结构选择切分策略，例如制度类文档按 policy_clause 条款切分，普通文本退回 paragraph_then_overlap。

在测试中，我验证了“事假怎么申请？”可以命中制度条款，“VPN 权限怎么申请？”可以命中 PDF 第 2 页，“产品入门训练营报名截止是什么时候？”可以命中 Excel 培训报名表第 2 行。最终 used_chunks_debug 可以展示 source_file、file_type、page、sheet_name、row_number 和 chunk_strategy，方便解释系统为什么这样回答。
```

---

## 11. 前端 Demo 测试结果

本阶段补充了基于 React + Vite + TypeScript 的轻量前端 Demo，验证结果如下：

```text
1. 前端可以正常访问 http://127.0.0.1:5173。
2. 页面可以调用后端 POST /ask_langchain 并展示回答及检索状态。
3. Excel 问题“产品入门训练营报名截止是什么时候？”能够在页面展示 sheet_name / row_number。
4. 未覆盖问题“公司年终奖发放规则是什么？”返回 low_confidence 时，页面能够展示 0 chunks。
5. 该前端主要用于展示 RAG 可解释性字段与演示检索链路，不是生产级 UI。
```
