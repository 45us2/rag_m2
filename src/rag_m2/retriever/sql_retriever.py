"""Text-to-SQL retriever over wahadb.sqlite (read-only)."""

import logging
import re
import sqlite3
from collections.abc import Callable
from dataclasses import dataclass

from rag_m2.settings import settings

log = logging.getLogger(__name__)

SYSTEM = """You write SQLite queries for a Warhammer 40,000 rules database.
Return JSON: {"sql": "<one SELECT query>"}.
Rules:
- Only a single SELECT (or WITH ... SELECT) statement. Use SELECT DISTINCT: many rows are duplicated across sources.
- All columns are TEXT; match names with LIKE '%...%' (case-insensitive), never exact equality on names.
- Join with the documented id columns. Prefer returning name + the relevant columns, not SELECT *.
- Abilities of a unit: core/faction abilities (Lone Operative, Leader, Deep Strike, Battle Focus...) are linked by datasheets_abilities.abilityId -> abilities.Id (name in abilities.name, da.name is empty); datasheet-specific abilities have their name in datasheets_abilities.name. Use LEFT JOIN abilities and COALESCE(NULLIF(da.name, ''), a.name).
- To check if a unit has something, list what it has rather than filtering on the thing (an empty result is ambiguous).
- Add LIMIT {max_rows}.

DATA DICTIONARY:
{dictionary}"""


@dataclass
class SqlResult:
    sql: str
    columns: list[str]
    rows: list[tuple]
    error: str | None = None

    def to_text(self) -> str:
        if self.error:
            return f"SQL error: {self.error}\nQuery: {self.sql}"
        if not self.rows:
            return f"Query: {self.sql}\n(no rows)"
        lines = [" | ".join(self.columns)] + [" | ".join(map(str, r)) for r in self.rows]
        return f"Query: {self.sql}\n" + "\n".join(lines)


def _clean(value, max_len: int) -> str:
    text = re.sub(r"<[^>]+>", " ", str(value or ""))
    try:  # fix mojibake (utf-8 read as latin-1), e.g. "TÃ¢â‚¬â„¢au" -> "T’au"
        text = text.encode("latin-1").decode("utf-8")
    except UnicodeError:
        pass
    text = re.sub(r"\s+", " ", text).strip()
    return text if len(text) <= max_len else text[:max_len] + "…"


class SqlRetriever:
    def __init__(self, llm: Callable[..., dict]) -> None:
        self.llm = llm  # generate_json(prompt, system)
        self.db = sqlite3.connect(f"file:{settings.sql_db_path.as_posix()}?mode=ro", uri=True, check_same_thread=False)
        dictionary = settings.sql_dictionary_path.read_text(encoding="utf-8")
        self.system = SYSTEM.replace("{dictionary}", dictionary).replace("{max_rows}", str(settings.sql_max_rows))

    def run(self, sql: str) -> SqlResult:
        if not re.match(r"^\s*(select|with)\b", sql, re.I) or ";" in sql.strip().rstrip(";"):
            return SqlResult(sql, [], [], "only a single SELECT is allowed")
        try:
            cur = self.db.execute(sql.strip().rstrip(";"))
            rows = [tuple(_clean(v, settings.sql_max_cell_length) for v in r) for r in cur.fetchmany(settings.sql_max_rows)]
            return SqlResult(sql, [d[0] for d in cur.description], rows)
        except sqlite3.Error as e:
            return SqlResult(sql, [], [], str(e))

    def retrieve(self, question: str, retries: int = 2) -> SqlResult:
        prompt, result = f"Question: {question}", None
        for _ in range(retries + 1):
            try:
                sql = self.llm(prompt, self.system).get("sql", "")
            except Exception as e:  # LLM/JSON failure: report it instead of crashing the agent
                return SqlResult("", [], [], f"SQL generation failed: {e}")
            result = self.run(sql)
            log.info("sql: %s -> %s rows (%s)", sql, len(result.rows), result.error)
            if not result.error and result.rows:
                return result
            prompt = f"Question: {question}\nYour previous query:\n{sql}\nfailed or returned no rows ({result.error}). Fix it (e.g. broader LIKE, other table)."
        return result

    def close(self) -> None:
        self.db.close()
