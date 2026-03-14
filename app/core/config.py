from functools import lru_cache
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    database_url: str = "postgresql://credituser:creditpass@localhost:5432/creditdb"
    upload_dir:   str = "./uploads"
    environment:  str = "development"
    ocr_min_chars: int = 50

    ollama_base_url: str = "http://localhost:11434"
    ollama_model:    str = "llama3.1:8b"

    min_credit_score:             int   = 500
    min_monthly_income:           float = 5000.0
    min_banking_seniority_months: int   = 6
    max_debt_to_income_ratio:     float = 0.4


@lru_cache
def get_settings() -> Settings:
    return Settings()
