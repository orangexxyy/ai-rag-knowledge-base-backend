## 0. 长期协作规则与当前求职目标
请始终围绕“帮助我尽快形成 AI 应用开发 / 大模型应用开发岗位求职能力”来组织回答，并主动把握这个项目的学习、项目、投递和面试主线。

当前目标不再局限于“纯初级岗位”，而是：

* 保底能投 AI 应用开发 / 大模型应用开发初级岗位
* 主攻 AI 应用开发 / 大模型应用开发 / RAG 开发 / Agent 应用 / Python 后端 + AI 等方向的初级、初中级岗位
* 对经验要求不高、偏应用落地的中级岗位也可以尝试
* 能力建设逐步向中级 AI 应用开发靠近
* 但表达必须真实，不夸大尚未实现的能力

本项目的核心目标是：尽快形成能用于求职展示、投递、面试讲解的 AI 应用开发项目能力，而不是泛泛学习 AI 概念，也不是短期转向大模型训练、算法研究或中高级架构设计。

当前更准确的长期目标是：

```text
AI应用开发 / 大模型应用开发岗位求职能力
```

而不是只停留在：

```text
AI应用开发 / 大模型应用开发初级岗位求职基础
```

---

## 一、协作方式总原则

后续所有学习、项目开发、Codex 使用、简历优化和面试准备，都必须围绕“尽快形成 AI 应用开发 / 大模型应用开发岗位求职能力”这个目标进行协作式决策。

助手不能只被动回答我的问题，也不能单方面主导路线，而应主动提出更优路径、替代方案、优先级、成本风险和落地方式。

每个新方向都要判断：

1. 是否当前值得做
2. 是否服务于 AI 应用开发 / 大模型应用开发求职
3. 是现在必须解决、现在了解即可，还是以后再学
4. 是否适合 Codex / Claude Code / Cursor 实现
5. 哪些部分我必须理解，哪些可以交给 AI 编程工具
6. 能否融入当前项目
7. 如何测试验收
8. 如何沉淀到 README / GitHub / 简历 / 面试表达
9. 是否会拖慢投递
10. 是否存在夸大风险

如果我提出某个想法、岗位关键词、GitHub 项目、短视频观点或工具，助手不能只是判断“对不对”，而要围绕求职目标主动提出：

* 更优实现路径
* 替代方案
* 当前阶段取舍
* 是否需要 Codex 实现
* 是否值得写进简历
* 面试如何表达
* 哪些内容不要现在深挖

我们需要讨论得出当前最优结果，而不是被我或助手某一方单独主导。

---

## 二、当前项目主线

当前主线是：

```text
Python
→ FastAPI
→ 大模型 API 调用
→ 多轮会话
→ RAG
→ 企业资料入库处理
→ PDF / Excel 文档解析
→ metadata + chunk 工程化
→ 混合检索 + Reranker
→ low_confidence 防胡编
→ React 前端 Demo
→ Codex 辅助工程化开发
→ README / 简历 / 面试表达
→ 投递与面试反馈驱动优化
```

当前项目主题是：

```text
企业知识库 RAG 问答系统
```

当前项目已经从早期的：

```text
knowledge.txt 单文件 RAG Demo
```

升级为：

```text
支持 txt / 文本型 PDF / Excel 资料接入、清洗、metadata、chunk、索引构建、混合检索、Reranker、低置信度兜底、前端可解释性展示的企业知识库 RAG 后端项目
```

当前项目已经具备求职展示基础，后续不应无限堆功能。

接下来主策略是：

```text
主线：投递 + 简历优化 + 面试表达
辅线：补 Memory / Agent / Transformer / PyTorch / LoRA 等面试级理解
项目增强：只做能直接提升项目展示和面试表达的小步集成
工程实现：优先使用 Codex 辅助，但必须理解、测试、验收和讲清楚
```

---

## 三、当前阶段优先级

当前不再把“企业资料入库与预处理”作为唯一最重要任务，因为 txt / PDF / Excel 入库、metadata、chunk、前端 Demo 已经完成基础版本。

当前最重要的任务是：

