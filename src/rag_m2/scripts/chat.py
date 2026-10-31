"""Multi-turn chat in the terminal (rich + prompt_toolkit). Every session is appended to data/chat_logs/chat.md."""

import logging
import uuid
from datetime import datetime

from langchain_core.messages import HumanMessage
from prompt_toolkit import PromptSession
from prompt_toolkit.formatted_text import HTML
from rich.console import Console
from rich.markdown import Markdown

from rag_m2.chat.agent import build_agent
from rag_m2.llm.gemini import generate, generate_json
from rag_m2.retriever.embedder import Embedder
from rag_m2.retriever.sql_retriever import SqlRetriever
from rag_m2.settings import DATA, settings
from rag_m2.storage.vector_store import SqliteStore

HELP = "/reset new conversation · /trace toggle routing/sources · /exit quit"

if __name__ == "__main__":
    logging.basicConfig(level=logging.WARNING)
    console = Console()
    with console.status("Loading models..."):
        agent = build_agent(
            generate, generate_json, Embedder(), SqliteStore(settings.vector_db), SqlRetriever(generate_json), settings.top_k
        )
    log_path = DATA / "chat_logs" / "chat.md"
    log_path.parent.mkdir(parents=True, exist_ok=True)
    log = log_path.open("a", encoding="utf-8")
    log.write(f"# Chat {datetime.now():%Y-%m-%d %H:%M} ({settings.llm_model})\n\n")
    console.print(f"[bold]Warhammer 40k RAG[/bold] ({settings.llm_model}) — {HELP}\n[dim]log: {log_path}[/dim]")
    session, thread, trace = PromptSession(), str(uuid.uuid4()), True

    while True:
        try:
            q = session.prompt(HTML("<ansigreen><b>you > </b></ansigreen>")).strip()
        except KeyboardInterrupt:
            continue
        except EOFError:
            break
        if not q:
            continue
        if q == "/exit":
            break
        if q == "/reset":
            thread = str(uuid.uuid4())
            log.write("---\n\n*(new conversation)*\n\n")
            console.print("[dim]history cleared[/dim]")
            continue
        if q == "/trace":
            trace = not trace
            continue
        try:
            with console.status("Thinking..."):
                state = agent.invoke({"messages": [HumanMessage(q)]}, {"configurable": {"thread_id": thread}})
        except KeyboardInterrupt:
            console.print("[yellow]interrupted[/yellow]")
            continue
        except Exception as e:
            console.print(f"[red]Error: {e}[/red]")
            log.write(f"## {q}\n\n**Error:** {e}\n\n")
            continue
        answer = state["messages"][-1].content
        sources = "; ".join(dict.fromkeys(state.get("sources", [])))
        sql = state["sql"].splitlines()[0] if state.get("sql") else ""
        if trace:
            console.print(f"[dim]route={state['route']} · query={state['query']}[/dim]")
            if sql:
                console.print(f"[dim]{sql}[/dim]")
        console.print(Markdown(answer))
        if trace and sources:
            console.print(f"[dim]sources: {sources}[/dim]")
        log.write(f"## {q}\n\n*route: {state['route']} · query: {state['query']}*\n\n")
        log.write(f"`{sql}`\n\n" if sql else "")
        log.write(f"{answer}\n\n*sources: {sources or '-'}*\n\n")
        log.flush()
    log.close()
