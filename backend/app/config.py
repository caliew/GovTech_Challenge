import os
from pydantic_settings import BaseSettings, SettingsConfigDict

class Settings(BaseSettings):
    ENVIRONMENT: str = "development"
    PORT: int = 8000
    HOST: str = "0.0.0.0"
    DATABASE_URL: str = "sqlite:///./policy_data.db"
    LLM_PROVIDER: str = "mock"  # mock, openai, gemini, fallback
    OPENAI_API_KEY: str = ""
    GEMINI_API_KEY: str = ""

    # Load from the .env file located at the workspace root
    model_config = SettingsConfigDict(
        env_file=os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))), ".env"),
        env_file_encoding="utf-8",
        extra="ignore"
    )

settings = Settings()
