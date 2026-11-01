"""Textual interface: chat on the left, routing trace on the right.

Keys: Ctrl+N new conversation · Ctrl+T show/hide trace · Ctrl+Q quit
"""

import uuid

from langchain_core.messages import HumanMessage
from textual import work
from textual.app import App, ComposeResult
from textual.containers import Horizontal, VerticalScroll
from textual.widgets import Footer, Header, Input, Markdown, RichLog


def default_agent():
    from rag_m2.chat.agent import build_agent
    from rag_m2.llm.gemini import generate, generate_json
    from rag_m2.retriever.embedder import Embedder
    from rag_m2.retriever.sql_retriever import SqlRetriever
    from rag_m2.settings import settings
    from rag_m2.storage.vector_store import SqliteStore

    return build_agent(
        generate, generate_json, Embedder(), SqliteStore(settings.vector_db), SqlRetriever(generate_json), settings.top_k
    )


class RagApp(App):
    TITLE = "Warhammer 40k RAG"
    CSS = """
    #chat { width: 2fr; padding: 0 1; }
    #trace { width: 1fr; border-left: solid $primary; }
    .user { color: $success; text-style: bold; margin-top: 1; }
    """
    BINDINGS = [
        ("ctrl+n", "new_chat", "New conversation"),
        ("ctrl+t", "toggle_trace", "Toggle trace"),
        ("ctrl+q", "quit", "Quit"),
    ]

    def __init__(self, agent_factory=default_agent) -> None:
        super().__init__()
        self.agent_factory, self.agent, self.thread = agent_factory, None, str(uuid.uuid4())

    def compose(self) -> ComposeResult:
        yield Header()
        with Horizontal():
            yield VerticalScroll(id="chat")
            yield RichLog(id="trace", wrap=True, markup=True)
        yield Input(placeholder="Loading models...", disabled=True)
        yield Footer()

    def on_mount(self) -> None:
        self.load_agent()

    @work(thread=True)
    def load_agent(self) -> None:
        self.agent = self.agent_factory()
        self.call_from_thread(self.ready)

    def ready(self) -> None:
        box = self.query_one(Input)
        box.disabled, box.placeholder = False, "Ask a question..."
        box.focus()

    def on_input_submitted(self, event: Input.Submitted) -> None:
        q = event.value.strip()
        if not q or self.agent is None:
            return
        event.input.value, event.input.disabled = "", True
        chat = self.query_one("#chat")
        chat.mount(Markdown(f"**you >** {q}", classes="user"))
        chat.scroll_end()
        self.ask(q)

    @work(thread=True, exclusive=True)
    def ask(self, q: str) -> None:
        try:
            state = self.agent.invoke({"messages": [HumanMessage(q)]}, {"configurable": {"thread_id": self.thread}})
        except Exception as e:
            state = {"messages": [HumanMessage(f"**Error:** {e}")], "route": "error", "query": q}
        self.call_from_thread(self.show, state)

    def show(self, state: dict) -> None:
        chat = self.query_one("#chat")
        chat.mount(Markdown(state["messages"][-1].content))
        chat.scroll_end()
        trace = self.query_one(RichLog)
        trace.write(f"[b]route[/b] {state.get('route')}\n[b]query[/b] {state.get('query')}")
        if state.get("sql"):
            trace.write(f"[b]sql[/b] {state['sql'].splitlines()[0]}")
        if state.get("sources"):
            trace.write("[b]sources[/b] " + "; ".join(dict.fromkeys(state["sources"])))
        trace.write("─" * 30)
        box = self.query_one(Input)
        box.disabled = False
        box.focus()

    def action_new_chat(self) -> None:
        self.thread = str(uuid.uuid4())
        self.query_one("#chat").remove_children()
        self.query_one(RichLog).write("[dim]new conversation[/dim]")

    def action_toggle_trace(self) -> None:
        trace = self.query_one(RichLog)
        trace.display = not trace.display


if __name__ == "__main__":
    RagApp().run()
