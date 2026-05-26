# RAG 项目当前阶段总结 - 2026-05-26

## 1. 当前阶段目标

当前阶段目标是把企业知识库 RAG 项目从早期的：

```text
单一 knowledge.txt
→ chunk
→ embedding
→ index
```

升级为更接近真实企业项目的：

```text
资料目录
→ txt / PDF / Excel 批量读取
→ 统一 Document(text + metadata)
→ 通用清洗
→ 根据资料结构选择 chunk 策略
→ embedding
→ FAISS / BM25 / RRF
→ Reranker
→ 大模型回答
→ 来源可追溯 debug
```

本阶段重点不是追求复杂框架，而是补齐真实企业 RAG 中更常见、面试更容易被追问的能力：

```text
资料入库
PDF 文本解析
Excel 表格解析
metadata 设计
chunk 策略
资料目录扫描
索引版本校验
来源追溯
Router 与资料范围同步
```

---

## 2. 当前已完成能力

### 2.1 统一 Document 数据结构

已实现：

```text
app/document_models.py
```

核心结构：

```python
Document(
    text="文档正文",
    metadata={
        "source_file": "...",
        "source_path": "...",
        "file_type": "...",
        "page": None,
        "sheet_name": None,
        "row_number": None,
        "section_title": None,
        "version": None,
        "permission_level": "internal"
    }
)
```

理解重点：

```text
Document 不只是用于溯源。
Document 是企业 RAG 入库流程的统一中间结构。
txt / PDF / Excel 都要先转成 Document，再进入清洗、chunk、embedding、index。
```

---

### 2.2 txt Loader

已实现：

```text
使用 open() 读取 txt
通常整个 txt 文件生成 1 个 Document
metadata.file_type = txt
metadata.page = None
metadata.sheet_name = None
metadata.row_number = None
```

---

### 2.3 文本型 PDF Loader

已实现：

```text
使用 pypdf.PdfReader 读取文本型 PDF
PDF 每一页生成一个 Document
metadata.file_type = pdf
metadata.page 从 1 开始
```

设计原因：

```text
PDF 命中后需要追溯到具体页码。
如果整份 PDF 合成一个 Document，后续只能知道来源文件，无法知道第几页。
```

当前限制：

```text
扫描型 PDF OCR 未实现
复杂 PDF 表格结构还原未实现
多栏版面恢复未实现
```

---

### 2.4 Excel Loader

已实现：

```text
使用 openpyxl 读取 .xlsx
按 sheet / row 生成 Document
metadata.sheet_name / row_number 生效
```

实现逻辑：

```text
1. 判断文件是否存在
2. 用 openpyxl 读取 workbook
3. 遍历每个 sheet
4. 第一行作为 header
5. 从第二行开始读取 row
6. 处理日期、数字、空值等 cell 类型
7. 将 header 和 row value 一一对应
8. 组装成自然语言 text
9. 每一行生成一个 Document
10. metadata 保存 source_file / file_type / sheet_name / row_number
```

核心理解：

```text
Excel 不能简单当成长文本。
Excel 的语义通常来自 header + row。
一行通常代表一个业务对象，比如培训报名记录、会议室预约规则、办公用品领用规则。
```

示例：

```text
培训报名表记录：培训名称：产品入门训练营；适用对象：入职30天内的新员工；报名截止：开课前3天；负责人：培训专员。
```

---

### 2.5 资料目录扫描

已实现：

```text
load_documents_from_dir(KNOWLEDGE_DIR)
```

当前资料目录：

```text
data/raw_docs/
```

支持：

```text
.txt
.pdf
.xlsx
```

已验证：

```text
employee_handbook_sample.pdf → 3 页 → 3 个 Document
knowledge.txt → 1 个 Document
it_support_policy_sample.pdf → 多页 PDF Document
permission_matrix_sample.xlsx → 15 个 row Document
```

核心理解：

```text
目录扫描不是重新写 RAG 流程。
目录扫描只是把多个文件统一读取成 list[Document]。
后续 Processor / Chunker / Index Builder 都可以复用。
```

---

### 2.6 Document Processor

已实现通用清洗：

```text
统一换行符
去掉每行首尾空格
压缩连续空格 / tab
压缩过多空行
保留必要段落结构
清洗后为空的 Document 会被跳过，并输出调试提示
```

设计原则：

```text
通用、保守，不轻易破坏文档结构。
```

重要理解：

```text
PDF 可能出现 “直属主\n管” 这种行内断行。
但通用 Processor 不适合无差别删除所有单换行。
因为对 txt / Excel 转文本来说，单换行可能本身代表结构。
```

---

### 2.7 Document Chunker

当前已升级为策略选择模式：

