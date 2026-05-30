# Session Memory Summary Plan

## Task Goal

Design and later implement a minimal session-level `memory_summary` mechanism for the existing FastAPI + RAG project.

The summary should be stored in SQLite, tied to `session_id`, and integrated into the existing `/ask_langchain` main chain primarily to improve Query Rewrite for long or compressed multi-turn context.

## Non-Goals

- Do not migrate FAISS retrieval to a vector database.
- Do not add Qdrant, Milvus, Chroma, or another vector memory store.
- Do not implement long-term memory, user profile memory, or vector memory.
- Do not replace `reference_text` with memory content.
- Do not replace existing `session_id` + SQLite chat history.
- Do not change FAISS + BM25 + RRF + reranker retrieval behavior.

## Current Related Files Read

- `AGENTS.md`
- `app/routes_langchain.py`
- `app/chat_history_store.py`
- `app/query_builder.py`
- `app/deepseek_api.py`
- `app/langchain_chains.py`
- `app/config.py`
- `app/main.py`
- `app/models.py`
- `scripts/`

## Current Structure Summary

- `app/main.py` calls `init_chat_db()` during FastAPI startup.
- `app/chat_history_store.py` owns `data/chat_history.db` and currently creates `chat_messages`.
- `app/routes_langchain.py` implements `POST /ask_langchain`:
  - reads `session_id`
  - loads full SQLite history via `get_session_history`
  - handles obvious chat
  - builds route context with `build_route_context`
  - runs semantic routing
  - for RAG, builds `retrieval_query` with `rebuild_retrieval_query_with_llm`
  - keeps FAISS + BM25 + RRF + reranker retrieval unchanged
  - saves each turn with `save_turn`
- `app/query_builder.py` currently uses only recent chat history for route context and Query Rewrite.
- Debug responses already include `retrieval_query`, `history_messages`, `intent_debug`, and chunk-level debug info when `RETURN_DEBUG_INFO` is enabled.

## Expected File Changes

- Modify `app/chat_history_store.py`
  - Add a `session_memory_summaries` SQLite table.
  - Add helper functions such as `get_memory_summary(session_id)` and `upsert_memory_summary(...)`.
  - Keep existing `chat_messages` schema unchanged.

- Modify `app/query_builder.py`
  - Add optional `memory_summary` input to Query Rewrite context assembly.
  - Keep old behavior when no summary exists.
  - Ensure summary is used as supplemental context, not as retrieval evidence.

- Modify `app/routes_langchain.py`
  - Load the summary alongside normal history.
  - Pass summary into Query Rewrite for RAG branch.
  - Return `memory_debug` in response data.
  - Update summary after a successful turn using the saved Q/A context.

- Modify `app/deepseek_api.py` or add a small helper module
  - Add a summarization call for session memory.
  - Prefer a small, constrained prompt that updates the previous summary with the latest turn.

- Possibly modify `app/config.py`
  - Add conservative controls such as `ENABLE_MEMORY_SUMMARY`, `MEMORY_SUMMARY_MIN_MESSAGES`, `MEMORY_SUMMARY_UPDATE_INTERVAL`, `MEMORY_SUMMARY_MIN_CHARS`, `MEMORY_RECENT_MESSAGES_KEEP`, and `MEMORY_SUMMARY_MAX_CHARS`.

- Possibly add `scripts/test_memory_summary.py`
  - Lightweight script or documented manual endpoint checks for normal RAG, follow-up, summary usage, compatibility, and low confidence.

- Later documentation update after implementation
  - `README.md`, `PROJECT_CONTEXT.md`, and/or `test_cases.md`, only after code exists.

## Proposed SQLite Schema

Table: `session_memory_summaries`

Fields:

- `session_id TEXT PRIMARY KEY`
- `summary TEXT NOT NULL`
- `summarized_message_count INTEGER NOT NULL`
- `updated_at TEXT NOT NULL`

`summarized_message_count` means the summary has already covered chat history up to this message count for the current `session_id`.

Migration impact:

- Safe additive migration through `CREATE TABLE IF NOT EXISTS`.
- No existing `chat_messages` columns are changed.
- Existing chat history remains readable.

## Data Flow

1. `/ask_langchain` receives `question` and `session_id`.
2. Existing history is loaded from `chat_messages`.
3. Existing session summary is loaded from `session_memory_summaries`.
4. Router continues to use existing recent history only in v1, unless we explicitly decide to add summary to route context later.
5. RAG branch calls Query Rewrite with:
   - previous summary if present
   - recent messages controlled by `MEMORY_RECENT_MESSAGES_KEEP`
   - current question
6. Retrieval still uses the rewritten query:
   - embedding
   - FAISS
   - BM25
   - RRF
   - reranker
7. Final answer still uses only `retrieval_query` + `reference_text`.
8. `memory_summary` does not enter `reference_text` and is not treated as factual evidence.
9. After response generation and before/after saving the turn, update session summary if thresholds are met.
10. Summary update is incremental: `previous_summary + newly added conversation messages -> updated_summary`.
11. Response includes `memory_debug`.

## Summary Trigger Conditions

Proposed config defaults:

- `ENABLE_MEMORY_SUMMARY = True`
- `MEMORY_SUMMARY_MIN_MESSAGES = 10`
- `MEMORY_SUMMARY_UPDATE_INTERVAL = 6`
- `MEMORY_SUMMARY_MIN_CHARS = 3000`
- `MEMORY_RECENT_MESSAGES_KEEP = 4`
- `MEMORY_SUMMARY_MAX_CHARS = 800`

