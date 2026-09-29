from pathlib import Path
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    workspace_root: Path = Path("artifacts")
    shortener_repo_root: Path = Path("../shortener-service")
    shortener_base_url: str = "http://localhost:8080"
    ollama_url: str = "http://localhost:11434"
    ollama_model: str = "qwen2.5-coder:7b"
    llm_enabled: bool = False
    live_service_validation: bool = False
    max_agent_retries: int = 2
    auto_approve_low_risk: bool = True
    run_maven_validation: bool = False
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")


settings = Settings()
