# testing.py
import asyncio
from indexer import load_indexes
from rag_pipeline import run_pipeline


async def test():
    print("=" * 60)
    print("SIMPLE RAG PIPELINE — TEST")
    print("=" * 60)

    loaded = load_indexes()
    print(f"index loaded: {loaded}")
    if not loaded:
        print("ERROR: build index first")
        return

    test_cases = [
        {
            "label": "RAG query — employee table",
            "query": "what is in the employee table?",
            "history": "",
        },
        {
            "label": "RAG query with history",
            "query": "what is their salary?",
            "history": "User asked about employees in the previous turn.",
        },
        {
            "label": "general knowledge — no docs needed",
            "query": "what is 2 + 2?",
            "history": "",
        },
        {
            "label": "out of context query",
            "query": "what is the nuclear launch code?",
            "history": "",
        },
    ]

    for case in test_cases:
        print(f"\n{'=' * 60}")
        print(f"TEST:    {case['label']}")
        print(f"QUERY:   {case['query']}")
        if case["history"]:
            print(f"HISTORY: {case['history']}")
        print("─" * 60)

        full_response = ""
        events_seen = []
        citations = []

        async for event in run_pipeline(
            query=case["query"],
            history=case["history"],
            top_k=5,
            top_n=3,
        ):
            t = event["type"]
            events_seen.append(t)

            if t == "retrieval_start":
                print("[ retrieval  ] searching...")

            elif t == "retrieval_complete":
                chunks = event.get("chunks", [])
                print(f"[ retrieval  ] {len(chunks)} chunks retrieved")
                for i, c in enumerate(chunks[:3], 1):
                    print(
                        f"               {i}. [{c['source']}] "
                        f"score={c['score']:.4f} — "
                        f"{c['text'][:50]}..."
                    )

            elif t == "rerank_complete":
                chunks = event.get("chunks", [])
                print(f"[ reranking  ] {len(chunks)} chunks after BGE reranker")
                for i, c in enumerate(chunks, 1):
                    print(
                        f"               {i}. [{c['source']}] "
                        f"score={c['score']:.4f}"
                    )

            elif t == "generation_start":
                print("[ generation ] streaming:\n")

            elif t == "token":
                print(event["token"], end="", flush=True)
                full_response += event["token"]

            elif t == "citation":
                citations.append(event)

            elif t == "token_usage":
                u = event["usage"]
                print(
                    f"\n\n[ usage      ] "
                    f"prompt={u['prompt_tokens']} "
                    f"context={u['context_tokens']} "
                    f"completion={u['completion_tokens']} "
                    f"total={u['total_tokens']}/{u['budget_limit']}"
                )

            elif t == "done":
                print("[ done       ] ✓")

            elif t == "error":
                print(
                    f"[ error      ] {event.get('error_type')}: "
                    f"{event.get('message')}"
                )

        # citations found
        if citations:
            print(f"[ citations  ] {len(citations)} found:")
            for c in citations:
                print(
                    f"               [{c['citation_index']}] "
                    f"chunk_id={c['citation_id'][:16]}..."
                )
        else:
            print("[ citations  ] none detected")

        # event sequence
        # deduplicate consecutive tokens for readability
        seq = []
        for e in events_seen:
            if e == "token" and seq and seq[-1] == "token":
                continue
            seq.append(e)
        print(f"\n[ events     ] {' → '.join(seq)}")

        last = events_seen[-1] if events_seen else ""
        mark = "✓" if last in ("done", "error") else "✗"
        print(f"[ sequence   ] {mark} ends with '{last}'")

    # ── PII test ──────────────────────────────────────
    print(f"\n{'=' * 60}")
    print("TEST:    PII redaction")
    print("─" * 60)

    pii_query = "what does john.doe@company.com say about the employees?"
    print(f"original:  {pii_query}")
    print("streaming:")

    async for event in run_pipeline(query=pii_query, history=""):
        t = event["type"]
        if t == "token":
            print(event["token"], end="", flush=True)
        elif t == "done":
            print("\n[ done ] ✓")
            break
        elif t == "error":
            print(f"\n[ error ] {event.get('message')}")
            break

    # ── no index fallback ─────────────────────────────
    print(f"\n{'=' * 60}")
    print("TEST:    no index fallback — pure LLM")
    print("─" * 60)

    import indexer as idx

    original = idx._is_ready
    idx._is_ready = False

    print("query: what is the capital of France?")
    async for event in run_pipeline(
        query="what is the capital of France?",
        history="",
    ):
        t = event["type"]
        if t == "generation_start":
            print("[ generation ] pure LLM (no retrieval)...")
        elif t == "token":
            print(event["token"], end="", flush=True)
        elif t == "done":
            print("\n[ done ] ✓")
            break
        elif t == "error":
            print(f"\n[ error ] {event.get('message')}")
            break

    idx._is_ready = original

    # ── citation map test ─────────────────────────────
    print(f"\n{'=' * 60}")
    print("TEST:    citation detection")
    print("─" * 60)

    citations_found = []
    async for event in run_pipeline(
        query="summarize all the documents",
        history="",
        top_k=5,
        top_n=3,
    ):
        t = event["type"]
        if t == "citation":
            citations_found.append(event)
            print(
                f"  citation [{event['citation_index']}] → "
                f"chunk {event['citation_id'][:16]}..."
            )
        elif t == "token":
            print(event["token"], end="", flush=True)
        elif t == "done":
            print(f"\n[ done ] {len(citations_found)} citations emitted ✓")
            break
        elif t == "error":
            print(f"\n[ error ] {event.get('message')}")
            break

    print(f"\n{'=' * 60}")
    print("SIMPLE RAG TEST COMPLETE ✓")
    print("=" * 60)


asyncio.run(test())