Update rules:

- Do not create a summary before the session has at least `MEMORY_SUMMARY_MIN_MESSAGES` messages.
- Do not update on every request; update only when at least `MEMORY_SUMMARY_UPDATE_INTERVAL` new messages exist beyond `summarized_message_count`.
- Do not summarize very short sessions unless accumulated unsummarized text reaches `MEMORY_SUMMARY_MIN_CHARS`.
- Keep the newest `MEMORY_RECENT_MESSAGES_KEEP` messages outside the summary so Query Rewrite can use both compressed older context and exact recent context.
- Keep summary length around `MEMORY_SUMMARY_MAX_CHARS`.

## Incremental Summary Strategy

- First summary:
  - summarize eligible older messages only.
  - leave the most recent `MEMORY_RECENT_MESSAGES_KEEP` messages unsummarized for exact recent context.
- Later updates:
  - read `previous_summary`.
  - select only messages after `summarized_message_count`, excluding the newest `MEMORY_RECENT_MESSAGES_KEEP` messages.
  - ask the model to merge `previous_summary` with the newly eligible messages.
  - write back `updated_summary` and the new `summarized_message_count`.
- Do not repeatedly summarize the full chat history.
- If summary update fails, keep the previous summary unchanged and continue the RAG answer path.

## Summarization Prompt Principles

- Keep only information useful for later understanding of user intent, references, constraints, entities, unfinished tasks, or follow-up questions.
- Remove greetings, thanks, filler, repeated assistant explanations, and irrelevant small talk.
- Do not add external knowledge.
- Do not infer or fabricate facts that were not present in the conversation.
- Preserve important user-stated facts and business context in concise language.
- Keep the output within `MEMORY_SUMMARY_MAX_CHARS`.

## Proposed `memory_debug`

Always return a backward-compatible optional field when available:

```json
{
  "enabled": true,
  "summary_exists": true,
  "summary_used_for_query_rewrite": true,
  "summary_updated": true,
  "summarized_message_count": 12,
  "summary_preview": "..."
}
```

For chat or no-summary cases:

```json
{
  "enabled": true,
  "summary_exists": false,
  "summary_used_for_query_rewrite": false,
  "summary_updated": false,
  "summarized_message_count": 0
}
```

Do not include full summary by default if it becomes long; use a preview to avoid noisy or sensitive debug output.

## API Impact

- Existing request body remains unchanged.
- Existing response fields remain unchanged.
- New `memory_debug` response field is additive and optional/backward compatible.
- `/ask_langchain` remains the main endpoint.

## Backward Compatibility

- No change to FAISS/BM25/RRF/reranker pipeline.
- No change to `reference_text` construction.
- `memory_summary` is used mainly for Query Rewrite and is never included in `reference_text` or treated as source evidence.
- No change to existing `chat_messages` table.
- If summary table is empty or summarization fails, Query Rewrite falls back to existing recent-history behavior.
- Existing `session_id` semantics stay intact.

## Step-by-Step Implementation Plan

- [x] Read AGENTS and current related code.
- [x] Create planning file before coding.
- [ ] Add SQLite summary table and helper functions.
- [ ] Add config flags and conservative thresholds.
- [ ] Extend Query Rewrite context to optionally include memory summary.
- [ ] Integrate summary load/use/update in `/ask_langchain`.
- [ ] Add `memory_debug` to matched, low_confidence, chat, and error-safe paths where practical.
- [ ] Ensure `ENABLE_MEMORY_SUMMARY=False` fully preserves old behavior.
- [ ] Ensure summary update failures do not fail normal RAG answers.
- [ ] Add or document targeted memory regression tests.
- [ ] Update docs after implementation.
- [ ] Run backend syntax checks and relevant manual/API tests.

## Test Checklist

- Normal RAG question:
  - `事假怎么申请？`
  - Expected: existing matched behavior remains stable.

- Multi-turn follow-up:
  - First: `报销500到2000元怎么审批？`
  - Follow-up: `那再高一点呢？`
  - Expected: Query Rewrite still resolves the higher amount case.

- Summary usage:
  - Build a session with enough turns to create summary.
  - Ask a short follow-up that depends on earlier context outside recent messages.
  - Expected: `memory_debug.summary_used_for_query_rewrite=true`.

- Disabled memory compatibility:
  - Set `ENABLE_MEMORY_SUMMARY=False`.
  - Ask normal RAG and multi-turn follow-up questions.
  - Expected: old history-based Query Rewrite behavior is preserved and no summary is used.

- Summary update failure:
  - Simulate summarization model/API failure.
  - Expected: RAG answer still succeeds or reaches the same retrieval fallback path; `memory_debug.summary_update_error` records the failure.

- Low confidence:
  - `公司年终奖发放规则是什么？`
  - Expected: `retriever_status=low_confidence`; memory does not fabricate reference evidence.

- Compatibility:
  - Existing request body without any new field still works.
  - Existing `session_id` and SQLite history still work.

## Risks And Rollback Notes

- Extra LLM call for summary update may add latency and cost.
  - Mitigation: threshold-based updates and config flag.

- Summary may over-compress or introduce incorrect context.
  - Mitigation: use summary only for Query Rewrite, never as `reference_text`.

- Debug output could expose too much conversation content.
  - Mitigation: return preview or metadata only.

- Summarization failure should not fail the RAG answer.
  - Mitigation: catch summary update errors and set `memory_debug.summary_update_error`.

- Rollback is simple:
  - Disable config flag or stop reading summary.
  - Leave additive SQLite table unused.
