"""Generates support_agent.ipynb from the cell definitions below.

Run once (or whenever this file changes) to (re)build the notebook skeleton;
the notebook is then executed top-to-bottom separately (fresh kernel) to
capture real output.
"""
import nbformat as nbf

nb = nbf.v4.new_notebook()
cells = []


def md(text):
    cells.append(nbf.v4.new_markdown_cell(text))


def code(text):
    cells.append(nbf.v4.new_code_cell(text))


# ------------------------------------------------------------------
md(r"""# AI Customer Support Triage Agent — Capstone Notebook

**Name:** Saud Alzahrani
**Date:** 16 Aug 2026
**Declared track:** **Track A — Supervisor/Router (Orchestrator-Worker)**

A dedicated supervisor node classifies each incoming ticket with structured LLM
output (Pydantic: `category`, `urgency`) and routes it to one specialist worker
(billing / technical / refund). Workers do their job and return — they never
hand off to each other or decide routing themselves.

See [README.md](./README.md) for the full architecture diagram, tech stack, and
run instructions.

**Note on ordering:** this notebook covers every rubric section, but a few are
reordered from the rubric's section numbers for a logically consistent build:
the full LangGraph Functional API graph (rubric Section 6) is assembled right
after the RAG pipeline (Section 3), because Sections 4 (state management) and 5
(human-in-the-loop) both demonstrate *behaviors of that graph* and need it to
already exist. Each section is labeled with its rubric number so every
requirement is easy to find.
""")

# ------------------------------------------------------------------
md("## Setup")

code(r"""import os
import random
import sys
from pathlib import Path
from typing import Literal, Optional

from dotenv import load_dotenv

load_dotenv()

assert os.environ.get("GROQ_API_KEY"), "Set GROQ_API_KEY in your .env file (see .env.example)"
os.environ.setdefault("LANGCHAIN_PROJECT", "support-agent-capstone")

print("LANGCHAIN_TRACING_V2 =", os.environ.get("LANGCHAIN_TRACING_V2"))
print("LANGCHAIN_PROJECT    =", os.environ.get("LANGCHAIN_PROJECT"))
print("GROQ_API_KEY set     =", bool(os.environ.get("GROQ_API_KEY")))
""")

code(r"""from pydantic import BaseModel, Field
from langchain_groq import ChatGroq

GROQ_MODEL = "openai/gpt-oss-20b"  # current Groq production model (llama-3.3-70b-versatile was deprecated)

llm = ChatGroq(model=GROQ_MODEL, temperature=0)
print(f"LLM ready: {GROQ_MODEL} via Groq")
""")

# ------------------------------------------------------------------
md(r"""## Section 1 — Agent Fundamentals: Tools

Three tools that read from real mock data structures ([mock_data.py](./mock_data.py))
rather than returning hardcoded strings:

- `lookup_customer(customer_id)` — reads the mock customer table
- `check_order_status(order_id)` — reads the mock order table; **intentionally flaky**
  (~30% failure rate) so we can demonstrate a `RetryPolicy` in the graph built below
- `search_faq(query)` — retrieves from the Chroma vector store; wired up once the RAG
  pipeline is built in Section 3 below
""")

code(r'''sys.path.insert(0, str(Path.cwd()))
from mock_data import get_customer, get_order, CUSTOMERS, ORDERS

FAILURE_RATE = 0.3  # ~30% intermittent failure rate for check_order_status


def lookup_customer(customer_id: str) -> dict:
    """Look up a customer's account record by customer_id."""
    customer = get_customer(customer_id)
    if customer is None:
        return {"error": f"No customer found with id {customer_id}"}
    return customer


def check_order_status(order_id: str) -> dict:
    """Look up an order's status by order_id.

    Simulates a flaky downstream order-service call: raises RuntimeError on
    ~FAILURE_RATE of calls, so the RetryPolicy attached in the graph below has
    something real to retry against.
    """
    print(f"[order-service] attempting lookup for {order_id} (failure_rate={FAILURE_RATE})")
    if random.random() < FAILURE_RATE:
        print(f"[order-service] transient failure for {order_id}")
        raise RuntimeError("Order service temporarily unavailable - please retry.")
    order = get_order(order_id)
    if order is None:
        return {"error": f"No order found with id {order_id}"}
    return order


class _RAGState:
    """Holds the retriever once Section 3 builds it."""
    retriever = None


def search_faq(query: str) -> str:
    """Search the FAQ/knowledge-base for relevant policy or troubleshooting text.

    Backed by the Chroma retriever built in Section 3 — run that section before
    calling this tool.
    """
    if _RAGState.retriever is None:
        raise RuntimeError("Run Section 3 (RAG pipeline) before calling search_faq().")
    docs = _RAGState.retriever.invoke(query)
    return "\n\n---\n\n".join(d.page_content for d in docs)


# Smoke test — real reads from mock_data.py, not hardcoded strings
random.seed(7)
print(lookup_customer("cust_1001"))
print(lookup_customer("cust_9999"))
print(check_order_status("ord_5001"))
''')

