"""Evaluate the SQL channel on hand-written questions whose answers were checked in wahadb.sqlite.

A question is correct when every expected value appears in the agent's answer (case-insensitive).
We also check the route and whether the expected values are present in the SQL result itself.
"""

import argparse
import json
import uuid
from pathlib import Path

import pandas as pd
from langchain_core.messages import HumanMessage

from rag_m2.chat.agent import build_agent
from rag_m2.llm.gemini import generate, generate_json
from rag_m2.retriever.embedder import Embedder
from rag_m2.retriever.sql_retriever import SqlRetriever
from rag_m2.settings import DATA, settings
from rag_m2.storage.vector_store import SqliteStore


def found(expected: list[str], text: str) -> bool:
    return all(e.lower() in text.lower() for e in expected)


if __name__ == "__main__":
    p = argparse.ArgumentParser()
    p.add_argument("--questions", type=Path, default=DATA / "eval" / "sql_questions.jsonl")
    p.add_argument("--output", type=Path, default=DATA / "eval" / "sql_results.csv")
    a = p.parse_args()

    rows = [json.loads(line) for line in a.questions.read_text(encoding="utf-8").splitlines() if line.strip()]
    agent = build_agent(
        generate, generate_json, Embedder(), SqliteStore(settings.vector_db), SqlRetriever(generate_json), settings.top_k
    )
    records = []
    for i, row in enumerate(rows, 1):
        print(f"[{i}/{len(rows)}] {row['question']}")
        try:
            s = agent.invoke({"messages": [HumanMessage(row["question"])]}, {"configurable": {"thread_id": str(uuid.uuid4())}})
            route, sql, answer = s["route"], s.get("sql", ""), s["messages"][-1].content
        except Exception as e:
            route, sql, answer = "error", "", f"Error: {e}"
        records.append(
            {
                "question": row["question"],
                "expected": " | ".join(row["expected"]),
                "route_ok": route in ("sql", "both"),
                "sql_ok": found(row["expected"], sql),
                "answer_ok": found(row["expected"], answer),
                "route": route,
                "sql": sql.splitlines()[0] if sql else "",
                "answer": answer,
            }
        )

    df = pd.DataFrame(records)
    a.output.parent.mkdir(parents=True, exist_ok=True)
    df.to_csv(a.output, index=False)
    print(df[["route_ok", "sql_ok", "answer_ok"]].mean().round(3).to_string())
    print(f"Saved {a.output}")
