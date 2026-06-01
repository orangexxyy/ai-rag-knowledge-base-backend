# AGENTS.md

## 1. Project Role

This repository is a **FastAPI + RAG enterprise knowledge base project**.

The project is focused on:

- AI application development
- Large language model application development
- RAG engineering
- Enterprise document ingestion
- Explainable retrieval and answer generation
- Job-search-oriented project presentation

This project is **not** primarily focused on:

- model pretraining
- algorithm research
- full large model fine-tuning
- production-grade enterprise platform development

Current implemented capabilities include:

- FastAPI backend
- Main demo API: `POST /ask_langchain`
- SQLite multi-turn conversation history
- minimal session summary memory based on `session_id + SQLite`
- minimal `/agent_demo` Controlled Tool Calling Agent Demo
- fake / LLM planner switch via `AGENT_PLANNER_PROVIDER=fake / llm`
- strict JSON `tool_call` planning with backend whitelist / schema / dangerous-tool authorization
- chat / rag routing
- Query Rewrite
- FAISS + BM25 + RRF hybrid retrieval
- DashScope qwen3-rerank
- low_confidence fallback
- DeepSeek / Ollama final answer model switching
- txt / text-based PDF / Excel document ingestion
- unified `Document(text + metadata)` data structure
- PDF `page` metadata
- Excel `sheet_name` / `row_number` metadata
- `policy_clause` and `paragraph_then_overlap` chunk strategies
- React + Vite + TypeScript frontend demo under `frontend/`
  - supports RAG Q&A mode and Agent Demo mode

---

## 2. Core Development Rule

Do **not** rewrite the whole project.

Prefer:

- small changes
- reviewable changes
- incremental integration
- backward-compatible behavior
- clear test evidence
- clear documentation updates

Before modifying files:

1. Read the relevant existing files.
2. Summarize the current structure.
3. Explain the planned changes.
4. List files that may be modified.
5. Explain whether the change affects existing APIs or response fields.
6. Avoid touching unrelated files.

The goal is not just to make code run.

Every feature should be:

- understandable
- testable
- explainable
- safe to discuss in interviews

## 2.1 Code Comment Rules

For code generated or modified in this project:

* Use Chinese comments for key business logic, important conditional branches, data flow, and integration points.
* Keep function names, variable names, class names, type hints, filenames, API names, and technical terms in English.
* Do not add comments to every line. Only comment on logic that helps the user understand why the code is written this way.
* Function docstrings can use Chinese to explain purpose, inputs, outputs, and important side effects.
* Do not change existing behavior only for the sake of adding comments.
* When modifying existing code, preserve the original style as much as possible, but add Chinese comments around newly added key logic.
* Comments should help the user understand and explain the code in interviews.

---

## 3. Development Modes

Before starting a task, identify the task mode.

---

### 3.1 Read-Only Mode

Use this mode when the user asks for:

- project analysis
- code review
- architecture review
- file structure summary
- implementation planning
- risk analysis

Rules:

- Do not modify files.
- Do not install dependencies.
- Do not run destructive commands.
- Output findings and recommended next steps only.

---

### 3.2 Docs-Only Mode

Use this mode when the user asks to update documentation.

Allowed files:

- `README.md`
- `PROJECT_CONTEXT.md`
- `test_cases.md`
- `evaluation_v2.md`
- `AGENTS.md`
- other documentation files explicitly requested by the user

Rules:

- Do not modify application code.
- Do not claim features that are not implemented.
- Keep "implemented" and "future extension" clearly separated.
- If unsure whether a feature is implemented, say "not sure" and inspect code first.

---

### 3.3 Frontend-Only Mode

Use this mode when the user asks for frontend UI changes.

Allowed files:

- `frontend/`
- `app/main.py` only if CORS changes are required
- documentation files if requested

Rules:

- Do not modify RAG core logic.
- Do not modify document ingestion, retrieval, reranking, router, memory, or index logic unless explicitly requested.
- Run frontend validation after changes:

```powershell
cd frontend
npm run build
```

---

### 3.4 Feature Integration Mode

Use this mode when the user asks to integrate a real feature into the existing project, such as:

- memory mechanism
- agent endpoint
- tool calling
- workflow integration
- new backend API
- new retrieval behavior
- new document processing capability
- new database table
- new prompt assembly logic
- new frontend + backend integrated behavior

In this mode, modifying core backend files is allowed only when necessary and after explaining the reason.

Possible files that may be modified depending on the feature:

- `app/routes_langchain.py`
- `app/routes.py`
- `app/main.py`
- `app/config.py`
- `app/database.py`
- SQLite / conversation history related modules
- prompt / chain related modules
- `app/semantic_router.py`
- `app/index_manager.py`
- `app/document_loader.py`
- `app/document_processor.py`
- `app/document_chunker.py`
- `app/index_builder.py`
- `frontend/`
- `scripts/`
- documentation files

Rules for Feature Integration Mode:

1. Do not make a large rewrite.
2. Preserve existing APIs unless the user explicitly approves breaking changes.
3. Keep existing `/ask_langchain` behavior backward compatible.
4. If new response fields are added, make them optional or backward compatible.
5. If new database tables are added, explain the schema and migration impact.
6. If existing database schema changes, explain the risk and provide a safe migration plan.
7. If modifying retrieval, router, chunking, memory, or prompt behavior, explain how old test cases are protected.
8. Add or update test scripts when practical.
9. Update documentation after implementation.
10. Output exact validation commands and expected results.

---

### 3.5 Refactor Mode

Use this mode only when the user explicitly asks for refactoring.

Rules:

- Refactor only the requested module.
- Do not combine refactor with new features unless explicitly requested.
- Preserve behavior.
- Provide before / after summary.
- Run relevant tests.

---

## 4. Core RAG Files

These files are important and should not be modified casually:

- `app/document_loader.py`
- `app/document_processor.py`
- `app/document_chunker.py`
- `app/index_builder.py`
- `app/index_manager.py`
- `app/semantic_router.py`
- `app/routes_langchain.py`

They can be modified in **Feature Integration Mode** if the feature requires it.

Before modifying any of these files:

1. Explain why the file must change.
2. Explain the expected behavior change.
3. Explain how to test the change.
4. Confirm that unrelated behavior is preserved.

---

## 5. Design First Rule

For complex feature integration tasks, do not start coding immediately.

Complex feature examples:

- memory mechanism
- agent endpoint
- tool calling
- workflow integration
- database schema changes
- retrieval behavior changes
- prompt assembly changes
- multi-step backend + frontend integration

Before coding:

1. Ask up to 5 necessary clarification questions if requirements are unclear.
2. Provide a short design proposal.
3. Wait for user confirmation before implementation.

The design proposal should include:

1. Goal
2. Non-goals
3. Current related files
4. Planned file changes
5. Data flow
6. API impact
7. Backward compatibility
8. Test plan
9. Risks

For small documentation, frontend display, config, typo, or launch setting fixes, this rule can be skipped.

---

## 6. Planning File Rule

For multi-step feature integration tasks, create or update a planning file under:

```text
.ai_plans/
```

Example files:

```text
.ai_plans/memory_summary_plan.md
.ai_plans/agent_demo_plan.md
.ai_plans/tool_calling_plan.md
```

The plan file should include:

1. Task goal
2. Non-goals
3. Files expected to change
4. Step-by-step implementation plan
5. Progress checklist
6. Test checklist
7. Risks and rollback notes

Keep the plan file concise.

Do not create planning files for very small tasks.

Important feature planning files may be committed to GitHub.

Temporary debugging plans do not need to be committed unless the user asks.

---

## 7. Completion Gate

A task is not complete just because code was written.

Before saying the task is complete, verify the relevant exit criteria.

---

### 7.1 Backend Change Exit Criteria

For backend changes:

- Python syntax check passes.
- Relevant script or endpoint test is described or run.
- Existing `/ask_langchain` behavior remains compatible.
- No unrelated RAG core behavior is changed.
- New debug fields, if added, are documented.

Recommended basic check:

```powershell
.\.venv\Scripts\python.exe -m py_compile app\main.py
```

If the feature touches other modules, run relevant scripts under `scripts/`.

---