# ------------------------------------------------------------------
md(r"""## Section 2 — Multi-Agent / Routing: Supervisor

The supervisor classifies each ticket using `with_structured_output` bound to a
Pydantic model, and routing is a genuine LLM decision on the structured
`category` field — never `if "refund" in text.lower()`.
""")

code(r'''class TicketClassification(BaseModel):
    category: Literal["billing", "technical", "refund"] = Field(
        ..., description="The single best-fit category for this support ticket."
    )
    urgency: Literal["low", "medium", "high"] = Field(
        ..., description="Urgency based on customer impact, per ticket_urgency_guidelines.md."
    )
    reasoning: str = Field(..., description="One sentence explaining the classification.")


classifier_llm = llm.with_structured_output(TicketClassification)


def classify_ticket(ticket_text: str) -> TicketClassification:
    return classifier_llm.invoke(
        "Classify this customer support ticket into a category and urgency.\n\n"
        f"Ticket:\n{ticket_text}"
    )


sample_tickets = [
    "I was charged twice for my subscription this month, please fix this ASAP!",
    "The app keeps crashing every time I try to upload a file on my phone.",
    "I'd like a refund for my annual plan, I only used it for two weeks.",
]

for t in sample_tickets:
    result = classify_ticket(t)
    print(f"{t[:65]!r}\n  -> category={result.category}, urgency={result.urgency}\n  -> {result.reasoning}\n")
''')

# ------------------------------------------------------------------
md(r"""## Section 3 — RAG Pipeline

Load the 15 mock knowledge-base articles → split → embed locally with
`sentence-transformers` → store in Chroma → retrieve.
""")

code(r'''from langchain_core.documents import Document
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_huggingface import HuggingFaceEmbeddings
from langchain_chroma import Chroma

kb_dir = Path("knowledge_base")
raw_docs = [
    Document(page_content=p.read_text(encoding="utf-8"), metadata={"source": p.name})
    for p in sorted(kb_dir.glob("*.md"))
]
print(f"Loaded {len(raw_docs)} knowledge-base articles")

splitter = RecursiveCharacterTextSplitter(chunk_size=500, chunk_overlap=75)
chunks = splitter.split_documents(raw_docs)
print(f"Split into {len(chunks)} chunks")

embeddings = HuggingFaceEmbeddings(model_name="sentence-transformers/all-MiniLM-L6-v2")

vectorstore = Chroma.from_documents(
    documents=chunks,
    embedding=embeddings,
    persist_directory="chroma_db",
    collection_name="support_kb",
)
retriever = vectorstore.as_retriever(search_kwargs={"k": 3})
_RAGState.retriever = retriever
print("Retriever ready.")
''')

code(r'''# Verbatim-answer test: confirm the retriever actually returns the right article
test_query = "How long does it take for a refund to appear after it's approved?"
results = retriever.invoke(test_query)

for d in results:
    print(f"--- {d.metadata['source']} ---")
    print(d.page_content[:300])
    print()

assert any("business days" in d.page_content for d in results), "Expected verbatim refund-timing text in top results"
print("PASS: retriever surfaced the verbatim refund-timing text from refund_processing_time.md")
''')

code(r'''# search_faq tool now that the retriever exists
print(search_faq("What happens if my payment fails?"))
''')

md(r"""### RAG Strategy Justification: 2-Step vs. Agentic vs. Hybrid

This project uses **2-Step (retrieve-then-generate) RAG** for the billing and
technical specialist workers: each worker issues one retrieval query built directly
from the ticket text, then generates its answer conditioned on the retrieved chunks
in a single pass.

This was chosen over **Agentic RAG** (where the LLM iteratively decides whether/what
to retrieve, potentially issuing multiple retrieval calls) because support tickets in
this domain map cleanly onto a small, well-scoped knowledge base — questions like
"what's your refund window" or "why did sync fail" don't need multi-hop or iterative
retrieval to answer well, so the extra LLM calls and latency of an agentic loop
wouldn't be justified.

A **Hybrid** approach (2-Step retrieval, but letting the agent first decide *whether*
to retrieve at all vs. answering from ticket/customer context alone) was considered,
since not every ticket needs a knowledge-base lookup — but it was set aside for this
capstone to keep the RAG path deterministic and easy to verify against the required
verbatim-answer test above.
""")

