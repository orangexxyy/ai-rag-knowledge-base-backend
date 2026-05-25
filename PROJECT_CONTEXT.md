# RAG 项目当前阶段总结 - 2026-05-25

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
→ txt / PDF 批量读取
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
metadata 设计
chunk 策略
资料目录扫描
索引版本校验
来源追溯
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
txt / PDF / 后续 Excel 都要先转成 Document，再进入清洗、chunk、embedding、index。
```

---

### 2.2 txt Loader

已实现：

```text
txt 文件读取
```

特点：

```text
使用 open() 读取
通常整个 txt 文件生成 1 个 Document
metadata.file_type = txt
metadata.page = None
```

---

### 2.3 文本型 PDF Loader

已实现：

```text
文本型 PDF 读取
按 page 生成 Document
metadata.page 生效
```

特点：

```text
使用 pypdf.PdfReader
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
复杂表格结构还原未实现
多栏版面恢复未实现
```

---

### 2.4 资料目录扫描

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
```

已验证：

```text
employee_handbook_sample.pdf → 3 页 → 3 个 Document
knowledge.txt → 1 个 Document
it_support_policy_sample.pdf → 多页 PDF Document
```

核心理解：

```text
目录扫描不是重新写 RAG 流程。
目录扫描只是把多个文件统一读取成 list[Document]。
后续 Processor / Chunker / Index Builder 都可以复用。
```

---

### 2.5 Document Processor

已实现通用清洗：

```text
统一换行符
去掉每行首尾空格
压缩连续空格 / tab
压缩过多空行
保留必要段落结构
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

### 2.6 Document Chunker

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

如果 file_type == txt：
    不做 PDF 专用规整，避免破坏 txt 原始结构
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

当前阶段不建议删除旧兼容，避免老测试脚本或临时调试被破坏。

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
document_pipeline_version
metadata_schema_version
```

目录 hash 用于判断：

```text
资料目录中支持文件新增、删除、重命名或内容变化时，旧索引需要重建。
```

---

## 6. 已验证测试结果

已验证：

```text
1. txt 文件可进入 Document Pipeline
2. 文本型 PDF 可按 page 生成 Document
3. PDF metadata.page 可传到 chunk 和 used_chunks_debug
4. employee_handbook_sample.pdf 中“事假怎么申请？”可命中 page=2 的事假条款
5. it_support_policy_sample.pdf 中“VPN 权限怎么申请？”可命中 page=2 的 VPN 条款
6. 不同内容的 txt / PDF 可以进入同一个资料目录索引
7. used_chunks_debug 可返回 source_file / file_type / page / chunk_strategy
8. policy_clause 泛化后可以识别账号权限制度条款、资产管理制度条款等非请假类条款
```

---

## 7. 当前完整入库链路

```text
data/raw_docs/
→ load_documents_from_dir()
→ load_document(file_path)
→ txt_loader / pdf_loader
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

## 8. 当前仍未实现

```text
Excel Loader
Word / docx Loader
扫描型 PDF OCR
复杂 PDF 表格结构还原
PDF 页眉页脚智能过滤
多栏 PDF 版面恢复
section_heading 小标题切分
真正的用户权限过滤
文档版本管理
重复资料去重
```

---

## 9. 当前最重要的面试表达

```text
我把原来的单文件 RAG Demo 升级成了资料目录入库模式。系统会扫描 data/raw_docs 目录，对 txt 和文本型 PDF 调用不同 Loader，但最终统一转换成 Document(text + metadata)。

txt 通常生成一个 Document，PDF 会按 page 生成多个 Document，并在 metadata 中保留 source_file、file_type 和 page。这样检索命中后可以追溯到 PDF 的具体页码。

在 chunk 阶段，我没有只用固定长度切分，而是根据内容结构选择策略。如果识别到“xxx制度条款A/B/C”这种业务结构，就按条款切分；识别不到时退回 paragraph_then_overlap。对于 PDF，因为抽取文本可能出现行内断行和页码噪声，我只在 file_type=pdf 时做轻量规整，避免影响结构正常的 txt。

最终 chunk_records 会保存 text、embedding 和 metadata。检索命中后，used_chunks_debug 可以展示 source_file、file_type、page、chunk_strategy、FAISS/BM25/RRF/rerank 分数，方便解释系统为什么这样回答。
```

---

## 10. 下一阶段建议

下一阶段建议进入：

```text
Excel Loader
```

目标：

```text
Excel 文件
→ 按 sheet / row 读取
→ 每行或业务对象转成自然语言 Document
→ metadata.sheet_name / row_number 生效
→ 复用现有 Processor / Chunker / Index Builder
```

学习重点：

```text
为什么 Excel 不能简单当成长文本
为什么表格要按 row 或业务对象转自然语言
metadata.sheet_name / row_number 如何用于来源追溯
```
