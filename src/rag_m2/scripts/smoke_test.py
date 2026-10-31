"""Run a fixed list of conversations through the agent and save the transcript (manual review)."""

import logging
import uuid
from datetime import datetime

from langchain_core.messages import HumanMessage

from rag_m2.chat.agent import build_agent
from rag_m2.llm.gemini import generate, generate_json
from rag_m2.retriever.embedder import Embedder
from rag_m2.retriever.sql_retriever import SqlRetriever
from rag_m2.settings import DATA, settings
from rag_m2.storage.vector_store import SqliteStore

# (expected route(s) separated by |, question) — each inner list is one conversation (multi-turn)
CONVERSATIONS = [
    [("rules", "How does Lone Operative work?")],
    [("rules", "Can a unit charge after it Advanced?")],
    [("rules", "What happens when a unit fails a Battle-shock test?")],
    [("rules", "How do invulnerable saves work against mortal wounds?")],
    [("sql", "describe me Time to Strike")],
    [("sql", "Which Aeldari stratagems can be used in the Movement phase?")],
    [("sql", "What is the toughness and save of an Intercessor Squad?")],
    [("sql", "How many points does a Land Raider cost?")],
    [("both", "Does Eldrad Ulthran have the Lone Operative ability, and what does it do?")],
    [
        ("sql", "What weapons does a Hellblaster Squad have?"),
        ("sql", "and what is their toughness?"),
        ("rules|both", "can they shoot after Falling Back?"),
    ],
    [("none", "hello!")],
]

if __name__ == "__main__":
    logging.basicConfig(level=logging.WARNING)
    agent = build_agent(
        generate, generate_json, Embedder(), SqliteStore(settings.vector_db), SqlRetriever(generate_json), settings.top_k
    )
    out = DATA / "chat_logs" / "smoke_test.md"
    out.parent.mkdir(parents=True, exist_ok=True)
    lines, ok, total = [f"# Smoke test {datetime.now():%Y-%m-%d %H:%M} ({settings.llm_model})\n"], 0, 0

    for conv in CONVERSATIONS:
        thread = {"configurable": {"thread_id": str(uuid.uuid4())}}
        for expected, q in conv:
            total += 1
            print(f"[{total}] {q}")
            try:
                s = agent.invoke({"messages": [HumanMessage(q)]}, thread)
            except Exception as e:
                lines.append(f"## {q}\n\n**Error:** {e}\n")
                continue
            good = s["route"] in expected.split("|")
            ok += good
            sql = s["sql"].splitlines()[0] if s.get("sql") else ""
            lines.append(
                f"## {q}\n\n*route: {s['route']} (expected {expected}) {'OK' if good else 'WRONG'} · query: {s['query']}*\n"
            )
            lines.append(f"`{sql}`\n" if sql else "")
            lines.append(f"{s['messages'][-1].content}\n\n*sources: {'; '.join(dict.fromkeys(s.get('sources', []))) or '-'}*\n")
        lines.append("---\n")

    lines.insert(1, f"Routing: {ok}/{total} as expected\n")
    out.write_text("\n".join(lines), encoding="utf-8")
    print(f"Routing {ok}/{total} — transcript saved to {out}")
