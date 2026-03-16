from pydantic_settings import BaseSettings
from typing import Optional
import os
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()


class Settings(BaseSettings):
    model_config = {"extra": "ignore"}
    APP_NAME: str = "rag-ai-system"
    PYTHON_ENV: str = "development"

    OPENAI_API_KEY: Optional[str] = None
    QDRANT_URL: str = "http://localhost:6333"
    QDRANT_API_KEY: Optional[str] = None
    QDRANT_COLLECTION: str = "rag_collection"

    EMBEDDING_MODEL: str = "text-embedding-3-small"
    LLM_MODEL: str = "gpt-4o-mini"

    # Database settings
    DATABASE_URL: str = "postgresql://user:password@localhost/rag_ai_db"

    # JWT settings
    JWT_SECRET_KEY: str = "your-super-secret-jwt-key-change-in-production"
    JWT_ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 30

    # Elasticsearch settings
    ELASTICSEARCH_URL: str = "http://localhost:9200"
    ELASTICSEARCH_INDEX: str = "rag_documents"

    # Hybrid search settings
    HYBRID_SEARCH_VECTOR_WEIGHT: float = 0.5
    HYBRID_SEARCH_KEYWORD_WEIGHT: float = 0.5
    HYBRID_SEARCH_TOP_K: int = 10


settings = Settings()
