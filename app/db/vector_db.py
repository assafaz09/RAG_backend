import qdrant_client
from qdrant_client import QdrantClient # שורה זו פותרת את השגיאה שלך!
from qdrant_client.http import models as rest
from app.core.config import settings
from typing import Any, Optional

_client: Optional[QdrantClient] = None

def get_qdrant_client() -> QdrantClient:
    global _client
    if _client is None:
        # אתחול הלקוח
        _client = QdrantClient(
            url=settings.QDRANT_URL, 
            api_key=settings.QDRANT_API_KEY
        )
        ensure_collection(_client, settings.QDRANT_COLLECTION)
    return _client

def ensure_collection(client: QdrantClient, name: str):
    try:
        collections = client.get_collections().collections
        if not any(c.name == name for c in collections):
            client.create_collection(
                collection_name=name,
                vectors_config=rest.VectorParams(size=1536, distance=rest.Distance.COSINE),
            )
    except Exception as e:
        print(f"DEBUG: Collection check error: {e}")