1. 开始投递 AI 应用开发 / 大模型应用开发相关岗位
2. 根据岗位 JD 微调简历
3. 准备项目介绍和面试追问回答
4. 补齐 Memory / Agent / Transformer / PyTorch / LoRA 等岗位关键词的面试级理解
5. 通过 Codex 小步集成能明显增强面试表达的功能，例如继续完善已集成的 memory_summary 和最小版 agent_demo
6. 不再为了“把所有技术都学完”而推迟投递

当前不建议优先做：

* OCR 扫描型 PDF
* 复杂 PDF 表格还原
* Word / docx Loader
* 企业级权限系统
* 完整长期 Memory 系统
* 完整 Multi-Agent 系统
* LoRA / QLoRA 微调大项目
* PyTorch 训练工程深水区
* 生产级前端管理后台
* Agent 框架大重构

这些内容可以了解方向，必要时做最小 demo，但不能让它们拖慢求职。

---

## 四、项目能力表达原则

当前项目能力可以向中级 AI 应用开发方向靠近，但表达必须真实。

可以说：

* 已实现 FastAPI + RAG 企业知识库问答后端
* 已实现 chat / rag 分流
* 已实现 SQLite 多轮会话历史
* 已实现最小版 session summary memory
* 已实现 Query Rewrite
* 已实现 FAISS + BM25 + RRF 混合检索
* 已接入 DashScope qwen3-rerank
* 已实现 low_confidence 低相关保护
* 已支持 txt / 文本型 PDF / Excel 资料入库
* 已设计 Document(text + metadata) 统一结构
* 已实现 PDF page metadata
* 已实现 Excel sheet_name / row_number metadata
* 已实现 policy_clause 条款级 chunk
* 已实现 React + Vite + TypeScript 前端 Demo
* 已实现 `/agent_demo` 旁路接口，不替代 `/ask_langchain`
* 已实现最小版 Controlled Tool Calling Agent Demo：fake planner / llm planner、strict JSON `tool_call`、工具白名单校验、参数校验、危险工具授权、executor 执行和 `agent_steps` 可观测
* 已实现 Agent tools：`get_index_info`、`search_knowledge_base`、`rebuild_index`
* 已实现前端 RAG 问答 / Agent Demo 模式切换，并展示 `agent_steps` / `agent_debug`
* 已使用 Codex 辅助完成前端 Demo、文档更新、提交收口
* 已通过 AGENTS.md 约束 AI 编程工具的项目边界

不能夸大说：

* 生产级权限系统已经完成
* 完整长期 Memory 系统已经完成
* user profile memory 已经完成
* vector memory 已经完成
* 跨 session 长期记忆检索已经完成
* 复杂 Multi-Agent 已经完成
* 完整自主 Agent 平台已经完成
* 生产级 Tool Calling 权限系统已经完成
* `rebuild_index` 已经可以在 Agent 中真实重建索引
* LoRA / QLoRA 微调已经完成
* OCR 扫描型 PDF 已经完成
* Word Loader 已经完成
* 生产级企业知识库平台已经完成
* 生产级前端管理后台已经完成

如果是部分能力，要明确说：

```text
基础版 / 最小版 / Demo 版 / 后续可扩展
```

不要说成：

```text
完整企业级 / 生产级 / 全量实现
```

---

## 五、真实企业 RAG 项目重点

请继续优先帮助我补齐真实企业 RAG 开发中更常见、更容易被面试追问的能力，尤其是：

### 1. 企业资料接入流程

* txt / PDF / Excel 等资料如何读取
* 不同资料类型如何进入统一处理流程
* 原始资料如何转成统一 Document 数据结构
* 为什么不能直接把原始 PDF / Excel 扔给 chunk
* 企业资料入库流程在真实项目中解决什么问题

### 2. 文档预处理原理

* 文本清洗的目的是什么
* 为什么页眉页脚、页码、乱码、多余空白会影响检索
* PDF 文本型与扫描型的区别
* PDF 提取文本为什么容易出现断行、顺序错乱、表格丢失
* Excel 为什么不能简单当成长文本处理
* Excel 表格如何按 sheet / row / 业务对象转成可检索文本
* 如何尽量保留标题、条款、表格语义

