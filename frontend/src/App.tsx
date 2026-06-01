import { FormEvent, useMemo, useState } from "react";

const API_BASE_URL =
  import.meta.env.VITE_API_BASE_URL ?? "http://127.0.0.1:8000";

type DemoMode = "rag" | "agent";

interface ChunkMetadata {
  source_file?: string;
  file_type?: string;
  page?: number | string;
  sheet_name?: string;
  row_number?: number | string;
  chunk_strategy?: string;
}

interface UsedChunk {
  text?: string;
  metadata?: ChunkMetadata;
  faiss_score?: number;
  bm25_score?: number;
  rrf_score?: number;
  rerank_score?: number;
}

interface MemoryDebug {
  enabled?: boolean;
  summary_exists?: boolean;
  summary_used_for_query_rewrite?: boolean;
  summarized_message_count?: number;
  summary_preview?: string;
  summary_updated?: boolean;
  summary_update_reason?: string;
  summary_update_error?: string | null;
  summary_provider?: string;
  memory_summary_provider?: string;
}

interface AnswerData {
  answer?: string;
  intent?: string;
  retriever_status?: string;
  retrieval_query?: string;
  reference_text?: string;
  used_chunks_debug?: UsedChunk[];
  answer_llm_provider?: string | null;
  answer_llm_model?: string | null;
  answer_llm_is_local?: boolean;
  memory_debug?: MemoryDebug;
}

interface AgentStep {
  step?: number;
  stage?: string;
  status?: string;
  tool_name?: string;
  tool_call?: unknown;
  result?: unknown;
}

interface AgentDebug {
  planner?: string;
  available_tools?: string[];
  allow_rebuild_index?: boolean;
  blocked?: boolean;
  tool_name?: string | null;
  execution_status?: string | null;
}

interface AgentData {
  answer?: string;
  agent_mode?: string;
  agent_steps?: AgentStep[];
  agent_debug?: AgentDebug;
}

interface ApiResponse<T> {
  success: boolean;
  message?: string;
  data?: T;
  error?: string | null;
}

function displayValue(value: unknown): string {
  return value === null || value === undefined || value === "" ? "-" : String(value);
}

function formatScore(score: number | undefined): string {
  return score === undefined || score === null ? "-" : score.toFixed(6);
}

function summarizeText(text = ""): string {
  const compactText = text.replace(/\s+/g, " ").trim();
  return compactText.length > 180 ? `${compactText.slice(0, 180)}...` : compactText || "-";
}

function formatJson(value: unknown): string {
  if (value === null || value === undefined || value === "") {
    return "-";
  }

  try {
    return JSON.stringify(value, null, 2);
  } catch {
    return String(value);
  }
}