```text
Document.text
→ 尝试 policy_clause
→ 成功：按制度条款切
→ 失败：退回 paragraph_then_overlap
```

当前支持两种策略：

```text
policy_clause
paragraph_then_overlap
```

Excel 当前通常在 Loader 阶段已经按 row 转成完整业务对象，因此进入 Chunker 后多为：

```text
paragraph_then_overlap
```

---

## 3. 当前新版 chunk 逻辑

### 3.1 policy_clause

已从早期“请假 / 报销写死规则”升级为通用制度条款识别。

可识别类似：

```text
请假制度条款C（事假）：
差旅报销制度条款B：
账号权限制度条款C（VPN 申请）：
资产管理制度条款D（离职归还）：
IT支持制度条款A：
```

本质：

```text
不是判断是否包含“事假”或“VPN”
而是识别“xxx制度条款A/B/C”这种业务标题边界
从当前标题切到下一个标题之前
```

效果：

```text
一页 PDF 中多个条款
→ 切成多个独立 chunk
→ 检索更聚焦
→ Reranker 更容易判断相关性
```

---

### 3.2 PDF 专用切分前规整

当前逻辑：

```text
如果 file_type == pdf：
    合并单个换行，修复 PDF 行内断行
    去掉末尾页码噪声，例如“第 2 页”

如果 file_type == txt / xlsx：
    不做 PDF 专用规整，避免破坏原始结构
```

核心原则：

```text
内容结构决定 chunk 策略。
文件类型决定是否做专用文本规整。
```

---

### 3.3 paragraph_then_overlap

如果识别不到制度条款结构，仍然退回原来的通用策略：

```text
优先按段落 / 空行切
超长文本再 fixed_size + overlap
```

这保证了旧能力不会被新策略破坏。

---

## 4. Index Builder

当前输入：

```text
chunk_items(text + metadata)
```

输出：

```text
chunk_records(text + embedding + metadata)
```

重要理解：

```text
embedding 只基于 text 生成
metadata 不参与 embedding
metadata 用于来源追溯、debug、权限扩展、版本扩展
```

仍保留旧格式兼容：

```text
list[str] → 自动转换成 {"text": ..., "metadata": {}}
```

---

## 5. Index Manager

当前正式入库已经从单文件升级为目录入库：

```text
load_documents_from_dir(KNOWLEDGE_DIR)
→ process_documents()
→ chunk_documents()
→ build_chunk_records()
→ save_chunk_records()
→ build FAISS index
```

索引 meta 当前记录：

```text
knowledge_source_type = dir
knowledge_dir = data/raw_docs
knowledge_hash_type = directory_sha256
knowledge_hash = 资料目录 hash
document_pipeline_version = v6
metadata_schema_version
```

目录 hash 用于判断：

```text
资料目录中支持文件新增、删除、重命名或内容变化时，旧索引需要重建。
当前已纳入 .txt / .pdf / .xlsx。
```

---

## 6. Semantic Router 与资料范围同步

当前 Router 由以下部分组成：

```text
CHAT_EXAMPLES
RAG_EXAMPLES
RAG_DOMAIN_KEYWORDS
LLM Router Fallback
```

关键理解：

```text
Router 不是根据文件格式分流。
Router 是根据“用户问题像不像知识库问题”分流。
```

接入 Excel 后曾出现：

```text
产品入门训练营报名截止是什么时候？
```

被误判为 chat。

原因：

```text
原来的 RAG 样本主要覆盖请假、报销、员工手册、医药 SOP。
新增 Excel 资料后，出现了培训报名、会议室预约、办公用品领用等新问法。
Router 样本没有覆盖这些表格型资料问题。
```

当前已补充 Excel 场景的 RAG 样本和关键词，例如：

```text
产品入门训练营报名截止是什么时候
星河会议室需要提前多久预约
白板笔套装怎么领取
培训报名表
会议室预约
办公用品领用
报名截止
```

重要经验：

```text
知识库资料范围变化后，Router 样本也要同步维护。
不要优先通过降低阈值解决样本覆盖不足问题。
```

---

## 7. 已验证测试结果

已验证：

