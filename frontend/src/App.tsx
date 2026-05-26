import { FormEvent, useMemo, useState } from "react";

const API_BASE_URL =
  import.meta.env.VITE_API_BASE_URL ?? "http://127.0.0.1:8000";

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
}

interface AskResponse {
  success: boolean;
  message?: string;
  data?: AnswerData;
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

export default function App() {
  const [question, setQuestion] = useState("产品入门训练营报名截止是什么时候？");
  const [sessionId, setSessionId] = useState("frontend_demo_001");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");
  const [result, setResult] = useState<AnswerData | null>(null);

  const chunks = useMemo(() => result?.used_chunks_debug ?? [], [result]);

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
    setResult(null);

    try {
      const response = await fetch(`${API_BASE_URL}/ask_langchain`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          question: trimmedQuestion,
          session_id: trimmedSessionId,
        }),
      });

      const payload = (await response.json()) as AskResponse;

      if (!response.ok || !payload.success) {
        throw new Error(payload.error || payload.message || `请求失败 (${response.status})`);
      }

      setResult(payload.data ?? null);
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
        <p className="eyebrow">FastAPI + RAG</p>
        <h1>企业知识库问答 Demo</h1>
        <p className="subtitle">
          向知识库提问，并查看检索命中的 chunk 与打分明细。
        </p>
      </header>

      <form className="ask-form" onSubmit={handleSubmit}>
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
          <button type="submit" disabled={loading}>
            {loading ? "查询中..." : "发送问题"}
          </button>
        </div>
      </form>

      {loading && <div className="notice loading">正在检索并生成回答，请稍候...</div>}
      {error && <div className="notice error">{error}</div>}

      {result && (
        <section className="results">
          <article className="answer-card">
            <h2>回答</h2>
            <p className="answer">{displayValue(result.answer)}</p>
            <dl className="status-grid">
              <div>
                <dt>intent</dt>
                <dd>{displayValue(result.intent)}</dd>
              </div>
              <div>
                <dt>retriever_status</dt>
                <dd>{displayValue(result.retriever_status)}</dd>
              </div>
              <div className="wide">
                <dt>retrieval_query</dt>
                <dd>{displayValue(result.retrieval_query)}</dd>
              </div>
              <div>
                <dt>answer_llm_provider</dt>
                <dd>{displayValue(result.answer_llm_provider)}</dd>
              </div>
              <div>
                <dt>answer_llm_model</dt>
                <dd>{displayValue(result.answer_llm_model)}</dd>
              </div>
              <div>
                <dt>answer_llm_is_local</dt>
                <dd>{displayValue(result.answer_llm_is_local)}</dd>
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
    </main>
  );
}
