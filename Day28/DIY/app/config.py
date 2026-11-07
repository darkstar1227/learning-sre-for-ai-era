"""
Configuration for Day28 DIY project.
"""
from pathlib import Path
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    """Settings for manifest validation and tracking."""

    # Manifest directory
    manifest_dir: str = "manifests"

    # Example settings for documentation
    example_team_name: str = "platform-team"

    class Config:
        env_file = ".env"
        case_sensitive = False


def get_settings() -> Settings:
    """Get application settings."""
    return Settings()


def ensure_manifest_dir() -> Path:
    """Ensure manifest directory exists."""
    settings = get_settings()
    path = Path(settings.manifest_dir)
    path.mkdir(parents=True, exist_ok=True)
    return path