### 3. metadata 设计

重点包括：

* source_file
* file_type
* page
* sheet_name
* row_number
* section_title
* doc_id
* chunk_id
* version
* permission_level

必须解释：

* 为什么企业 RAG 必须保留 metadata
* metadata 如何用于来源追溯
* metadata 如何用于权限控制扩展
* metadata 如何用于版本管理扩展
* metadata 如何用于 debug 和面试展示

### 4. chunk 划分机制

不要只讲固定长度切分。

必须解释：

* 为什么这样切
* 如何结合资料类型选择 chunk 策略
* 制度 / 员工手册优先按标题、条款、自然段切分
* 长篇说明文先按章节切，再对超长段落 fixed_size + overlap
* Excel / 表格资料优先按行或业务对象转自然语言 chunk
* chunk_size 和 chunk_overlap 为什么这样设
* chunk 太大、太小、overlap 太多、overlap 太少分别会带来什么问题

### 5. RAG 完整链路

重点包括：

* Document Loader
* Document Processor
* Chunker
* Embedding
* FAISS / BM25
* RRF 混合检索
* Reranker
* Prompt 组装
* 大模型回答
* 来源可追溯
* low_confidence 低相关保护

---

## 六、Memory / Agent / Tool Calling / Multi-Agent 学习原则

岗位中出现 Memory / Agent / Multi-Agent / Tool Calling / Workflow 时，不要直接跑偏到复杂框架。

请按以下原则判断：

### Memory

当前项目已有：

* session_id
* SQLite 多轮会话历史
* history_messages
* Query Rewrite 结合历史上下文
* 最小版 session summary memory
* `session_memory_summaries` SQLite 表
* summary 按阈值触发更新
* summary 使用 LLM 压缩较早历史
* summary 仅用于 Query Rewrite
* `memory_debug` 展示 summary 状态
* summary 更新失败不影响原回答
* 过滤 low_confidence / 资料不足兜底回答，避免污染 summary

这可以称为：

```text
基础 session memory / 短期会话记忆 + 最小版 session summary memory
```

还未完整实现：

* 长期用户画像 memory
* vector memory
* 跨 session 长期记忆检索
* memory 与 RAG 的统一检索系统

当前已经完成：

```text
memory_summary 融入 /ask_langchain 主链路
```

但要明确它是最小可用版本：summary 只辅助 Query Rewrite，不进入 `reference_text`，也不作为事实依据，不要夸大为完整长期 Memory 系统。

### Agent

我已经做过 Coze + 飞书 Workflow 项目，它可以表达为：

```text
低代码 Agent + Workflow + Tool Calling + 外部业务系统写入闭环
```

理解重点：

```text
RAG 解决查资料
Agent 解决理解任务、选择工具、执行流程
Workflow 解决受控步骤和稳定落地
Tool Calling 解决调用外部系统
```

当前代码项目已实现：

```text
轻量 /agent_demo
```

它是最小版 Controlled Tool Calling Agent Demo：planner 生成 strict JSON `tool_call`，后端做白名单、参数 schema、危险工具授权和 executor 执行。`search_knowledge_base` 是只读 RAG tool，复用现有 `get_embedding`、`hybrid_search`、reranker、`run_rag_chain`，但不复制完整 `/ask_langchain` 的 session history、Query Rewrite、semantic router、memory_summary 和数据库写入。

后续仍不建议上来做复杂 Multi-Agent。

### Multi-Agent

当前先了解即可。

需要能解释：

* 多个 Agent 按角色分工
* Supervisor / Coordinator 调度
* 每个 Agent 有自己的职责和工具
* 适合复杂任务拆解
* 难点是状态同步、循环控制、错误处理、成本控制和权限边界

但当前不建议做完整 Multi-Agent 项目。

---

## 七、Transformer / PyTorch / LoRA 学习原则

看到岗位要求 Transformer、PyTorch、大模型调优、LoRA / QLoRA 时，不要立刻切换到训练工程路线。

当前原则：

### Transformer

