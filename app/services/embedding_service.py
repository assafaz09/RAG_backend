from typing import List
from openai import OpenAI
from app.core.config import settings

client = OpenAI(api_key=settings.OPENAI_API_KEY)


def embed_texts(texts: List[str]) -> List[List[float]]:
    if not texts:
        return []
    resp = client.embeddings.create(model=settings.EMBEDDING_MODEL, input=texts)
    return [r.embedding for r in resp.data]
