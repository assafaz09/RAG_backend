from typing import List
from openai import OpenAI
from app.core.config import settings
import asyncio

# Handle missing API key gracefully
try:
    client = OpenAI(api_key=settings.OPENAI_API_KEY)
except Exception:
    client = None

async def embed_texts(texts: List[str]) -> List[List[float]]:
    if not texts:
        return []
    if client is None:
        return []
    
    # Run the blocking OpenAI call in thread pool
    loop = asyncio.get_event_loop()
    resp = await loop.run_in_executor(None, lambda: client.embeddings.create(model=settings.EMBEDDING_MODEL, input=texts))
    return [r.embedding for r in resp.data]

def embed_texts_sync(texts: List[str]) -> List[List[float]]:
    """Sync version for backward compatibility"""
    if not texts:
        return []
    if client is None:
        return []
    resp = client.embeddings.create(model=settings.EMBEDDING_MODEL, input=texts)
    return [r.embedding for r in resp.data]

# Helper function that Routes is looking for
async def generate_embedding(text: str) -> List[float]:
    if not text:
        return []
    # We simply use the existing function and send it a list with one item
    embeddings = await embed_texts([text])
    return embeddings[0] if embeddings else []