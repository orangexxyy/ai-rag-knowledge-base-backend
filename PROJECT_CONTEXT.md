# RAG 项目当前阶段总结 - 2026-05-23

## 当前阶段目标

本阶段目标是补齐企业 RAG 项目中的资料入库处理能力，让项目从单一 `knowledge.txt → chunk → embedding` 的 Demo，升级为具备基础 Document Ingestion Pipeline 的企业知识库 RAG 后端项目。

## 已完成能力

### 1. 统一 Document 数据结构

新增：

```text
app/document_models.py
```

定义统一 `Document`：

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

作用：

```text
让 txt / PDF / Excel 等不同来源资料先统一转换成 Document，再进入清洗、chunk、embedding 和索引构建流程。
```

---

### 2. Document Loader

新增：

```text
app/document_loader.py
```

当前已支持：

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
PDF → 按 page 生成 Document
Excel → 按 sheet / row 生成 Document
```

---

### 3. Document Processor

新增：

```text
app/document_processor.py
```

当前实现最小文本清洗：

```text
统一换行符
去掉每行首尾空格
压缩连续空格 / tab
压缩过多空行
保留必要段落结构
```

设计原则：

```text
清理噪声，但不破坏标题、段落和条款边界。
```

---

### 4. Document Chunker

新增：

```text
app/document_chunker.py
```

当前功能：

```text
Document(text + metadata)
→ chunk_items(text + metadata)
```

特点：

```text
chunk 不再只是字符串，而是继续携带 metadata。
```

这样后续 PDF / Excel 接入后，可以保留：

```text
PDF page
Excel sheet_name
Excel row_number
source_file
permission_level
```

---

### 5. Index Builder 升级

修改：

```text
app/index_builder.py
```

原来：

```python
{
    "chunk_id": 0,
    "text": "...",
    "embedding": [...]
}
```

现在：

```python
{
    "chunk_id": 0,
    "text": "...",
    "embedding": [...],
    "metadata": {...}
}
```

同时兼容旧的 `list[str]` 输入，避免一次性破坏旧链路。

---

### 6. Index Manager 接入新入库链路

修改：

```text
app/index_manager.py
```

新版正式建库流程：

```text
load_document(KNOWLEDGE_FILE)
→ process_documents()
→ chunk_documents()
→ build_chunk_records()
→ save_chunk_records()
→ build FAISS index
```

---

### 7. metadata 贯穿检索与 debug 返回

已修改：

```text
app/faiss_retriever.py
app/bm25_retriever.py
app/hybrid_search.py
app/routes_langchain.py
```

现在 `/ask_langchain` 的 `used_chunks_debug` 可以返回：

```json
{
  "chunk_id": 11,
  "metadata": {
    "source_file": "knowledge.txt",
    "file_type": "txt",
    "chunk_index_in_document": 11,
    "chunk_char_length": 64
  }
}
```

---

### 8. 索引版本校验增强

新增配置：

```python
DOCUMENT_PIPELINE_VERSION = "v1"
METADATA_SCHEMA_VERSION = "v1"
```

作用：

```text
不仅根据 knowledge_hash 判断资料内容是否变化，也根据文档处理流程版本和 metadata 结构版本判断是否需要重建索引。
```

解决的问题：

```text
代码处理逻辑变了，但原始 knowledge.txt 没变时，旧索引不会自动失效。
```

---

## 当前完整入库链路

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
```

---

## 当前已实现范围

已实现：

```text
txt 文件进入新 Document Pipeline
metadata 保存到 chunk_records
metadata 传递到 FAISS / BM25 / Hybrid Search
metadata 返回到 /ask_langchain debug 字段
document_pipeline_version / metadata_schema_version 版本校验
```

尚未实现：

```text
PDF Loader
Excel Loader
OCR
复杂表格结构还原
权限过滤
版本化文档管理
来源展示到最终自然语言回答
```

---

## 面试表达

可以这样讲：

```text
我把原来的 knowledge.txt 单文件 RAG Demo，升级成了一个基础的企业资料入库链路。现在项目中新增了 Document Loader、Document Processor 和 Document Chunker。

Loader 负责把原始资料转换成统一 Document；Processor 负责清洗文本但保留 metadata；Chunker 负责按当前 chunk 策略切分文本，同时让每个 chunk 继承原始 Document 的 metadata；Index Builder 再为每个 chunk 生成 embedding，并把 text、embedding、metadata 一起写入 chunk_records。

这样后续检索命中某个 chunk 时，不仅能拿到文本内容，还能知道来源文件、文件类型、chunk 在文档中的位置等信息。后续接入 PDF 和 Excel 时，page、sheet_name、row_number 也会沿同一套 metadata 链路传到最终 debug 返回中。
```