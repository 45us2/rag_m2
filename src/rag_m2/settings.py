"""Global settings loaded from environment variables / .env (singleton)."""

from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict

ROOT = Path(__file__).resolve().parents[2]
DATA = ROOT / "data"


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=ROOT / ".env", extra="ignore")

    google_api_key: str = ""
    llm_model: str = "gemini-3.5-flash-lite"
    llm_requests_per_minute: int = 10
    embedding_model: str = "BAAI/bge-small-en-v1.5"

    pdf_path: Path = DATA / "raw" / "Core Rules.pdf"
    markdown_path: Path = DATA / "processed" / "core_rules.md"
    vector_db: Path = DATA / "vectors.db"
    sql_db_path: Path = DATA / "raw" / "wahadb.sqlite"
    sql_dictionary_path: Path = DATA / "raw" / "SQL_AGENT_DATA_DICTIONARY.md"

    chunk_size: int = 1000
    chunk_overlap: int = 150
    chunk_min_size: int = 300
    top_k: int = 5
    sql_max_rows: int = 30
    sql_max_cell_length: int = 2000


settings = Settings()
