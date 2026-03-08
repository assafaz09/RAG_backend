from app.db.vector_db import get_qdrant_client
from app.core.config import settings

def retrieve(query_vector: list[float], top_k: int = 5):
    client = get_qdrant_client()
    
    try:
        print(f"DEBUG: Executing retrieval on {settings.QDRANT_COLLECTION}")
        
        # שימוש ב-query_points שהיא המתודה החדשה והיציבה יותר בגרסאות 1.10+
        # היא מחליפה את search ומיועדת בדיוק למקרים כאלו
        response = client.query_points(
            collection_name=settings.QDRANT_COLLECTION,
            query=query_vector,
            limit=top_k,
            with_payload=True
        )
        
        # חילוץ הטקסט מהנקודות שחזרו
        results = [hit.payload.get("text", "") for hit in response.points if hit.payload]
        print(f"DEBUG: Successfully found {len(results)} hits")
        return results

    except Exception as e:
        print(f"DEBUG: query_points failed, trying manual search: {e}")
        try:
            # ניסיון אחרון עם קריאה דינמית למתודה
            search_method = getattr(client, "search")
            hits = search_method(
                collection_name=settings.QDRANT_COLLECTION,
                query_vector=query_vector,
                limit=top_k,
                with_payload=True
            )
            return [hit.payload.get("text", "") for hit in hits if hit.payload]
        except Exception as final_e:
            print(f"DEBUG: !! All retrieval attempts failed: {final_e}")
            return []