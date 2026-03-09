from qdrant_client.http.models import PointStruct
from typing import List, Dict
import uuid
from app.services.embedding_service import embed_texts
from app.db.vector_db import get_qdrant_client
from app.core.config import settings

def ingest_documents(docs: List[Dict]):
    if not docs:
        return
    
    texts = [d["text"] for d in docs]
    vectors = embed_texts(texts)
    
    client = get_qdrant_client()
    
    points = []
    for i, (doc, vec) in enumerate(zip(docs, vectors)):
        payload = doc.get("meta") or {}
        payload["text"] = doc["text"]
        payload["filename"] = doc.get("filename", "unknown")
        
        point_id = str(uuid.uuid4()) 
        
        points.append(PointStruct(
            id=point_id,
            vector=vec,
            payload=payload
        ))
    
    try:
        client.upsert(
            collection_name=settings.QDRANT_COLLECTION,
            points=points
        )
    except Exception as e:
        print(f"Error upserting to Qdrant: {e}")
        raise