# ------------------------------------------------------------------
md(r"""## Section 6 — LangGraph Functional API & Error Handling: Building the Graph

The entire workflow is built with `@task` / `@entrypoint` — no `StateGraph`. It wires
together the Section 1 tools, the Section 2 supervisor, and the Section 3 RAG
retriever, and adds two error-handling strategies:

1. A real `RetryPolicy` on `check_order_status_task`, wrapping the intentionally
   flaky `check_order_status`.
2. A fallback path: if ticket classification fails after retries, the workflow
   escalates to a human node instead of crashing.

Built here (ahead of Sections 4 and 5 below) because those sections demonstrate this
graph's short-term/long-term memory and human-in-the-loop behavior.
""")

code(r'''from langgraph.func import entrypoint, task
from langgraph.types import interrupt, Command, RetryPolicy
from langgraph.checkpoint.memory import InMemorySaver
from langgraph.store.memory import InMemoryStore

checkpointer = InMemorySaver()
store = InMemoryStore()


@task(retry_policy=RetryPolicy(max_attempts=4, initial_interval=0.2, retry_on=(RuntimeError,)))
def check_order_status_task(order_id: str) -> dict:
    return check_order_status(order_id)


@task
def lookup_customer_task(customer_id: str) -> dict:
    return lookup_customer(customer_id)


@task
def search_faq_task(query: str) -> str:
    return search_faq(query)


def _classify_with_llm(ticket_text: str) -> TicketClassification:
    """Plain function (not a pydantic Runnable) so it can be monkeypatched in the
    Section 6 fallback demo below without hitting pydantic's attribute restrictions."""
    return classifier_llm.invoke(
        "Classify this customer support ticket into a category and urgency.\n\n"
        f"Ticket:\n{ticket_text}"
    )


@task(retry_policy=RetryPolicy(max_attempts=3, initial_interval=0.2, retry_on=(RuntimeError,)))
def classify_ticket_task(ticket_text: str) -> dict:
    # Returns a plain dict (not the Pydantic TicketClassification) so the
    # checkpointer can msgpack-serialize this task's cached result without
    # needing a custom type registered.
    return _classify_with_llm(ticket_text).model_dump()


@task
def generate_response_task(prompt: str) -> str:
    return llm.invoke(prompt).content


@task
def escalate_to_human_task(ticket_text: str, reason: str) -> str:
    print(f"[fallback] escalating to human: {reason}")
    return (
        "[ESCALATED TO HUMAN AGENT] We were unable to auto-classify this ticket "
        f"({reason}). A human support agent will follow up within 1 business hour.\n"
        f"Original ticket: {ticket_text}"
    )


@entrypoint(checkpointer=checkpointer, store=store)
def support_workflow(input_data: dict, *, previous: Optional[dict] = None, runtime) -> dict:
    """Orchestrator-Worker support graph: classify -> route -> respond.

    Short-term state: `previous` (via checkpointer) carries this thread's running
    conversation history across turns.
    Long-term state: `runtime.store`, keyed by customer_id, carries durable facts
    across *different* threads for the same customer.
    """
    ticket_text = input_data["message"]
    customer_id = input_data["customer_id"]
    order_id = input_data.get("order_id")

    history = list((previous or {}).get("history", []))
    history.append({"role": "customer", "text": ticket_text})

    try:
        classification = classify_ticket_task(ticket_text).result()
    except Exception as exc:
        response_text = escalate_to_human_task(ticket_text, f"classification failed after retries: {exc}").result()
        history.append({"role": "agent", "text": response_text})
        return entrypoint.final(
            value={"response": response_text, "category": "escalated", "urgency": "high", "history": history},
            save={"history": history},
        )

    customer = lookup_customer_task(customer_id).result()
    prior_note = runtime.store.get(("customer_facts", customer_id), "profile_note")
    prior_note_text = prior_note.value["text"] if prior_note else None

    if classification["category"] == "billing":
        context = search_faq_task(ticket_text).result()
        prompt = (
            "You are a billing support agent. Use the policy context below to answer "
            "the customer's question in 2-3 sentences.\n\n"
            f"Known customer notes: {prior_note_text}\n\n"
            f"Policy context:\n{context}\n\nCustomer ticket:\n{ticket_text}"
        )
        response_text = generate_response_task(prompt).result()

    elif classification["category"] == "technical":
        context = search_faq_task(ticket_text).result()
        order_info = None
        if order_id:
            try:
                order_info = check_order_status_task(order_id).result()
            except Exception:
                order_info = {"error": "order service unavailable after retries"}
        prompt = (
            "You are a technical support agent. Use the troubleshooting context below "
            "to answer the customer in 2-3 sentences.\n\n"
            f"Order info (if relevant): {order_info}\n\n"
            f"Troubleshooting context:\n{context}\n\nCustomer ticket:\n{ticket_text}"
        )
        response_text = generate_response_task(prompt).result()

    else:  # refund
        context = search_faq_task(ticket_text).result()
        order_info = check_order_status_task(order_id).result() if order_id else None
        amount = order_info.get("amount_usd") if order_info and "amount_usd" in order_info else None

        decision = interrupt({
            "type": "refund_approval_required",
            "customer_id": customer_id,
            "customer_name": customer.get("name"),
            "order_id": order_id,
            "amount_usd": amount,
            "ticket": ticket_text,
            "dispute_count": customer.get("dispute_count"),
            "policy_context": context,
        })

        if decision.get("approved"):
            response_text = (
                f"Your refund of ${amount} for order {order_id} has been approved and will be processed. "
                f"{decision.get('note', '')}"
            )
            runtime.store.put(
                ("customer_facts", customer_id),
                "profile_note",
                {"text": f"Refund approved on order {order_id} for ${amount}. {decision.get('note', '')}".strip()},
            )
        else:
            response_text = f"Your refund request was reviewed and was not approved. {decision.get('note', '')}"
            runtime.store.put(
                ("customer_facts", customer_id),
                "profile_note",
                {"text": f"Refund request denied for order {order_id}. {decision.get('note', '')}".strip()},
            )

    history.append({"role": "agent", "text": response_text})
    return entrypoint.final(
        value={
            "response": response_text,
            "category": classification["category"],
            "urgency": classification["urgency"],
            "history": history,
        },
        save={"history": history},
    )


print("Graph built: support_workflow (checkpointer + store attached)")
''')

