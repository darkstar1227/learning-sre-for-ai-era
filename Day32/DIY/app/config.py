"""Configuration and environment loading."""

from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    """Application settings from environment variables."""

    # Service
    service_name: str = "answer-api"
    service_version: str = "0.1.0"
    debug: bool = False

    # Observability: Langfuse (if using Langfuse)
    langfuse_base_url: str = ""
    langfuse_public_key: str = ""
    langfuse_secret_key: str = ""

    # Observability: OpenTelemetry Collector (if using Collector path)
    otel_collector_endpoint: str = "http://localhost:4317"

    # Observability mode: "langfuse", "collector", or "disabled"
    observability_mode: str = "disabled"

    # LLM Configuration (for testing/demo)
    gemini_api_key: str = ""
    model_name: str = "gemini-2.0-flash"

    # LangSmith (optional, for comparison)
    langsmith_api_key: str = ""
    langsmith_project: str = "learning-sre-for-ai-era"

    class Config:
        env_file = ".env"
        case_sensitive = False


settings = Settings()
