from pydantic.v1 import BaseSettings
from typing import Optional


class Settings(BaseSettings):
    APP_NAME: str = "rag-ai-system"
    PYTHON_ENV: str = "development"

    OPENAI_API_KEY: Optional[str] = None
    QDRANT_URL: str = "http://localhost:6333"
    QDRANT_API_KEY: Optional[str] = None
    QDRANT_COLLECTION: str = "rag_collection"

    EMBEDDING_MODEL: str = "text-embedding-3-small"
    LLM_MODEL: str = "gpt-4o-mini"

    class Config:
        env_file = ".env"


settings = Settings()