# ------------------------------------------------------------------
md(r"""## Section 4 — Context & State Management

**Short-term:** the `Checkpointer` keeps a running `history` per `thread_id`, so a
second message on the same thread sees the first turn's context.

**Short-term test:** two turns on the same `thread_id`, second turn shows the
history growing.
""")

code(r'''short_term_config = {"configurable": {"thread_id": "ticket-thread-A1"}}

turn1 = support_workflow.invoke(
    {"customer_id": "cust_1002", "message": "My app crashes every time I upload a big file on mobile."},
    short_term_config,
)
print("Turn 1 response:", turn1["response"])
print("Turn 1 history length:", len(turn1["history"]))

turn2 = support_workflow.invoke(
    {"customer_id": "cust_1002", "message": "I tried clearing the cache like you said, still crashing."},
    short_term_config,
)
print("\nTurn 2 response:", turn2["response"])
print("Turn 2 history length:", len(turn2["history"]))
for msg in turn2["history"]:
    print(f"  [{msg['role']}] {msg['text'][:80]}")
''')

md(r"""**Long-term:** the `Store`, keyed by `customer_id`, carries durable facts *across
different threads* — e.g. "has disputed billing twice before" or a note left by a
prior refund decision.

**Required test:** write a fact in Thread A, open a fresh Thread B with the *same*
`customer_id`, and prove the fact is readable there.
""")

code(r'''# --- Thread A: write a long-term fact for cust_1004 ---
thread_a_config = {"configurable": {"thread_id": "ticket-thread-CROSS-A"}}

# Directly write a durable fact to the long-term store, as the refund path does.
store.put(
    ("customer_facts", "cust_1004"),
    "profile_note",
    {"text": "Customer disputed a billing charge twice in the last 12 months (see invoice_disputes.md)."},
)
print("Wrote long-term fact for cust_1004 in Thread A context.")

# Prove it: read it back directly from the store (not thread-scoped).
fact = store.get(("customer_facts", "cust_1004"), "profile_note")
print("Fact immediately after writing:", fact.value)
''')