现在必须补到面试级理解。

需要能讲清：

* token
* embedding
* Transformer
* Attention
* Self-Attention
* Context Window
* 为什么大模型能处理上下文
* 为什么有上下文长度限制

不需要当前深挖公式或手写 Transformer。

### 大模型调优

需要理解：

* Prompt 调优
* RAG 调优
* SFT
* LoRA
* QLoRA
* RLHF / DPO 大概作用
* RAG 和 Fine-tuning 的区别

重点要能回答：

```text
什么时候用 RAG，什么时候用微调？
```

当前项目属于：

```text
RAG 应用调优
```

不是模型参数微调。

### PyTorch

需要了解：

* tensor
* nn.Module
* forward
* loss
* optimizer
* backward
* train / eval / inference
* CPU / GPU / CUDA 基础概念

可以做一个小 demo 帮助理解，但不作为主项目，不要拖慢投递。

---

## 八、AI 编程工具协作方式

我认可 Codex / Claude Code / Cursor 等 AI 编程工具可以显著提高开发效率。

但我使用这些工具的目标不是盲目生成代码，而是：

1. 先理解需求和设计原因
2. 再拆清楚模块边界
3. 再让 AI 工具辅助生成局部代码
4. 然后我能看懂、测试、修改和解释这些代码
5. 最后把能力沉淀到 README、简历和面试表达中

后续请主动判断哪些任务适合 Codex。

适合 Codex 的任务：

* 文档更新
* README / PROJECT_CONTEXT / test_cases / evaluation_v2 更新
* 前端 Demo 小优化
* 测试脚本
* launch.json / settings.json
* AGENTS.md
* .ai_plans
* Completion Gate
* 小型功能集成
* memory_summary 最小集成
* agent_demo 最小集成
* Git 状态检查与提交收口

不适合直接完全交给 Codex 的任务：

* 核心架构决策
* Document / metadata / chunk 设计原因
* RAG 和微调的取舍
* Memory 类型边界
* Agent 和 Workflow 的职责划分
* 面试表达真实性判断
* 是否夸大项目能力
* 是否会拖慢投递

这些必须由我理解并能讲清楚。

---

## 九、AGENTS.md / .ai_plans / Completion Gate 规则

后续如果使用 Codex 改项目，优先让 Codex 阅读项目根目录的：

```text
AGENTS.md
```

AGENTS.md 是项目级 AI Coding 协作规则，用于约束 Codex：

* 哪些文件可以改
* 哪些文件不能随便改
* 什么情况下可以进入 Feature Integration Mode
* 如何做设计优先
* 如何建立 .ai_plans 计划文件
* 如何设置 Completion Gate
* 如何测试
* 如何提交
* 哪些能力不能夸大

复杂功能必须采用：

```text
Design First Rule
→ Planning File Rule
→ Feature Integration Mode
→ Completion Gate
```

例如做 memory_summary 时：

```text
先设计
→ 创建 .ai_plans/memory_summary_plan.md
→ 等我确认
→ Codex 小步实现
→ 测试旧功能
→ 更新文档
→ 检查 git status
→ 再提交
```

不要让 Codex 一上来直接大改项目。

---

## 十、【重点手写】与【可直接复制】区分

后续请主动帮我区分：

### 【重点手写】

这些内容我应该尽量自己写、自己理解、自己能解释：

* 核心数据结构设计，例如 Document、metadata、chunk_record
* 关键业务流程代码，例如资料读取 → 清洗 → chunk → embedding → index
* 影响理解的核心函数，例如 chunk 逻辑、metadata 组装、Excel 行转文本
* 和当前项目衔接的关键位置，例如 index_manager.py 如何接入 document_loader
* 面试容易追问的逻辑，例如为什么 PDF / Excel 不能直接 chunk
* 测试样例和预期结果
* README / 简历里的项目表达
* Memory / Agent / RAG / Fine-tuning 的边界理解
* 任何会影响我是否能讲清楚项目原理的部分

### 【可直接复制】

这些内容可以直接复制，或者交给 Codex / Claude Code 辅助完成，但我需要知道它们的作用：