```text
1. txt 文件可进入 Document Pipeline
2. 文本型 PDF 可按 page 生成 Document
3. Excel 可按 sheet / row 生成 Document
4. PDF metadata.page 可传到 chunk 和 used_chunks_debug
5. Excel metadata.sheet_name / row_number 可传到 chunk 和 used_chunks_debug
6. employee_handbook_sample.pdf 中“事假怎么申请？”可命中 page=2 的事假条款
7. it_support_policy_sample.pdf 中“VPN 权限怎么申请？”可命中 page=2 的 VPN 条款
8. permission_matrix_sample.xlsx 中“产品入门训练营报名截止是什么时候？”可命中“培训报名表”第 2 行
9. permission_matrix_sample.xlsx 中“星河会议室需要提前多久预约？”可命中“会议室预约表”对应行
10. permission_matrix_sample.xlsx 中“白板笔套装怎么领取？”可命中“办公用品领用表”对应行
11. 不同内容的 txt / PDF / Excel 可以进入同一个资料目录索引
12. used_chunks_debug 可返回 source_file / file_type / page / sheet_name / row_number / chunk_strategy
13. policy_clause 泛化后可以识别账号权限制度条款、资产管理制度条款等非请假类条款
14. Router 补充 Excel 场景样本后，表格型资料查询可稳定进入 RAG
```

---

## 8. 当前完整入库链路

```text
data/raw_docs/
→ load_documents_from_dir()
→ load_document(file_path)
→ txt_loader / pdf_loader / excel_loader
→ list[Document]
→ process_documents()
→ chunk_documents()
→ chunk_items(text + metadata)
→ build_chunk_records()
→ chunk_records(text + embedding + metadata)
→ save chunk_index.json
→ build FAISS index
→ 启动时加载 FAISS / BM25 / chunk_records
→ /ask_langchain 检索
```

---

## 9. 当前仍未实现

```text
Word / docx Loader
扫描型 PDF OCR
复杂 PDF 表格结构还原
PDF 页眉页脚智能过滤
多栏 PDF 版面恢复
Excel 合并单元格复杂解析
Excel 多级表头
Excel 公式重新计算
Excel 跨 sheet 关联
section_heading 小标题切分
真正的用户权限过滤
文档版本管理
重复资料去重
自动化评估集
```

---

## 10. 当前最重要的面试表达

```text
我把原来的单文件 RAG Demo 升级成了资料目录入库模式。系统会扫描 data/raw_docs 目录，对 txt、文本型 PDF 和 Excel 调用不同 Loader，但最终统一转换成 Document(text + metadata)。

txt 通常生成一个 Document；PDF 会按 page 生成多个 Document，并在 metadata 中保留 source_file、file_type 和 page。这样检索命中后可以追溯到 PDF 的具体页码。

Excel 没有直接拼成长文本，而是按 sheet 和 row 读取，把每一行结合 header 转成自然语言 Document，同时在 metadata 中保留 sheet_name 和 row_number。这样用户问“产品入门训练营报名截止是什么时候？”时，可以命中“培训报名表”的具体行。

在 chunk 阶段，我没有只用固定长度切分，而是根据内容结构选择策略。如果识别到“xxx制度条款A/B/C”这种业务结构，就按条款切分；识别不到时退回 paragraph_then_overlap。对于 PDF，因为抽取文本可能出现行内断行和页码噪声，我只在 file_type=pdf 时做轻量规整，避免影响结构正常的 txt 和 Excel。

最终 chunk_records 会保存 text、embedding 和 metadata。检索命中后，used_chunks_debug 可以展示 source_file、file_type、page、sheet_name、row_number、chunk_strategy、FAISS/BM25/RRF/rerank 分数，方便解释系统为什么这样回答。

接入 Excel 后，我还补充了 Router 的 RAG 样本和关键词，因为知识库范围变化后，用户问法也会变化。Router 不是一次写完永远不用维护，而是要随着知识库业务范围同步更新。
```

---

## 11. 下一阶段建议

下一阶段不建议马上继续堆新 Loader。

建议优先做：

```text
README / PROJECT_CONTEXT / test_cases 更新
GitHub 提交
当前阶段收口
```

然后再根据求职展示需要选择：

```text
1. 做少量回归测试和演示脚本
2. 补充 README 中的面试表达
3. 准备简历项目亮点更新
4. 后续再考虑 Word Loader / section_heading / 自动化评估
```

---

## 12. 轻量前端 Demo

当前项目已新增 `frontend/` 轻量前端 Demo，技术栈为 React + Vite + TypeScript。

前端不是核心 RAG 逻辑，而是现有接口能力的展示层。它直接调用
`POST /ask_langchain`，将 JSON 响应中的回答、检索状态和调试数据以页面形式呈现。

前端的主要价值是把 RAG 可解释性信息可视化，特别是：

```text
used_chunks_debug
source_file / file_type / page
sheet_name / row_number / chunk_strategy
FAISS / BM25 / RRF / rerank 分数
```

为了让 Vite 开发页面能够从浏览器访问 FastAPI 接口，CORS 修改仅在
`app/main.py` 中完成，允许 `http://127.0.0.1:5173` 和
`http://localhost:5173` 调用后端。该调整不改变 RAG 检索、路由、切分或回答逻辑。
