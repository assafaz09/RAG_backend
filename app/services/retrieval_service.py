from typing import List
from app.db.vector_db import get_qdrant_client  # חסר היה
from app.core.config import settings

def retrieve(query_vector: List[float], top_k: int = 5):
    client = get_qdrant_client()
    try:
        # הדפסת דיבאג לוודא שהגענו לכאן
        print(f"DEBUG: Searching Qdrant collection: {settings.QDRANT_COLLECTION}")
        
        hits = client.search(
            collection_name=settings.QDRANT_COLLECTION,
            query_vector=query_vector,
            limit=top_k,
            with_payload=True
        )
        
        # הדפסה של מה שמצאנו (או לא מצאנו)
        print(f"DEBUG: Qdrant returned {len(hits)} hits")
        for i, hit in enumerate(hits):
            print(f"DEBUG: Hit {i} - Score: {hit.score}")
            
        return hits
    except Exception as e:
        print(f"DEBUG: !! Qdrant Search Error: {str(e)}")
        return []