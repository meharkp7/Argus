"""Application configuration loaded from environment variables."""

from functools import lru_cache
from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict

PROJECT_ROOT = Path(__file__).resolve().parents[2]
DATA_DIR = PROJECT_ROOT / "data"
CORPUS_DIR = PROJECT_ROOT / "backend" / "rag" / "corpus"
PLANT_LAYOUT_PATH = DATA_DIR / "plant_layout" / "plant_map.geojson"
SCENARIO_PATH = DATA_DIR / "simulation" / "scenarios" / "compound_risk_scenario.json"
RISK_GRAPH_SCHEMA_PATH = PROJECT_ROOT / "backend" / "risk_graph" / "graph_schema.json"
LEDGER_DB_PATH = DATA_DIR / "ledger" / "evidence.db"
VECTOR_STORE_PATH = DATA_DIR / "vector_store"
FEEDBACK_DB_PATH = DATA_DIR / "trust_calibration" / "feedback.db"


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    app_name: str = "ARGUS"
    app_version: str = "1.0.0"
    debug: bool = False

    api_host: str = "0.0.0.0"
    api_port: int = 8000
    cors_origins: list[str] = ["http://localhost:5173", "http://localhost:3000"]

    anthropic_api_key: str | None = None
    anthropic_model: str = "claude-sonnet-4-20250514"

    embedding_model: str = "all-MiniLM-L6-v2"
    rag_top_k: int = 5
    rag_min_similarity: float = 0.35

    sensor_zscore_threshold: float = 2.5
    sensor_ewma_alpha: float = 0.3
    sensor_baseline_window: int = 60
    isolation_forest_contamination: float = 0.05

    alert_confidence_high: float = 0.85
    alert_confidence_medium: float = 0.65
    compound_risk_threshold: float = 0.70

    simulation_tick_interval_seconds: float = 1.0
    weather_api_url: str = "https://api.open-meteo.com/v1/forecast"

    ledger_batch_size: int = 100


@lru_cache
def get_settings() -> Settings:
    return Settings()