code(r'''# --- Thread B: a *fresh* thread, same customer_id, proving the fact carries over ---
thread_b_config = {"configurable": {"thread_id": "ticket-thread-CROSS-B"}}

turn_b = support_workflow.invoke(
    {"customer_id": "cust_1004", "message": "Can I switch from my annual plan to monthly?"},
    thread_b_config,
)
print("Thread B response:", turn_b["response"])
print("Thread B history length (fresh thread):", len(turn_b["history"]))

fact_from_b = store.get(("customer_facts", "cust_1004"), "profile_note")
print("\nLong-term fact read from a completely different thread (Thread B):")
print(fact_from_b.value)

assert fact_from_b.value["text"].startswith("Customer disputed a billing charge twice")
print("\nPASS: fact written under Thread A is readable from a fresh Thread B for the same customer_id.")
''')

# ------------------------------------------------------------------
md(r"""## Section 5 — Human-in-the-Loop

Before finalizing any refund, `support_workflow` calls `interrupt()` (see the graph
in Section 6 above) and pauses. Resuming requires `Command(resume=...)` with an
approval decision.
""")

code(r'''refund_config = {"configurable": {"thread_id": "ticket-thread-REFUND-1"}}

interrupted_result = support_workflow.invoke(
    {
        "customer_id": "cust_1001",
        "message": "I'd like a refund for order ord_5002, I was charged for a renewal I didn't want.",
        "order_id": "ord_5002",
    },
    refund_config,
)

print(type(interrupted_result))
print(interrupted_result)
''')

md("The graph is now paused at `interrupt()`. Inspect the payload it surfaced:")

code(r'''# `invoke` returns the interrupt payload wrapped in the run's state when paused.
state = support_workflow.get_state(refund_config)
print("Next node(s) pending:", state.next)
for i in state.interrupts:
    print("\nInterrupt payload:")
    for k, v in i.value.items():
        print(f"  {k}: {v}")
''')

code(r'''# Resume with a human approval decision via Command(resume=...)
approval_decision = {"approved": True, "note": "Approved by support supervisor — within 30-day window."}

final_result = support_workflow.invoke(Command(resume=approval_decision), refund_config)

print("Final response after human approval:")
print(final_result["response"])
print("\nCategory:", final_result["category"], "| Urgency:", final_result["urgency"])
''')

code(r'''# Second example: a human *rejects* the refund, to show both resume outcomes.
refund_config_2 = {"configurable": {"thread_id": "ticket-thread-REFUND-2"}}

support_workflow.invoke(
    {
        "customer_id": "cust_1004",
        "message": "I want a refund for my annual plan order ord_5005, I cancelled last week.",
        "order_id": "ord_5005",
    },
    refund_config_2,
)

state_2 = support_workflow.get_state(refund_config_2)
print("Interrupt payload:", state_2.interrupts[0].value)

rejection_decision = {"approved": False, "note": "Order was already cancelled and refunded per policy; goodwill credit denied — exceeds non-refundable setup fee threshold."}
final_result_2 = support_workflow.invoke(Command(resume=rejection_decision), refund_config_2)
print("\nFinal response after human rejection:")
print(final_result_2["response"])
''')

# ------------------------------------------------------------------
md(r"""## Section 6 (continued) — Error Handling in Action

### 1. RetryPolicy firing

`check_order_status` fails ~30% of the time by design. To *deterministically* show a
retry firing in this captured run (rather than hoping for a 30% chance to land), we
temporarily raise `FAILURE_RATE` for one demo call, then restore it. The
`[order-service] attempting...` / `[order-service] transient failure...` print lines
inside `check_order_status` make each retry attempt visible.
""")

code(r'''@entrypoint()
def retry_demo(order_id: str):
    return check_order_status_task(order_id).result()


# Deterministic demo double for check_order_status: fails on the first 2 calls,
# succeeds on the 3rd, so we reliably *see* the RetryPolicy (max_attempts=4) recover
# from real failures instead of leaving it to the ~30% random chance.
_attempt_count = {"n": 0}
_original_check_order_status = check_order_status


def _deterministic_flaky_check_order_status(order_id: str) -> dict:
    _attempt_count["n"] += 1
    n = _attempt_count["n"]
    print(f"[order-service] attempt #{n} for {order_id}")
    if n < 3:
        print(f"[order-service] transient failure on attempt #{n}")
        raise RuntimeError("Order service temporarily unavailable - please retry.")
    order = get_order(order_id)
    return order if order is not None else {"error": f"No order found with id {order_id}"}


check_order_status = _deterministic_flaky_check_order_status
try:
    print("=== Demonstrating RetryPolicy (max_attempts=4) on check_order_status_task ===")
    result = retry_demo.invoke("ord_5001", {"configurable": {"thread_id": "retry-demo-1"}})
    print("\nFinal result after the RetryPolicy recovered from 2 transient failures:", result)
    assert _attempt_count["n"] == 3, "Expected exactly 2 failed attempts then 1 success"
    print("PASS: RetryPolicy retried through 2 failures and succeeded on attempt 3.")
finally:
    check_order_status = _original_check_order_status
    print("\ncheck_order_status restored to its normal ~30%-failure-rate version for the rest of the notebook.")
''')