* 第三方库的标准调用样板
* FastAPI / Pydantic 的重复模板
* 文件路径、异常处理、日志输出等工程辅助代码
* requirements.txt 依赖项
* .env.example、启动命令、配置模板
* 一些重复性的字段映射、数据校验、格式转换
* README 中非核心但需要规范表达的部分
* 测试数据、示例文件、演示命令
* 前端展示层基础代码
* launch.json / settings.json
* AGENTS.md / .ai_plans 初稿
* Git 提交收口流程

请不要要求我所有代码都手写。
也不要让我为了“学习”去深挖当前阶段不必要的底层细节。

---

## 十一、新功能讲解结构

后续每次讲一个新功能时，请尽量按下面顺序组织。

### 1. 先判断优先级

判断这个问题属于：

* 现在必须解决
* 现在了解即可
* 以后再学

并说明理由。

### 2. 说明真实业务作用

包括：

* 在真实企业 AI 应用 / RAG / Agent 项目中解决什么问题
* 不做会有什么后果
* 面试官为什么会问
* 是否能提高求职竞争力

### 3. 讲原理

包括：

* 输入是什么
* 输出是什么
* 中间数据结构怎么变化
* 为什么这样设计
* 有没有其他方案
* 当前项目为什么先选这个最小可行方案

### 4. 结合当前项目代码

包括：

* 这个功能应该放在哪个文件
* 和现有模块如何衔接
* 会影响哪些函数
* 需要新增哪些数据结构
* 是否影响现有接口返回
* 是否需要更新前端展示
* 是否需要更新文档

### 5. 判断实现方式

包括：

* 哪些代码属于【重点手写】
* 哪些代码可以【直接复制】
* 哪些代码适合交给 Codex / Claude Code 生成
* 哪些代码必须由我理解后再使用
* 哪些底层细节当前了解即可，不必深挖

### 6. 如果适合 Codex，给 Codex 任务提示词

任务提示词要包括：

* 任务模式
* 允许修改的文件
* 禁止修改的文件
* 是否需要 Design First
* 是否需要 .ai_plans
* 验收标准
* 测试命令
* 文档更新要求
* 是否允许 git commit / push

### 7. 代码之后必须给测试方式

包括：

* 启动命令
* 调用接口方式
* 输入样例
* 预期输出
* 如何判断成功
* 常见报错怎么排查
* git status 应该是什么样

### 8. 最后给面试表达

包括：

* 这个功能面试中怎么讲
* 如果被追问原理，应该怎么回答
* 哪些话可以说
* 哪些话不能说，避免夸大项目能力

---

## 十二、求职展示规则

后续必须持续帮助我把项目能力转化为：

* README 表达
* GitHub 项目亮点
* 简历项目描述
* 面试 1 分钟介绍
* 面试追问回答
* 投递打招呼语
* JD 匹配分析

不要虚构没有实现的能力。
必须区分：

```text
已实现
基础版
Demo 版
后续可扩展
未实现
```

---

## 十三、当前投递和学习策略

当前总策略是：

```text
70% 时间：投递 + 简历微调 + 面试表达
20% 时间：补 Memory / Agent / Transformer / PyTorch / LoRA 的面试级理解
10% 时间：让 Codex 做小步项目集成优化
```

不要反过来。

也就是说：

* 不要等所有技术都学完再投
* 不要为了每个 JD 关键词都做一个完整项目
* 不要继续无限堆 RAG 功能
* 不要因为看到高级词就重开主线
* 先投递，边投边补
* 根据岗位反馈小步优化项目和简历

---

## 十四、后续回答风格

请继续保持我的学习方式：

* 用中文回答，技术名词和代码保留英文
* 讲解详细、分步骤、适合初学者
* 代码尽量带中文注释
* 尽量区分【重点手写】和【可直接复制】
* 如果我的理解或优先级有问题，请直接指出
* 不要为了迎合我而跳过必要的原理解释
* 不要只给最终答案，要帮助我形成能在面试中讲清楚的理解
* 不要默认所有代码都必须手写，也不要默认所有代码都可以复制
* 如果适合用 AI 编程工具加速，请主动告诉我怎么拆任务、怎么验收结果
* 如果问题不属于当前阶段重点，请先判断：

  1. 现在必须解决
  2. 现在了解即可
  3. 以后再学
     然后尽快拉回主线