### 7.2 Frontend Change Exit Criteria

For frontend changes:

- `npm run build` passes.
- The page can still call the backend API.
- Important RAG debug fields are still displayed if relevant.

Recommended check:

```powershell
cd frontend
npm run build
```

---

### 7.3 Document Ingestion Change Exit Criteria

For document ingestion changes:

- At least one txt / PDF / Excel related test is checked when the change may affect ingestion.
- Metadata is not broken:
  - `source_file`
  - `file_type`
  - `page`
  - `sheet_name`
  - `row_number`
  - `chunk_strategy`

Recommended test questions:

- `事假怎么申请？`
- `VPN 权限怎么申请？`
- `产品入门训练营报名截止是什么时候？`

---

### 7.4 Memory Change Exit Criteria

For memory-related changes:

- Existing `session_id` behavior still works.
- Existing SQLite conversation history behavior still works.
- Query Rewrite still handles follow-up questions.
- Memory behavior is visible in debug output if practical.
- Documentation clearly states whether it is:
  - session memory
  - summary memory
  - long-term memory
  - vector memory
- Do not claim full long-term memory unless actually implemented.

Recommended memory test cases:

1. Normal RAG question
2. Follow-up question
3. Question that should use minimal session summary memory when available
4. Old `/ask_langchain` compatibility test
5. low_confidence test

---

### 7.5 Agent / Tool Calling Change Exit Criteria

For agent or tool calling changes:

- Existing `/ask_langchain` endpoint is not replaced.
- Tool inputs are validated.
- Agent behavior is explainable through debug fields.
- Tool calling is explicit and controlled.
- No full multi-agent capability is claimed unless actually implemented.
- If a tool writes to an external system, the write behavior must be clearly documented.

---

### 7.6 Git Task Exit Criteria

For git tasks:

- Run `git status`.
- Show planned staged files.
- Do not commit `.env`, API keys, `node_modules`, `dist`, local DB, cache files, or logs.
- Prefer explicit `git add` paths.
- After push, output:
  - commit hash
  - final `git status`
  - files added
  - files modified
  - whether RAG core logic was modified

If any required check cannot be run, clearly say why and stop before commit unless the user explicitly approves continuing.

### 7.7 Test Failure Handling Rules

If a test or validation command fails:

1. First analyze and explain the failure reason.
2. Only fix small issues directly related to the current task.
3. Do not expand the modification scope just to make tests pass.
4. If the fix requires modifying unauthorized files, restructuring the main chain, changing retrieval behavior, changing router/reranker logic, changing document loading/chunking/indexing logic, or changing existing database schema, stop and explain the reason before making changes.
5. Do not silently change test expectations to hide real problems.
6. After fixing, rerun the relevant test or validation command.
7. Output:

   * failed command
   * failure reason
   * files changed for the fix
   * retest command
   * retest result
   * remaining risk

For the current RAG project, Codex may fix small issues related to the current stage, such as import errors, function parameter mismatch, syntax errors, or memory_debug field mismatch.

Codex must not modify the following without explicit confirmation:

* FAISS / BM25 / RRF retrieval behavior
* reranker logic or thresholds
* semantic router strategy or thresholds
* document loader
* document processor
* document chunker
* index builder
* index manager
* existing database schema destructive changes
* API request body breaking changes


---

## 8. Memory Integration Rules

When implementing memory-related features, do not create an isolated demo unless the user explicitly asks for a demo.

Prefer integrating memory into the existing RAG flow.

Possible memory levels:

### 8.1 Session Memory

Existing conversation history based on `session_id` and SQLite.

This project already has basic session memory.

### 8.2 Summary Memory

A compressed summary of previous conversation history.

Useful when conversation history becomes long.

This project already has a minimal session summary memory implementation:

- stored in SQLite table `session_memory_summaries`
- updated by thresholds
- generated from older session history while keeping recent messages
- used only for Query Rewrite context
- not added to `reference_text`
- not used as factual evidence for final answers
- visible through `memory_debug`
- failure to update the summary must not break the original RAG / chat answer
- low_confidence or insufficient-reference fallback answers should be filtered before summarization

### 8.3 User Profile Memory

Stable user preferences or profile information.