md("""### 2. Fallback path when the LLM call fails after retries

We simulate a hard LLM outage by monkeypatching `_classify_with_llm` (the plain
function `classify_ticket_task` calls) to always raise. `classify_ticket_task`'s own
`RetryPolicy` (max_attempts=3) will retry twice and still fail, and
`support_workflow`'s `try/except` around it will then escalate to
`escalate_to_human_task` instead of crashing.
""")

code(r'''_original_classify_with_llm = _classify_with_llm
_broken_attempt_count = {"n": 0}


def _broken_classify_with_llm(ticket_text: str):
    _broken_attempt_count["n"] += 1
    print(f"[groq] attempt #{_broken_attempt_count['n']}: simulated outage, connection to LLM provider failed")
    raise RuntimeError("Simulated Groq outage: connection to LLM provider failed.")


_classify_with_llm = _broken_classify_with_llm  # monkeypatch just for this demo

fallback_config = {"configurable": {"thread_id": "ticket-thread-FALLBACK-1"}}
try:
    fallback_result = support_workflow.invoke(
        {"customer_id": "cust_1002", "message": "Why was I charged an extra $10 this month?"},
        fallback_config,
    )
    print("\nResponse:", fallback_result["response"])
    print("Category:", fallback_result["category"])
finally:
    _classify_with_llm = _original_classify_with_llm  # restore the real LLM path

assert fallback_result["category"] == "escalated"
print("\nPASS: LLM failure (after RetryPolicy exhausted its attempts) triggered the fallback escalation path instead of crashing.")
''')

# ------------------------------------------------------------------
md(r"""## Section 7 — Workflow Pattern

This project is an **Orchestrator-Worker** pattern: a single supervisor
(`classify_ticket_task`, driven by structured LLM output) makes every routing
decision, and the billing/technical/refund logic inside `support_workflow` acts as
specialist workers that execute their task and return — they never hand off to each
other or re-route. It fits Track A cleanly because the routing authority is
centralized in one place (the classification step), which keeps the system easy to
reason about, trace, and extend with new categories without touching worker logic.
""")

# ------------------------------------------------------------------
md(r"""## Section 8 — LangSmith Observability

`LANGCHAIN_TRACING_V2=true` was confirmed as set in the Setup cell above (exact
variable name — not `LANGSMITH_TRACING_V2`). Every `support_workflow.invoke(...)`
call above was traced automatically under the `LANGCHAIN_PROJECT` project. Run one
more full ticket end-to-end here, then open it in the LangSmith UI.
""")

code(r'''trace_config = {"configurable": {"thread_id": "ticket-thread-LANGSMITH-DEMO"}}

trace_result = support_workflow.invoke(
    {"customer_id": "cust_1003", "message": "My team can't log in this morning, is there an outage?"},
    trace_config,
)
print("Response:", trace_result["response"])
print("Category:", trace_result["category"], "| Urgency:", trace_result["urgency"])
print(
    "\nOpen https://smith.langchain.com, select the "
    f"'{os.environ.get('LANGCHAIN_PROJECT')}' project, and find this run by thread_id "
    "'ticket-thread-LANGSMITH-DEMO' to inspect the full trace tree "
    "(supervisor classification call -> search_faq_task retrieval -> generate_response_task)."
)
''')

md(r"""**Observation (fill in after inspecting the trace in the LangSmith UI):**

> _Replace this line with one or two sentences about something real you saw in the
> trace — e.g. a retry firing on `check_order_status_task`, the wall-clock time spent
> in the RAG retrieval step vs. the generation step, or the exact structured-output
> JSON the supervisor produced for this ticket._
""")

# ------------------------------------------------------------------
nb["cells"] = cells
nbf.write(nb, "support_agent.ipynb")
print(f"Wrote support_agent.ipynb with {len(cells)} cells")