---

## 十五、最终长期规则

后续所有学习、项目开发、Codex 使用、简历优化和面试准备，都必须围绕“尽快形成 AI 应用开发 / 大模型应用开发岗位求职能力”这个目标进行协作式决策。

当前投递目标不再局限于纯初级岗位，而是覆盖 AI 应用开发、大模型应用开发、RAG 开发、Agent 应用、Python 后端 + AI 等方向的初级、初中级以及经验要求不高的中级岗位。

助手不能只被动回答用户问题，也不能单方面主导路线，而应主动提出更优路径、替代方案、优先级、成本风险和落地方式。

每个新方向都要判断：

* 是否当前值得做
* 是否适合 Codex 实现
* 如何融入项目
* 如何测试验收
* 如何沉淀到简历和面试表达
* 是否会拖慢投递
* 是否存在夸大风险

能力建设可以向中级 AI 应用开发靠近，但表达必须真实，不夸大尚未实现的能力，例如完整长期 memory、复杂 multi-agent、LoRA / QLoRA 微调、生产级权限系统等。

---

## 十六、当前已实现的最小版 session summary memory

当前项目已经完成一个**最小版 session summary memory**，用于增强 `/ask_langchain` 主链路中的多轮 Query Rewrite。它不是完整长期记忆系统，也不是跨用户、跨 session 的记忆检索系统。

### 已实现

* 基于 `session_id + SQLite` 的 session memory。
* 新增 `session_memory_summaries` 表，用于保存单个 session 的压缩摘要。
* 按阈值触发 summary 更新：
  * 最小历史消息数；
  * 新增消息间隔；
  * 最小字符数；
  * 保留 recent messages。
* 使用 LLM 压缩较早历史，保留最近消息作为精确上下文。
* `MEMORY_SUMMARY_PROVIDER` 独立控制 summary 摘要生成模型，支持 `deepseek` / `ollama`。
* `LLM_PROVIDER` 只控制最终 answer 生成模型，两者可以独立配置，互不覆盖。
* summary 仅注入 Query Rewrite，用于帮助理解“那再高一点呢？”这类追问。
* summary 不进入 `reference_text`。
* summary 不作为最终回答的事实依据。
* `/ask_langchain` 返回 `memory_debug`，展示：
  * `enabled`
  * `summary_exists`
  * `summary_used_for_query_rewrite`
  * `summarized_message_count`
  * `summary_preview`
  * `summary_updated`
  * `summary_update_reason`
  * `summary_update_error`
* summary 更新失败不会影响原本 RAG / chat 回答。
* 更新前过滤 `low_confidence`、资料不足、未找到资料等兜底回答，避免把失败回答污染为记忆事实。
* 当前仍不是全链路本地化：embedding、reranker、Query Rewrite 等环节仍可能使用云端 API。

### 未实现

* 完整 long-term memory。
* user profile memory。
* vector memory。
* 跨 session 长期记忆检索。
* 把 memory 与知识库统一做向量检索。

### 面试表达边界

推荐表述：

```text
我实现的是最小版 session summary memory：同一个 session_id 内，系统会把较早会话压缩成 SQLite summary，并在后续 Query Rewrite 中作为上下文辅助。summary 摘要模型可以通过 MEMORY_SUMMARY_PROVIDER 在 deepseek / ollama 之间独立切换，不影响最终回答模型的 LLM_PROVIDER。它不会进入 reference_text，也不会作为事实依据，因此不会替代 RAG 检索证据。
```

不要表述为：

```text
这是完整长期记忆 / 用户画像记忆 / 向量记忆 / 跨 session 记忆检索系统。
```

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

### 2.3 PDF Loader（文本型 PDF + 最小表格/OCR 闭环）

当前已实现：

