# AI Customer Support Triage Agent

**Author:** Saud Alzahrani
**Programme / cohort:** BuildAgentCap — cohort dated 16 Aug 2026
**Declared track:** Track A — Supervisor/Router

## Project Description

A multi-agent customer support system built with LangGraph's **Functional API**
(`@task` / `@entrypoint`, not `StateGraph`). A dedicated supervisor node classifies
each incoming support ticket using an LLM structured-output call (Pydantic schema:
`category`, `urgency`) and routes it to one of three specialist worker agents:
billing, technical, or refund. Workers do their job and return — they never hand off
to each other or decide routing themselves, which is what makes this Track A
(Orchestrator-Worker) rather than a peer-to-peer handoff design.

Each specialist agent answers questions using **RAG** over a local knowledge base of
15 mock support articles (billing policy, refund policy, troubleshooting guides),
embedded locally with `sentence-transformers` and stored in a local **Chroma**
vector store — no embedding API key required.

The system persists:
- **Short-term state** — per-ticket, multi-turn conversation memory via a LangGraph
  `Checkpointer` keyed by `thread_id`.
- **Long-term state** — durable, cross-thread customer facts (e.g. prior disputes)
  via a LangGraph `Store` keyed by `customer_id`.

Before any refund is finalized, the graph **pauses for human approval** using
`interrupt()` and resumes via `Command(resume=...)`. Tool calls that fail
intermittently (a mock `check_order_status` that raises ~30% of the time) are
protected by a `RetryPolicy`, with a fallback/escalation path if the LLM itself
fails after retries. All runs are traced in **LangSmith**.

## Architecture

```
Customer message
      │
      ▼
[Supervisor node] ── structured output (Pydantic) classifies:
      │                category: billing | technical | refund
      │                urgency: low | medium | high
      ▼
  ┌───────────────┬────────────────┬──────────────┐
  ▼               ▼                ▼
[Billing agent] [Technical agent] [Refund agent]
  │               │                │
  │ RAG lookup     │ RAG lookup     │ interrupt() before
  │ over FAQ docs  │ over docs      │ approving refund
  │                                 │ → Command(resume=...)
  ▼               ▼                ▼
        [Response returned to customer]
        [Long-term memory updated: Store]
        [Short-term state saved: Checkpointer, thread_id]
```

This is an **Orchestrator-Worker** pattern: a single supervisor makes all routing
decisions via structured LLM output, and specialist workers execute their task
without any peer-to-peer handoff logic.

## Tech Stack

| Component | Tool/Library | API Key Needed? |
|---|---|---|
| LLM (routing, classification, generation) | Groq (`langchain-groq`) | Yes — `GROQ_API_KEY` |
| Embeddings (RAG) | `sentence-transformers`, local `all-MiniLM-L6-v2` | No |
| Vector store | Chroma (local, on-disk) | No |
| Orchestration | LangGraph Functional API (`@task`/`@entrypoint`) | No |
| Short-term memory | LangGraph `MemorySaver` checkpointer | No |
| Long-term memory | LangGraph `InMemoryStore` | No |
| Observability | LangSmith | Yes — `LANGCHAIN_API_KEY` |

## How to Run

1. **Create and activate a virtual environment** (Python 3.11+; developed and
   verified on 3.14):

   ```bash
   python -m venv .venv
   .venv\Scripts\activate
   ```

2. **Install dependencies:**

   ```bash
   pip install -r requirements.txt
   ```

3. **Set up your `.env` file** — copy `.env.example` to `.env` and fill in your own
   keys. `.env` is git-ignored and must never be committed.

   ```bash
   cp .env.example .env
   ```

   Required keys:
   - `GROQ_API_KEY` — from [console.groq.com](https://console.groq.com)
   - `LANGCHAIN_API_KEY` — from [smith.langchain.com](https://smith.langchain.com)
   - `LANGCHAIN_TRACING_V2=true` — **exact variable name**, not `LANGSMITH_TRACING_V2`

4. **Launch Jupyter and run the notebook top to bottom** after restarting the
   kernel, so all captured output reflects a clean run:

   ```bash
   jupyter notebook support_agent.ipynb
   ```

   The first RAG-related cell will build a local Chroma index under `chroma_db/`
   (git-ignored, regenerated automatically — safe to delete).

## Repository Structure

```
.
├── support_agent.ipynb      # Main notebook — all sections, run top to bottom
├── mock_data.py              # Mock customers/orders read by tools
├── knowledge_base/           # 15 mock FAQ/policy articles used for RAG
├── requirements.txt
├── .env.example               # Template — copy to .env and fill in real keys
├── .gitignore
└── README.md
```

## RAG Strategy: 2-Step vs. Agentic vs. Hybrid

This project uses **2-Step (retrieve-then-generate) RAG** for the billing and
technical specialist agents: each worker issues a single retrieval query built
directly from the ticket text, then generates its answer conditioned on the
retrieved chunks in one pass. This was chosen over Agentic RAG (where the LLM
decides iteratively whether/what to retrieve, possibly issuing multiple retrieval
calls) because support-ticket questions map cleanly onto a small, well-scoped
knowledge base — multi-hop or iterative retrieval isn't needed to answer "what's
your refund window" or "why did sync fail." A Hybrid approach (2-Step retrieval,
but letting the agent decide *whether* to retrieve at all vs. answer from the
ticket/customer context alone) was considered, since not every ticket needs a
knowledge-base lookup, but was set aside for this capstone to keep the RAG path
deterministic and easy to verify against the required "verbatim answer" test.
Full reasoning and the retrieval test are shown in Section 3 of the notebook.

## Deliverables Checklist

- [x] Full name in header (Saud Alzahrani)
- [x] Kernel restarted, notebook run top to bottom, output captured (`jupyter nbconvert --execute`, 0 errors across all 18 code cells)
- [x] Interrupt and resume both ran with visible output (approval and rejection paths, Section 5)
- [x] Cross-thread long-term memory test shown (Thread A write → Thread B read, Section 4)
- [x] No API keys in code or git history (`.env` git-ignored, `.env.example` only)
- [x] No placeholder/TODO text left, except the one intentional line asking you to fill in your own LangSmith trace observation after you open the UI (Section 8) — everything else is real captured output
- [x] Declared track (A) stated explicitly
- [x] Write-up per section matches actual notebook output (verified against the executed `support_agent.ipynb`)
- [x] README: project description + how to run + programme name & cohort dates (programme name still a placeholder — fill in `[PROGRAMME NAME]` above)
- [x] `.gitignore` excludes `.env` and generated files
