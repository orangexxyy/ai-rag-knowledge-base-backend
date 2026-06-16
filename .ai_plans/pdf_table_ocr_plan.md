# PDF Table + Minimal OCR Plan

## Task Goal

为当前企业知识库 RAG 主项目补充 PDF 表格处理和最小 OCR 闭环，让面试中关于“PDF 里的表格和图片怎么处理”的追问有可运行、可解释的工程答案。

## Non-goals

- 不做生产级 PDF 图文解析系统。
- 不做图片语义理解、图表含义理解、流程图结构理解。
- 不做复杂表格区域去重、跨页表格合并、多栏版面恢复。
- 不修改 `/ask_langchain` 主业务流程。
- 不修改 `/agent_demo`、frontend、`data/chat_history.db`。
- 不把 paddleocr / easyocr 加入 requirements。

## Files Expected to Change

- `app/document_loader.py`
- `app/config.py`
- `requirements.txt`
- `scripts/test_pdf_table_ocr_loader.py`
- `README.md`
- `PROJECT_CONTEXT.md`

## Implementation Plan

1. 在 `config.py` 增加 `OCR_PROVIDER=none` 默认配置和轻量 OCR 参数。
2. 在 `document_loader.py` 保留原有 `pypdf` page text Document。
3. 使用可选 `pdfplumber` 提取文本型 PDF 表格，将 header + row 转成自然语言 Document。
4. 增加扫描页启发式判断：页面普通文本很少且图片占比/数量达到阈值时才处理 OCR 或占位。
5. 默认 `OCR_PROVIDER=none` 时不 import OCR 引擎，只生成谨慎的 `image_placeholder`。
6. 启用 `OCR_PROVIDER=paddleocr/easyocr` 时才动态 import 对应 OCR 引擎，并通过 PyMuPDF 渲染页面图片后生成 `ocr_text` Document。
7. 新增测试脚本覆盖文本 PDF、表格转换函数、默认 OCR 关闭、占位/OCR metadata。
8. 更新 README 和 PROJECT_CONTEXT，明确已实现能力和未实现边界。

## Progress Checklist

- [x] Planning file created
- [x] Config updated
- [x] PDF loader enhanced
- [x] Test script added
- [x] Documentation updated
- [x] Validation run

## Test Checklist

- [x] `.\.venv\Scripts\python.exe -m py_compile app\main.py app\document_loader.py app\config.py`
- [x] `.\.venv\Scripts\python.exe scripts\test_pdf_table_ocr_loader.py`

## Risks and Rollback Notes

- `pdfplumber` 和 `PyMuPDF` 是新增轻量依赖，未安装时可通过 requirements 安装。
- OCR 引擎保持可选，不进入 requirements，避免默认启动失败。
- 新增 metadata 字段向后兼容，旧 Document 不要求包含 `content_type`。
- 如需回滚，移除 loader 增强函数、OCR 配置、测试脚本和文档段落即可，不涉及数据库 schema。
