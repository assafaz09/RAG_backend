from typing import List
from openai import OpenAI
from app.core.config import settings

# Handle missing API key gracefully
try:
    client = OpenAI(api_key=settings.OPENAI_API_KEY)
except Exception:
    client = None

def embed_texts(texts: List[str]) -> List[List[float]]:
    if not texts:
        return []
    if client is None:
        return []
    resp = client.embeddings.create(model=settings.EMBEDDING_MODEL, input=texts)
    return [r.embedding for r in resp.data]

# פונקציית העזר החדשה שה-Routes מחפש
def generate_embedding(text: str) -> List[float]:
    if not text:
        return []
    # אנחנו פשוט משתמשים בפונקציה הקיימת ושולחים לה רשימה עם איבר אחד
    embeddings = embed_texts([text])
    return embeddings[0] if embeddings else []