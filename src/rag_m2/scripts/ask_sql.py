"""Try the text-to-SQL retriever alone."""

import logging
import sys

from rag_m2.llm.gemini import generate_json
from rag_m2.retriever.sql_retriever import SqlRetriever

if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format="%(name)s %(message)s")
    print(SqlRetriever(generate_json).retrieve(" ".join(sys.argv[1:]) or "Which Aeldari units have toughness 4?").to_text())
