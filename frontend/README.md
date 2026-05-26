# RAG Frontend Demo

这是一个使用 Vite + React + TypeScript 编写的轻量问答页面，用于访问项目已有的
`POST /ask_langchain` 接口，并查看检索调试信息。

## 功能

- 输入问题与 `session_id`（默认值为 `frontend_demo_001`）
- 展示回答、意图、检索状态与改写后的检索问题
- 展示最终回答所使用的模型信息
- 展示 `used_chunks_debug` 中每个 chunk 的来源 metadata 和检索/重排分数

## 启动后端

在项目根目录运行：

```powershell
.\.venv\Scripts\Activate.ps1
uvicorn app.main:app --reload
```

后端默认访问地址为 `http://127.0.0.1:8000`。

## 启动前端

打开新的终端，在项目根目录运行：

```powershell
cd frontend
npm install
npm run dev
```

浏览器打开 Vite 输出的页面地址，默认是 `http://127.0.0.1:5173`。

前端默认请求 `http://127.0.0.1:8000/ask_langchain`。如需切换后端地址，可在
`frontend/` 下创建 `.env.local`：

```dotenv
VITE_API_BASE_URL=http://127.0.0.1:8000
```

## 测试问题

可直接使用页面预填问题：

```text
产品入门训练营报名截止是什么时候？
```

也可以测试 PDF 或 Excel 来源追踪相关的问题，检查调试面板中的
`source_file`、`page`、`sheet_name`、`row_number` 和各项 score 是否符合预期。

## 接口请求示例

```json
{
  "question": "产品入门训练营报名截止是什么时候？",
  "session_id": "frontend_demo_001"
}
```
