"""Offline tests: chunking, SQL safety, hybrid search and agent routing with a fake LLM."""

import numpy as np

from rag_m2.chat.agent import build_agent
from rag_m2.chunker.markdown_chunker import Chunk, chunk_markdown
from rag_m2.retriever.sql_retriever import SqlRetriever
from rag_m2.storage.vector_store import SqliteStore

MD = (
    "## MOVEMENT PHASE\n\n"
    + "Units move. " * 60
    + "\n\n## 1. HIT ROLL\n\nRoll a D6.\n\n## 2. WOUND ROLL\n\n"
    + "Compare S and T. " * 40
)


def test_chunker_merges_small_sections():
    chunks = chunk_markdown(MD)
    assert any("HIT ROLL" in c.header and "WOUND ROLL" in c.header for c in chunks)
    assert all(len(c.content) <= 1000 for c in chunks)


def test_sql_rejects_writes():
    sql = SqlRetriever(lambda *_: {"sql": "SELECT name FROM factions LIMIT 3"})
    assert sql.run("DROP TABLE factions").error
    assert sql.run("SELECT 1; DELETE FROM factions").error
    assert len(sql.retrieve("factions?").rows) == 3


class FakeEmbedder:
    def embed_query(self, text):
        return np.ones(4, dtype=np.float32) / 2


def test_agent_routes_and_remembers(tmp_path):
    store = SqliteStore(tmp_path / "v.db")
    store.reset([Chunk("LONE OPERATIVE", 'Cannot be targeted beyond 12".'), Chunk("STEALTH", "-1 to hit.")], np.eye(4)[:2] / 1.0)
    calls = []

    def llm_json(prompt, system):
        calls.append(prompt)
        if "SQLite" in system:
            return {"sql": "SELECT name FROM factions WHERE name LIKE '%Aeldari%'"}
        return {"route": "both", "query": "What is Lone Operative?"}

    agent = build_agent(lambda p, s: "answer", llm_json, FakeEmbedder(), store, SqlRetriever(llm_json), k=2)
    cfg = {"configurable": {"thread_id": "t"}}
    state = agent.invoke({"messages": [("user", "lone operative?")]}, cfg)
    assert state["route"] == "both" and state["contexts"] and "Aeldari" in state["sql"]
    agent.invoke({"messages": [("user", "and stealth?")]}, cfg)
    router_prompts = [c for c in calls if c.startswith("Conversation")]
    assert "lone operative?" in router_prompts[-1] and "and stealth?" in router_prompts[-1]