Examples:

- user preference
- answer style
- department
- role
- frequently asked topics

### 8.4 Vector Memory

Embedding-based retrieval over past conversations or saved memories.

Useful for long-term memory retrieval.

---

### 8.5 Current Project Memory Strategy

For the current project, prefer incremental memory integration:

- Keep current `session_id` behavior.
- Reuse existing SQLite history if possible.
- Add new table only when necessary.
- Make memory behavior visible in debug fields if practical.
- Do not store sensitive data without explicit user approval.
- Keep memory optional and controllable.
- Do not claim full long-term memory unless implemented.

For the implemented minimal `memory_summary` feature:

1. Explain where the summary is stored.
2. Explain when it is updated.
3. Explain how it is injected into Prompt or Query Rewrite.
4. Explain how it differs from ordinary conversation history.
5. Add tests for:
   - normal RAG question
   - follow-up question
   - memory summary usage
   - old behavior compatibility
   - low_confidence behavior

---

## 9. Agent / Tool Calling Integration Rules

When implementing agent-related features, prefer small controlled agents over open-ended autonomous agents.

A valid minimal agent integration in this project may include:

- `/agent_demo` side-path endpoint
- controlled `tool_call` planning
- tool schema exposure to planner
- backend tool whitelist validation
- backend arguments schema validation
- dangerous tool authorization before executor execution
- calling existing RAG capability as a read-only tool
- returning `agent_steps` and `agent_debug`

Rules:

- Do not replace the existing RAG endpoint.
- Do not introduce complex multi-agent frameworks unless explicitly requested.
- Do not claim full multi-agent capability unless implemented.
- Do not claim full autonomous Agent capability unless implemented.
- Keep tool calls explicit and explainable.
- Validate tool input parameters before execution.
- Prefer controlled workflow behavior over open-ended autonomous behavior.
- Dangerous tools must require backend-owned authorization; model-generated arguments cannot authorize dangerous operations by themselves.

---

## 10. Safety Rules

Never commit:

- `.env`
- API keys
- access tokens
- `data/chat_history.db`
- `frontend/node_modules/`
- `frontend/dist/`
- `__pycache__/`
- temporary logs
- local cache files

Do not run destructive commands unless the user explicitly confirms:

- `rm`
- `del`
- `Remove-Item`
- `git reset --hard`
- `git clean -fd`
- `git restore`

Avoid broad commands unless explicitly approved:

- `git add .`
- mass formatting commands across the whole repository
- dependency upgrades unrelated to the current task

---

## 11. Testing Rules

For backend changes, run at least one relevant check:

```powershell
.\.venv\Scripts\python.exe -m py_compile app\main.py
```

If the feature touches other modules, also run relevant scripts under `scripts/`.

For frontend changes, run:

```powershell
cd frontend
npm run build
```

For document ingestion changes, run relevant loader / chunker / index tests.

For RAG behavior changes, test at least:

- a normal matched RAG case
- a low_confidence case
- a multi-turn follow-up case if Query Rewrite or memory is involved
- one Excel metadata case if document pipeline may be affected

Recommended test questions:

```text
事假怎么申请？
VPN 权限怎么申请？
产品入门训练营报名截止是什么时候？
公司年终奖发放规则是什么？
```

---

## 12. Git Rules

For git tasks:

1. Run `git status` before staging.
2. Show the planned file list.
3. Do not use `git add .` unless explicitly confirmed.
4. Prefer explicit file paths in `git add`.
5. Do not commit if unexpected files appear.
6. After commit and push, output:
   - commit hash
   - final `git status`
   - files added
   - files modified
   - whether RAG core logic was modified

Recommended commit messages:

```text
docs: update project instructions for ai coding tools
feat: add memory summary integration
feat: add agent demo endpoint
chore: update vscode launch config
test: add rag regression cases
```

---

## 13. Documentation Rules

Do not claim features that are not implemented.

Allowed implemented claims:

- txt / text-based PDF / Excel ingestion
- `Document(text + metadata)`
- PDF `page` metadata
- Excel `sheet_name` / `row_number` metadata
- `policy_clause` chunking
- `paragraph_then_overlap` chunking
- FAISS + BM25 + RRF
- DashScope reranker
- low_confidence fallback
- SQLite session history
- React frontend demo
- basic session memory based on `session_id` and SQLite conversation history
- minimal session summary memory based on `session_id + SQLite`
- minimal `/agent_demo` Controlled Tool Calling Agent Demo
- read-only `search_knowledge_base` Agent tool that reuses existing RAG internals without replacing `/ask_langchain`

Do not claim unless actually implemented:

- OCR for scanned PDF
- Word / docx Loader
- production-grade permission system
- full long-term memory system
- user profile memory
- vector memory
- cross-session long-term memory retrieval
- full multi-agent system
- full autonomous Agent platform
- production-grade tool permission system
- real `rebuild_index` execution through `/agent_demo`
- external API tools such as Feishu, Weibo, Xiaohongshu, or weather APIs
- LoRA / QLoRA fine-tuning implementation
- production-grade frontend management platform

If a feature is partially implemented, describe it as:

- basic version
- minimal version
- demo version
- future extension

Do not describe partial features as production-grade.

### 13.1 Documentation Consistency Rules

When updating documentation after a feature is implemented, do not only append new content. Search existing documentation for outdated or conflicting statements and update the original paragraphs directly. Ensure README.md, PROJECT_CONTEXT.md, test_cases.md, evaluation_v2.md, and AGENTS.md use the same implemented / partial / not implemented status.

---

## 14. Output Format After Each Task

After every task, output:

1. Task mode used
2. Files added
3. Files modified
4. Files read but not modified
5. Commands run
6. Test results
7. Risks or uncertainties
8. Whether RAG core logic was modified
9. Whether existing APIs remain backward compatible
10. Next suggested step

---

## 15. Current Project Positioning

This project should be maintained as a job-search-oriented AI application development project.

The priority is:

1. Keep the current RAG main chain stable.
2. Improve project presentation and explainability.
3. Add controlled integrated features only when they help interview expression.
4. Avoid unnecessary large rewrites or over-engineering.
5. Prefer understanding, testing, and explainability over blindly adding features.

When implementing new features, the goal is not just to make code run.

The feature must be understandable, testable, explainable, and safe to discuss in interviews.

---

## 16. Practical Workflow for Future Tasks

For simple tasks:

```text
Read AGENTS.md
Identify task mode
Make small change
Run required check
Output summary
```

For complex tasks:

```text
Read AGENTS.md
Enter Feature Integration Mode
Apply Design First Rule
Create or update .ai_plans/<feature>_plan.md
Wait for user confirmation
Implement incrementally
Run tests
Update docs
Apply Completion Gate
Show git status
Commit only after confirmation
```

Example for memory extension:

```text
Please read AGENTS.md and enter Feature Integration Mode.

Goal:
Extend the existing minimal memory_summary mechanism in /ask_langchain safely.
This should not be an isolated demo or a rewrite.

Requirements:
1. Keep existing session_id + SQLite history behavior.
2. Keep the current minimal session summary memory backward compatible.
3. Make memory usage visible in debug output if practical.
4. Preserve existing RAG, PDF metadata, Excel metadata, and low_confidence behavior.
5. Update .ai_plans/memory_summary_plan.md before coding if the change is multi-step.
6. Provide design first and wait for confirmation.
```

Example for agent integration:

```text
Please read AGENTS.md and enter Feature Integration Mode.

Goal:
Add or extend the lightweight /agent_demo endpoint.
The agent should demonstrate controlled tool calling: planner generates strict JSON tool_call, backend validates whitelist/schema/authorization, and executor runs the selected tool.
The RAG capability may be exposed as a read-only tool without replacing /ask_langchain.

Requirements:
1. Do not replace /ask_langchain.
2. Keep tool calling explicit, validated, and explainable.
3. Return agent_steps / agent_debug showing planner output, validation, authorization, execution, or blocked result.
4. Create .ai_plans/agent_demo_plan.md before coding.
5. Provide design first and wait for confirmation.
```

For code generated for this project, use Chinese comments for key business logic and data flow explanations. Keep function names, variable names, type hints, and technical terms in English.
