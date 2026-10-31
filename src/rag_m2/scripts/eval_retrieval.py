"""Run the agent on the test set (checkpointed) then score it with RAGAS + a fuzzy context hit rate."""

import argparse
import json
import uuid
from pathlib import Path

from langchain_core.messages import HumanMessage
from ragas import EvaluationDataset, evaluate
from ragas.metrics import FactualCorrectness, Faithfulness, LLMContextPrecisionWithReference, LLMContextRecall
from ragas.run_config import RunConfig
from rapidfuzz import fuzz

from rag_m2.chat.agent import build_agent
from rag_m2.evaluations.ragas_adapters import EmbedderRagasEmbeddings, GeminiRagasLLM
from rag_m2.llm.gemini import generate, generate_json
from rag_m2.retriever.embedder import Embedder
from rag_m2.retriever.sql_retriever import SqlRetriever
from rag_m2.settings import DATA, settings
from rag_m2.storage.vector_store import SqliteStore


def context_hit(reference_contexts: list[str], retrieved: list[str], threshold: int = 80) -> float:
    """Share of reference contexts found (fuzzy) in at least one retrieved chunk. No LLM needed."""
    if not reference_contexts:
        return float("nan")
    hits = [any(fuzz.partial_ratio(ref[:500], r) >= threshold for r in retrieved) for ref in reference_contexts]
    return sum(hits) / len(hits)


if __name__ == "__main__":
    p = argparse.ArgumentParser()
    p.add_argument("--testset", type=Path, default=DATA / "eval" / "testset.jsonl")
    p.add_argument("--checkpoint", type=Path, default=DATA / "eval_checkpoints" / "answers.jsonl")
    p.add_argument("--output", type=Path, default=DATA / "eval" / "results.csv")
    p.add_argument("--vector_db", type=Path, default=settings.vector_db)
    p.add_argument("--k", type=int, default=settings.top_k)
    p.add_argument("--no_sql", action="store_true", help="disable the SQL channel (rules-only evaluation)")
    p.add_argument("--skip_ragas", action="store_true", help="only compute the fuzzy context hit rate")
    a = p.parse_args()

    rows = [json.loads(line) for line in a.testset.read_text(encoding="utf-8").splitlines() if line.strip()]
    a.checkpoint.parent.mkdir(parents=True, exist_ok=True)
    saved = {}
    if a.checkpoint.exists():
        saved = {r["user_input"]: r for r in map(json.loads, a.checkpoint.read_text(encoding="utf-8").splitlines())}

    embedder = Embedder()
    sql = None if a.no_sql else SqlRetriever(generate_json)
    agent = build_agent(generate, generate_json, embedder, SqliteStore(a.vector_db), sql, a.k)

    records = []
    with a.checkpoint.open("a", encoding="utf-8") as ckpt:
        for i, row in enumerate(rows, 1):
            q = row["user_input"]
            print(f"[{i}/{len(rows)}] {q[:80]}")
            if q not in saved:
                state = agent.invoke({"messages": [HumanMessage(q)]}, {"configurable": {"thread_id": str(uuid.uuid4())}})
                contexts = state.get("contexts", []) + ([state["sql"]] if state.get("sql") else [])
                saved[q] = {
                    "user_input": q,
                    "reference": row["reference"],
                    "reference_contexts": row.get("reference_contexts") or [],
                    "response": state["messages"][-1].content,
                    "retrieved_contexts": contexts or ["(none)"],
                    "route": state.get("route"),
                }
                ckpt.write(json.dumps(saved[q], ensure_ascii=False) + "\n")
                ckpt.flush()
            records.append(saved[q])

    hit = [context_hit(r["reference_contexts"], r["retrieved_contexts"]) for r in records]
    print(f"Fuzzy context hit rate: {sum(hit) / len(hit):.3f}")
    a.output.parent.mkdir(parents=True, exist_ok=True)
    if a.skip_ragas:
        import pandas as pd

        pd.DataFrame({"user_input": [r["user_input"] for r in records], "context_hit": hit}).to_csv(a.output, index=False)
        raise SystemExit

    keys = ("user_input", "reference", "response", "retrieved_contexts")
    results = evaluate(
        EvaluationDataset.from_list([{k: r[k] for k in keys} for r in records]),
        metrics=[Faithfulness(), FactualCorrectness(), LLMContextPrecisionWithReference(), LLMContextRecall()],
        llm=GeminiRagasLLM(),
        embeddings=EmbedderRagasEmbeddings(embedder),
        run_config=RunConfig(max_workers=2, timeout=300),
        raise_exceptions=False,
    ).to_pandas()
    table = results[["user_input"]].copy()
    for col in results.columns:
        if results[col].dtype.kind == "f":
            table[col] = results[col]
    table["context_hit"] = hit
    table["route"] = [r["route"] for r in records]
    table["response"] = [r["response"] for r in records]
    table.to_csv(a.output, index=False)
    print(table.mean(numeric_only=True).round(3).to_string())
    print(f"Saved {a.output}")
