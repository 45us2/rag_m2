"""LangGraph agent: router -> (rules vector search | SQL | both) -> grounded answer, with memory."""

import logging
from collections.abc import Callable
from typing import Annotated, TypedDict

from langchain_core.messages import AIMessage, AnyMessage
from langgraph.checkpoint.memory import MemorySaver
from langgraph.graph import END, START, StateGraph
from langgraph.graph.message import add_messages

from rag_m2.retriever.embedder import Embedder
from rag_m2.retriever.sql_retriever import SqlRetriever
from rag_m2.storage.vector_store import SqliteStore

log = logging.getLogger(__name__)

ROUTER = """You route questions for a Warhammer 40,000 assistant with two sources:
- "rules": the Core Rules book (game phases, movement, shooting, charges, fights, morale, terrain, core abilities, keywords, missions...).
- "sql": a database of army data (factions, units/datasheets, model stats like toughness/wounds/save, weapons profiles, points costs, stratagems, detachments, enhancements, unit abilities, keywords).
- "both" if the question is about a specific unit/faction AND asks how a rule or core ability works (e.g. "does X have Lone Operative and what does it do?").
- "none" for greetings/off-topic.
Rewrite the last user message as a standalone question using the conversation (resolve pronouns like "it", "this unit").
Keep it short and close to the user's words: do NOT add "Warhammer 40,000", "core rules" or other generic words (they hurt the search).
Return JSON: {"route": "rules|sql|both|none", "query": "<standalone question>"}"""

ANSWER = """You are a Warhammer 40,000 rules assistant.
Answer the question using ONLY the context below. If the context does not contain the answer, say you don't know.
Be concise and precise (keep exact numbers, distances, dice). Database rows are the facts about units; if a unit's list of abilities/weapons does not contain something, it does not have it. Cite sources at the end, e.g. (Core Rules: <section>) or (Game database)."""


class State(TypedDict, total=False):
    messages: Annotated[list[AnyMessage], add_messages]
    route: str
    query: str
    contexts: list[str]
    sql: str
    sources: list[str]


def history(messages: list[AnyMessage], n: int = 6) -> str:
    return "\n".join(f"{m.type}: {m.content}" for m in messages[-n:])


def build_agent(
    llm: Callable[..., str],
    llm_json: Callable[..., dict],
    embedder: Embedder,
    store: SqliteStore,
    sql_retriever: SqlRetriever | None,
    k: int = 5,
):
    def router(state: State) -> State:
        try:
            out = llm_json(f"Conversation:\n{history(state['messages'])}", ROUTER)
            route, query = out.get("route", "rules"), out.get("query") or state["messages"][-1].content
        except Exception as e:  # bad JSON -> fall back on the rules book
            log.warning("router failed: %s", e)
            route, query = "rules", state["messages"][-1].content
        if route in ("sql", "both") and sql_retriever is None:
            route = "rules"
        log.info("router: %s | %s", route, query)
        return {"route": route, "query": query, "contexts": [], "sql": "", "sources": []}

    def retrieve_rules(state: State) -> State:
        results = store.search(state["query"], embedder.embed_query(state["query"]), k=k)
        return {"contexts": [r.chunk.text for r in results], "sources": [f"rules: {r.chunk.header}" for r in results]}

    def retrieve_sql(state: State) -> State:
        return {"sql": sql_retriever.retrieve(state["query"]).to_text()}

    def answer(state: State) -> State:
        if state["route"] == "none":
            context = "(no retrieval: small talk)"
        else:
            parts = [f"[Core Rules]\n{c}" for c in state.get("contexts", [])]
            if state.get("sql"):
                parts.append(f"[Game database]\n{state['sql']}")
            context = "\n\n---\n\n".join(parts)
        prompt = f"Conversation so far:\n{history(state['messages'][:-1])}\n\nCONTEXT:\n{context}\n\nQuestion: {state['query']}"
        sources = state.get("sources", []) + (["sql"] if state.get("sql") else [])
        return {"messages": [AIMessage(llm(prompt, ANSWER))], "sources": sources}

    def dispatch(state: State) -> list[str]:
        return {"rules": ["rules"], "sql": ["sql"], "both": ["rules", "sql"]}.get(state["route"], ["answer"])

    g = StateGraph(State)
    g.add_node("router", router)
    g.add_node("rules", retrieve_rules)
    g.add_node("sql", retrieve_sql)
    g.add_node("answer", answer)
    g.add_edge(START, "router")
    g.add_conditional_edges("router", dispatch, ["rules", "sql", "answer"])
    g.add_edge("rules", "answer")
    g.add_edge("sql", "answer")
    g.add_edge("answer", END)
    return g.compile(checkpointer=MemorySaver())