export default function App() {
  const [mode, setMode] = useState<DemoMode>("rag");
  const [question, setQuestion] = useState("产品入门训练营报名截止是什么时候？");
  const [sessionId, setSessionId] = useState("frontend_demo_001");
  const [allowRebuildIndex, setAllowRebuildIndex] = useState(false);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");
  const [ragResult, setRagResult] = useState<AnswerData | null>(null);
  const [agentResult, setAgentResult] = useState<AgentData | null>(null);

  const chunks = useMemo(() => ragResult?.used_chunks_debug ?? [], [ragResult]);
  const memoryDebug = ragResult?.memory_debug;
  const agentSteps = agentResult?.agent_steps ?? [];
  const agentDebug = agentResult?.agent_debug;

  async function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    const trimmedQuestion = question.trim();
    const trimmedSessionId = sessionId.trim();

    if (!trimmedQuestion) {
      setError("请输入问题。");
      return;
    }

    if (!trimmedSessionId) {
      setError("请输入 session_id。");
      return;
    }

    setLoading(true);
    setError("");
    setRagResult(null);
    setAgentResult(null);

    try {
      const endpoint = mode === "rag" ? "/ask_langchain" : "/agent_demo";
      // RAG 模式保持原有请求体；Agent 模式额外携带后端授权上下文。
      const requestBody =
        mode === "rag"
          ? {
              question: trimmedQuestion,
              session_id: trimmedSessionId,
            }
          : {
              question: trimmedQuestion,
              session_id: trimmedSessionId,
              allow_rebuild_index: allowRebuildIndex,
            };

      const response = await fetch(`${API_BASE_URL}${endpoint}`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(requestBody),
      });

      const payload = (await response.json()) as ApiResponse<AnswerData | AgentData>;

      if (!response.ok || !payload.success) {
        throw new Error(payload.error || payload.message || `请求失败 (${response.status})`);
      }

      if (mode === "rag") {
        setRagResult((payload.data as AnswerData) ?? null);
      } else {
        setAgentResult((payload.data as AgentData) ?? null);
      }
    } catch (requestError) {
      const message =
        requestError instanceof Error ? requestError.message : "请求后端服务失败。";
      setError(message);
    } finally {
      setLoading(false);
    }
  }

  return (
    <main className="page">
      <header className="header">
        <p className="eyebrow">FastAPI + RAG + Agent</p>
        <h1>企业知识库问答 Demo</h1>
        <p className="subtitle">
          在 RAG 问答和 Controlled Tool Calling Agent Demo 之间切换，展示检索证据与工具调用步骤。
        </p>
      </header>

      <form className="ask-form" onSubmit={handleSubmit}>
        <div className="mode-switch" role="group" aria-label="Demo mode">
          <button
            type="button"
            className={mode === "rag" ? "active" : ""}
            onClick={() => setMode("rag")}
          >
            RAG 问答
          </button>
          <button
            type="button"
            className={mode === "agent" ? "active" : ""}
            onClick={() => setMode("agent")}
          >
            Agent Demo
          </button>
        </div>

        <label>
          <span>问题</span>
          <textarea
            value={question}
            onChange={(event) => setQuestion(event.target.value)}
            placeholder="请输入希望查询的知识库问题"
            rows={4}
          />
        </label>

        <div className="form-footer">
          <label className="session-field">
            <span>session_id</span>
            <input
              value={sessionId}
              onChange={(event) => setSessionId(event.target.value)}
              placeholder="frontend_demo_001"
            />
          </label>

          {mode === "agent" && (
            <label className="checkbox-field">
              <input
                type="checkbox"
                checked={allowRebuildIndex}
                onChange={(event) => setAllowRebuildIndex(event.target.checked)}
              />
              <span>允许执行重建索引测试</span>
            </label>
          )}

          <button className="submit-button" type="submit" disabled={loading}>
            {loading ? "查询中..." : "发送问题"}
          </button>
        </div>
      </form>

      {loading && <div className="notice loading">正在请求后端并生成展示结果，请稍等...</div>}
      {error && <div className="notice error">{error}</div>}

      {ragResult && (
        <section className="results">
          <article className="answer-card">
            <h2>回答</h2>
            <p className="answer">{displayValue(ragResult.answer)}</p>
            <dl className="status-grid">
              <div>
                <dt>intent</dt>
                <dd>{displayValue(ragResult.intent)}</dd>
              </div>
              <div>
                <dt>retriever_status</dt>
                <dd>{displayValue(ragResult.retriever_status)}</dd>
              </div>
              <div className="wide">
                <dt>retrieval_query</dt>
                <dd>{displayValue(ragResult.retrieval_query)}</dd>
              </div>
              <div>
                <dt>answer_llm_provider</dt>
                <dd>{displayValue(ragResult.answer_llm_provider)}</dd>
              </div>
              <div>
                <dt>answer_llm_model</dt>
                <dd>{displayValue(ragResult.answer_llm_model)}</dd>
              </div>
              <div>
                <dt>answer_llm_is_local</dt>
                <dd>{displayValue(ragResult.answer_llm_is_local)}</dd>
              </div>
            </dl>
          </article>

          <article className="debug-panel memory-panel">
            <div className="panel-title">
              <h2>memory_debug</h2>
              <span>session summary</span>
            </div>
            {/* memory_debug 是后端可选调试字段；缺失字段统一显示 "-"，避免旧响应报错。 */}
            <dl className="memory-grid">
              <div>
                <dt>enabled</dt>
                <dd>{displayValue(memoryDebug?.enabled)}</dd>
              </div>
              <div>
                <dt>summary_exists</dt>
                <dd>{displayValue(memoryDebug?.summary_exists)}</dd>
              </div>
              <div>
                <dt>summary_used_for_query_rewrite</dt>
                <dd>{displayValue(memoryDebug?.summary_used_for_query_rewrite)}</dd>
              </div>
              <div>
                <dt>summary_updated</dt>
                <dd>{displayValue(memoryDebug?.summary_updated)}</dd>
              </div>
              <div>
                <dt>summary_update_reason</dt>
                <dd>{displayValue(memoryDebug?.summary_update_reason)}</dd>
              </div>
              <div>
                <dt>summary_update_error</dt>
                <dd>{displayValue(memoryDebug?.summary_update_error)}</dd>
              </div>
              <div>
                <dt>summarized_message_count</dt>
                <dd>{displayValue(memoryDebug?.summarized_message_count)}</dd>
              </div>
              <div>
                <dt>summary_provider</dt>
                <dd>
                  {displayValue(
                    memoryDebug?.summary_provider ?? memoryDebug?.memory_summary_provider,
                  )}
                </dd>
              </div>
              <div className="wide">
                <dt>summary_preview</dt>
                <dd>{displayValue(memoryDebug?.summary_preview)}</dd>
              </div>
            </dl>
          </article>

          <article className="debug-panel">
            <div className="panel-title">
              <h2>used_chunks_debug</h2>
              <span>{chunks.length} chunks</span>
            </div>

            {chunks.length === 0 ? (
              <p className="empty">当前响应未包含命中的 chunk 调试数据。</p>
            ) : (
              <div className="chunk-list">
                {chunks.map((chunk, index) => (
                  <section className="chunk-card" key={`${chunk.metadata?.source_file}-${index}`}>
                    <h3>Chunk {index + 1}</h3>
                    <p className="chunk-text">{summarizeText(chunk.text)}</p>
                    <dl className="detail-grid">
                      <div>
                        <dt>source_file</dt>
                        <dd>{displayValue(chunk.metadata?.source_file)}</dd>
                      </div>
                      <div>
                        <dt>file_type</dt>
                        <dd>{displayValue(chunk.metadata?.file_type)}</dd>
                      </div>
                      <div>
                        <dt>page</dt>
                        <dd>{displayValue(chunk.metadata?.page)}</dd>
                      </div>
                      <div>
                        <dt>sheet_name</dt>
                        <dd>{displayValue(chunk.metadata?.sheet_name)}</dd>
                      </div>
                      <div>
                        <dt>row_number</dt>
                        <dd>{displayValue(chunk.metadata?.row_number)}</dd>
                      </div>
                      <div>
                        <dt>chunk_strategy</dt>
                        <dd>{displayValue(chunk.metadata?.chunk_strategy)}</dd>
                      </div>
                      <div>
                        <dt>faiss_score</dt>
                        <dd>{formatScore(chunk.faiss_score)}</dd>
                      </div>
                      <div>
                        <dt>bm25_score</dt>
                        <dd>{formatScore(chunk.bm25_score)}</dd>
                      </div>
                      <div>
                        <dt>rrf_score</dt>
                        <dd>{formatScore(chunk.rrf_score)}</dd>
                      </div>
                      <div>
                        <dt>rerank_score</dt>
                        <dd>{formatScore(chunk.rerank_score)}</dd>
                      </div>
                    </dl>
                  </section>
                ))}
              </div>
            )}
          </article>
        </section>
      )}

      {agentResult && (
        <section className="results">
          <article className="answer-card">
            <h2>Agent 回答</h2>
            <p className="answer">{displayValue(agentResult.answer)}</p>
            <dl className="status-grid">
              <div className="wide">
                <dt>agent_mode</dt>
                <dd>{displayValue(agentResult.agent_mode)}</dd>
              </div>
            </dl>
          </article>

          <article className="debug-panel agent-debug-panel">
            <div className="panel-title">
              <h2>agent_debug</h2>
              <span>controlled tool calling</span>
            </div>
            {/* Agent debug 用于面试演示：展示 planner、工具白名单、授权上下文和执行状态。 */}
            <dl className="agent-debug-grid">
              <div>
                <dt>planner</dt>
                <dd>{displayValue(agentDebug?.planner)}</dd>
              </div>
              <div>
                <dt>available_tools</dt>
                <dd>{displayValue(agentDebug?.available_tools?.join(", "))}</dd>
              </div>
              <div>
                <dt>allow_rebuild_index</dt>
                <dd>{displayValue(agentDebug?.allow_rebuild_index)}</dd>
              </div>
              <div>
                <dt>blocked</dt>
                <dd>{displayValue(agentDebug?.blocked)}</dd>
              </div>
              <div>
                <dt>tool_name</dt>
                <dd>{displayValue(agentDebug?.tool_name)}</dd>
              </div>
              <div>
                <dt>execution_status</dt>
                <dd>{displayValue(agentDebug?.execution_status)}</dd>
              </div>
            </dl>
          </article>

          <article className="debug-panel">
            <div className="panel-title">
              <h2>agent_steps</h2>
              <span>{agentSteps.length} steps</span>
            </div>

            {agentSteps.length === 0 ? (
              <p className="empty">当前响应未包含 agent_steps。</p>
            ) : (
              <div className="agent-step-list">
                {agentSteps.map((step, index) => (
                  <section className="agent-step-card" key={`${step.stage}-${index}`}>
                    <div className="agent-step-heading">
                      <h3>Step {displayValue(step.step ?? index + 1)}</h3>
                      <span>{displayValue(step.status)}</span>
                    </div>
                    <dl className="agent-step-grid">
                      <div>
                        <dt>stage</dt>
                        <dd>{displayValue(step.stage)}</dd>
                      </div>
                      <div>
                        <dt>tool_name</dt>
                        <dd>{displayValue(step.tool_name)}</dd>
                      </div>
                      <div>
                        <dt>tool_call</dt>
                        <dd>
                          <pre>{formatJson(step.tool_call)}</pre>
                        </dd>
                      </div>
                      <div>
                        <dt>result</dt>
                        <dd>
                          <pre>{formatJson(step.result)}</pre>
                        </dd>
                      </div>
                    </dl>
                  </section>
                ))}
              </div>
            )}
          </article>
        </section>
      )}
    </main>
  );
}