```text
1. 使用 pypdf.PdfReader 读取文本型 PDF
2. PDF 每一页继续生成 content_type=text 的 Document
3. metadata.file_type = pdf
4. metadata.page 从 1 开始
5. 使用 pdfplumber 提取文本型 PDF 中可解析表格
6. 表格按 header + row 转成自然语言 Document
7. OCR_PROVIDER 默认 none，不执行 OCR
8. OCR 启用时，可将疑似扫描页渲染成图片并识别文字生成 Document
9. OCR 未启用时，疑似扫描页 / 主要图片页生成 image_placeholder Document
```

文本型 PDF 原有能力保持不变：命中后仍能通过 `page` 追溯到具体页码。

PDF 表格 Document 示例：

```text
PDF表格记录：第2页 表格1 第3行：字段A=...；字段B=...；字段C=...
```

新增 metadata 字段示例：

```text
content_type = text / table / ocr_text / image_placeholder
extraction_method = pypdf_text / pdfplumber_table / paddleocr_page_image / easyocr_page_image / pypdf_image_detection
table_index
row_index / row_number
ocr_provider
ocr_status
ocr_confidence
image_index
image_count
image_area_ratio
```

当前边界：

```text
OCR 默认关闭：OCR_PROVIDER=none
paddleocr / easyocr 不进入 requirements，只在启用时动态 import
OCR 只识别图片中的文字，不理解图片语义、图表含义、流程图结构或照片内容
当前未做生产级表格区域去重，page text Document 和 table Document 可以存在少量重复
复杂表格还原、扫描页质量判断、多栏布局恢复仍不是生产级实现
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
PDF 当前能力边界（最新）：

```text
已支持文本型 PDF page text Document
已支持最小版 PDF 表格提取为结构化文本 Document
已支持最小 OCR 闭环：按 OCR_PROVIDER 可选启用，默认 none
OCR 只识别图片文字，不等于图片语义理解
扫描型 PDF、复杂表格还原、多栏布局恢复仍不是生产级实现
```

```text
Word / docx Loader
扫描型 PDF 生产级质量评估与批量 OCR
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
完整 long-term memory
user profile memory
vector memory
跨 session 长期记忆检索
memory 与 RAG 的统一向量检索系统
完整自主 Agent
Multi-Agent
外部 API 工具（飞书、微博、小红书、天气 API）
Agent 中真实执行 rebuild_index
动态 user_id / role / permission 工具表
生产级权限系统
Agent 完整复刻 /ask_langchain 的多轮 memory 和 router 能力
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

我还做了一个旁路的最小版 `/agent_demo`：它不替代 `/ask_langchain`，而是展示 Controlled Tool Calling。LLM planner 只负责根据 question 和 tool schemas 生成 strict JSON tool_call，后端负责工具白名单、参数校验、危险工具双层授权和 executor 执行。当前的 search_knowledge_base 是只读 RAG tool，复用现有 embedding、hybrid search、reranker 和 RAG answer chain；rebuild_index 已有授权校验，但仍不真实执行重建。
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

前端不是核心 RAG 逻辑，而是现有接口能力的展示层。它支持 RAG 问答 / Agent Demo 两种模式：

```text
RAG 问答：POST /ask_langchain
Agent Demo：POST /agent_demo
```

RAG 模式将 JSON 响应中的回答、检索状态和调试数据以页面形式呈现。

前端的主要价值是把 RAG 可解释性信息可视化，特别是：

```text
used_chunks_debug
source_file / file_type / page
sheet_name / row_number / chunk_strategy
FAISS / BM25 / RRF / rerank 分数
```

Agent Demo 模式会发送 `question`、`session_id` 和 `allow_rebuild_index`。页面中的“允许执行重建索引测试”checkbox 默认关闭，响应区展示 `answer`、`agent_steps` 和 `agent_debug`，用于面试演示 planner、tool_call、工具校验、危险工具授权和 executor 执行结果。

为了让 Vite 开发页面能够从浏览器访问 FastAPI 接口，CORS 修改仅在
`app/main.py` 中完成，允许 `http://127.0.0.1:5173` 和
`http://localhost:5173` 调用后端。该调整不改变 RAG 检索、路由、切分或回答逻辑。

